from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import yaml
from ultralytics import YOLO


PRESETS = {
    "smoke": {"model": "yolo26m.pt", "epochs": 1, "imgsz": 640, "patience": 1, "name": "yolo26m-tt100k-smoke"},
    "baseline": {"model": "yolo26m.pt", "epochs": 80, "imgsz": 640, "patience": 25, "name": "yolo26m-tt100k-640"},
    "final": {"model": "yolo26l.pt", "epochs": 200, "imgsz": 960, "patience": 40, "name": "yolo26l-tt100k-960"},
}

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def smoke_data_file(data_path: Path, project: Path, validation_limit: int) -> Path:
    """为冒烟测试生成一个小验证清单，避免结束阶段遍历完整 8,016 张验证集。"""
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    val_dir = Path(str(data["val"]))
    if not val_dir.is_absolute():
        root = Path(str(data.get("path", data_path.parent)))
        val_dir = root / val_dir
    images = sorted(path.resolve() for path in val_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise ValueError(f"冒烟验证目录没有图片：{val_dir}")
    project.mkdir(parents=True, exist_ok=True)
    val_list = project / "_smoke_validation.txt"
    val_list.write_text("\n".join(str(path) for path in images[:validation_limit]), encoding="utf-8")
    data["val"] = str(val_list.resolve())
    smoke_yaml = project / "_smoke_tt100k.yaml"
    smoke_yaml.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return smoke_yaml


def main() -> None:
    parser = argparse.ArgumentParser(description="在 TT100K 上训练 YOLO26")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--preset", choices=PRESETS, default="smoke")
    parser.add_argument("--device", default="0")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch", default="-1", help="整数或 -1 自动批量")
    parser.add_argument("--project", type=Path, default=Path("runs"))
    parser.add_argument("--fraction", type=float, default=1.0, help="冒烟测试可用 0.01；正式训练保持 1.0")
    parser.add_argument("--no-val", action="store_true", help="仅用于快速冒烟；正式训练不要关闭验证")
    parser.add_argument("--smoke-val-limit", type=int, default=64, help="冒烟测试验证图片上限")
    parser.add_argument("--resume", action="store_true", help="从当前预设目录的 last.pt 恢复中断训练")
    parser.add_argument("--promote", action="store_true", help="完成后复制 best.pt 到系统 models 目录")
    args = parser.parse_args()
    preset = PRESETS[args.preset]
    batch = int(args.batch)
    project = args.project.resolve()
    data_path = args.data.resolve()
    if args.preset == "smoke":
        data_path = smoke_data_file(data_path, project, args.smoke_val_limit)
    run_dir = project / preset["name"]
    resume_weight = run_dir / "weights" / "last.pt"
    if args.resume:
        if not resume_weight.exists():
            raise FileNotFoundError(f"没有可恢复的检查点：{resume_weight}")
        model = YOLO(str(resume_weight))
        model.train(resume=True, device=args.device, workers=args.workers, batch=batch)
        return

    model = YOLO(preset["model"])
    model.train(
        data=str(data_path),
        epochs=preset["epochs"],
        imgsz=preset["imgsz"],
        batch=batch,
        device=args.device,
        workers=args.workers,
        amp=True,
        patience=preset["patience"],
        save_period=5,
        cache=False,
        seed=0,
        deterministic=True,
        fraction=args.fraction,
        val=not args.no_val,
        project=str(project),
        name=preset["name"],
        exist_ok=True,
    )
    weights_dir = run_dir / "weights"
    best = weights_dir / "best.pt"
    if not best.exists() and args.no_val:
        best = weights_dir / "last.pt"
    if args.promote:
        destination = Path(__file__).resolve().parents[1] / "models" / "yolo26-tt100k-best.pt"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(best, destination)
        print(f"已将最终权重复制到 {destination}")


if __name__ == "__main__":
    main()
