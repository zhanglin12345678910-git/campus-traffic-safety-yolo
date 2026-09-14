import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("cloud_packager", ROOT / "scripts/package-cloud-release.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


def test_cloud_packager_excludes_raw_campus_and_runtime_data(tmp_path):
    for name in ("frontend/public/campus/raw.JPG", "frontend/dist/campus/raw.JPG", "backend/data/campus.db",
                 "backend/.runtime/runtime.py", "backend/.env.private", "backend/app/valid.py", "frontend/dist/index.html"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test", encoding="utf-8")
    names = {p.relative_to(tmp_path).as_posix() for p in packager.selected_files(tmp_path)}
    assert "backend/app/valid.py" in names and "frontend/dist/index.html" in names
    assert not any(n.startswith(("frontend/public/campus/", "frontend/dist/campus/", "backend/data/", "backend/.runtime/")) for n in names)
    assert not any(".env.private" in n for n in names)


def test_cloud_packager_normalizes_linux_shell_only(tmp_path):
    script = tmp_path / "entry.sh"
    script.write_bytes(b"#!/bin/sh\r\nexit 0\r\n")
    assert packager.packaged_bytes(script) == b"#!/bin/sh\nexit 0\n"
    assert script.read_bytes() == b"#!/bin/sh\r\nexit 0\r\n"
