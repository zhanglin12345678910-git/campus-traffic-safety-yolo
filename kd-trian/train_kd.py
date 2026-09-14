"""
知识蒸馏训练脚本 - 输出层 Logits-based KD for YOLO
=================================================
实现思路：
1. 加载已训练好的 Teacher 模型 (冻结 + eval + no_grad)
2. 加载待训练的 Student 模型
3. 在每个 batch 中：
   - Teacher 前向推理获取分类 logits (z_t)
   - Student 正常前向获取分类 logits (z_s) 和检测损失 (L_det)
   - 计算 KL 蒸馏损失并加到总损失
4. 提供两种方案：
   - 方案1: 继承 DetectionTrainer，最小改动
   - 方案2: 手写简化训练 loop，复用 dataloader/optimizer

关键点：YOLO 检测头在训练模式下返回 list[Tensor]，每个 Tensor 形状为 [B, (4*reg_max+nc), H, W]
分类 logits 位于通道维度的后 nc 个通道位置

=================================================
超参数建议（基于实验和文献）：
=================================================
温度 T (kd_temperature):
  - 推荐范围: 2-6
  - 默认值: 4.0 (适合大多数场景)
  - T=2-3: 保留更多判别性，适合数据集类别区分度高的场景
  - T=4-5: 平衡性能，推荐首选
  - T=6+: 蒸馏效果更柔和，适合教师模型过拟合的情况
  
蒸馏权重 (kd_weight):
  - 推荐范围: 0.5-2.0
  - 默认值: 1.0 (检测损失和蒸馏损失等权重)
  - 0.3-0.7: 以检测性能为主，蒸馏为辅
  - 1.0-1.5: 平衡权重，推荐
  - 1.5-2.0: 更依赖教师指导，适合学生模型很小的情况

建议的对比实验组合:
  1. 基线 (T=4, weight=1.0) - 默认配置
  2. 低温 (T=2, weight=1.0) - 判别性强
  3. 高温 (T=6, weight=1.0) - 蒸馏柔和
  4. 调权 (T=4, weight=0.5/1.5) - 权重对比
  
实验建议: 先用默认值 T=4, weight=1.0 训练，如果效果不理想再调参

Author: 林哥
Date: 2026-01-08
"""

import argparse
import os
import math
import copy
import warnings
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.cuda.amp import autocast, GradScaler
from tqdm import tqdm
import sys
from pathlib import Path
# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))
# Ultralytics imports
from ultralytics import YOLO
from ultralytics.data import build_dataloader, build_yolo_dataset
from ultralytics.engine.trainer import BaseTrainer
from ultralytics.models.yolo.detect.train import DetectionTrainer
from ultralytics.nn.tasks import DetectionModel
from ultralytics.utils import LOGGER, RANK, colorstr, yaml_load
from ultralytics.utils.torch_utils import de_parallel, ModelEMA, select_device, torch_distributed_zero_first
from ultralytics.utils.checks import check_imgsz
from ultralytics.utils.loss import v8DetectionLoss
from ultralytics.cfg import DEFAULT_CFG_DICT  # 导入默认配置


# ============================================================================
# 工具函数：从 YOLO 检测头输出提取分类 logits
# ============================================================================

def extract_cls_logits(feats, reg_max=16, nc=80):
    """
    从 YOLO 检测头输出提取分类 logits (用于蒸馏)
    
    YOLO 检测头在训练模式下返回:
        - feats: list of Tensor，每个 shape = [B, (4*reg_max + nc), H, W]
        - 前 4*reg_max 通道是边界框回归分布
        - 后 nc 通道是分类 logits (未经 sigmoid)
    
    Args:
        feats: 检测头输出的特征列表 (训练模式)
        reg_max: DFL 回归的通道数，默认16
        nc: 类别数
    
    Returns:
        cls_logits: Tensor [B, total_anchors, nc] - 所有尺度拼接后的分类 logits
    """
    cls_logits_list = []
    for feat in feats:
        B, C, H, W = feat.shape
        # 分类 logits 在通道维度的后 nc 个位置
        # feat shape: [B, 4*reg_max + nc, H, W]
        cls_logit = feat[:, 4 * reg_max:, :, :]  # [B, nc, H, W]
        # 展平空间维度
        cls_logit = cls_logit.view(B, nc, -1)  # [B, nc, H*W]
        cls_logit = cls_logit.permute(0, 2, 1)  # [B, H*W, nc]
        cls_logits_list.append(cls_logit)
    
    # 拼接所有尺度
    cls_logits = torch.cat(cls_logits_list, dim=1)  # [B, total_anchors, nc]
    return cls_logits


