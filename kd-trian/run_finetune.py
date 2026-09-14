"""
稀疏微调启动脚本 - 一键启动第二阶段训练

用途：
  加强稀疏化效果，从sparse_lambda=1e-4增加到5e-4
  从已保存的best.pt权重继续训练50个epoch
  预期效果：BN gamma参数压缩，获得明显的稀疏信号用于剪枝

运行方式：
  python run_finetune.py
  
或带参数：
  python run_finetune.py --epochs 50 --sparse_lambda 5e-4 --lr0 0.001
"""

import os
import subprocess
import sys
from pathlib import Path

# 工作目录设置
WORK_DIR = "D:/project_workspace/最新yolo11代码/ultralytics-yolo11-main/kd-trian"
print(f"工作目录: {WORK_DIR}")
os.chdir(WORK_DIR)

# 模型路径
MODEL_PATH = "D:/project_workspace/最新yolo11代码/ultralytics-yolo11-main/runs/sparse_train/PSSM-YOLO-Lite-稀疏训练2/weights/best.pt"

print("\n" + "="*60)
print("稀疏微调第二阶段 - 启动")
print("="*60)

# 检查模型是否存在
if not os.path.exists(MODEL_PATH):
    print(f"❌ 错误：找不到预训练权重")
    print(f"   预期路径: {MODEL_PATH}")
    print(f"   请确保第一阶段稀疏训练已完成")
    sys.exit(1)

print(f"✓ 找到预训练权重: {MODEL_PATH}")

# 启动微调
cmd = [
    sys.executable, 
    os.path.join(WORK_DIR, "train_sparse_finetune.py"),
    "--pretrained", MODEL_PATH,
    "--epochs", "50",
    "--sparse_lambda", "5e-4",  # 增加5倍
    "--lr0", "0.001",           # 较低学习率
    "--device", "0",
]

print(f"\n执行命令:")
print(f"  {' '.join(cmd)}\n")
print("="*60)

try:
    result = subprocess.run(cmd, check=True)
    print("\n" + "="*60)
    print("✓ 稀疏微调完成！")
    print("="*60)
except subprocess.CalledProcessError as e:
    print(f"\n❌ 训练过程中出错: {e}")
    sys.exit(1)
