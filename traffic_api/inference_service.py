from __future__ import annotations

import threading
from typing import Any, Callable

from traffic_api.config import AppSettings, get_settings
from traffic_api.exceptions import ModelLoadError, ModelNotConfiguredError, PredictionError
from traffic_api.inference_core import PredictionOutput, run_prediction


class TrafficSignDetector:
    def __init__(self, settings: AppSettings | None = None, yolo_cls: Callable[[str], Any] | None = None):
        self.settings = settings or get_settings()
        self._yolo_cls = yolo_cls
        self._model: Any | None = None
        self._model_lock = threading.Lock()
        self._predict_lock = threading.Lock()
        self._load_count = 0

    @property
    def load_count(self) -> int:
        return self._load_count

    def get_model(self) -> Any:
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model
            self._model = self._load_model()
            self._load_count += 1
            return self._model

    def detect_image(self, image: Any) -> PredictionOutput:
        model = self.get_model()
        try:
            with self._predict_lock:
                return run_prediction(model, image, self.settings)
        except Exception as exc:
            raise PredictionError(f"YOLO prediction failed: {exc}") from exc

    def _load_model(self) -> Any:
        if self.settings.model_path is None:
            raise ModelNotConfiguredError()
        if not self.settings.model_path.exists():
            raise ModelNotConfiguredError(f"YOLO_MODEL_PATH does not exist: {self.settings.model_path}")

        yolo_cls = self._yolo_cls or _import_yolo()
        try:
            return yolo_cls(str(self.settings.model_path))
        except Exception as exc:
            raise ModelLoadError(f"Failed to load YOLO model from {self.settings.model_path}: {exc}") from exc


def _import_yolo() -> Callable[[str], Any]:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ModelLoadError("ultralytics is not installed or cannot be imported in this Python environment.") from exc
    return YOLO

