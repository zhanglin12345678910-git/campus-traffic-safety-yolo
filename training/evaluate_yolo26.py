from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import ultralytics
import yaml
from ultralytics import YOLO


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def count_split_images(data_path: Path, split: str) -> int:
    """独立统计评估清单，避免只凭参数声称使用了完整测试集。"""
    config = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    source = config.get(split)
    if source is None:
        raise ValueError(f"数据配置缺少 {split} 划分")
    root = Path(str(config.get("path", data_path.parent)))
    if not root.is_absolute():
        root = data_path.parent / root
    sources = source if isinstance(source, list) else [source]
    count = 0
    for item in sources:
        path = Path(str(item))
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            count += sum(1 for file in path.rglob("*") if file.suffix.lower() in IMAGE_SUFFIXES)
        elif path.is_file() and path.suffix.lower() == ".txt":
            count += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        elif path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
            count += 1
        else:
            raise FileNotFoundError(f"无法统计 {split} 数据源：{path}")
    return count


def normalize_names(raw_names: list | dict) -> list[str]:
    if isinstance(raw_names, list):
        return [str(name) for name in raw_names]
    if isinstance(raw_names, dict):
        try:
            keys = sorted(raw_names, key=lambda item: int(item))
        except (TypeError, ValueError) as exc:
            raise ValueError("类别名称字典的键必须可转换为整数") from exc
        return [str(raw_names[key]) for key in keys]
    raise TypeError(f"无法解析类别名称：{type(raw_names).__name__}")


def main() -> None:
    parser = argparse.ArgumentParser(description="在 TT100K 独立测试集上评估 YOLO26")
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--device", default="0")
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--end2end", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--expected-test-images", type=int, default=3992)
    parser.add_argument("--expected-classes", type=int, default=45)
    parser.add_argument("--expected-epochs", type=int, default=80)
    parser.add_argument("--output", type=Path, default=Path("evaluation-result.json"))
    args = parser.parse_args()
    weights_path = args.weights.resolve()
    data_path = args.data.resolve()
    if weights_path.name.lower() != "best.pt" or "smoke" in str(weights_path).lower():
        raise ValueError(f"正式评估只接受非冒烟 best.pt：{weights_path}")

    data_config = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    test_images = count_split_images(data_path, "test")
    if test_images != args.expected_test_images:
        raise ValueError(f"独立测试集应为 {args.expected_test_images} 张，实际为 {test_images} 张")
    dataset_names = normalize_names(data_config.get("names"))
    if len(dataset_names) != args.expected_classes:
        raise ValueError(f"数据集应为 {args.expected_classes} 类，实际为 {len(dataset_names)} 类")

    run_dir = weights_path.parent.parent
    training_args_path = run_dir / "args.yaml"
    training_results_path = run_dir / "results.csv"
    if not training_args_path.is_file() or not training_results_path.is_file():
        raise FileNotFoundError("正式权重目录缺少 args.yaml 或 results.csv，无法证明训练来源")
    training_args = yaml.safe_load(training_args_path.read_text(encoding="utf-8"))
    if float(training_args.get("fraction", 0)) != 1.0:
        raise ValueError(f"训练 fraction 不是 1.0：{training_args.get('fraction')}")
    if not bool(training_args.get("val")):
        raise ValueError("正式训练未启用验证集")
    if int(training_args.get("epochs", 0)) != args.expected_epochs:
        raise ValueError(f"训练计划轮次不是 {args.expected_epochs}：{training_args.get('epochs')}")
    if int(training_args.get("imgsz", 0)) != args.imgsz:
        raise ValueError(f"训练与评估图像尺寸不一致：{training_args.get('imgsz')} != {args.imgsz}")
    if "yolo26" not in str(training_args.get("name", "")).lower():
        raise ValueError(f"训练运行名无法证明 YOLO26 来源：{training_args.get('name')}")
    trained_data_path = Path(str(training_args.get("data", ""))).resolve()
    if trained_data_path != data_path:
        raise ValueError(f"训练与评估数据配置不一致：{trained_data_path} != {data_path}")

    result_lines = [line for line in training_results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    completed_epochs = max(0, len(result_lines) - 1)
    if completed_epochs < 1:
        raise ValueError("results.csv 没有完整训练轮次")

    model = YOLO(str(weights_path))
    model_names = normalize_names(model.names)
    if model_names != dataset_names:
        raise ValueError("best.pt 的类别名称或顺序与 TT100K 数据配置不一致")
    checkpoint = getattr(model, "ckpt", None)
    raw_checkpoint_epoch = checkpoint.get("epoch") if isinstance(checkpoint, dict) else None
    checkpoint_epoch_index = int(raw_checkpoint_epoch) if raw_checkpoint_epoch is not None else None
    metrics = model.val(
        data=str(data_path),
        split="test",
        imgsz=args.imgsz,
        device=args.device,
        batch=args.batch,
        workers=args.workers,
        end2end=args.end2end,
        plots=True,
    )
    speed = getattr(metrics, "speed", {}) or {}
    result = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "weights": str(weights_path),
        "weights_size_bytes": weights_path.stat().st_size,
        "weights_sha256": sha256(weights_path),
        "dataset_yaml": str(data_path),
        "dataset_yaml_sha256": sha256(data_path),
        "ultralytics_version": ultralytics.__version__,
        "class_count": len(model_names),
        "class_names": model_names,
        "split": "test",
        "test_images": test_images,
        "imgsz": args.imgsz,
        "end2end": args.end2end,
        "checkpoint_epoch_index": checkpoint_epoch_index,
        "checkpoint_completed_epoch": checkpoint_epoch_index + 1 if isinstance(checkpoint_epoch_index, int) else None,
        "training_artifacts": {
            "run_dir": str(run_dir),
            "args_yaml": str(training_args_path),
            "args_yaml_sha256": sha256(training_args_path),
            "results_csv": str(training_results_path),
            "results_csv_sha256": sha256(training_results_path),
            "completed_epochs": completed_epochs,
            "configured_epochs": int(training_args["epochs"]),
            "fraction": float(training_args["fraction"]),
            "validation_enabled": bool(training_args["val"]),
            "training_imgsz": int(training_args["imgsz"]),
            "training_batch": int(training_args["batch"]),
            "training_workers": int(training_args["workers"]),
            "training_name": str(training_args["name"]),
            "training_data": str(trained_data_path),
        },
        "integrity_checks": {
            "expected_test_images": args.expected_test_images,
            "expected_classes": args.expected_classes,
            "expected_epochs": args.expected_epochs,
            "full_training_fraction": True,
            "class_names_match_dataset": True,
            "training_data_matches_evaluation": True,
            "non_smoke_best_checkpoint": True,
        },
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "map50": float(metrics.box.map50),
        "map50_95": float(metrics.box.map),
        "speed_ms": {key: float(value) for key, value in speed.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
