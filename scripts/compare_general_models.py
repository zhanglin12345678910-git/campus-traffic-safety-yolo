"""对比通用检测模型 yolo26n.pt（nano）与 yolo26m.pt（medium）在真实巡检图片上的置信度表现。

背景：系统最初用 `models/yolo26n.pt`（nano，5.5MB）做人员/车辆检测，
阈值 `general_yolo_default_conf=0.2` / `general_yolo_review_conf=0.35`。
实测多个巡检任务因「低置信度检测」被判定为 review（如 car 置信度仅 0.245~0.380），
项目现已把验证收益更好的 `models/yolo26m.pt`（medium，44MB）作为默认通用模型。

本脚本用同一批图片、同一阈值跑两个模型，量化置信度差异，
用于复现 nano 与 medium 的选型依据。

用法：
    <项目 python> scripts/compare_general_models.py
    <项目 python> scripts/compare_general_models.py --conf 0.2 --imgsz 640
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
import warnings
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

warnings.filterwarnings("ignore")

KEEP = ("person", "bicycle", "car", "motorcycle", "bus", "truck")
COCO_IDS = [0, 1, 2, 3, 5, 7]  # person, bicycle, car, motorcycle, bus, truck
ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "uploads/inspections"


def unique_images(directory: Path) -> tuple[list[Path], list[dict]]:
    """One inference per SHA-256 content, preserving all aliases as provenance."""
    groups: dict[str, list[Path]] = {}
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            groups.setdefault(digest, []).append(path)
    manifest = [
        {"sha256": digest, "representative": paths[0].name,
         "files": [p.name for p in paths]}
        for digest, paths in groups.items()
    ]
    return [paths[0] for paths in groups.values()], manifest


def run(model_path: str, images: list[Path], conf: float, imgsz: int, device: str = "cpu") -> dict[str, list[dict]]:
    from ultralytics import YOLO

    model = YOLO(model_path)
    result: dict[str, list[dict]] = {}
    for img in images:
        r = model.predict(source=str(img), conf=conf, imgsz=imgsz, classes=COCO_IDS, device=device, verbose=False)[0]
        boxes = []
        for box in r.boxes:
            boxes.append(
                {
                    "class": KEEP[COCO_IDS.index(int(box.cls[0].item()))],
                    "confidence": round(float(box.conf[0].item()), 6),
                }
            )
        result[img.name] = boxes
    return result


def summarize(boxes_by_img: dict[str, list[dict]], conf: float) -> dict:
    flat = [b for boxes in boxes_by_img.values() for b in boxes]
    confs = [b["confidence"] for b in flat]
    per_class: dict[str, list[float]] = defaultdict(list)
    for b in flat:
        per_class[b["class"]].append(b["confidence"])
    return {
        "total": len(flat),
        "images_with_detection": sum(1 for v in boxes_by_img.values() if v),
        "mean_conf": round(statistics.fmean(confs), 4) if confs else None,
        "max_conf": round(max(confs), 4) if confs else None,
        "below_review_threshold": sum(1 for c in confs if c < 0.35),
        "below_default_conf": sum(1 for c in confs if c < conf),
        "per_class": {
            k: {
                "count": len(v),
                "mean": round(statistics.fmean(v), 4),
                "max": round(max(v), 4),
            }
            for k, v in sorted(per_class.items())
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--conf", type=float, default=0.2, help="检测阈值，默认用系统配置 0.2")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--images", type=Path, default=IMG_DIR)
    ap.add_argument("--output", type=Path, default=ROOT / "outputs" / (
        "general_model_comparison_unique_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    ))
    args = ap.parse_args()
    if args.output.exists():
        ap.error("输出文件已存在；请使用新路径，保留历史取证结果")

    images, manifest = unique_images(args.images)
    if not images:
        raise SystemExit(f"{IMG_DIR} 下没有图片")
    file_count = sum(len(item["files"]) for item in manifest)
    print(f"文件 {file_count} 个 / 唯一图片 {len(images)} 张，conf={args.conf}，imgsz={args.imgsz}，device={args.device}\n")

    started = time.perf_counter()
    nano = run(str(ROOT / "models/yolo26n.pt"), images, args.conf, args.imgsz, args.device)
    nano_seconds = time.perf_counter() - started
    print("--- yolo26n (nano) 完成 ---", flush=True)
    started = time.perf_counter()
    medium = run(str(ROOT / "models/yolo26m.pt"), images, args.conf, args.imgsz, args.device)
    medium_seconds = time.perf_counter() - started
    print("--- yolo26m (medium) 完成 ---\n", flush=True)

    sn = summarize(nano, args.conf)
    sm = summarize(medium, args.conf)

    print("=" * 78)
    print(f"{'指标':<26}{'yolo26n (nano)':>22}{'yolo26m (medium)':>22}")
    print("-" * 78)
    rows = [
        ("检出总数", "total"),
        ("有检出的图片数", "images_with_detection"),
        ("平均置信度", "mean_conf"),
        ("最高置信度", "max_conf"),
        ("置信度 < 0.35（复核阈值）", "below_review_threshold"),
    ]
    for label, key in rows:
        print(f"{label:<26}{str(sn[key]):>22}{str(sm[key]):>22}")

    print("\n按类别对比（数量 / 平均置信度）：")
    print(f"{'类别':<14}{'nano':>20}{'medium':>20}   变化")
    print("-" * 78)
    for cls in KEEP:
        a = sn["per_class"].get(cls)
        b = sm["per_class"].get(cls)
        if not a and not b:
            continue
        sa = f"{a['count']} / {a['mean']}" if a else "-"
        sb = f"{b['count']} / {b['mean']}" if b else "-"
        delta = ""
        if a and b:
            d = b["mean"] - a["mean"]
            delta = f"均值 {d:+.3f}"
        print(f"{cls:<14}{sa:>20}{sb:>20}   {delta}")

    print("\n逐图对比（检出数 / 平均置信度）：")
    for img in images:
        a, b = nano[img.name], medium[img.name]
        ma = f"{statistics.fmean([x['confidence'] for x in a]):.3f}" if a else "-"
        mb = f"{statistics.fmean([x['confidence'] for x in b]):.3f}" if b else "-"
        print(f"  {img.name:<46} n={len(a):<3}({ma:>6})  m={len(b):<3}({mb:>6})")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file_count": file_count, "unique_image_count": len(images),
        "deduplication": "sha256_file_content", "manifest": manifest,
        "source_note": "混合来源巡检样本，非全部本校实拍；无人工真值，不计算准确率或召回率",
        "device": args.device, "conf": args.conf, "imgsz": args.imgsz,
        "review_threshold": 0.35,
        "elapsed_seconds_including_load": {"nano": nano_seconds, "medium": medium_seconds},
        "weight_sha256": {name: hashlib.sha256((ROOT / 'models' / filename).read_bytes()).hexdigest()
                          for name, filename in [('nano', 'yolo26n.pt'), ('medium', 'yolo26m.pt')]},
        "nano": sn, "medium": sm, "raw": {"nano": nano, "medium": medium},
    }
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        )
    print(f"\n详细结果已写入 {args.output}")


if __name__ == "__main__":
    main()
