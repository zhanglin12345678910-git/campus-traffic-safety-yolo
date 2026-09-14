from pathlib import Path
from typing import Any, Tuple

from traffic_api.schemas import ImageInfo


def _shape_tuple(image: Any) -> Tuple[int, ...]:
    shape = getattr(image, "shape", None)
    if shape is None:
        raise ValueError("Image must expose a numpy-like shape")

    try:
        values = tuple(int(value) for value in shape)
    except (TypeError, ValueError) as exc:
        raise ValueError("Image shape must be a sequence of integers") from exc

    if any(value <= 0 for value in values):
        raise ValueError("Image shape dimensions must be positive")

    return values


def ensure_rgb_or_bgr_image(image: Any) -> Any:
    shape = _shape_tuple(image)
    if len(shape) == 2:
        return image

    if len(shape) == 3 and shape[2] == 3:
        return image

    raise ValueError("Image must be 2D grayscale or 3D RGB/BGR with 3 channels")


def get_image_info(image: Any) -> ImageInfo:
    ensure_rgb_or_bgr_image(image)
    shape = _shape_tuple(image)

    if len(shape) == 2:
        height, width = shape
        channels = 1
    else:
        height, width, channels = shape

    return ImageInfo(width=width, height=height, channels=channels)


def _import_cv2(function_name: str) -> Any:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(f"cv2 is required for {function_name}") from exc

    return cv2


def _import_numpy(function_name: str) -> Any:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(f"numpy is required for {function_name}") from exc

    return np


def decode_image_bytes(data: bytes) -> Any:
    cv2 = _import_cv2("decode_image_bytes")
    np = _import_numpy("decode_image_bytes")

    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise ValueError("Image data must be bytes-like")

    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image bytes")

    return ensure_rgb_or_bgr_image(image)


def encode_image_jpeg(image: Any) -> bytes:
    ensure_rgb_or_bgr_image(image)
    cv2 = _import_cv2("encode_image_jpeg")

    success, encoded = cv2.imencode(".jpg", image)
    if not success:
        raise ValueError("Failed to encode image as JPEG")

    return encoded.tobytes()


def save_image(image: Any, path: Any) -> None:
    ensure_rgb_or_bgr_image(image)
    cv2 = _import_cv2("save_image")

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(str(output_path), image)
    if not success:
        raise ValueError(f"Failed to save image to {output_path}")


__all__ = [
    "decode_image_bytes",
    "encode_image_jpeg",
    "ensure_rgb_or_bgr_image",
    "get_image_info",
    "save_image",
]