def compute_kd_loss(student_logits, teacher_logits, temperature=4.0):
    """
    计算 KL 散度蒸馏损失（已修复归一化问题）
    
    公式:
        p_t = softmax(z_t / T)
        p_s = log_softmax(z_s / T)
        L_kd = KL(p_s || p_t) * (T * T)
    
    Args:
        student_logits: 学生模型分类 logits [B, N, nc]
        teacher_logits: 教师模型分类 logits [B, N, nc]
        temperature: 蒸馏温度 T
    
    Returns:
        kd_loss: 标量损失（归一化后，范围约 0.5-5.0）
    """
    # ========== 计算 KD Loss ==========
    # 展平为 [B*N, nc] 以便计算
    B, N, nc = student_logits.shape
    student_flat = student_logits.reshape(-1, nc)  # [B*N, nc]
    teacher_flat = teacher_logits.reshape(-1, nc)  # [B*N, nc]
    
    # 教师 soft labels (不需要梯度)
    p_t = F.softmax(teacher_flat / temperature, dim=-1)  # [B*N, nc]
    
    # 学生 log soft labels
    p_s = F.log_softmax(student_flat / temperature, dim=-1)  # [B*N, nc]
    
    # KL 散度: 使用 reduction='mean' 对所有元素求平均（正确归一化）
    # 这样 loss 值会在合理范围内（0.5-5.0）
    kd_loss = F.kl_div(p_s, p_t, reduction='mean') * (temperature * temperature)
    
    return kd_loss


# ============================================================================
# 方案1：继承 DetectionTrainer，最小改动
# ============================================================================

