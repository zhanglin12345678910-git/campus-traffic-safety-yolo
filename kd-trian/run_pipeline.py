"""
完整流程一键运行脚本 - 稀疏训练→剪枝→微调→蒸馏增强
=================================================
这个脚本整合了整个轻量化流程，可以一键执行：
1. 稀疏训练：对学生模型进行BN层L1正则化训练
2. 结构化剪枝：基于BN gamma值剪除冗余通道
3. 微调训练：恢复剪枝造成的精度损失
4. 蒸馏增强：使用教师模型进行知识蒸馏提升性能

Author: 林哥
Date: 2026-01-29
"""

import os
import sys
from pathlib import Path
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultralytics.utils import LOGGER


# ============================================================================
# 完整流程配置
# ============================================================================

PIPELINE_CONFIG = {
    # ========== 基础配置 ==========
    'student_model': 'yolo11-CSP-PMSFA-Lite-NoP5.yaml',  # 学生模型配置文件
    'teacher_model': '<LOCAL_PATH>',
    'data': '%USERPROFILE%\\Desktop\\CCTSDB 2021\\实验\\cctsdb.yaml',
    'device': '0',
    'workers': 8,
    'batch': 32,
    'imgsz': 640,
    
    # ========== 阶段1：稀疏训练 ==========
    'sparse': {
        'enabled': True,                    # 是否执行稀疏训练
        'epochs': 100,                      # 稀疏训练轮数
        'sparse_lambda': 1e-4,              # 稀疏惩罚系数
        'sparse_warmup_epochs': 5,          # 稀疏预热轮数
        'lr0': 0.01,
        'project': 'runs/pipeline',
        'name': '1_sparse_train',
    },
    
    # ========== 阶段2：结构化剪枝（使用torch-pruning真正剪枝）==========
    'prune': {
        'enabled': True,                    # 是否执行剪枝
        'prune_ratio': 0.3,                 # 剪枝率（真正删除30%通道）
        'save_dir': 'runs/pipeline/2_pruned',
    },
    
    # ========== 阶段3：微调训练 ==========
    'finetune': {
        'enabled': True,                    # 是否执行微调
        'epochs': 50,                       # 微调轮数
        'lr0': 0.001,                       # 学习率（比正常训练小）
        'project': 'runs/pipeline',
        'name': '3_finetune',
    },
    
    # ========== 阶段4：蒸馏增强 ==========
    'distill': {
        'enabled': True,                    # 是否执行蒸馏
        'epochs': 50,                       # 蒸馏轮数
        'kd_temp': 4.0,                     # 蒸馏温度
        'kd_weight': 1.0,                   # 蒸馏损失权重
        'lr0': 0.005,
        'project': 'runs/pipeline',
        'name': '4_distill',
    },
}


def run_sparse_training(config):
    """执行稀疏训练"""
    from train_sparse import SparseTrainer
    from ultralytics.cfg import DEFAULT_CFG_DICT
    
    LOGGER.info(f"\n{'#'*60}")
    LOGGER.info(f"# Stage 1: Sparse Training")
    LOGGER.info(f"{'#'*60}\n")
    
    sparse_cfg = config['sparse']
    
    overrides = {
        'model': config['student_model'],
        'data': config['data'],
        'epochs': sparse_cfg['epochs'],
        'batch': config['batch'],
        'imgsz': config['imgsz'],
        'device': config['device'],
        'workers': config['workers'],
        'lr0': sparse_cfg['lr0'],
        'project': sparse_cfg['project'],
        'name': sparse_cfg['name'],
    }
    
    trainer = SparseTrainer(
        cfg=DEFAULT_CFG_DICT,
        overrides=overrides,
        sparse_lambda=sparse_cfg['sparse_lambda'],
        sparse_warmup_epochs=sparse_cfg['sparse_warmup_epochs'],
    )
    trainer.train()
    
    # 返回最佳模型路径
    best_model = Path(sparse_cfg['project']) / sparse_cfg['name'] / 'weights' / 'best.pt'
    return str(best_model)


def run_pruning(config, sparse_model_path):
    """执行真正的结构化剪枝（使用torch-pruning）"""
    from prune_model import prune_model
    
    LOGGER.info(f"\n{'#'*60}")
    LOGGER.info(f"# Stage 2: Structural Pruning (torch-pruning)")
    LOGGER.info(f"{'#'*60}\n")
    
    prune_cfg = config['prune']
    
    # 调用真正的结构化剪枝
    pruned_model_path = prune_model(
        model_path=sparse_model_path,
        prune_ratio=prune_cfg['prune_ratio'],
        save_dir=prune_cfg['save_dir'],
    )
    
    return pruned_model_path
    
    return pruned_model_path


