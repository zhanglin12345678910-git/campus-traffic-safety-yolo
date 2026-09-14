"""
剪枝后微调脚本 - Fine-tuning after Pruning
=================================================
实现思路：
1. 加载剪枝后的模型
2. 使用较小的学习率进行微调训练
3. 恢复因剪枝损失的精度

Author: 林哥
Date: 2026-01-29
"""

import argparse
import os
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from ultralytics import YOLO
from ultralytics.utils import LOGGER


# ============================================================================
# 配置区
# ============================================================================

CONFIG = {
    # ========== 模型文件（必需）==========
    'model': 'runs/pruned/PSSM-YOLO-Lite-剪枝/pruned_model.pt',  # 剪枝后的模型
    'data': '%USERPROFILE%\\Desktop\\CCTSDB 2021\\实验\\cctsdb.yaml',  # 数据集配置文件
    
    # ========== 微调训练参数 ==========
    'epochs': 50,          # 微调轮数（比完整训练少）
    'batch': 32,           # 批次大小
    'imgsz': 640,          # 图像尺寸
    'device': '0',         # GPU设备
    'workers': 8,          # 数据加载线程数
    
    # ========== 微调特殊参数 ==========
    'lr0': 0.001,          # 初始学习率（比正常训练小，推荐 0.001-0.01）
    'lrf': 0.01,           # 最终学习率比例
    'warmup_epochs': 3,    # 预热轮数
    'cos_lr': True,        # 使用余弦学习率衰减
    
    # ========== 冻结参数（可选）==========
    'freeze': None,        # 冻结前N层（None表示不冻结）
    
    # ========== 保存路径 ==========
    'project': 'runs/finetune',
    'name': 'PSSM-YOLO-Lite-微调',
}


def finetune(config):
    """
    执行微调训练
    
    Args:
        config: 配置字典
    """
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Fine-tuning after Pruning")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Model: {config['model']}")
    LOGGER.info(f"Dataset: {config['data']}")
    LOGGER.info(f"Epochs: {config['epochs']}")
    LOGGER.info(f"Learning Rate: {config['lr0']}")
    LOGGER.info(f"{'='*60}\n")
    
    # 加载剪枝后的模型
    model = YOLO(config['model'])
    
    # 开始微调训练
    results = model.train(
        data=config['data'],
        epochs=config['epochs'],
        batch=config['batch'],
        imgsz=config['imgsz'],
        device=config['device'],
        workers=config['workers'],
        lr0=config['lr0'],
        lrf=config['lrf'],
        warmup_epochs=config['warmup_epochs'],
        cos_lr=config['cos_lr'],
        freeze=config['freeze'],
        project=config['project'],
        name=config['name'],
        exist_ok=True,
        
        # 微调通常使用的额外设置
        resume=False,
        pretrained=True,  # 从剪枝后的权重开始
        optimizer='SGD',
        
        # 数据增强（微调时可以适当减少）
        mosaic=0.5,       # 减少mosaic增强
        mixup=0.0,        # 关闭mixup
        copy_paste=0.0,   # 关闭copy_paste
    )
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Fine-tuning completed!")
    LOGGER.info(f"Best model: {config['project']}/{config['name']}/weights/best.pt")
    LOGGER.info(f"Next step: Run train_kd_after_prune.py for knowledge distillation")
    LOGGER.info(f"{'='*60}")
    
    return results


if __name__ == '__main__':
    """
    ========================================================================
    剪枝后微调 - 使用说明
    ========================================================================
    
    【训练流程】
    1. 稀疏训练 → 2. 结构化剪枝 → 3. 微调（本脚本）→ 4. 蒸馏增强
    
    【前置条件】
    - 需要先运行 prune_model.py 完成剪枝
    
    【微调策略】
    1. 使用较小的学习率（0.001-0.01）
    2. 训练轮数适中（30-100轮）
    3. 减少数据增强强度
    4. 可选择冻结部分层
    
    【参数说明】
    - lr0: 初始学习率
      * 推荐 0.001-0.01（比正常训练小1个数量级）
    
    - epochs: 微调轮数
      * 推荐 30-100 轮（根据精度恢复情况调整）
    
    - freeze: 冻结前N层
      * None: 不冻结，全部微调
      * 10: 冻结前10层
    
    【下一步】
    微调完成后，使用 train_kd_after_prune.py 进行知识蒸馏增强
    
    ========================================================================
    """
    
    finetune(CONFIG)
