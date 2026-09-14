from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np

from app.config import Settings


class YOLOToolError(RuntimeError):
    pass


class TrafficSignDetectionTool:
    """Run the custom sign model and the official people/vehicle model.

    Both models are lazy-loaded and reused for the life of the backend process.
    The public class name is retained for API and test compatibility.
    """

    _GENERAL_DISPLAY_NAMES = {
        "person": "人员",
        "bicycle": "自行车",
        "car": "汽车",
        "motorcycle": "摩托车",
        "bus": "公交车",
        "truck": "货车",
    }

    def __init__(self, settings: Settings, yolo_factory: Callable[[str], Any] | None = None):
        self.settings = settings
        self._yolo_factory = yolo_factory
        self._model: Any | None = None
        self._general_model: Any | None = None
        self._load_lock = threading.Lock()
        self._general_load_lock = threading.Lock()
        self._predict_lock = threading.Lock()
        self.load_count = 0
        self.general_load_count = 0

    @property
    def model_loaded(self) -> bool:
        return self._model is not None

    @property
    def general_model_loaded(self) -> bool:
        return self._general_model is not None

    def _factory(self) -> Callable[[str], Any]:
        if self._yolo_factory is not None:
            return self._yolo_factory
        try:
            local_packages = Path(__file__).resolve().parents[2] / ".runtime" / "python-packages"
            if local_packages.is_dir() and str(local_packages) not in sys.path:
                # Append so the environment's pinned NumPy/OpenCV stack wins;
                # the local directory is only a fallback for missing packages
                # such as the ByteTrack LAP solver.
                sys.path.append(str(local_packages))
            # Keep Ultralytics runtime settings inside ignored application data
            # rather than the Windows roaming profile used by default.
            config_dir = self.settings.ultralytics_config_dir.resolve()
            config_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir))
            from ultralytics import YOLO
        except ImportError as exc:
            raise YOLOToolError("当前环境未安装 Ultralytics YOLO") from exc
        return YOLO

    def get_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            path = self.settings.yolo_model_path
            if not path.exists():
                raise YOLOToolError("等待真实交通标志模型权重：请配置 YOLO_MODEL_PATH")
            try:
                self._model = self._factory()(str(path))
            except Exception as exc:
                raise YOLOToolError(f"交通标志 YOLO 模型加载失败：{exc}") from exc
            self.load_count += 1
            return self._model

    def get_general_model(self) -> Any:
        if not self.settings.general_yolo_enabled:
            raise YOLOToolError("通用人员车辆模型未启用")
        if self._general_model is not None:
            return self._general_model
        with self._general_load_lock:
            if self._general_model is not None:
                return self._general_model
            self._general_model = self.create_general_model()
            self.general_load_count += 1
            return self._general_model

    def create_general_model(self) -> Any:
        """Load a new general-model instance that is not shared with image inference.

        ``model.track()`` registers ByteTrack callbacks on the model object and
        Ultralytics never removes them, and a predictor is not thread-safe.
        Video tracking therefore uses its own instance from this method instead
        of the ``get_general_model()`` singleton.
        """
        if not self.settings.general_yolo_enabled:
            raise YOLOToolError("通用人员车辆模型未启用")
        path = self.settings.general_yolo_model_path
        if not path.exists():
            raise YOLOToolError("等待通用人员车辆模型权重：请配置 GENERAL_YOLO_MODEL_PATH")
        try:
            return self._factory()(str(path))
        except Exception as exc:
            raise YOLOToolError(f"通用人员车辆 YOLO 模型加载失败：{exc}") from exc

    def detect(self, image_path: str | Path, conf: float | None = None, imgsz: int | None = None) -> dict[str, Any]:
        path = Path(image_path)
        if not path.exists():
            raise YOLOToolError("待检测图片不存在")

        original = self._read_image(path)
        height, width = int(original.shape[0]), int(original.shape[1])
        imgsz_value = self.settings.yolo_default_imgsz if imgsz is None else imgsz
        started = time.perf_counter()

        traffic_result = self._predict(
            self.get_model(),
            path,
            self.settings.yolo_default_conf if conf is None else conf,
            imgsz_value,
            "交通标志",
        )
        traffic_detections = self._extract_detections(
            traffic_result,
            model_role="traffic_sign",
            model_name=self.settings.yolo_model_path.name,
        )

        general_detections: list[dict[str, Any]] = []
        general_result: Any | None = None
        general_error: str | None = None
        if self.settings.general_yolo_enabled:
            try:
                general_result = self._predict(
                    self.get_general_model(),
                    path,
                    self.settings.general_yolo_default_conf,
                    imgsz_value,
                    "人员车辆",
                )
                general_detections = self._extract_detections(
                    general_result,
                    model_role="general_object",
                    model_name=self.settings.general_yolo_model_path.name,
                    allowed_names=self.settings.general_object_class_names,
                )
            except YOLOToolError as exc:
                # The custom traffic-sign workflow remains available if the
                # optional general model is temporarily unavailable.
                general_error = str(exc)

        detections = traffic_detections + general_detections
        vision_events = self._build_vision_events(general_detections)
        total_ms = (time.perf_counter() - started) * 1000

        result_dir = self.settings.output_dir / "detections"
        result_dir.mkdir(parents=True, exist_ok=True)
        result_name = f"{path.stem}-{uuid.uuid4().hex[:12]}.jpg"
        result_path = result_dir / result_name
        annotated = self._annotate(original.copy(), detections)
        encoded_ok, encoded = cv2.imencode(".jpg", annotated)
        if not encoded_ok:
            raise YOLOToolError("检测结果图保存失败")
        try:
            encoded.tofile(str(result_path))
        except OSError as exc:
            raise YOLOToolError(f"检测结果图保存失败：{exc}") from exc

        traffic_speed = getattr(traffic_result, "speed", {}) or {}
        general_speed = (getattr(general_result, "speed", {}) or {}) if general_result is not None else {}
        traffic_inference = self._round_optional(traffic_speed.get("inference"))
        general_inference = self._round_optional(general_speed.get("inference"))
        inference_values = [value for value in (traffic_inference, general_inference) if value is not None]

        return {
            "success": True,
            "image_width": width,
            "image_height": height,
            "detections": detections,
            "vision_events": vision_events,
            "object_count": len(detections),
            "model_name": self.settings.yolo_model_path.name,
            "models": [
                {
                    "role": "traffic_sign",
                    "name": self.settings.yolo_model_path.name,
                    "detections": len(traffic_detections),
                    "success": True,
                },
                {
                    "role": "general_object",
                    "name": self.settings.general_yolo_model_path.name,
                    "detections": len(general_detections),
                    "success": general_error is None and self.settings.general_yolo_enabled,
                    "error": general_error,
                },
            ],
            "result_image_path": str(result_path),
            "result_image_url": f"/outputs/detections/{result_name}",
            "timing": {
                "preprocess_ms": self._sum_speed(traffic_speed, general_speed, "preprocess"),
                "inference_ms": round(sum(inference_values), 2) if inference_values else None,
                "postprocess_ms": self._sum_speed(traffic_speed, general_speed, "postprocess"),
                "total_ms": round(total_ms, 2),
                "traffic_sign_inference_ms": traffic_inference,
                "general_object_inference_ms": general_inference,
            },
        }

    def _predict(self, model: Any, path: Path, conf: float, imgsz: int, label: str) -> Any:
        try:
            with self._predict_lock:
                results = model.predict(
                    str(path),
                    conf=conf,
                    iou=self.settings.yolo_default_iou,
                    imgsz=imgsz,
                    device=self.settings.yolo_device,
                    verbose=False,
                )
        except Exception as exc:
            raise YOLOToolError(f"{label} YOLO 推理失败：{exc}") from exc
        if not results:
            raise YOLOToolError(f"{label} YOLO 未返回推理结果")
        return results[0]

    def _extract_detections(
        self,
        result: Any,
        *,
        model_role: str,
        model_name: str,
        allowed_names: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        names = getattr(result, "names", {})
        detections: list[dict[str, Any]] = []
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections
        for box in boxes:
            class_id = int(box.cls[0].item())
            class_name = self._class_name(names, class_id)
            if allowed_names is not None and class_name.lower() not in allowed_names:
                continue
            confidence = float(box.conf[0].item())
            coords = [float(value) for value in box.xyxy[0].tolist()]
            detections.append(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "display_name": self._GENERAL_DISPLAY_NAMES.get(class_name.lower(), class_name),
                    "confidence": round(confidence, 6),
                    "bbox_xyxy": [round(value, 2) for value in coords],
                    "model_role": model_role,
                    "model_name": model_name,
                }
            )
        return detections

    def _build_vision_events(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.settings.crowd_detection_enabled:
            return []
        people = [item for item in detections if item["class_name"].lower() == "person"]
        count = len(people)
        if count < self.settings.crowd_min_persons:
            return []
        mean_confidence = sum(float(item["confidence"]) for item in people) / count
        return [
            {
                "event_type": "personnel_gathering",
                "label": "人员聚集候选",
                "severity": "high" if count >= self.settings.crowd_min_persons * 2 else "medium",
                "status": "candidate",
                "object_count": count,
                "threshold": self.settings.crowd_min_persons,
                "confidence": round(mean_confidence, 6),
                "model_name": self.settings.general_yolo_model_path.name,
                "requires_manual_review": True,
                "requires_video_confirmation": True,
                "evidence": f"静态图片中检测到 {count} 人，达到人员聚集阈值 {self.settings.crowd_min_persons} 人",
            }
        ]

    def _read_image(self, path: Path) -> np.ndarray:
        try:
            image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        except (OSError, ValueError):
            image = None
        if image is None:
            raise YOLOToolError("无法读取 YOLO 原始图像")
        return image

    @staticmethod
    def _annotate(image: np.ndarray, detections: list[dict[str, Any]]) -> np.ndarray:
        for item in detections:
            x1, y1, x2, y2 = (int(round(value)) for value in item["bbox_xyxy"])
            role = item.get("model_role", "traffic_sign")
            color = (255, 180, 35) if role == "traffic_sign" else (70, 220, 120)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)
            prefix = "SIGN" if role == "traffic_sign" else "GENERAL"
            label = f"{prefix}:{item['class_name']} {float(item['confidence']):.2f}"
            text_y = max(24, y1 - 8)
            cv2.putText(image, label, (max(0, x1), text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)
        return image

    @staticmethod
    def _class_name(names: Any, class_id: int) -> str:
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
            return str(names[class_id])
        return str(class_id)

    @staticmethod
    def _round_optional(value: Any) -> float | None:
        return None if value is None else round(float(value), 2)

    @classmethod
    def _sum_speed(cls, first: dict[str, Any], second: dict[str, Any], key: str) -> float | None:
        values = [cls._round_optional(source.get(key)) for source in (first, second)]
        present = [value for value in values if value is not None]
        return round(sum(present), 2) if present else None
