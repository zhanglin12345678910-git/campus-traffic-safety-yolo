"""
剪枝后知识蒸馏训练脚本 - 蒸馏增强
=================================================
实现思路：
1. 加载已训练好的 Teacher 模型 (PSSM-YOLO高精度模型)
2. 加载剪枝/微调后的 Student 模型 (PSSM-YOLO-Lite)
3. 使用输出层分类logits蒸馏策略进行训练
4. 重点提升剪枝模型的召回率与mAP

损失函数：
    L_total = L_det + β * L_kd

其中:
    L_kd = T^2 * KL(p_t || p_s)
    p_t = softmax(z_t / T)
    p_s = softmax(z_s / T)

Author: 林哥
Date: 2026-01-29
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
import numpy as np
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ultralytics imports
from ultralytics import YOLO
from ultralytics.engine.trainer import BaseTrainer
from ultralytics.models.yolo.detect.train import DetectionTrainer
from ultralytics.nn.tasks import DetectionModel
from ultralytics.utils import LOGGER, RANK, colorstr
from ultralytics.utils.torch_utils import de_parallel, ModelEMA, select_device
from ultralytics.utils.loss import v8DetectionLoss
from ultralytics.cfg import DEFAULT_CFG_DICT


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
    计算 KL 散度蒸馏损失
    
    公式:
        p_t = softmax(z_t / T)
        p_s = log_softmax(z_s / T)
        L_kd = KL(p_s || p_t) * (T * T)
    
    Args:
        student_logits: 学生模型分类 logits [B, N, nc]
        teacher_logits: 教师模型分类 logits [B, N, nc]
        temperature: 蒸馏温度 T
    
    Returns:
        kd_loss: 标量损失
    """
    B, N, nc = student_logits.shape
    student_flat = student_logits.reshape(-1, nc)
    teacher_flat = teacher_logits.reshape(-1, nc)
    
    # 教师 soft labels
    p_t = F.softmax(teacher_flat / temperature, dim=-1)
    
    # 学生 log soft labels
    p_s = F.log_softmax(student_flat / temperature, dim=-1)
    
    # KL 散度
    kd_loss = F.kl_div(p_s, p_t, reduction='mean') * (temperature * temperature)
    
    return kd_loss


# ============================================================================
# 蒸馏增强训练器
# ============================================================================