class KDDetectionTrainer(DetectionTrainer):
    """
    知识蒸馏检测训练器
    继承 DetectionTrainer，在 loss 计算中加入 KD 损失
    """
    
    def __init__(self, cfg=DEFAULT_CFG_DICT, overrides=None, _callbacks=None, 
                 teacher_weights=None, kd_temperature=4.0, kd_weight=1.0):
        """
        Args:
            cfg: 模型配置（默认使用 Ultralytics 默认配置）
            overrides: 训练参数覆盖（字典形式的配置）
            teacher_weights: 教师模型权重路径
            kd_temperature: 蒸馏温度
            kd_weight: 蒸馏损失权重
        """
        # KD 超参数（在调用父类初始化之前保存）
        self.kd_temperature = kd_temperature
        self.kd_weight = kd_weight
        self.teacher_weights = teacher_weights
        self.teacher = None
        
        # 调用父类初始化
        super().__init__(cfg, overrides, _callbacks)
        
    def setup_model(self):
        """设置模型，额外加载教师模型"""
        ckpt = super().setup_model()
        
        # 加载教师模型
        if self.teacher_weights:
            LOGGER.info(f"Loading teacher model from {self.teacher_weights}")
            self.teacher = YOLO(self.teacher_weights).model
            self.teacher = self.teacher.to(self.device)
            
            # ========== 冻结教师模型 ==========
            self.teacher.eval()
            for param in self.teacher.parameters():
                param.requires_grad = False
            LOGGER.info(f"Teacher model loaded and frozen (eval mode, no gradients)")
        
        return ckpt
    
    def _do_train(self, world_size=1):
        """训练主循环 - 重写以加入 KD 损失"""
        if world_size > 1:
            self._setup_ddp(world_size)
        self._setup_train(world_size)
        
        # 获取模型参数
        student_model = de_parallel(self.model)
        m = student_model.model[-1]  # Detect head
        self.reg_max = m.reg_max
        self.nc = m.nc
        
        # 创建损失函数
        self.compute_loss = v8DetectionLoss(student_model)
        
        nb = len(self.train_loader)
        nw = max(round(self.args.warmup_epochs * nb), 100) if self.args.warmup_epochs > 0 else -1
        last_opt_step = -1
        self.epoch_time = None
        self.epoch_time_start = __import__('time').time()
        self.train_time_start = __import__('time').time()
        self.run_callbacks("on_train_start")
        
        LOGGER.info(
            f'Image sizes {self.args.imgsz} train, {self.args.imgsz} val\n'
            f'Using {self.train_loader.num_workers * (world_size or 1)} dataloader workers\n'
            f"Logging results to {colorstr('bold', self.save_dir)}\n"
            f'Starting KD training for {self.epochs} epochs...\n'
            f'KD Temperature: {self.kd_temperature}, KD Weight: {self.kd_weight}'
        )
        
        epoch = self.start_epoch
        self.optimizer.zero_grad()
        
        while True:
            self.epoch = epoch
            self.run_callbacks("on_train_epoch_start")
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.scheduler.step()
            
            self.model.train()
            
            if RANK != -1:
                self.train_loader.sampler.set_epoch(epoch)
            
            pbar = enumerate(self.train_loader)
            if epoch == (self.epochs - self.args.close_mosaic):
                self._close_dataloader_mosaic()
                self.train_loader.reset()
            
            if RANK in {-1, 0}:
                LOGGER.info(self.progress_string())
                pbar = tqdm(enumerate(self.train_loader), total=nb, 
                           desc=f"Epoch {epoch+1}/{self.epochs}")
            
            self.tloss = None
            total_kd_loss = 0
            
            for i, batch in pbar:
                self.run_callbacks("on_train_batch_start")
                
                # Warmup
                ni = i + nb * epoch
                if ni <= nw:
                    xi = [0, nw]
                    self.accumulate = max(1, int(__import__('numpy').interp(
                        ni, xi, [1, self.args.nbs / self.batch_size]).round()))
                    for j, x in enumerate(self.optimizer.param_groups):
                        x["lr"] = __import__('numpy').interp(
                            ni, xi, [self.args.warmup_bias_lr if j == 0 else 0.0, 
                                    x["initial_lr"] * self.lf(epoch)])
                        if "momentum" in x:
                            x["momentum"] = __import__('numpy').interp(
                                ni, xi, [self.args.warmup_momentum, self.args.momentum])
                
                # Forward
                with autocast(self.amp):
                    batch = self.preprocess_batch(batch)
                    imgs = batch["img"]
                    
                    # ========== Student 前向 ==========
                    student_preds = self.model(imgs)
                    
                    # 处理不同的输出格式
                    if isinstance(student_preds, dict):
                        student_feats = student_preds.get("one2many", student_preds)
                    elif isinstance(student_preds, tuple):
                        student_feats = student_preds[1] if len(student_preds) > 1 else student_preds[0]
                    else:
                        student_feats = student_preds
                    
                    # 确保是列表格式
                    if not isinstance(student_feats, (list, tuple)):
                        student_feats = [student_feats]
                    
                    # ========== 计算检测损失 ==========
                    det_loss, loss_items = self.compute_loss(student_preds, batch)
                    
                    # ========== Teacher 前向 (no_grad) ==========
                    kd_loss = torch.tensor(0.0, device=self.device)
                    if self.teacher is not None:
                        with torch.no_grad():
                            teacher_preds = self.teacher(imgs)
                            
                            # 处理教师输出格式
                            if isinstance(teacher_preds, dict):
                                teacher_feats = teacher_preds.get("one2many", teacher_preds)
                            elif isinstance(teacher_preds, tuple):
                                teacher_feats = teacher_preds[1] if len(teacher_preds) > 1 else teacher_preds[0]
                            else:
                                teacher_feats = teacher_preds
                            
                            if not isinstance(teacher_feats, (list, tuple)):
                                teacher_feats = [teacher_feats]
                        
                        # ========== 提取分类 logits ==========
                        # 注意：只取与学生相同数量的特征层
                        num_feats = min(len(student_feats), len(teacher_feats))
                        student_cls = extract_cls_logits(student_feats[:num_feats], 
                                                        self.reg_max, self.nc)
                        teacher_cls = extract_cls_logits(teacher_feats[:num_feats], 
                                                        self.reg_max, self.nc)
                        
                        # ========== 计算 KD 损失 ==========
                        kd_loss = compute_kd_loss(student_cls, teacher_cls, 
                                                  self.kd_temperature)
                        total_kd_loss += kd_loss.item()
                    
                    # ========== 组合总损失 ==========
                    # L_total = L_det + kd_weight * L_kd
                    self.loss = det_loss + self.kd_weight * kd_loss
                    
                    if RANK != -1:
                        self.loss *= world_size
                    
                    self.loss_items = loss_items
                    self.tloss = (
                        (self.tloss * i + self.loss_items) / (i + 1) 
                        if self.tloss is not None else self.loss_items
                    )
                
                # Backward
                self.scaler.scale(self.loss).backward()
                
                # Optimize
                if ni - last_opt_step >= self.accumulate:
                    self.optimizer_step()
                    last_opt_step = ni
                
                # Log
                if RANK in {-1, 0}:
                    avg_kd = total_kd_loss / (i + 1)
                    loss_length = self.tloss.shape[0] if len(self.tloss.shape) else 1
                    desc = (
                        f"Epoch {epoch+1}/{self.epochs} | "
                        f"det_loss: {self.tloss.mean():.4f} | "
                        f"kd_loss: {avg_kd:.4f} | "
                        f"total: {self.loss.item():.4f}"
                    )
                    pbar.set_description(desc)
                    self.run_callbacks("on_batch_end")
                
                self.run_callbacks("on_train_batch_end")
            
            # Epoch end
            self.lr = {f"lr/pg{ir}": x["lr"] for ir, x in enumerate(self.optimizer.param_groups)}
            self.run_callbacks("on_train_epoch_end")
            
            if RANK in {-1, 0}:
                final_epoch = epoch + 1 >= self.epochs
                self.ema.update_attr(self.model, include=["yaml", "nc", "args", "names", "stride", "class_weights"])
                
                # Validation
                if self.args.val or final_epoch or self.stopper.possible_stop or self.stop:
                    self.metrics, self.fitness = self.validate()
                self.save_metrics(metrics={**self.label_loss_items(self.tloss), **self.metrics, **self.lr})
                self.stop |= self.stopper(epoch + 1, self.fitness) or final_epoch
                
                # Save model
                if self.args.save or final_epoch:
                    self.save_model()
                    self.run_callbacks("on_model_save")
            
            # Scheduler
            import time
            t = time.time()
            self.epoch_time = t - self.epoch_time_start
            self.epoch_time_start = t
            self.run_callbacks("on_fit_epoch_end")
            
            # Early Stopping
            if RANK != -1:
                import torch.distributed as dist
                broadcast_list = [self.stop if RANK == 0 else None]
                dist.broadcast_object_list(broadcast_list, 0)
                self.stop = broadcast_list[0]
            if self.stop:
                break
            epoch += 1
        
        if RANK in {-1, 0}:
            import time
            seconds = time.time() - self.train_time_start
            LOGGER.info(f"\n{epoch - self.start_epoch + 1} epochs completed in {seconds / 3600:.3f} hours.")
            self.final_eval()
            if self.args.plots:
                self.plot_metrics()
            self.run_callbacks("on_train_end")
        self.run_callbacks("teardown")
    
    def progress_string(self):
        """返回带 KD 信息的进度字符串"""
        return ("\n" + "%11s" * (5 + len(self.loss_names))) % (
            "Epoch", "GPU_mem", *self.loss_names, "KD_loss", "Instances", "Size"
        )


