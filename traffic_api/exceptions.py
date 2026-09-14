from __future__ import annotations


class TrafficAPIError(Exception):
    """Base class for API errors with stable machine-readable codes."""

    def __init__(self, message: str, code: str = "traffic_api_error", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class ModelNotConfiguredError(TrafficAPIError):
    def __init__(self, message: str = "YOLO_MODEL_PATH is not configured and no fallback best.pt was found."):
        super().__init__(message, code="model_not_configured", status_code=500)


class ModelLoadError(TrafficAPIError):
    def __init__(self, message: str):
        super().__init__(message, code="model_load_failed", status_code=500)


class PredictionError(TrafficAPIError):
    def __init__(self, message: str):
        super().__init__(message, code="prediction_failed", status_code=500)


class InvalidImageError(TrafficAPIError):
    def __init__(self, message: str):
        super().__init__(message, code="invalid_image", status_code=400)

