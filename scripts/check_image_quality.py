"""诊断图片质量护栏的清晰度判定，辅助重新标定 blur_threshold。

背景：`backend/app/tools/image_quality.py` 先把图片长边归一化，再用
`cv2.Laplacian(gray, cv2.CV_64F).var() < blur_threshold` 判「模糊」。

该指标有两个设计缺陷，会在校园场景下**误杀**：

1. **它量的是「画面里有多少高频纹理」，不是「对焦准不准」**。
   实测对照：被判「模糊」的 `IMG_9794`（大面积纯色招牌 + 混凝土柱 + 湿地面）
   在 1:1 裁切下边缘清晰锐利，但得分仅 64.7；
   而一张「通过」的图 `IMG_9759` 因画面里全是树叶（每片叶子边缘都是高频细节）得分 2077.6。
   两者差距来自**纹理密度**，不是清晰度。
   对校园巡检尤其致命——墙面、路面、天空、标志牌都是低纹理画面。

2. **绝对阈值 + 未归一化，对分辨率极度敏感**。
   实测同一批图缩到长边 1024 后再算，`IMG_9794` 从 64.7 → **1010.3（涨 15.6 倍）**，
   `IMG_9769` 从 264.6 → **4060.6（涨 15.3 倍）**。

历史实现会在质量告警时直接跳过检测；当前实现只把告警作为人工复核理由，
可解码图片仍会继续完成 YOLO、知识检索与风险分析。本脚本用于防止阈值回归。

用法：
    <项目 python> scripts/check_image_quality.py                      # 扫描 uploads/inspections
    <项目 python> scripts/check_image_quality.py 图片路径 [更多路径...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings


SETTINGS = Settings()
CURRENT_THRESHOLD = SETTINGS.blur_threshold
NORMALIZE_LONG_SIDE = SETTINGS.blur_normalize_long_side
TILE_GRID = 4


def metrics(image: np.ndarray) -> dict[str, float]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    global_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    scale = NORMALIZE_LONG_SIDE / max(h, w)
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    resized = cv2.resize(
        gray,
        (max(1, round(w * scale)), max(1, round(h * scale))),
        interpolation=interpolation,
    )
    normalized_score = float(cv2.Laplacian(resized, cv2.CV_64F).var())

    th, tw = h // TILE_GRID, w // TILE_GRID
    tiles = [
        float(cv2.Laplacian(gray[i * th : (i + 1) * th, j * tw : (j + 1) * tw], cv2.CV_64F).var())
        for i in range(TILE_GRID)
        for j in range(TILE_GRID)
        if gray[i * th : (i + 1) * th, j * tw : (j + 1) * tw].size
    ]
    return {
        "global": global_score,
        "normalized": normalized_score,
        "tile_max": max(tiles) if tiles else 0.0,
        "tile_median": float(np.median(tiles)) if tiles else 0.0,
        "brightness": float(gray.mean()),
        "width": float(w),
        "height": float(h),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="图片路径；留空则扫描 uploads/inspections")
    args = ap.parse_args()

    if args.paths:
        images = [Path(p) for p in args.paths]
    else:
        d = Path("uploads/inspections")
        images = sorted(p for p in d.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})

    rows = []
    for path in images:
        img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"跳过（无法解码）：{path}")
            continue
        rows.append((path.name, metrics(img)))

    rows.sort(key=lambda r: r[1]["normalized"])

    print(
        f"当前阈值 blur_threshold = {CURRENT_THRESHOLD}"
        f"（判定依据：长边 {NORMALIZE_LONG_SIDE}px 的 Laplacian 方差）\n"
    )
    print(f"{'图片':<44}{'原图':>10}{'归一化':>10}{'分块最大':>10}{'分块中位':>10}  当前判定")
    print("-" * 100)
    for name, m in rows:
        verdict = "质量告警 <<<" if m["normalized"] < CURRENT_THRESHOLD else "通过"
        print(
            f"{name:<44}{m['global']:>10.1f}{m['normalized']:>10.1f}"
            f"{m['tile_max']:>10.1f}{m['tile_median']:>10.1f}  {verdict}"
        )

    failed = [r for r in rows if r[1]["normalized"] < CURRENT_THRESHOLD]
    passed = [r for r in rows if r[1]["normalized"] >= CURRENT_THRESHOLD]
    print()
    print(f"产生质量告警 {len(failed)} 张 / 判定通过 {len(passed)} 张")
    if failed:
        print("\n产生质量告警的图片，其归一化得分：")
        for name, m in failed:
            print(f"  {name:<44}{m['normalized']:>10.1f}")
    if passed:
        lo = min(m["normalized"] for _, m in passed)
        hi = max(m["normalized"] for _, m in passed)
        print(f"\n通过组归一化得分区间：{lo:.1f} ~ {hi:.1f}")


if __name__ == "__main__":
    main()
