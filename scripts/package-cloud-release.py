"""Create a secret-free cloud source/weights/prebuilt-web archive from current files.

Not git archive: the release includes valid uncommitted source edits. Production
data and raw campus media are never included. Linux shell files are LF-normalized.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cloud_admin import KNOWLEDGE_NAMES
from app.config import Settings

EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".runtime", "data", "node_modules", "output", "design-references", "incidents", "campus", ".git"}


def selected_files(root: Path):
    for folder in ("backend", "deploy", "frontend/dist", "frontend/src", "frontend/public"):
        for path in sorted((root / folder).rglob("*")):
            relative = path.relative_to(root)
            # Vite copies unused public campus originals into dist as well.
            # No current runtime source references these; do not publish them.
            if relative.as_posix().startswith(("frontend/public/campus/", "frontend/dist/campus/")):
                continue
            if path.is_file() and not EXCLUDED_PARTS.intersection(relative.parts):
                if path.suffix not in {".pyc", ".log", ".tsbuildinfo"} and not path.name.startswith(".env"):
                    yield path
    for name in (".dockerignore", "docker-compose.cloud.yml", "README.md", "models/README.md", "frontend/Dockerfile.cloud",
                 "frontend/Dockerfile", "frontend/.dockerignore", "frontend/nginx.conf", "frontend/package.json",
                 "frontend/package-lock.json", "frontend/index.html", "frontend/vite.config.ts", "frontend/tsconfig.json",
                 "frontend/tsconfig.app.json", "frontend/tsconfig.node.json", "frontend/DESIGN.md",
                 "scripts/package-cloud-release.py", "docs/DEPLOYMENT.md", "models/yolo26-tt100k-best.pt", "models/yolo26m.pt"):
        path = root / name
        if path.is_file():
            yield path
    for name in KNOWLEDGE_NAMES:
        yield root / "knowledge" / name


def packaged_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix == ".sh":
        data = data.replace(b"\r\n", b"\n")
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output already exists; choose a new archive name, do not overwrite a release")
    for name in ("frontend/dist/index.html", "backend/Dockerfile", "frontend/Dockerfile.cloud", "deploy/cloud.env.example",
                 "models/yolo26-tt100k-best.pt", "models/yolo26m.pt"):
        if not (ROOT / name).is_file() or not (ROOT / name).stat().st_size:
            raise SystemExit(f"Required release input missing: {name}")
    settings = Settings()
    secrets = [str(s).encode() for s in (settings.llm_api_key, settings.vision_llm_api_key, settings.amap_web_service_key, settings.api_key)
               if s and len(str(s)) >= 8]
    files = sorted(set(selected_files(ROOT)))
    manifest = {"created_utc": datetime.now(timezone.utc).isoformat(), "target": "linux/amd64 cpu",
                "training": "partial checkpoint; see model documentation", "history_migrated": False,
                "container_runtime_verified": False, "files": {}}
    # Scan before opening the output, so a detected credential cannot leak into a partial ZIP.
    text_extensions = {".py", ".md", ".json", ".yml", ".yaml", ".ts", ".vue", ".css", ".html", ".js", ".conf", ".sh", ".example", ".txt", ".ini", ".mako"}
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if not path.is_file():
            raise SystemExit(f"Required retained source missing: {relative}")
        data = packaged_bytes(path)
        if path.suffix in text_extensions or path.name.startswith("Dockerfile"):
            if any(secret in data for secret in secrets):
                raise SystemExit(f"Credential detected in release text: {relative}; archive not created")
        manifest["files"][relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            data = packaged_bytes(path)
            # Reject concurrent edits rather than package a mixed source snapshot.
            if hashlib.sha256(data).hexdigest() != manifest["files"][relative]["sha256"]:
                raise RuntimeError("Source changed during packaging; do not use this partial archive")
            archive.writestr("campus-safety-agent/" + relative, data)
        archive.writestr("campus-safety-agent/RELEASE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Archive CRC check failed")
        for relative, entry in manifest["files"].items():
            if hashlib.sha256(archive.read("campus-safety-agent/" + relative)).hexdigest() != entry["sha256"]:
                raise RuntimeError("Archive SHA-256 check failed")
    checksum = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"archive": str(args.output), "files": len(files), "bytes": args.output.stat().st_size,
                      "sha256": checksum, "crc_and_file_hashes": "passed", "known_credentials_scan": "passed",
                      "container_runtime_verified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
