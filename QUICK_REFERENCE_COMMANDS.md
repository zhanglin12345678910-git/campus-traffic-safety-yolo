# PMSFA Ablation Study - Quick Reference Commands

## Dataset Setup

```bash
# Ensure CCTSDB data.yaml path (update <PATH> accordingly)
# Example: %USERPROFILE%\Desktop\CCTSDB 2021\实验\cctsdb.yaml
```

## Training Commands

### Single Variant Training

**K=3,3,3 (Baseline)**
```bash
python train.py --model ultralytics/cfg/models/11/yolo11n_pmsfa_k333.yaml \
                --data C:/Users/project_user/Desktop/CCTSDB\ 2021/实验/cctsdb.yaml \
                --epochs 100 --imgsz 640 --device 0 --batch 32
```

**K=3,5,7 [Ours] (Proposed)**
```bash
python train.py --model ultralytics/cfg/models/11/yolo11n_pmsfa_k357.yaml \
                --data C:/Users/project_user/Desktop/CCTSDB\ 2021/实验/cctsdb.yaml \
                --epochs 100 --imgsz 640 --device 0 --batch 32
```

**K=5,7,9 (Larger)**
```bash
python train.py --model ultralytics/cfg/models/11/yolo11n_pmsfa_k579.yaml \
                --data C:/Users/project_user/Desktop/CCTSDB\ 2021/实验/cctsdb.yaml \
                --epochs 100 --imgsz 640 --device 0 --batch 32
```

### Sequential Training (All Three)

