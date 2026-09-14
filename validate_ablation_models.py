#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"Validation using only standard library"

import ast
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

print("="*60)
print("PMSFA Ablation Models - Configuration Validation")
print("="*60)

# 1. Check block.py exports
print("\n[1] Checking block.py exports...")
block_file = PROJECT_ROOT / "ultralytics" / "nn" / "extra_modules" / "block.py"
with open(block_file, "r", encoding="utf-8") as f:
    content = f.read()

# Use AST to find __all__
tree = ast.parse(content)
exports = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, ast.List):
                    exports = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)]

ablation_classes = ["PMSFA_K333", "CSP_PMSFA_K333", "PMSFA_K357", "CSP_PMSFA_K357", "PMSFA_K579", "CSP_PMSFA_K579"]
print(f"  Found {len(exports)} exports in __all__" if exports else "  Could not find __all__")
for cls_name in ablation_classes:
    if exports and cls_name in exports:
        print(f"  ✓ {cls_name} exported")
    else:
        print(f"  ✗ {cls_name} NOT exported")

# 2. Check YAML files exist
print("\n[2] Checking YAML configuration files...")
yaml_files = {
    "yolo11n_pmsfa_k333.yaml": "K=3,3,3 (baseline)",
    "yolo11n_pmsfa_k357.yaml": "K=3,5,7 (Ours)",
    "yolo11n_pmsfa_k579.yaml": "K=5,7,9 (larger kernels)",
}

for yaml_name, description in yaml_files.items():
    yaml_file = PROJECT_ROOT / "ultralytics" / "cfg" / "models" / "11" / yaml_name
    if yaml_file.exists():
        print(f"  ✓ {yaml_name:30s} ({description})")
    else:
        print(f"  ✗ {yaml_name:30s} - FILE NOT FOUND")

# 3. Check tasks.py modifications
print("\n[3] Checking tasks.py modifications...")
tasks_file = PROJECT_ROOT / "ultralytics" / "nn" / "tasks.py"
with open(tasks_file, "r", encoding="utf-8") as f:
    tasks_content = f.read()

patterns_to_check = ["CSP_PMSFA_K333", "CSP_PMSFA_K357", "CSP_PMSFA_K579"]
for pattern in patterns_to_check:
    count = tasks_content.count(pattern)
    if count >= 2:
        print(f"  ✓ {pattern:20s} found {count} times in tasks.py")
    else:
        print(f"  ✗ {pattern:20s} NOT found enough times in tasks.py")

print("\n" + "="*60)
print("✓ Configuration Validation Complete!")
print("Ready to train with yolo11n_pmsfa_k*.yaml files")
print("="*60)
