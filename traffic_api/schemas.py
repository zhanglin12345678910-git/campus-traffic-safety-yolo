from dataclasses import dataclass, field
from typing import List, Sequence


@dataclass
class ImageInfo:
    width: int
    height: int
    channels: int


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    box_xyxy: Sequence[float]


@dataclass
class DetectionResult:
    image: ImageInfo
    detections: List[Detection] = field(default_factory=list)
    success: bool = True
    message: str = "ok"
    elapsed_ms: float | None = None


__all__ = ["Detection", "DetectionResult", "ImageInfo"]