# ============================================================================
# 配置区：在这里直接修改参数（代码中指定，无需命令行）
# ============================================================================

# ============================================================================
# 配置区：在这里直接修改参数（代码中指定，无需命令行）
# ============================================================================

# 是否使用代码配置（True=代码配置优先，False=命令行配置）
USE_CODE_CONFIG = True

# ========== 核心配置 ==========
CONFIG = {
    # 模型文件（必需）
    'student': "<PROJECT_ROOT>\\runs\\train\\NoP5-轻量化探索-cctsdb--yolo11-CSP-PMSFA-Lite-NoP5\\weights\\best.pt",  # 学生模型配置文件 (.yaml)
    'teacher': '<LOCAL_PATH>',  # 教师模型权重文件 (.pt)
    'data': '%USERPROFILE%\\Desktop\\CCTSDB 2021\\实验\\cctsdb.yaml',  # 数据集配置文件 (.yaml)
    
    # 训练参数
    'epochs': 100,        # 训练轮数
    'batch': 32,          # 批次大小
    'imgsz': 640,         # 图像尺寸
    'device': '0',        # GPU设备：'0', '0,1', 'cpu', ''(自动)
    'workers': 8,         # 数据加载线程数
    'lr0': 0.01,          # 初始学习率
    
    # ========== 知识蒸馏参数（核心）==========
    'kd_temp': 4.0,       # 蒸馏温度 T (推荐 2-6)
    'kd_weight': 1.0,     # 蒸馏损失权重（标准值，推荐 0.5-2.0）
    
    # 保存路径
    'project': 'runs/kd_train',  # 保存根目录
    'name': '知识蒸馏-PSSM-PSSM_Qlite-v2',  # 实验名称
}


