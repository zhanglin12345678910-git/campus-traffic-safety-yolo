#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证新增的消融类能否正确定义和加载"""

import sys
import os

# 添加项目路径
project_root = r"<PROJECT_ROOT>"
sys.path.insert(0, project_root)

try:
    # 测试导入 block.py 中的新消融类
    print("正在测试导入新增消融类...")
    from ultralytics.nn.extra_modules.block import (
        PMSFA, CSP_PMSFA,
        PMSFA_K333, CSP_PMSFA_K333,
        PMSFA_K357, CSP_PMSFA_K357,
        PMSFA_K579, CSP_PMSFA_K579,
    )
    
    print("✓ 所有消融类导入成功！")
    print("\n导入的类：")
    print(f"  - PMSFA（原始）")
    print(f"  - CSP_PMSFA（原始C2f包装）")
    print(f"  - PMSFA_K333 / CSP_PMSFA_K333（消融 (3,3,3)）")
    print(f"  - PMSFA_K357 / CSP_PMSFA_K357（消融 (3,5,7)）")
    print(f"  - PMSFA_K579 / CSP_PMSFA_K579（消融 (5,7,9)）")
    
    # 简单验证类能否实例化
    print("\n正在验证类的可实例化性...")
    import torch
    test_inc = 64
    
    k333 = PMSFA_K333(test_inc)
    print(f"✓ PMSFA_K333 实例化成功")
    
    k357 = PMSFA_K357(test_inc)
    print(f"✓ PMSFA_K357 实例化成功")
    
    k579 = PMSFA_K579(test_inc)
    print(f"✓ PMSFA_K579 实例化成功")
    
    print("\n" + "="*60)
    print("✓✓✓ 所有检查通过！代码准备就绪，可以开始训练 ✓✓✓")
    print("="*60)
    
except ImportError as e:
    print(f"✗ ImportError: {e}")
    sys.exit(1)
except NameError as e:
    print(f"✗ NameError（类定义问题）: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ 其他错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
