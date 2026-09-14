# 多尺度特征提取模块对比实验说明

## 实验目的

本文件夹用于论文中补充“不同多尺度特征提取模块对比实验”，作为 PSSM/PMSFA 模块的同类方法对照。三个模型均基于原始 YOLO11n 的 P3/P4/P5 检测结构，仅替换特征提取位置的 C3k2/C2f 模块，不引入 DA、P2、WIoU、SlimNeck、剪枝或蒸馏等其他改动。

## 文件列表

| 文件 | 论文表格建议命名 | 作用 |
|---|---|---|
| `yolo11n-C2f-SPPFEnhance.yaml` | YOLO11n+SPPF | 使用 SPPF 风格上下文增强模块，扩大感受野 |
| `yolo11n-C2f-ASPP.yaml` | YOLO11n+ASPP | 使用经典空洞卷积多尺度并行分支 |
| `yolo11n-C2f-MSConv.yaml` | YOLO11n+MSConv | 使用普通 3x3/5x5/7x7 并行卷积分支 |

## 代码注册位置

为了保证这些 YAML 可以被 Ultralytics 正常解析，模块注册代码保留在原工程位置，不能剪切到本文件夹：

| 文件 | 内容 |
|---|---|
| `ultralytics/nn/extra_modules/block.py` | 新增 `C2f_SPPFEnhance`、`C2f_ASPP`、`C2f_MSConv` |
| `ultralytics/nn/tasks.py` | 将三个模块加入 `parse_model` 的通道解析和重复次数解析列表 |

## 已验证模型信息

验证环境中三个 YAML 均可正常构建并显示参数量和 FLOPs：

| 模型 | Params | GFLOPs |
|---|---:|---:|
| YOLO11n+SPPF | 2.27M | 6.5 |
| YOLO11n+ASPP | 2.55M | 7.5 |
| YOLO11n+MSConv | 3.59M | 11.1 |

## 训练命令示例

将 `data=xxx.yaml` 替换为你的交通标志数据集配置文件。

```bash
yolo detect train model=PMSFA_Ablation_Study_20260524/MultiScale_Module_Comparison/yolo11n-C2f-SPPFEnhance.yaml data=xxx.yaml imgsz=640 epochs=300 batch=32

yolo detect train model=PMSFA_Ablation_Study_20260524/MultiScale_Module_Comparison/yolo11n-C2f-ASPP.yaml data=xxx.yaml imgsz=640 epochs=300 batch=32

yolo detect train model=PMSFA_Ablation_Study_20260524/MultiScale_Module_Comparison/yolo11n-C2f-MSConv.yaml data=xxx.yaml imgsz=640 epochs=300 batch=32
```

## 论文写法建议

该组实验建议与 `YOLO11n`、`YOLO11n+C2f-PSSM` 或 `YOLO11n+CSP-PMSFA` 放在同一张表中，指标建议包含 Precision、Recall、mAP50、mAP50-95、Params、GFLOPs 和 FPS。这样可以说明 PSSM/PMSFA 并非简单堆叠大卷积或上下文模块，而是在交通标志小目标场景中通过递进式多尺度建模取得更好的精度和效率平衡。
