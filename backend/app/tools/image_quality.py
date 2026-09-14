from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.config import Settings


class ImageQualityTool:
    """使用可解释的传统图像指标检查输入质量。"""

    def __init__(self, settings: Settings):
        self.settings = settings

    def analyze_path(self, image_path: str | Path) -> dict[str, Any]:
        try:
            image = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        except (OSError, ValueError):
            image = None
        if image is None:
            return {
                "blurred": False,
                "dark": False,
                "overexposed": False,
                "too_small": False,
                "valid": False,
                "analyzable": False,
                "width": 0,
                "height": 0,
                "blur_score": None,
                "blur_score_raw": None,
                "blur_normalized_long_side": self.settings.blur_normalize_long_side,
                "mean_brightness": None,
                "message": "图片无法解码或文件已损坏",
            }
        return self.analyze(image)

    def analyze(self, image: Any) -> dict[str, Any]:
        if image is None or not hasattr(image, "shape") or len(image.shape) not in (2, 3):
            raise ValueError("image must be a decoded grayscale or color image")

        height, width = int(image.shape[0]), int(image.shape[1])
        gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        raw_blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        normalized_gray = self._normalize_for_blur(gray)
        blur_score = float(cv2.Laplacian(normalized_gray, cv2.CV_64F).var())
        mean_brightness = float(gray.mean())
        blurred = blur_score < self.settings.blur_threshold
        dark = mean_brightness < self.settings.dark_threshold
        overexposed = mean_brightness > self.settings.bright_threshold
        too_small = width < self.settings.min_image_width or height < self.settings.min_image_height

        issues: list[str] = []
        if blurred:
            issues.append("图片可能模糊")
        if dark:
            issues.append("图片过暗")
        if overexposed:
            issues.append("图片可能过曝")
        if too_small:
            issues.append(
                f"图片尺寸过小（至少 {self.settings.min_image_width}×{self.settings.min_image_height}）"
            )

        return {
            "blurred": blurred,
            "dark": dark,
            "overexposed": overexposed,
            "too_small": too_small,
            "valid": not issues,
            # A decoded image can still be analysed even when quality warnings
            # require a cautious/manual final decision.  Only corrupt or
            # undecodable inputs are non-analyzable.
            "analyzable": True,
            "width": width,
            "height": height,
            "blur_score": round(blur_score, 2),
            "blur_score_raw": round(raw_blur_score, 2),
            "blur_normalized_long_side": self.settings.blur_normalize_long_side,
            "mean_brightness": round(mean_brightness, 2),
            "message": "；".join(issues) if issues else "图片质量检查通过",
        }

    def _normalize_for_blur(self, gray: Any) -> Any:
        height, width = int(gray.shape[0]), int(gray.shape[1])
        target = self.settings.blur_normalize_long_side
        long_side = max(height, width)
        if long_side == target:
            return gray
        scale = target / long_side
        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
        return cv2.resize(
            gray,
            (max(1, round(width * scale)), max(1, round(height * scale))),
            interpolation=interpolation,
        )
