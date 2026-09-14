from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile


class UploadValidationError(ValueError):
    pass


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
KNOWLEDGE_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}


@dataclass(frozen=True)
class StoredUpload:
    original_name: str
    stored_path: Path
    mime_type: str
    size_bytes: int
    sha256: str


async def store_upload(
    upload: UploadFile,
    target_dir: Path,
    max_bytes: int,
    allowed_extensions: set[str],
) -> StoredUpload:
    original_name = Path(upload.filename or "upload").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in allowed_extensions:
        raise UploadValidationError(f"不支持的文件类型：{suffix or '无扩展名'}")

    data = await upload.read(max_bytes + 1)
    if not data:
        raise UploadValidationError("上传文件为空")
    if len(data) > max_bytes:
        raise UploadValidationError(f"文件超过 {max_bytes // 1024 // 1024} MB 限制")

    target_dir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff_.-]+", "_", Path(original_name).stem).strip("._") or "upload"
    stored_path = target_dir / f"{stem}-{uuid.uuid4().hex[:12]}{suffix}"
    stored_path.write_bytes(data)
    return StoredUpload(
        original_name=original_name,
        stored_path=stored_path,
        mime_type=upload.content_type or "application/octet-stream",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
