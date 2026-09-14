"""
稀疏训练脚本 - BN层缩放因子稀疏化训练
=================================================
实现思路：
1. 在训练损失中加入BN层γ参数的L1正则化
2. 使网络自动抑制无效通道的γ值趋近于0
3. 为后续结构化剪枝提供依据

损失函数：
    L_sparse = L_det + λ * Σ(|γ|)

其中:
    - L_det: 原始YOLO检测损失
    - Σ(|γ|): 所有BN层缩放系数γ的L1范数之和
    - λ: 稀疏惩罚系数

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
# 工具函数：获取模型中所有BN层的gamma参数
# ============================================================================

def get_bn_layers(model):
    """
    获取模型中所有BatchNorm层
    
    Returns:
        bn_layers: list of nn.BatchNorm2d layers
    """
    bn_layers = []
    for name, module in model.named_modules():
        if isinstance(module, (nn.BatchNorm2d, nn.BatchNorm1d)):
            bn_layers.append((name, module))
    return bn_layers


def compute_bn_l1_loss(model):
    """
    计算所有BN层gamma参数的L1损失
    
    Args:
        model: 神经网络模型
    
    Returns:
        l1_loss: BN层gamma参数的L1范数之和
        num_params: gamma参数总数
    """
    l1_loss = 0.0
    num_params = 0
    
    for name, module in model.named_modules():
        if isinstance(module, (nn.BatchNorm2d, nn.BatchNorm1d)):
            # gamma 是 BN 层的 weight 参数
            if module.weight is not None:
                l1_loss += torch.sum(torch.abs(module.weight))
                num_params += module.weight.numel()
    
    return l1_loss, num_params


def analyze_bn_sparsity(model, threshold=0.01):
    """
    分析BN层gamma参数的稀疏程度
    
    Args:
        model: 神经网络模型
        threshold: 判断gamma是否为"零"的阈值
    
    Returns:
        stats: 稀疏统计信息字典
    """
    all_gammas = []
    zero_count = 0
    total_count = 0
    
    for name, module in model.named_modules():
        if isinstance(module, (nn.BatchNorm2d, nn.BatchNorm1d)):
            if module.weight is not None:
                gamma = module.weight.data.cpu().numpy()
                all_gammas.extend(gamma.flatten().tolist())
                zero_count += np.sum(np.abs(gamma) < threshold)
                total_count += gamma.size
    
    all_gammas = np.array(all_gammas)
    
    stats = {
        'total_channels': total_count,
        'zero_channels': zero_count,
        'sparsity_ratio': zero_count / total_count if total_count > 0 else 0,
        'gamma_min': np.min(all_gammas) if len(all_gammas) > 0 else 0,
        'gamma_max': np.max(all_gammas) if len(all_gammas) > 0 else 0,
        'gamma_mean': np.mean(np.abs(all_gammas)) if len(all_gammas) > 0 else 0,
        'gamma_std': np.std(all_gammas) if len(all_gammas) > 0 else 0,
    }
    
    return stats


# ============================================================================
# 稀疏训练器：继承 DetectionTrainer，添加BN稀疏正则化
# ============================================================================

class SparseTrainer(DetectionTrainer):
    """
    稀疏训练检测器
    继承 DetectionTrainer，在 loss 计算中加入 BN L1 稀疏损失
    """
    
    def __init__(self, cfg=DEFAULT_CFG_DICT, overrides=None, _callbacks=None, 
                 sparse_lambda=1e-4, sparse_warmup_epochs=5):
        """
        Args:
            cfg: 模型配置
            overrides: 训练参数覆盖
            sparse_lambda: BN稀疏惩罚系数λ
            sparse_warmup_epochs: 稀疏损失预热轮数（前几轮不加稀疏约束）
        """
        # 稀疏训练超参数
        self.sparse_lambda = sparse_lambda
        self.sparse_warmup_epochs = sparse_warmup_epochs
        
        # 调用父类初始化
        super().__init__(cfg, overrides, _callbacks)
    
    def _do_train(self, world_size=1):
        """训练主循环 - 重写以加入 BN 稀疏损失"""
        if world_size > 1:
            self._setup_ddp(world_size)
        self._setup_train(world_size)
        
        # 获取模型参数
        student_model = de_parallel(self.model)
        
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
            f'Starting Sparse training for {self.epochs} epochs...\n'
            f'Sparse Lambda: {self.sparse_lambda}, Warmup Epochs: {self.sparse_warmup_epochs}'
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
            total_sparse_loss = 0
            
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
                    preds = self.model(imgs)
                    
                    # ========== 计算检测损失 ==========
                    det_loss, loss_items = self.compute_loss(preds, batch)
                    
                    # ========== 计算BN稀疏损失 ==========
                    sparse_loss = torch.tensor(0.0, device=self.device)
                    
                    # 仅在预热阶段之后添加稀疏约束
                    if epoch >= self.sparse_warmup_epochs:
                        bn_l1_loss, num_bn_params = compute_bn_l1_loss(de_parallel(self.model))
                        sparse_loss = self.sparse_lambda * bn_l1_loss
                        total_sparse_loss += sparse_loss.item()
                    
                    # ========== 组合总损失 ==========
                    # L_sparse = L_det + λ * Σ(|γ|)
                    self.loss = det_loss + sparse_loss
                    
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
                    avg_sparse = total_sparse_loss / (i + 1) if epoch >= self.sparse_warmup_epochs else 0
                    desc = (
                        f"Epoch {epoch+1}/{self.epochs} | "
                        f"det_loss: {self.tloss.mean():.4f} | "
                        f"sparse_loss: {avg_sparse:.6f} | "
                        f"total: {self.loss.item():.4f}"
                    )
                    pbar.set_description(desc)
                    self.run_callbacks("on_batch_end")
                
                self.run_callbacks("on_train_batch_end")
            
            # ========== Epoch 结束：分析稀疏程度 ==========
            if RANK in {-1, 0}:
                stats = analyze_bn_sparsity(de_parallel(self.model))
                LOGGER.info(
                    f"\n[Sparsity Analysis] "
                    f"Total: {stats['total_channels']}, "
                    f"Near-Zero: {stats['zero_channels']}, "
                    f"Sparsity: {stats['sparsity_ratio']*100:.2f}%, "
                    f"|γ| mean: {stats['gamma_mean']:.4f}"
                )
            
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
        
        # ========== 训练结束：保存最终稀疏分析 ==========
        if RANK in {-1, 0}:
            import time
            seconds = time.time() - self.train_time_start
            LOGGER.info(f"\n{epoch - self.start_epoch + 1} epochs completed in {seconds / 3600:.3f} hours.")
            
            # 最终稀疏度分析
            final_stats = analyze_bn_sparsity(de_parallel(self.model))
            LOGGER.info(f"\n{'='*60}")
            LOGGER.info(f"Final Sparsity Analysis:")
            LOGGER.info(f"  Total Channels: {final_stats['total_channels']}")
            LOGGER.info(f"  Near-Zero Channels: {final_stats['zero_channels']}")
            LOGGER.info(f"  Sparsity Ratio: {final_stats['sparsity_ratio']*100:.2f}%")
            LOGGER.info(f"  |γ| Range: [{final_stats['gamma_min']:.4f}, {final_stats['gamma_max']:.4f}]")
            LOGGER.info(f"  |γ| Mean: {final_stats['gamma_mean']:.4f}")
            LOGGER.info(f"{'='*60}")
            
            self.final_eval()
            if self.args.plots:
                self.plot_metrics()
            self.run_callbacks("on_train_end")
        self.run_callbacks("teardown")
    
    def progress_string(self):
        """返回带稀疏信息的进度字符串"""
        return ("\n" + "%11s" * (5 + len(self.loss_names))) % (
            "Epoch", "GPU_mem", *self.loss_names, "Sparse", "Instances", "Size"
        )


# ============================================================================
# 配置区：在这里直接修改参数
# ============================================================================

CONFIG = {
    # ========== 模型文件（必需）==========
    'model': "<PROJECT_ROOT>\\runs\\train\\NoP5-轻量化探索-cctsdb--yolo11-CSP-PMSFA-Lite-NoP5\\weights\\best.pt",  # 学生模型配置文件
    'data': '%USERPROFILE%\\Desktop\\CCTSDB 2021\\实验\\cctsdb.yaml',  # 数据集配置文件
    
    # ========== 训练参数 ==========
    'epochs': 100,        # 训练轮数
    'batch': 32,          # 批次大小
    'imgsz': 640,         # 图像尺寸
    'device': '0',        # GPU设备
    'workers': 8,         # 数据加载线程数
    'lr0': 0.01,          # 初始学习率
    
    # ========== 稀疏训练参数（核心）==========
    'sparse_lambda': 1e-4,      # 稀疏惩罚系数λ (推荐 1e-5 ~ 1e-3)
                                # 值越大，稀疏化越强，但可能影响精度
    'sparse_warmup_epochs': 5,  # 前几轮不加稀疏约束（让网络先学习基本特征）
    
    # ========== 保存路径 ==========
    'project': 'runs/sparse_train',
    'name': 'PSSM-YOLO-Lite-稀疏训练',
}


if __name__ == '__main__':
    """
    ========================================================================
    稀疏训练 - 使用说明
    ========================================================================
    
    【训练流程】
    1. 稀疏训练（本脚本）→ 2. 结构化剪枝 → 3. 微调 → 4. 蒸馏增强
    
    【参数说明】
    - sparse_lambda: 稀疏惩罚系数
      * 1e-5: 轻度稀疏，精度损失小
      * 1e-4: 中度稀疏（推荐）
      * 1e-3: 强度稀疏，可能影响精度
    
    - sparse_warmup_epochs: 稀疏预热轮数
      * 让网络先学习基本特征，再引入稀疏约束
      * 推荐值：3-10 轮
    
    【输出结果】
    - 保存路径：runs/sparse_train/<name>/weights/
    - best.pt: 验证集最优的稀疏模型
    - last.pt: 最后一轮的稀疏模型
    
    【下一步】
    稀疏训练完成后，使用 prune_model.py 进行结构化剪枝
    
    ========================================================================
    """
    
    # 验证必需参数
    required = ['model', 'data']
    for key in required:
        if not CONFIG.get(key):
            raise ValueError(f"错误：必需参数 '{key}' 未设置")
    
    # 创建保存目录
    save_dir = Path(CONFIG['project']) / CONFIG['name']
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # 打印配置信息
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Sparse Training (BN L1 Regularization)")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Model: {CONFIG['model']}")
    LOGGER.info(f"Dataset: {CONFIG['data']}")
    LOGGER.info(f"Sparse Lambda: {CONFIG['sparse_lambda']}")
    LOGGER.info(f"Warmup Epochs: {CONFIG['sparse_warmup_epochs']}")
    LOGGER.info(f"Epochs: {CONFIG['epochs']}, Batch: {CONFIG['batch']}")
    LOGGER.info(f"{'='*60}\n")
    
    # 构建训练参数覆盖
    overrides = {
        'model': CONFIG['model'],
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
    trainer = SparseTrainer(
        cfg=DEFAULT_CFG_DICT,
        overrides=overrides,
        sparse_lambda=CONFIG['sparse_lambda'],
        sparse_warmup_epochs=CONFIG['sparse_warmup_epochs'],
    )
    trainer.train()
