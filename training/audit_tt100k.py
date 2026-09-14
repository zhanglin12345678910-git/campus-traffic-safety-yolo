from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def resolve_split(config_path: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        root = Path(config_path.parent)
        path_value = config_path_data.get("path")
        if path_value:
            root = Path(path_value)
        path = root / path
    return path


def label_dir_for(image_dir: Path) -> Path:
    parts = list(image_dir.parts)
    for index, part in enumerate(parts):
        if part.lower() == "images":
            parts[index] = "labels"
            return Path(*parts)
    return image_dir.parent.parent / "labels" / image_dir.name


def audit_split(name: str, image_dir: Path, nc: int) -> dict:
    label_dir = label_dir_for(image_dir)
    images = sorted(path for path in image_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    labels = sorted(label_dir.glob("*.txt")) if label_dir.exists() else []
    image_stems = {item.stem for item in images}
    label_stems = {item.stem for item in labels}
    invalid_lines = []
    empty_labels = []
    class_counts = [0] * nc
    for label in labels:
        lines = [line.strip() for line in label.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
        if not lines:
            empty_labels.append(str(label))
        for line_number, line in enumerate(lines, 1):
            parts = line.split()
            try:
                class_id = int(parts[0])
                coords = [float(value) for value in parts[1:]]
                valid = len(parts) == 5 and 0 <= class_id < nc and all(0 <= value <= 1 for value in coords)
                if not valid:
                    raise ValueError("越界或字段数错误")
                class_counts[class_id] += 1
            except (ValueError, IndexError) as exc:
                invalid_lines.append({"file": str(label), "line": line_number, "content": line, "error": str(exc)})
    return {
        "split": name,
        "image_dir": str(image_dir),
        "label_dir": str(label_dir),
        "images": len(images),
        "labels": len(labels),
        "missing_labels": sorted(image_stems - label_stems),
        "orphan_labels": sorted(label_stems - image_stems),
        "empty_labels": empty_labels,
        "invalid_lines": invalid_lines,
        "class_counts": class_counts,
    }


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_cross_split_duplicates(split_dirs: dict[str, Path]) -> list[dict]:
    seen: dict[str, tuple[str, str]] = {}
    duplicates = []
    for split, directory in split_dirs.items():
        for image in sorted(path for path in directory.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES):
            digest = file_digest(image)
            previous = seen.get(digest)
            if previous and previous[0] != split:
                duplicates.append({"sha256": digest, "first": previous, "duplicate": (split, str(image))})
            else:
                seen[digest] = (split, str(image))
    return duplicates


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 TT100K YOLO 数据划分和标签")
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("audit-report.json"))
    parser.add_argument("--hash-duplicates", action="store_true")
    args = parser.parse_args()
    global config_path_data
    config_path_data = yaml.safe_load(args.data.read_text(encoding="utf-8"))
    nc = int(config_path_data["nc"])
    split_dirs = {name: resolve_split(args.data, str(config_path_data[name])) for name in ("train", "val", "test")}
    report = {
        "data": str(args.data.resolve()),
        "nc": nc,
        "names": config_path_data.get("names", []),
        "splits": [audit_split(name, path, nc) for name, path in split_dirs.items()],
        "cross_split_duplicates": find_cross_split_duplicates(split_dirs) if args.hash_duplicates else "not_checked",
    }
    report["valid"] = all(
        not item["missing_labels"] and not item["orphan_labels"] and not item["invalid_lines"]
        for item in report["splits"]
    )
    summary = {"valid": report["valid"], "splits": [{"name": x["split"], "images": x["images"], "labels": x["labels"], "invalid": len(x["invalid_lines"]), "missing_labels": len(x["missing_labels"]), "orphan_labels": len(x["orphan_labels"]), "empty_labels": len(x["empty_labels"])} for x in report["splits"]]}
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["valid"] else 1


config_path_data: dict = {}


if __name__ == "__main__":
    raise SystemExit(main())
