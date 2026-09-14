from ultralytics import YOLO
import torch

# 加载v1和v2模型
print("="*80)
print("📊 对比 v1 和 v2 模型参数")
print("="*80 + "\n")

# v1 模型
model_v1 = YOLO('yolo11-CSP-PMSFA.yaml')
print("🔵 v1 模型 (P2/P3/P4/P5 四层检测):")
model_v1.info(detailed=False)

print("\n" + "-"*80 + "\n")

# v2 模型
model_v2 = YOLO('yolo11-CSP-PMSFA-v2-noP5.yaml')
print("🟢 v2 模型 (P2/P3/P4 三层检测):")
model_v2.info(detailed=False)

print("\n" + "="*80)
print("📈 对比总结")
print("="*80)

