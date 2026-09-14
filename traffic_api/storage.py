from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from traffic_api.image_utils import save_image


def safe_stem(filename: str | None) -> str:
    if not filename:
        return "image"
    stem = Path(filename).stem
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
    return cleaned or "image"


def save_result_image(image: Any, save_dir: Path, original_filename: str | None = None) -> Path:
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{safe_stem(original_filename)}-{uuid.uuid4().hex[:12]}.jpg"
    output_path = save_dir / filename
    save_image(image, output_path)
    return output_path

