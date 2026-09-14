#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test if YOLO can load the new ablation model YAML correctly"""

import sys
sys.path.insert(0, r"<PROJECT_ROOT>")

try:
    print("Testing YOLO model loading...")
    from ultralytics import YOLO
    
    # Test loading K333 model
    print("\n[1] Loading yolo11n_pmsfa_k333.yaml...")
    model_k333 = YOLO(r'<PROJECT_ROOT>\ultralytics\cfg\models\11\yolo11n_pmsfa_k333.yaml')
    print("✓ K333 model loaded successfully")
    
    # Test loading K357 model
    print("\n[2] Loading yolo11n_pmsfa_k357.yaml...")
    model_k357 = YOLO(r'<PROJECT_ROOT>\ultralytics\cfg\models\11\yolo11n_pmsfa_k357.yaml')
    print("✓ K357 model loaded successfully")
    
    # Test loading K579 model
    print("\n[3] Loading yolo11n_pmsfa_k579.yaml...")
    model_k579 = YOLO(r'<PROJECT_ROOT>\ultralytics\cfg\models\11\yolo11n_pmsfa_k579.yaml')
    print("✓ K579 model loaded successfully")
    
    print("\n" + "="*60)
    print("✓✓✓ All three ablation models loaded successfully! ✓✓✓")
    print("✓✓✓ Ready to start training! ✓✓✓")
    print("="*60)
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
