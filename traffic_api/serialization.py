from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from traffic_api.schemas import Detection, DetectionResult, ImageInfo


def image_info_to_dict(image: ImageInfo) -> Dict[str, int]:
    return {
        "width": int(image.width),
        "height": int(image.height),
        "channels": int(image.channels),
    }


def detection_to_dict(detection: Detection) -> Dict[str, object]:
    box = [float(value) for value in detection.box_xyxy]
    if len(box) != 4:
        raise ValueError("Detection.box_xyxy must contain exactly 4 values")

    return {
        "class_id": int(detection.class_id),
        "class_name": str(detection.class_name),
        "confidence": float(detection.confidence),
        "box_xyxy": box,
    }


def summary_to_dict(detections: Iterable[Detection]) -> Dict[str, Optional[object]]:
    detection_list = list(detections)
    top_detection = max(detection_list, key=lambda item: float(item.confidence), default=None)

    return {
        "total": len(detection_list),
        "top_class": top_detection.class_name if top_detection is not None else None,
    }


def result_to_dict(result: DetectionResult) -> Dict[str, object]:
    detections: List[Detection] = list(result.detections)

    return {
        "success": bool(result.success),
        "message": str(result.message),
        "data": {
            "image": image_info_to_dict(result.image),
            "detections": [detection_to_dict(detection) for detection in detections],
            "summary": summary_to_dict(detections),
        },
    }


def result_to_contract_dict(
    result: DetectionResult,
    task_id: str,
    model_path: Path | str | None = None,
    device: str | None = None,
    img_size: int | None = None,
    conf_threshold: float | None = None,
    iou_threshold: float | None = None,
    result_image_url: str | None = None,
    filename: str | None = None,
    location: str | None = None,
    description: str | None = None,
    review_reasons: list[str] | None = None,
) -> Dict[str, Any]:
    detections = [detection_to_dict(detection) for detection in result.detections]
    reasons = list(review_reasons or [])
    return {
        "success": bool(result.success),
        "task_id": task_id,
        "image": {
            "filename": filename,
            **image_info_to_dict(result.image),
        },
        "model": {
            "weights": _model_weight_name(model_path),
            "device": device,
            "img_size": img_size,
            "conf_threshold": conf_threshold,
            "iou_threshold": iou_threshold,
        },
        "detections": detections,
        "object_count": len(detections),
        "review_required": bool(reasons),
        "review_reasons": reasons,
        "result_image_url": result_image_url,
        "timing": {
            "elapsed_ms": None if result.elapsed_ms is None else round(float(result.elapsed_ms), 2),
        },
        "location": location,
        "description": description,
        "error": None,
    }


def _model_weight_name(model_path: Path | str | None) -> str | None:
    if model_path is None:
        return None
    return Path(model_path).name


__all__ = [
    "detection_to_dict",
    "image_info_to_dict",
    "result_to_contract_dict",
    "result_to_dict",
    "summary_to_dict",
]
