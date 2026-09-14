"""Lightweight configuration for the traffic sign API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


MODEL_CANDIDATES = (
    Path("runs/train/TT100K-增强-yolo11-第一个实验-newt100k2/weights/best.pt"),
    Path("runs/train/579-pssm-消融/weights/best.pt"),
    Path("runs/train/ASPP-pssm-cctsdb-200e/weights/best.pt"),
)


@dataclass(frozen=True)
class AppSettings:
    app_name: str
    api_prefix: str
    infer_device: str
    img_size: int
    conf_threshold: float
    iou_threshold: float
    save_dir: Path
    model_path: Path | None
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_key: str | None = None


def get_settings(env: Mapping[str, str] | None = None, base_dir: Path | None = None) -> AppSettings:
    """Build app settings from environment-style values without importing heavy runtime deps."""
    values = os.environ if env is None else env
    root = Path(__file__).resolve().parents[1] if base_dir is None else Path(base_dir)

    return AppSettings(
        app_name=values.get("APP_NAME", "安巡智脑"),
        api_prefix=values.get("API_PREFIX", "/api/v1"),
        infer_device=_get_first(values, ("YOLO_DEVICE", "INFER_DEVICE"), "0"),
        img_size=_parse_int(values, ("YOLO_DEFAULT_IMGSZ", "IMG_SIZE"), 640),
        conf_threshold=_parse_float(values, ("YOLO_DEFAULT_CONF", "CONF_THRESHOLD"), 0.3),
        iou_threshold=_parse_float(values, ("YOLO_DEFAULT_IOU", "IOU_THRESHOLD"), 0.5),
        save_dir=_path_value(values, ("OUTPUT_DIR", "SAVE_DIR"), root / "outputs" / "detections", root),
        model_path=_model_path(values, root),
        api_host=values.get("API_HOST", "127.0.0.1"),
        api_port=_parse_int(values, "API_PORT", 8000),
        api_key=values.get("API_KEY") or None,
    )


def find_default_model_path(base_dir: Path | None = None) -> Path | None:
    root = Path(__file__).resolve().parents[1] if base_dir is None else Path(base_dir)
    for relative_path in MODEL_CANDIDATES:
        candidate = root / relative_path
        if candidate.exists():
            return candidate
    return None


Settings = AppSettings


def _parse_int(env: Mapping[str, str], name: str | tuple[str, ...], default: int) -> int:
    key, value = _get_named_value(env, name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer, got {value!r}") from exc


def _parse_float(env: Mapping[str, str], name: str | tuple[str, ...], default: float) -> float:
    key, value = _get_named_value(env, name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be a float, got {value!r}") from exc


def _path_value(env: Mapping[str, str], name: str | tuple[str, ...], default: Path, base_dir: Path) -> Path:
    _, value = _get_named_value(env, name)
    if value is None:
        return default
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def _model_path(env: Mapping[str, str], base_dir: Path) -> Path | None:
    configured_path = env.get("YOLO_MODEL_PATH")
    if configured_path is not None:
        path = Path(configured_path)
        return path if path.is_absolute() else base_dir / path

    return find_default_model_path(base_dir)


def _get_first(env: Mapping[str, str], names: tuple[str, ...], default: str) -> str:
    _, value = _get_named_value(env, names)
    return value if value is not None else default


def _get_named_value(env: Mapping[str, str], name: str | tuple[str, ...]) -> tuple[str, str | None]:
    names = (name,) if isinstance(name, str) else name
    for item in names:
        value = env.get(item)
        if value is not None:
            return item, value
    return names[-1], None
    return None
