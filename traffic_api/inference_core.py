from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from traffic_api.config import AppSettings
from traffic_api.image_utils import get_image_info
from traffic_api.schemas import Detection, DetectionResult


@dataclass
class PredictionOutput:
    detection_result: DetectionResult
    visual_image: Any | None
    raw_result: Any
    elapsed_ms: float


def run_prediction(model: Any, image: Any, settings: AppSettings) -> PredictionOutput:
    started = time.perf_counter()
    results = model.predict(
        image,
        device=settings.infer_device,
        imgsz=settings.img_size,
        conf=settings.conf_threshold,
        iou=settings.iou_threshold,
        verbose=False,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    raw_result = results[0]
    detection_result = prediction_result_to_detection_result(raw_result, image=image, elapsed_ms=elapsed_ms)
    visual_image = raw_result.plot() if hasattr(raw_result, "plot") else None
    return PredictionOutput(
        detection_result=detection_result,
        visual_image=visual_image,
        raw_result=raw_result,
        elapsed_ms=elapsed_ms,
    )


def prediction_result_to_detection_result(result: Any, image: Any | None = None, elapsed_ms: float | None = None) -> DetectionResult:
    source_image = image if image is not None else getattr(result, "orig_img", None)
    image_info = get_image_info(source_image)
    detections = extract_detections(result)
    message = f"detected {len(detections)} traffic signs" if detections else "no traffic sign detected"
    return DetectionResult(image=image_info, detections=detections, message=message, elapsed_ms=elapsed_ms)


def extract_detections(result: Any) -> list[Detection]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    class_ids = _as_list(getattr(boxes, "cls", []))
    confidences = _as_list(getattr(boxes, "conf", []))
    box_values = _as_list(getattr(boxes, "xyxy", []))
    names = getattr(result, "names", {})

    detections: list[Detection] = []
    for index in range(len(boxes)):
        class_id = int(_item(class_ids, index, 0))
        confidence = float(_item(confidences, index, 0.0))
        xyxy = tuple(float(value) for value in _item(box_values, index, (0.0, 0.0, 0.0, 0.0)))
        if len(xyxy) != 4:
            raise ValueError("YOLO xyxy box must contain exactly 4 values")
        detections.append(
            Detection(
                class_id=class_id,
                class_name=_class_name(names, class_id),
                confidence=confidence,
                box_xyxy=xyxy,
            )
        )

    return detections


def _item(values: Sequence[Any], index: int, default: Any) -> Any:
    try:
        return values[index]
    except (IndexError, TypeError):
        return default


def _class_name(names: Any, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
        return str(names[class_id])
    return str(class_id)


def _as_list(value: Any) -> list[Any]:
    converted = _to_plain_value(value)
    if converted is None:
        return []
    if isinstance(converted, list):
        return converted
    if isinstance(converted, tuple):
        return list(converted)
    if _is_iterable(converted):
        return list(converted)
    return [converted]


def _to_plain_value(value: Any) -> Any:
    current = value
    for method_name in ("cpu", "numpy", "tolist"):
        method = getattr(current, method_name, None)
        if callable(method):
            current = method()
    return current


def _is_iterable(value: Any) -> bool:
    if isinstance(value, (str, bytes)):
        return False
    return isinstance(value, Iterable)

