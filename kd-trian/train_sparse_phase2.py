"""
稀疏训练第二阶段 - 直接复用SparseTrainer
=================================================
目标：加强稀疏化（sparse_lambda从1e-4 → 5e-4）

使用方式：
    python train_sparse_phase2.py
"""

import sys
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接复用 train_sparse.py 中的类
from train_sparse import SparseTrainer, analyze_bn_sparsity

from ultralytics.utils import LOGGER
from ultralytics.cfg import DEFAULT_CFG_DICT


# ============================================================================
# 第二阶段配置：加强稀疏化
# ============================================================================
CONFIG = {
    # ========== 模型文件（加载第一阶段best.pt）==========
    'model': "D:/project_workspace/最新yolo11代码/ultralytics-yolo11-main/runs/sparse_train/PSSM-YOLO-Lite-稀疏训练2/weights/best.pt",
    'data': 'C:/Users/project_user/Desktop/CCTSDB 2021/实验/cctsdb.yaml',
    
    # ========== 训练参数 ==========
    'epochs': 50,         # 微调轮数
    'batch': 32,          # 批次大小
    'imgsz': 640,         # 图像尺寸（与第一阶段保持一致）
    'device': '0',        # GPU设备
    'workers': 8,         # 数据加载线程数
    'lr0': 0.005,         # 较低学习率（保护已学特征）
    
    # ========== 稀疏训练参数（核心变化！）==========
    'sparse_lambda': 5e-4,      # 增大5倍！（从1e-4 → 5e-4）
    'sparse_warmup_epochs': 0,  # 不需要预热（已经训练过）
    
    # ========== 保存路径 ==========
    'project': 'runs/sparse_train',
    'name': 'PSSM-YOLO-Lite-稀疏训练-Phase2',
}


if __name__ == '__main__':
    """
    第二阶段稀疏训练 - 加强BN稀疏化
    """
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Sparse Training Phase 2 - Stronger Sparsity")
    LOGGER.info(f"{'='*60}")
    LOGGER.info(f"Model: {CONFIG['model']}")
    LOGGER.info(f"Dataset: {CONFIG['data']}")
    LOGGER.info(f"Sparse Lambda: {CONFIG['sparse_lambda']} (5x stronger)")
    LOGGER.info(f"Warmup Epochs: {CONFIG['sparse_warmup_epochs']}")
    LOGGER.info(f"Epochs: {CONFIG['epochs']}, Batch: {CONFIG['batch']}")
    LOGGER.info(f"Learning Rate: {CONFIG['lr0']} (reduced)")
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
    
    LOGGER.info(f"\n{'='*60}")
    LOGGER.info(f"Phase 2 Sparse Training Completed!")
    LOGGER.info(f"Best weights: {trainer.best}")
    LOGGER.info(f"{'='*60}\n")
