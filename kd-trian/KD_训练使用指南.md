# 知识蒸馏训练 - 快速使用指南

## 🚀 方案1：使用 Trainer（推荐）

### 1️⃣ 最简单的用法

```bash
python train_kd.py \
    --student yolo11-CSP-PMSFA-Lite.yaml \
    --teacher teacher.pt \
    --data dataset/data.yaml \
    --mode trainer
```

**说明**：
- 只需指定 3 个必需参数：`--student`, `--teacher`, `--data`
- 其他参数自动使用默认值
- 温度默认 4.0，权重默认 1.0

---

### 2️⃣ 自定义温度和权重

```bash
python train_kd.py \
    --student yolo11-CSP-PMSFA-Lite.yaml \
    --teacher teacher.pt \
    --data dataset/data.yaml \
    --kd-temp 2.0 \
    --kd-weight 1.5 \
    --mode trainer
```

**参数说明**：
- `--kd-temp 2.0` : 设置蒸馏温度为 2.0（较低温度）
- `--kd-weight 1.5` : 设置蒸馏损失权重为 1.5

---

### 3️⃣ 完整参数控制

```bash
python train_kd.py \
    --student yolo11-CSP-PMSFA-Lite.yaml \
    --teacher teacher.pt \
    --data dataset/data.yaml \
    --epochs 200 \
    --batch 32 \
    --device 0 \
    --kd-temp 4.0 \
    --kd-weight 1.0 \
    --name my_experiment \
    --mode trainer
```

---

## 📊 参数对照表

| 命令行参数 | 代码中的变量 | 默认值 | 说明 |
|-----------|-------------|--------|------|
| `--student` | - | 必需 | 学生模型 .yaml 文件 |
| `--teacher` | - | 必需 | 教师模型 .pt 文件 |
| `--data` | - | 必需 | 数据集 .yaml 文件 |
| `--kd-temp` | `args.kd_temp` → `kd_temperature` | 4.0 | 蒸馏温度 |
| `--kd-weight` | `args.kd_weight` → `kd_weight` | 1.0 | 蒸馏权重 |
| `--epochs` | `args.epochs` | 100 | 训练轮数 |
| `--batch` | `args.batch` | 16 | 批次大小 |
| `--device` | `args.device` | '' (自动) | GPU设备 |
| `--mode` | `args.mode` | 'trainer' | 方案选择 |

---

## 🔧 如何修改默认值？

### 方法1：每次运行时指定（推荐）
```bash
python train_kd.py --kd-temp 3.0 --kd-weight 0.5 ...
```

### 方法2：修改代码中的默认值
打开 `train_kd.py`，找到第 748-751 行：

```python
# ========== KD 核心参数 (这里修改默认温度和权重) ==========
parser.add_argument('--kd-temp', type=float, default=4.0,    # 改这里
                   help='Knowledge distillation temperature (推荐 2-6)')
parser.add_argument('--kd-weight', type=float, default=1.0,  # 改这里
                   help='Knowledge distillation loss weight (推荐 0.5-2.0)')
```

修改 `default=` 后面的数值即可。

---

## 📝 实际使用示例

### 示例1：基线实验（默认参数）
```bash
python train_kd.py \
    --student yolo11-CSP-PMSFA-Lite.yaml \
    --teacher teacher.pt \
    --data dataset/data.yaml \
    --name baseline \
    --mode trainer
```

### 示例2：低温实验
```bash
python train_kd.py \
    --student yolo11-CSP-PMSFA-Lite.yaml \
    --teacher teacher.pt \
    --data dataset/data.yaml \
    --kd-temp 2.0 \
    --name low_temp \
    --mode trainer
```

### 示例3：高温实验
```bash
python train_kd.py \
    --student yolo11-CSP-PMSFA-Lite.yaml \
    --teacher teacher.pt \
    --data dataset/data.yaml \
    --kd-temp 6.0 \
    --name high_temp \
    --mode trainer
```

---

## ❓ 常见问题

### Q1: 我必须指定 `--kd-temp` 吗？
**A**: 不需要，如果不指定，会使用默认值 4.0

### Q2: 我想用温度 3.5，怎么办？
**A**: 运行时加上 `--kd-temp 3.5` 即可

### Q3: 参数在哪里生效？
**A**: 参数传递流程：
```
命令行 --kd-temp 4.0 
  ↓
parse_args() 解析为 args.kd_temp 
  ↓
KDDetectionTrainer(kd_temperature=args.kd_temp)
  ↓
在训练循环中使用 self.kd_temperature
```

### Q4: 我可以在代码里直接改吗？
**A**: 可以，但不推荐。找到第 786 行附近：
```python
trainer = KDDetectionTrainer(
    overrides=overrides,
    teacher_weights=args.teacher,
    kd_temperature=args.kd_temp,  # 或者改成 kd_temperature=3.5
    kd_weight=args.kd_weight,     # 或者改成 kd_weight=1.2
)
```

---

## 🎯 推荐使用方式

**最佳实践**：使用命令行参数，保持代码不变

```bash
# 快速测试（1-2个epoch）
python train_kd.py --student xxx.yaml --teacher xxx.pt --data xxx.yaml --epochs 2

# 正式训练
python train_kd.py --student xxx.yaml --teacher xxx.pt --data xxx.yaml --epochs 100 --kd-temp 4.0

# 对比实验
python train_kd.py --kd-temp 2.0 --name T2
python train_kd.py --kd-temp 4.0 --name T4
python train_kd.py --kd-temp 6.0 --name T6
```

---

## 📌 记住

✅ 方案1 不需要修改代码，所有参数都在命令行指定  
✅ 温度和权重参数：`--kd-temp` 和 `--kd-weight`  
✅ 默认值：温度=4.0，权重=1.0  
✅ 如果不确定用什么值，就用默认值
