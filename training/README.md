# YOLO26 训练

本目录负责在现有 45 类 TT100K 数据上训练 YOLO26。旧 YOLO11 权重仅作对照，不会被当作 YOLO26。

## 当前项目采用结果（2026-09-08）

- 用户已明确要求停止训练，不再续跑 80 轮计划。
- 完整完成 32 轮；第 33 轮中断于 `142/2341` batch，不计为完成轮次。
- 第 32 轮在全部完整轮次中具有最高验证集 `mAP50-95=0.62980`，已作为项目正式权重。
- 独立 test 集 3,992 张图片：Precision 0.865597、Recall 0.763761、mAP50 0.838795、mAP50-95 0.646661。
- 正式模型：`../models/yolo26-tt100k-best.pt`。
- 模型 SHA256：`0d4ad7756c965bdb5ec2520c7124a195fabc28084cc6039ec02e1aa6a15dd9af`。
- 训练状态为 `completed_partial_by_user`；watchdog 和 baseline 启动脚本会识别该状态并拒绝自动恢复。

上述状态是本项目的最终交付策略，但不表示 80 轮计划已经完整训练。不得把未完成轮次、目标值或 smoke 指标写成最终结果。

## 将来明确决定重新训练时

以下顺序仅供未来重新开启训练计划时使用；当前不要执行：

1. `python audit_tt100k.py --data <LOCAL_PATH>`
2. `python train_yolo26.py --preset smoke --fraction 0.01 --data <LOCAL_PATH>`
3. `python train_yolo26.py --preset baseline --data <LOCAL_PATH>`
4. `python train_yolo26.py --preset final --data <LOCAL_PATH> --promote`
5. `python evaluate_yolo26.py --weights runs\yolo26l-tt100k-960\weights\best.pt --data <LOCAL_PATH> --imgsz 960`

评估脚本只接受训练目录中的 `best.pt`，并要求上一级目录存在 `args.yaml` 和 `results.csv`；`--imgsz` 必须等于训练尺寸（`baseline` 为 640，`final` 为 960）。`../models/yolo26-tt100k-best.pt` 是晋升后的副本，不能直接用于正式评估。

训练意外中断后可用同一预设恢复，例如：`python train_yolo26.py --preset baseline --data <LOCAL_PATH> --resume`。每 5 个 epoch 额外保存一次检查点，并持续更新 `last.pt`。当前用户停止锁存在时，项目启动脚本会拒绝该操作；只有用户未来明确改变决定后才可解除锁定。

预设：

- `smoke`：YOLO26m、640、1 epoch；建议 `--fraction 0.01`。脚本默认只取 64 张验证图，避免把链路自检误当成耗时很长的正式评估。
- `baseline`：YOLO26m、640、80 epochs。
- `final`：YOLO26l、960、200 epochs，精度优先。

训练集 28,083 张、验证集 8,016 张、测试集 3,992 张。完整最终训练会长时间占用 GPU，应保留日志和 `results.csv`，不得把目标指标写成真实结果。