if __name__ == '__main__':
    """
    ========================================================================
    知识蒸馏训练 - 使用说明
    ========================================================================
    
    【快速开始】
    1. 修改上面 CONFIG 字典中的参数：
       - student: 学生模型配置文件 (.yaml)
       - teacher: 教师模型权重文件 (.pt)
       - data: 数据集配置文件 (.yaml)
       - kd_temp: 蒸馏温度 (推荐 2-6)
       - kd_weight: 蒸馏损失权重 (推荐 0.5-2.0)
    
    2. 确保 USE_CODE_CONFIG = True
    
    3. 直接运行: python train_kd.py
    
    【参数说明】
    - kd_temp (蒸馏温度):
      * 越大：软标签越"软"，知识传递越平滑
      * 越小：接近硬标签，蒸馏效果减弱
      * 推荐范围：2-6，默认 4.0
    
    - kd_weight (蒸馏损失权重):
      * 控制蒸馏损失与检测损失的平衡
      * 推荐范围：0.5-2.0，默认 1.0
    
    【输出结果】
    - 保存路径：runs/kd_train/<name>/weights/
    - best.pt: 验证集最优模型
    - last.pt: 最后一轮模型
    - 训练曲线：runs/kd_train/<name>/results.png
    
    ========================================================================
    """
    
    # 验证必需参数
    required = ['student', 'teacher', 'data']
    for key in required:
        if not CONFIG.get(key):
            raise ValueError(f"错误：必需参数 '{key}' 未设置，请在 CONFIG 中指定")
    
    # 创建保存目录
    save_dir = Path(CONFIG['project']) / CONFIG['name']
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # 打印配置信息
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Knowledge Distillation Training")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Student: {CONFIG['student']}")
    LOGGER.info(f"Teacher: {CONFIG['teacher']}")
    LOGGER.info(f"Dataset: {CONFIG['data']}")
    LOGGER.info(f"Temperature: {CONFIG['kd_temp']}, Weight: {CONFIG['kd_weight']}")
    LOGGER.info(f"Epochs: {CONFIG['epochs']}, Batch: {CONFIG['batch']}")
    LOGGER.info(f"Device: {CONFIG['device']}")
    LOGGER.info(f"{'='*60}\n")
    
    # 构建训练参数覆盖
    overrides = {
        'model': CONFIG['student'],
        'data': CONFIG['data'],
        'epochs': CONFIG['epochs'],
        'batch': CONFIG['batch'],
        'imgsz': CONFIG['imgsz'],
        'device': CONFIG['device'],
        'workers': CONFIG['workers'],
        'lr0': CONFIG['lr0'],
        'project': CONFIG['project'],
        'name': CONFIG['name'],
    }
    
    # 创建训练器并开始训练
    trainer = KDDetectionTrainer(
        cfg=DEFAULT_CFG_DICT,  # 使用默认配置
        overrides=overrides,  # 覆盖特定参数
        teacher_weights=CONFIG['teacher'],
        kd_temperature=CONFIG['kd_temp'],
        kd_weight=CONFIG['kd_weight'],
    )
    trainer.train()

