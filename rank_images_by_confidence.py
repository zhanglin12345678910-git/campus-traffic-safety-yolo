import argparse
import shutil
import warnings
from pathlib import Path

import pandas as pd
from ultralytics import YOLO

# 关闭非关键告警，避免控制台输出过于冗长
warnings.filterwarnings("ignore")


def parse_args():
    """
    解析命令行参数。

    这个脚本的目标是：在同一批图片上分别跑“改进模型”和“原模型”，
    计算每张图的分数差值 diff = my_score - base_score，
    然后把“改进模型更好（diff > 0）”的图片按差值降序输出。
    """
    parser = argparse.ArgumentParser(
        description="Compare two YOLO models on same images and rank images where my model has higher confidence."
    )
    parser.add_argument(
        "--my-model",
        type=str,
        default=r"<PROJECT_ROOT>\runs\train\GTSDB-修改好的模型-实验\weights\best.pt",
        help="Path to your improved model (.pt/.yaml)",
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default=r"<PROJECT_ROOT>\runs\train\GTSDB-YOLO11-实验\weights\best.pt",
        help="Path to baseline model (.pt/.yaml)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=r"%USERPROFILE%\Desktop\AI研究\GTSDB-real\images\test",
        help="Image dir/file/list for prediction",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Inference image size")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.7, help="NMS IoU threshold")
    parser.add_argument("--device", type=str, default="", help="Device, e.g. 0 or cpu")
    parser.add_argument(
        "--score-mode",
        type=str,
        default="mean",
        choices=["mean", "max", "sum", "topk_mean"],
        help="How to aggregate box confidences into one score per image",
    )
    parser.add_argument("--topk", type=int, default=3, help="Used when score-mode=topk_mean")
    parser.add_argument("--topn", type=int, default=100, help="Print top-N better images in terminal")
    parser.add_argument(
        "--compare-mode",
        type=str,
        default="single_target",
        choices=["single_target", "all"],
        help="single_target: only compare images where both models detect exactly 1 object; all: compare all images",
    )
    parser.add_argument("--out-dir", type=str, default=".", help="Output directory")
    parser.add_argument(
        "--run-prefix",
        type=str,
        default="train",
        help="Auto run folder prefix, e.g. train -> train_1, train_2",
    )
    return parser.parse_args()


def create_next_run_dir(root_dir, prefix="train"):
    """在 root_dir 下自动创建下一个编号目录，如 train_1、train_2。"""
    root = Path(root_dir)
    root.mkdir(parents=True, exist_ok=True)

    max_idx = 0
    target_prefix = f"{prefix}_"
    for p in root.iterdir():
        if not p.is_dir() or not p.name.startswith(target_prefix):
            continue
        suffix = p.name[len(target_prefix):]
        if suffix.isdigit():
            max_idx = max(max_idx, int(suffix))

    run_dir = root / f"{prefix}_{max_idx + 1}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def score_from_result(result, mode="mean", topk=3):
    """
    将单张图片的检测结果聚合为一个“图片分数”。

    参数:
        result: YOLO 的单图预测结果对象。
        mode: 聚合方式，支持:
            - mean: 所有检测框置信度平均值
            - max:  最大置信度
            - sum:  置信度求和（检测框多时会更大）
            - topk_mean: 取前 topk 个最高置信度再求平均
        topk: topk_mean 模式下使用的 k 值。

    返回:
        float，当前图片分数。若无检测框则返回 0.0。
    """
    # 没有检测框，默认分数为 0
    if result.boxes is None or len(result.boxes) == 0:
        return 0.0

    # 取出每个检测框的置信度
    confs = result.boxes.conf
    if confs is None or len(confs) == 0:
        return 0.0

    # Tensor -> Python list，便于排序和统计
    values = confs.detach().cpu().tolist()
    if not values:
        return 0.0

    # 先降序，便于 max/topk 计算
    values = sorted(values, reverse=True)

    if mode == "max":
        return float(values[0])
    if mode == "sum":
        return float(sum(values))
    if mode == "topk_mean":
        # 防止 topk 越界，至少取 1 个，最多取检测框总数
        k = max(1, min(topk, len(values)))
        return float(sum(values[:k]) / k)

    # 默认 mean
    return float(sum(values) / len(values))


def infer_scores(model_path, source, imgsz, conf, iou, device, score_mode, topk):
    """
    对输入图片集合进行推理，返回“图片路径 -> 图片分数”的映射。

    说明:
        - 使用 stream=True 逐张产出结果，适合大量图片（如 2000 张）
        - save=False，不保存可视化图，仅做数值比较
    """
    model = YOLO(model_path)
    results = model.predict(
        source=source,
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        device=device if device else None,
        save=False,
        verbose=False,
        stream=True,
    )

    score_map = {}
    for r in results:
        # 统一为绝对路径，确保两个模型结果可以按同一图片准确对齐
        image_path = str(Path(r.path).resolve())
        score_map[image_path] = score_from_result(r, mode=score_mode, topk=topk)
    return score_map


def infer_details(model_path, source, imgsz, conf, iou, device, score_mode, topk):
    """
    对输入图片集合进行推理，返回每张图的详细信息。

    返回结构:
        {
            image_path: {
                "score": float,
                "count": int,         # 检测框数量
                "top1_conf": float,    # 最高置信度
                "top1_cls": int|None,  # 最高置信度对应类别
            }
        }
    """
    model = YOLO(model_path)
    results = model.predict(
        source=source,
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        device=device if device else None,
        save=False,
        verbose=False,
        stream=True,
    )

    detail_map = {}
    for r in results:
        image_path = str(Path(r.path).resolve())
        count = len(r.boxes) if r.boxes is not None else 0

        top1_conf = 0.0
        top1_cls = None
        if r.boxes is not None and len(r.boxes) > 0 and r.boxes.conf is not None and len(r.boxes.conf) > 0:
            conf_values = r.boxes.conf.detach().cpu().tolist()
            cls_values = r.boxes.cls.detach().cpu().tolist() if r.boxes.cls is not None else []
            if conf_values:
                max_idx = max(range(len(conf_values)), key=lambda idx: conf_values[idx])
                top1_conf = float(conf_values[max_idx])
                if cls_values and max_idx < len(cls_values):
                    top1_cls = int(cls_values[max_idx])

        detail_map[image_path] = {
            "score": score_from_result(r, mode=score_mode, topk=topk),
            "count": int(count),
            "top1_conf": float(top1_conf),
            "top1_cls": top1_cls,
        }

    return detail_map


def save_visual_predictions(model_path, source, imgsz, conf, iou, device, out_dir, run_name):
    """
    保存整批图片的预测可视化结果（带检测框）。

    参数:
        model_path: 模型权重路径。
        source: 输入图片目录/文件。
        imgsz/conf/iou/device: 推理参数。
        out_dir: 输出根目录。
        run_name: 当前模型结果子目录名。

    返回:
        结果目录路径（Path）。
    """
    model = YOLO(model_path)
    save_root = Path(out_dir)
    model.predict(
        source=source,
        imgsz=imgsz,
        conf=conf,
        iou=iou,
        device=device if device else None,
        save=True,
        project=str(save_root),
        name=run_name,
        exist_ok=True,
        verbose=False,
    )
    return save_root / run_name


def main():
    """
    主流程：
    1) 跑改进模型分数
    2) 跑原模型分数
    3) 对比排序并导出表格
    4) 复制“改进模型更好”的原图
    5) 保存两套模型的可视化预测图
    """
    args = parse_args()

    print("[1/5] Running improved model inference for scoring...")
    my_details = infer_details(
        args.my_model,
        args.source,
        args.imgsz,
        args.conf,
        args.iou,
        args.device,
        args.score_mode,
        args.topk,
    )

    print("[2/5] Running baseline model inference for scoring...")
    base_details = infer_details(
        args.base_model,
        args.source,
        args.imgsz,
        args.conf,
        args.iou,
        args.device,
        args.score_mode,
        args.topk,
    )

    print("[3/5] Comparing and ranking...")
    # 并集保证即使某一模型缺少某张图结果，也不会丢图
    all_images = sorted(set(my_details.keys()) | set(base_details.keys()))

    rows = []
    skipped_non_single_target = 0
    for image_path in all_images:
        my_info = my_details.get(
            image_path,
            {"score": 0.0, "count": 0, "top1_conf": 0.0, "top1_cls": None},
        )
        base_info = base_details.get(
            image_path,
            {"score": 0.0, "count": 0, "top1_conf": 0.0, "top1_cls": None},
        )

        # 单目标模式：必须两个模型在该图都检测到且都仅检测到 1 个目标
        if args.compare_mode == "single_target" and not (my_info["count"] == 1 and base_info["count"] == 1):
            skipped_non_single_target += 1
            continue

        # 某模型无该图结果时，默认该图分数为 0
        my_score = float(my_info["score"])
        base_score = float(base_info["score"])
        # 关键指标：差值 > 0 说明改进模型在该图上更好
        diff = my_score - base_score
        rows.append(
            {
                "image": image_path,
                "my_score": my_score,
                "base_score": base_score,
                "my_count": int(my_info["count"]),
                "base_count": int(base_info["count"]),
                "my_top1_cls": my_info["top1_cls"],
                "base_top1_cls": base_info["top1_cls"],
                "my_top1_conf": float(my_info["top1_conf"]),
                "base_top1_conf": float(base_info["top1_conf"]),
                "diff": diff,
            }
        )

    # 全部图片按差值降序，前面就是“提升最明显”的图片
    df_all = pd.DataFrame(rows).sort_values("diff", ascending=False).reset_index(drop=True)
    # 仅保留改进模型更好的图片
    df_better = df_all[df_all["diff"] > 0].copy().reset_index(drop=True)

    # 每次运行自动创建一个新子目录，避免覆盖历史结果
    run_dir = create_next_run_dir(args.out_dir, args.run_prefix)

    all_csv = run_dir / "conf_compare_all.csv"
    better_csv = run_dir / "conf_better_rank.csv"
    better_txt = run_dir / "conf_gain_rank.txt"
    better_img_dir = run_dir / "better_images"

    # 导出 CSV 便于后续在 Excel 中筛选、统计
    df_all.to_csv(all_csv, index=False, encoding="utf-8-sig")
    df_better.to_csv(better_csv, index=False, encoding="utf-8-sig")

    # 导出纯文本排行榜，便于快速浏览
    with better_txt.open("w", encoding="utf-8") as f:
        for idx, row in df_better.iterrows():
            f.write(
                f"{idx + 1:04d} | diff={row['diff']:.6f} | my={row['my_score']:.6f} | base={row['base_score']:.6f} | {row['image']}\n"
            )

    # 将“改进模型更好”的原图集中拷贝出来，便于人工快速查看
    print("[4/5] Copying better original images...")
    copied_count = 0
    if len(df_better) > 0:
        better_img_dir.mkdir(parents=True, exist_ok=True)
        for _, row in df_better.iterrows():
            src = Path(row["image"])
            if src.exists() and src.is_file():
                dst = better_img_dir / src.name
                # 同名时自动追加序号，避免覆盖
                if dst.exists():
                    stem, suffix = src.stem, src.suffix
                    idx = 1
                    while True:
                        candidate = better_img_dir / f"{stem}_{idx}{suffix}"
                        if not candidate.exists():
                            dst = candidate
                            break
                        idx += 1
                shutil.copy2(src, dst)
                copied_count += 1

    # 分别保存改进模型和原模型的预测可视化结果
    print("[5/5] Saving visual predictions for both models...")
    my_vis_dir = save_visual_predictions(
        model_path=args.my_model,
        source=args.source,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        out_dir=run_dir,
        run_name="pred_improved_model",
    )
    base_vis_dir = save_visual_predictions(
        model_path=args.base_model,
        source=args.source,
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        out_dir=run_dir,
        run_name="pred_base_model",
    )

    total = len(df_all)
    better_count = len(df_better)
    print(f"\nMode: {args.compare_mode}")
    if args.compare_mode == "single_target":
        print(f"Skipped non-single-target images: {skipped_non_single_target}")
    print(f"Total compared images: {total}")
    print(f"Run directory: {run_dir}")
    print(f"My model better on: {better_count}")
    print(f"Saved: {all_csv}")
    print(f"Saved: {better_csv}")
    print(f"Saved: {better_txt}")
    print(f"Saved better images: {better_img_dir} (count={copied_count})")
    print(f"Saved improved model predictions: {my_vis_dir}")
    print(f"Saved baseline model predictions: {base_vis_dir}")

    # 控制台显示前 topn 个提升最大的图片
    if better_count > 0:
        print(f"\nTop {min(args.topn, better_count)} images where my model is better:")
        for i, row in df_better.head(args.topn).iterrows():
            print(f"{i + 1:04d}. diff={row['diff']:.6f} | {row['image']}")


if __name__ == "__main__":
    main()