def run_finetuning(config, pruned_model_path):
    """执行微调训练"""
    from ultralytics import YOLO
    
    LOGGER.info(f"\n{'#'*60}")
    LOGGER.info(f"# Stage 3: Fine-tuning")
    LOGGER.info(f"{'#'*60}\n")
    
    finetune_cfg = config['finetune']
    
    model = YOLO(pruned_model_path)
    
    results = model.train(
        data=config['data'],
        epochs=finetune_cfg['epochs'],
        batch=config['batch'],
        imgsz=config['imgsz'],
        device=config['device'],
        workers=config['workers'],
        lr0=finetune_cfg['lr0'],
        project=finetune_cfg['project'],
        name=finetune_cfg['name'],
        exist_ok=True,
        mosaic=0.5,
        mixup=0.0,
    )
    
    # 返回最佳模型路径
    best_model = Path(finetune_cfg['project']) / finetune_cfg['name'] / 'weights' / 'best.pt'
    return str(best_model)


def run_distillation(config, finetuned_model_path):
    """执行知识蒸馏"""
    from train_kd_after_prune import KDAfterPruneTrainer
    from ultralytics.cfg import DEFAULT_CFG_DICT
    
    LOGGER.info(f"\n{'#'*60}")
    LOGGER.info(f"# Stage 4: Knowledge Distillation")
    LOGGER.info(f"{'#'*60}\n")
    
    distill_cfg = config['distill']
    
    overrides = {
        'model': finetuned_model_path,
        'data': config['data'],
        'epochs': distill_cfg['epochs'],
        'batch': config['batch'],
        'imgsz': config['imgsz'],
        'device': config['device'],
        'workers': config['workers'],
        'lr0': distill_cfg['lr0'],
        'project': distill_cfg['project'],
        'name': distill_cfg['name'],
    }
    
    trainer = KDAfterPruneTrainer(
        cfg=DEFAULT_CFG_DICT,
        overrides=overrides,
        teacher_weights=config['teacher_model'],
        kd_temperature=distill_cfg['kd_temp'],
        kd_weight=distill_cfg['kd_weight'],
    )
    trainer.train()
    
    # 返回最终模型路径
    best_model = Path(distill_cfg['project']) / distill_cfg['name'] / 'weights' / 'best.pt'
    return str(best_model)


def run_full_pipeline(config):
    """
    执行完整的轻量化流程
    """
    start_time = time.time()
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Starting Full Lightweight Pipeline")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Student Model: {config['student_model']}")
    LOGGER.info(f"Teacher Model: {config['teacher_model']}")
    LOGGER.info(f"Dataset: {config['data']}")
    LOGGER.info(f"{'='*60}\n")
    
    current_model = config['student_model']
    
    # 阶段1：稀疏训练
    if config['sparse']['enabled']:
        current_model = run_sparse_training(config)
        LOGGER.info(f"Sparse training completed. Model: {current_model}")
    else:
        LOGGER.info("Skipping sparse training (disabled)")
    
    # 阶段2：结构化剪枝
    if config['prune']['enabled']:
        current_model = run_pruning(config, current_model)
        LOGGER.info(f"Pruning completed. Model: {current_model}")
    else:
        LOGGER.info("Skipping pruning (disabled)")
    
    # 阶段3：微调训练
    if config['finetune']['enabled']:
        current_model = run_finetuning(config, current_model)
        LOGGER.info(f"Fine-tuning completed. Model: {current_model}")
    else:
        LOGGER.info("Skipping fine-tuning (disabled)")
    
    # 阶段4：蒸馏增强
    if config['distill']['enabled']:
        current_model = run_distillation(config, current_model)
        LOGGER.info(f"Distillation completed. Model: {current_model}")
    else:
        LOGGER.info("Skipping distillation (disabled)")
    
    # 完成
    total_time = time.time() - start_time
    hours = total_time / 3600
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Pipeline Completed!")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Total time: {hours:.2f} hours")
    LOGGER.info(f"Final model: {current_model}")
    LOGGER.info(f"{'='*60}\n")
    
    return current_model


if __name__ == '__main__':
    """
    ========================================================================
    完整轻量化流程 - 使用说明
    ========================================================================
    
    【流程概述】
    稀疏训练 → 结构化剪枝 → 微调 → 蒸馏增强
    
    【配置说明】
    在 PIPELINE_CONFIG 中修改以下参数：
    
    1. 基础配置
       - student_model: 学生模型配置文件
       - teacher_model: 教师模型权重路径
       - data: 数据集配置文件
    
    2. 各阶段配置
       - enabled: True/False 控制是否执行该阶段
       - epochs: 训练轮数
       - 其他阶段特定参数
    
    【灵活执行】
    可以通过设置 enabled=False 跳过某些阶段：
    - 只做稀疏训练：prune/finetune/distill 设为 False
    - 跳过稀疏直接剪枝：需要提供预训练模型
    - 只做蒸馏：sparse/prune/finetune 设为 False
    
    【输出路径】
    runs/pipeline/
    ├── 1_sparse_train/    # 稀疏训练结果
    ├── 2_pruned/          # 剪枝后模型
    ├── 3_finetune/        # 微调结果
    └── 4_distill/         # 最终蒸馏结果
    
    ========================================================================
    """
    
    # 执行完整流程
    final_model = run_full_pipeline(PIPELINE_CONFIG)
    
    print(f"\n最终模型保存在: {final_model}")