class KDAfterPruneTrainer(DetectionTrainer):
    """
    剪枝后知识蒸馏训练器
    用于对剪枝/微调后的轻量化模型进行蒸馏增强
    """
    
    def __init__(self, cfg=DEFAULT_CFG_DICT, overrides=None, _callbacks=None, 
                 teacher_weights=None, kd_temperature=4.0, kd_weight=1.0):
        """
        Args:
            cfg: 模型配置
            overrides: 训练参数覆盖
            teacher_weights: 教师模型权重路径
            kd_temperature: 蒸馏温度
            kd_weight: 蒸馏损失权重
        """
        self.kd_temperature = kd_temperature
        self.kd_weight = kd_weight
        self.teacher_weights = teacher_weights
        self.teacher = None
        
        super().__init__(cfg, overrides, _callbacks)
        
    def setup_model(self):
        """设置模型，额外加载教师模型"""
        ckpt = super().setup_model()
        
        # 加载教师模型
        if self.teacher_weights:
            LOGGER.info(f"Loading teacher model from {self.teacher_weights}")
            self.teacher = YOLO(self.teacher_weights).model
            self.teacher = self.teacher.to(self.device)
            
            # 冻结教师模型
            self.teacher.eval()
            for param in self.teacher.parameters():
                param.requires_grad = False
            LOGGER.info(f"Teacher model loaded and frozen")
        
        return ckpt
    
    def _do_train(self, world_size=1):
        """训练主循环 - 加入 KD 损失"""
        if world_size > 1:
            self._setup_ddp(world_size)
        self._setup_train(world_size)
        
        # 获取模型参数
        student_model = de_parallel(self.model)
        m = student_model.model[-1]  # Detect head
        self.reg_max = getattr(m, 'reg_max', 16)
        self.nc = m.nc
        
        # 获取教师模型的参数（可能不同）
        if self.teacher is not None:
            teacher_m = self.teacher.model[-1]
            self.teacher_reg_max = getattr(teacher_m, 'reg_max', 16)
            self.teacher_nc = teacher_m.nc
            
            if self.nc != self.teacher_nc:
                LOGGER.warning(f"Teacher nc={self.teacher_nc} != Student nc={self.nc}")
        
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
            f'Starting KD training (after pruning) for {self.epochs} epochs...\n'
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
                    self.accumulate = max(1, int(np.interp(
                        ni, xi, [1, self.args.nbs / self.batch_size]).round()))
                    for j, x in enumerate(self.optimizer.param_groups):
                        x["lr"] = np.interp(
                            ni, xi, [self.args.warmup_bias_lr if j == 0 else 0.0, 
                                    x["initial_lr"] * self.lf(epoch)])
                        if "momentum" in x:
                            x["momentum"] = np.interp(
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
                    
                    if not isinstance(student_feats, (list, tuple)):
                        student_feats = [student_feats]
                    
                    # ========== 计算检测损失 ==========
                    det_loss, loss_items = self.compute_loss(student_preds, batch)
                    
                    # ========== Teacher 前向 (no_grad) ==========
                    kd_loss = torch.tensor(0.0, device=self.device)
                    if self.teacher is not None:
                        with torch.no_grad():
                            teacher_preds = self.teacher(imgs)
                            
                            if isinstance(teacher_preds, dict):
                                teacher_feats = teacher_preds.get("one2many", teacher_preds)
                            elif isinstance(teacher_preds, tuple):
                                teacher_feats = teacher_preds[1] if len(teacher_preds) > 1 else teacher_preds[0]
                            else:
                                teacher_feats = teacher_preds
                            
                            if not isinstance(teacher_feats, (list, tuple)):
                                teacher_feats = [teacher_feats]
                        
                        # ========== 提取分类 logits ==========
                        # 处理教师和学生检测头数量不同的情况
                        num_student_feats = len(student_feats)
                        num_teacher_feats = len(teacher_feats)
                        
                        if num_student_feats != num_teacher_feats:
                            # 学生模型(NoP5)有3个检测头，教师模型可能有4个
                            # 只对齐前几个尺度进行蒸馏
                            LOGGER.debug(f"Student feats: {num_student_feats}, Teacher feats: {num_teacher_feats}")
                            
                            # 对齐策略：根据特征图大小匹配
                            # 假设特征图按从大到小排列（P2, P3, P4 for student; P2, P3, P4, P5 for teacher）
                            num_feats = min(num_student_feats, num_teacher_feats)
                            
                            student_cls = extract_cls_logits(student_feats[:num_feats], 
                                                            self.reg_max, self.nc)
                            teacher_cls = extract_cls_logits(teacher_feats[:num_feats], 
                                                            self.teacher_reg_max, self.teacher_nc)
                        else:
                            student_cls = extract_cls_logits(student_feats, self.reg_max, self.nc)
                            teacher_cls = extract_cls_logits(teacher_feats, self.teacher_reg_max, self.teacher_nc)
                        
                        # 确保维度匹配
                        if student_cls.shape == teacher_cls.shape:
                            kd_loss = compute_kd_loss(student_cls, teacher_cls, self.kd_temperature)
                            total_kd_loss += kd_loss.item()
                        else:
                            LOGGER.warning(f"Shape mismatch: student {student_cls.shape}, teacher {teacher_cls.shape}")
                    
                    # ========== 组合总损失 ==========
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
# 配置区
# ============================================================================

CONFIG = {
    # ========== 模型文件（必需）==========
    # 学生模型：剪枝/微调后的轻量化模型
    'student': 'runs/finetune/PSSM-YOLO-Lite-微调/weights/best.pt',
    
    # 教师模型：高精度PSSM-YOLO模型
    'teacher': '<LOCAL_PATH>',
    
    # 数据集
    'data': '%USERPROFILE%\\Desktop\\CCTSDB 2021\\实验\\cctsdb.yaml',
    
    # ========== 训练参数 ==========
    'epochs': 50,          # 蒸馏轮数
    'batch': 32,           # 批次大小
    'imgsz': 640,          # 图像尺寸
    'device': '0',         # GPU设备
    'workers': 8,          # 数据加载线程数
    'lr0': 0.005,          # 初始学习率（适中）
    
    # ========== 知识蒸馏参数（核心）==========
    'kd_temp': 4.0,        # 蒸馏温度 T (推荐 2-6)
    'kd_weight': 1.0,      # 蒸馏损失权重 β (推荐 0.5-2.0)
    
    # ========== 保存路径 ==========
    'project': 'runs/kd_after_prune',
    'name': 'PSSM-YOLO-Lite-蒸馏增强',
}


if __name__ == '__main__':
    """
    ========================================================================
    剪枝后知识蒸馏增强 - 使用说明
    ========================================================================
    
    【训练流程】
    1. 稀疏训练 → 2. 结构化剪枝 → 3. 微调 → 4. 蒸馏增强（本脚本）
    
    【前置条件】
    - 需要先运行 finetune.py 完成微调
    - 或者直接使用剪枝后的模型进行蒸馏
    
    【蒸馏策略】
    - 使用高精度PSSM-YOLO作为教师模型
    - 对剪枝后的轻量化模型进行分类logits蒸馏
    - 重点提升召回率和mAP
    
    【参数说明】
    - kd_temp: 蒸馏温度
      * T=2-3: 保留更多判别性
      * T=4-5: 平衡性能（推荐）
      * T=6+: 蒸馏效果更柔和
    
    - kd_weight: 蒸馏损失权重
      * 0.5-0.7: 以检测损失为主
      * 1.0: 平衡权重（推荐）
      * 1.5-2.0: 更依赖教师指导
    
    【教师-学生检测头数量不同的处理】
    - 学生模型 (NoP5) 有 3 个检测头 (P2, P3, P4)
    - 教师模型可能有 4 个检测头 (P2, P3, P4, P5)
    - 脚本会自动对齐，只对共同尺度进行蒸馏
    
    【输出结果】
    - 保存路径：runs/kd_after_prune/<name>/weights/
    - best.pt: 最终的轻量化高性能模型
    
    ========================================================================
    """
    
    # 验证必需参数
    required = ['student', 'teacher', 'data']
    for key in required:
        if not CONFIG.get(key):
            raise ValueError(f"错误：必需参数 '{key}' 未设置")
    
    # 创建保存目录
    save_dir = Path(CONFIG['project']) / CONFIG['name']
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # 打印配置信息
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Knowledge Distillation After Pruning")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Student: {CONFIG['student']}")
    LOGGER.info(f"Teacher: {CONFIG['teacher']}")
    LOGGER.info(f"Dataset: {CONFIG['data']}")
    LOGGER.info(f"Temperature: {CONFIG['kd_temp']}, Weight: {CONFIG['kd_weight']}")
    LOGGER.info(f"Epochs: {CONFIG['epochs']}, Batch: {CONFIG['batch']}")
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
    trainer = KDAfterPruneTrainer(
        cfg=DEFAULT_CFG_DICT,
        overrides=overrides,
        teacher_weights=CONFIG['teacher'],
        kd_temperature=CONFIG['kd_temp'],
        kd_weight=CONFIG['kd_weight'],
    )
    trainer.train()