```bash
# Windows PowerShell
$data_path = "C:/Users/project_user/Desktop/CCTSDB 2021/实验/cctsdb.yaml"
foreach ($variant in "k333", "k357", "k579") {
    python train.py --model "ultralytics/cfg/models/11/yolo11n_pmsfa_${variant}.yaml" `
                    --data $data_path --epochs 100 --device 0
    Write-Host "Completed $variant"
    Start-Sleep -Seconds 30
}
```

### Parallel Training (All Three - Batch)

```bash
# Windows batch file or PowerShell background jobs
$data_path = "C:/Users/project_user/Desktop/CCTSDB 2021/实验/cctsdb.yaml"
foreach ($variant in "k333", "k357", "k579") {
    Start-Job -ScriptBlock {
        param($v, $d)
        python train.py --model "ultralytics/cfg/models/11/yolo11n_pmsfa_${v}.yaml" `
                        --data $d --epochs 100
    } -ArgumentList $variant, $data_path
}
Get-Job | Wait-Job
```

## Validation Commands

### Validate Best Weights

```bash
python val.py --weights runs/detect/yolo11n_pmsfa_k333/weights/best.pt \
              --data C:/Users/project_user/Desktop/CCTSDB\ 2021/实验/cctsdb.yaml \
              --imgsz 640

python val.py --weights runs/detect/yolo11n_pmsfa_k357/weights/best.pt \
              --data C:/Users/project_user/Desktop/CCTSDB\ 2021/实验/cctsdb.yaml \
              --imgsz 640

python val.py --weights runs/detect/yolo11n_pmsfa_k579/weights/best.pt \
              --data C:/Users/project_user/Desktop/CCTSDB\ 2021/实验/cctsdb.yaml \
              --imgsz 640
```

## Inference Commands

### Detect on Image/Directory

```bash
python detect.py --weights runs/detect/yolo11n_pmsfa_k357/weights/best.pt \
                 --source <IMAGE_PATH> \
                 --imgsz 640 \
                 --conf 0.25

# Or on directory
python detect.py --weights runs/detect/yolo11n_pmsfa_k357/weights/best.pt \
                 --source <DIRECTORY_PATH> \
                 --imgsz 640 \
                 --conf 0.25
```

## Metrics Extraction

### Extract Key Metrics (Python)

```python
import pandas as pd
import os

variants = ['k333', 'k357', 'k579']
results = {}

for var in variants:
    csv_path = f'runs/detect/yolo11n_pmsfa_{var}/results.csv'
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        last_epoch = df.iloc[-1]
        results[var] = {
            'Precision': f"{last_epoch[' precision']*100:.2f}%",
            'Recall': f"{last_epoch[' recall']*100:.2f}%",
            'mAP50': f"{last_epoch[' mAP50']*100:.2f}%",
            'mAP50-95': f"{last_epoch[' mAP50-95']*100:.2f}%",
        }

# Print comparison
for var, metrics in results.items():
    print(f"K={var}: {metrics}")
```

### Get Model Complexity

```python
from ultralytics import YOLO

variants = ['k333', 'k357', 'k579']

for var in variants:
    model = YOLO(f'ultralytics/cfg/models/11/yolo11n_pmsfa_{var}.yaml')
    params = sum(p.numel() for p in model.model.parameters()) / 1e6
    print(f"K={var}: {params:.2f}M parameters")

# Or using yolo command
# yolo detect profile model=ultralytics/cfg/models/11/yolo11n_pmsfa_k357.yaml imgsz=640
```

## Results Monitoring

### Check Training Progress

```bash
# After training, check results
cat runs/detect/yolo11n_pmsfa_k357/results.csv
```

### Compare All Results

```python
import os
import pandas as pd

variants = ['k333', 'k357', 'k579']

for var in variants:
    csv = f'runs/detect/yolo11n_pmsfa_{var}/results.csv'
    if os.path.exists(csv):
        df = pd.read_csv(csv)
        best_idx = df[' mAP50'].idxmax()
        best_row = df.loc[best_idx]
        
        print(f"\n{'='*50}")
        print(f"K={var} BEST EPOCH {best_idx}")
        print(f"{'='*50}")
        print(f"Precision: {best_row[' precision']:.4f}")
        print(f"Recall:    {best_row[' recall']:.4f}")
        print(f"mAP50:     {best_row[' mAP50']:.4f}")
        print(f"mAP50-95:  {best_row[' mAP50-95']:.4f}")
```

## Troubleshooting Quick Fixes

### OOM (Out of Memory)

```bash
# Reduce batch size
python train.py --model ... --batch 8

# Reduce image size
python train.py --model ... --imgsz 416
```

### Slow Training

```bash
# Verify GPU usage
nvidia-smi

# Use specific GPU
python train.py --model ... --device 0

# Check data loading
python train.py --model ... --cache memory  # Cache to RAM
```

### Model Not Found

```bash
# Verify YAML exists
ls ultralytics/cfg/models/11/yolo11n_pmsfa_*.yaml

# Verify classes are exported
python -c "from ultralytics.nn.extra_modules import CSP_PMSFA_K357; print('OK')"
```

## Tensorboard Monitoring

```bash
# Start tensorboard (after training starts)
tensorboard --logdir runs/detect/

# Then visit http://localhost:6006
```

## Complete Workflow Example

```bash
# 1. Set dataset path
$DATA="C:/Users/project_user/Desktop/CCTSDB 2021/实验/cctsdb.yaml"

# 2. Train K357 variant (main model)
python train.py --model ultralytics/cfg/models/11/yolo11n_pmsfa_k357.yaml \
                --data $DATA --epochs 100 --device 0 --batch 32

# 3. Validate
python val.py --weights runs/detect/yolo11n_pmsfa_k357/weights/best.pt \
              --data $DATA

# 4. Extract metrics
python << 'EOF'
import pandas as pd
df = pd.read_csv('runs/detect/yolo11n_pmsfa_k357/results.csv')
print(df.iloc[-1][['precision', 'recall', 'mAP50', 'mAP50-95']])
EOF

# 5. Test inference
python detect.py --weights runs/detect/yolo11n_pmsfa_k357/weights/best.pt \
                 --source <TEST_IMAGE> --imgsz 640
```

## Hyperparameter Tuning (Optional)

```bash
# Try different batch sizes
for batch in 16 32 64; do
    python train.py --model ultralytics/cfg/models/11/yolo11n_pmsfa_k357.yaml \
                    --data $DATA --batch $batch --epochs 50 --device 0
done

# Try different image sizes
for size in 416 640 1024; do
    python train.py --model ultralytics/cfg/models/11/yolo11n_pmsfa_k357.yaml \
                    --data $DATA --imgsz $size --epochs 50 --device 0
done
```

## Common File Locations

```
Model Configs:    ultralytics/cfg/models/11/yolo11n_pmsfa_k*.yaml
Module Classes:   ultralytics/nn/extra_modules/block.py (lines 7878-7959)
Training Results: runs/detect/yolo11n_pmsfa_k*/
Weights:          runs/detect/yolo11n_pmsfa_k*/weights/{best,last}.pt
Metrics:          runs/detect/yolo11n_pmsfa_k*/results.csv
```

---

**TIP:** For the paper's blind review response, focus on K=3,5,7 variant which should show:
- ✓ Best balance of accuracy and efficiency
- ✓ Justifies the progressive kernel choice
- ✓ Validates the design decision

Start with single training run first to verify setup, then run all three for comparison.
