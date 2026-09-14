#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""诊断训练错误"""

import warnings
warnings.filterwarnings('ignore')

from ultralytics import YOLO
import traceback

print("="*80)
print("🔍 诊断 yolo11-CSP-PMSFA.yaml 错误")
print("="*80 + "\n")

yaml_path = r'<PROJECT_ROOT>\yolo11-CSP-PMSFA.yaml'

try:
    print(f"尝试加载: {yaml_path}\n")
    model = YOLO(yaml_path)
    print("✅ 加载成功！")
    model.info(detailed=False)
    
except TypeError as e:
    print(f"❌ TypeError: {e}\n")
    print("📋 完整错误栈:")
    traceback.print_exc()
    
    print("\n" + "="*80)
    print("💡 问题分析:")
    print("="*80)
    print("""
这个错误通常由以下原因引起:
1. YAML文件中使用了 Detect_LSCD 等特殊检测头,但参数格式不正确
2. Detect_LSCD 需要 [nc, hidc] 两个参数,但只提供了 [nc]

解决方案:
A. 修改YAML,将 Detect_LSCD 改回标准 Detect
B. 或者添加 hidc 参数: Detect_LSCD, [nc, 256]

建议: 使用标准 Detect 检测头更稳定！
    """)
    
except Exception as e:
    print(f"❌ 其他错误: {e}\n")
    traceback.print_exc()

print("\n" + "="*80)
print("🧪 现在测试 v2 版本 (yolo11-CSP-PMSFA-v2-noP5.yaml)")
print("="*80 + "\n")

v2_path = 'yolo11-CSP-PMSFA-v2-noP5.yaml'
try:
    model_v2 = YOLO(v2_path)
    print("✅ v2 加载成功！\n")
    model_v2.info(detailed=False)
    print("\n🎉 v2 配置完全正常,可以开始训练!")
except Exception as e:
    print(f"❌ v2 也有问题: {e}\n")
    traceback.print_exc()

