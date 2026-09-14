from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from traffic_api.image_utils import get_image_info


@dataclass(frozen=True)
class ImageQualityReport:
    ok: bool
    width: int
    height: int
    channels: int
    message: str = "ok"


def assess_image_quality(image: Any, min_width: int = 16, min_height: int = 16) -> ImageQualityReport:
    info = get_image_info(image)
    if info.width < min_width or info.height < min_height:
        return ImageQualityReport(
            ok=False,
            width=info.width,
            height=info.height,
            channels=info.channels,
            message=f"image is too small; minimum size is {min_width}x{min_height}",
        )
    return ImageQualityReport(ok=True, width=info.width, height=info.height, channels=info.channels)

