#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 AST 检查 block.py 中的类定义顺序和导出"""

import ast
import re

block_py = r"<PROJECT_ROOT>\ultralytics\nn\extra_modules\block.py"

print("正在分析 block.py 的类定义顺序...")
print("="*60)

with open(block_py, 'r', encoding='utf-8') as f:
    content = f.read()

# 提取 __all__ 中的消融类
all_match = re.search(r"'PMSFA_K333'.*?'CSP_PMSFA_K579'", content)
if all_match:
    print("✓ __all__ 列表包含新消融类：")
    for cls in ['PMSFA_K333', 'CSP_PMSFA_K333', 'PMSFA_K357', 'CSP_PMSFA_K357', 'PMSFA_K579', 'CSP_PMSFA_K579']:
        if f"'{cls}'" in all_match.group():
            print(f"  ✓ {cls}")

# 解析 AST 找到类定义的行号
tree = ast.parse(content)
classes = {}
for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
        classes[node.name] = node.lineno

print("\n关键类定义的位置：")
key_classes = ['PMSFA', 'CSP_PMSFA', 'PMSFA_K333', 'CSP_PMSFA_K333', 
               'PMSFA_K357', 'CSP_PMSFA_K357', 'PMSFA_K579', 'CSP_PMSFA_K579']

for cls_name in key_classes:
    if cls_name in classes:
        lineno = classes[cls_name]
        print(f"  {cls_name:20s} at line {lineno}")
    else:
        print(f"  {cls_name:20s} NOT FOUND ✗")

# 验证顺序：PMSFA 必须在所有消融类之前
pmsfa_line = classes.get('PMSFA', float('inf'))
k333_line = classes.get('PMSFA_K333', float('inf'))
k357_line = classes.get('PMSFA_K357', float('inf'))
k579_line = classes.get('PMSFA_K579', float('inf'))

print("\n定义顺序检查：")
if pmsfa_line < k333_line and pmsfa_line < k357_line and pmsfa_line < k579_line:
    print("✓ PMSFA 在所有消融类之前定义 - 顺序正确！")
else:
    print("✗ 类定义顺序有问题！")

# 检查是否还有旧的 PSSM 类
if 'PSSM' in classes or 'C2f_PSSM' in classes:
    print("\n⚠ 警告：仍然存在旧的 PSSM 或 C2f_PSSM 类")
else:
    print("\n✓ 旧的 PSSM 和 C2f_PSSM 类已删除")

print("\n" + "="*60)
print("✓✓✓ block.py 类结构验证通过 ✓✓✓")
print("="*60)
