"""Actual browser video upload/inference/playback in disposable local stores."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BROWSER = Path(os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE", r"local-path/chrome-headless-shell.exe"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    video = args.video.resolve(strict=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    ports = (8003, 5177)
    for port in ports:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    cases, signals, facts = [], [], {"isolated": True, "device_requested": "0", "media": str(video), "browser_executable": str(BROWSER)}

    def check(name, action):
        start = time.monotonic()
        try:
            action()
            cases.append({"name": name, "passed": True, "seconds": round(time.monotonic() - start, 2)})
        except Exception as exc:
            cases.append({"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}", "seconds": round(time.monotonic() - start, 2)})

    children = []
    with tempfile.TemporaryDirectory(prefix="demo-video-", dir=ROOT / "outputs") as temp:
        isolated = Path(temp)
        env = dict(os.environ, DATABASE_URL=f"sqlite:///{isolated / 'test.db'}", QDRANT_URL="", QDRANT_PATH=str(isolated / "qdrant"),
                   UPLOAD_DIR=str(isolated / "uploads"), OUTPUT_DIR=str(isolated / "outputs"), YOLO_DEVICE="0", API_KEY="",
                   YOLO_MODEL_PATH=str(ROOT / "models/yolo26-tt100k-best.pt"), GENERAL_YOLO_MODEL_PATH=str(ROOT / "models/yolo26m.pt"),
                   VITE_DEV_API_TARGET="http://127.0.0.1:8003")
        with (isolated / "process.log").open("w", encoding="utf-8") as log:
            try:
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                children.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8003"], cwd=ROOT / "backend", env=env, stdout=log, stderr=log, creationflags=flags))
                children.append(subprocess.Popen([shutil.which("node") or "node", str(ROOT / "frontend/node_modules/vite/bin/vite.js"), "--host", "127.0.0.1", "--port", "5177", "--strictPort"], cwd=ROOT / "frontend", env=env, stdout=log, stderr=log, creationflags=flags))
                with httpx.Client(base_url="http://127.0.0.1:5177", trust_env=False, timeout=30) as client:
                    deadline = time.monotonic() + 90
                    while True:
                        try:
                            client.get("/api/v1/health").raise_for_status()
                            break
                        except httpx.HTTPError:
                            assert all(child.poll() is None for child in children), "Isolated service exited"
                            if time.monotonic() > deadline:
                                raise TimeoutError("Isolated service not ready")
                            time.sleep(1)
                    with sync_playwright() as pw:
                        browser = pw.chromium.launch(executable_path=str(BROWSER), headless=True)
                        page = browser.new_page(viewport={"width": 1440, "height": 1000})
                        page.on("pageerror", lambda error: signals.append(str(error)))
                        page.on("console", lambda message: signals.append(message.text) if message.type == "error" else None)
                        result = {}

                        def preview():
                            page.goto("http://127.0.0.1:5177/inspection/new")
                            page.get_by_text("视频轨迹分析", exact=True).click()
                            page.get_by_role("button", name="开始视频轨迹分析", exact=True).click()
                            page.get_by_text("请填写地点并选择巡检视频", exact=True).wait_for()
                            page.get_by_placeholder("例如：学校大门东侧入口").fill("隔离视频演示-配置方向非真值")
                            page.locator('.upload-zone input[type="file"]').set_input_files(str(video))
                            page.wait_for_function("document.querySelector('.upload-zone video')?.readyState >= 2", timeout=30000)
                            facts["source_playback_metadata"] = page.locator(".upload-zone video").evaluate("video => ({width: video.videoWidth, height: video.videoHeight, duration: video.duration})")
                            assert facts["source_playback_metadata"]["width"] > 0 and facts["source_playback_metadata"]["height"] > 0, "Browser decoded audio but no source video track"
                            page.locator(".upload-zone video").evaluate("video => video.play()")
                            page.wait_for_function("document.querySelector('.upload-zone video').currentTime > 0", timeout=15000)
                            page.locator(".upload-zone video").evaluate("video => video.pause()")
                        check("视频模式必填校验与真实原视频预览可解码", preview)

                        def analyze():
                            with page.expect_response(lambda response: response.url.endswith("/api/v1/video-analytics") and response.request.method == "POST", timeout=600000) as pending:
                                page.get_by_role("button", name="开始视频轨迹分析", exact=True).click()
                                page.get_by_text("正在上传并执行 YOLO26m + ByteTrack", exact=False).wait_for()
                            response = pending.value
                            assert response.status == 200, f"Video API status {response.status}"
                            result.update(response.json())
                            assert result["processed_frames"] > 0 and result["tracker"] == "ByteTrack" and result["unique_people_tracks"] > 0
                            assert client.get("/api/v1/health").json()["services"]["general_yolo"]["tracking_loaded"]
                            gpu = subprocess.run(["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=15)
                            assert str(children[0].pid) in gpu.stdout.split(), "GPU inference process not observed"
                            facts.update({key: result[key] for key in ("source_frames", "processed_frames", "frame_stride", "analysis_width", "analysis_height", "max_people_in_frame", "unique_people_tracks", "wrong_way_count", "duration_ms")})
                            facts["gpu_process_seen"] = True
                            facts["direction_note"] = "移动镜头与left_to_right只测规则配置，不代表实际逆行真值"
                            page.get_by_role("heading", name="视频轨迹分析结果", exact=True).wait_for()
                            values = page.locator(".video-metrics strong").all_inner_texts()
                            assert values == [str(result[key]) for key in ("max_people_in_frame", "unique_people_tracks", "unique_vehicle_tracks", "wrong_way_count")]
                            assert len(page.locator(".video-event-list article").all()) == len(result["events"])
                            page.screenshot(path=str(args.output.parent / "video-result.png"), full_page=True)
                        check("真实网页上传→GPU YOLO26m/ByteTrack→结果与事件显示一致", analyze)

                        def playback():
                            player = page.locator(".video-result-panel video")
                            page.wait_for_function("document.querySelector('.video-result-panel video')?.readyState >= 2", timeout=30000)
                            player.evaluate("video => video.play()")
                            page.wait_for_function("document.querySelector('.video-result-panel video').currentTime > 0", timeout=15000)
                            facts["result_playback"] = player.evaluate("video => ({width: video.videoWidth, height: video.videoHeight, duration: video.duration, currentTime: video.currentTime, error: video.error?.code || null})")
                            assert facts["result_playback"]["error"] is None
                            assert facts["result_playback"]["width"] > 0 and facts["result_playback"]["height"] > 0
                            local = Path(result["result_video_path"])
                            capture = cv2.VideoCapture(str(local))
                            ok, frame = capture.read()
                            capture.release()
                            assert ok and frame is not None
                            facts["result_opencv_decodable"] = True
                            player.evaluate("video => video.pause()")
                            page.screenshot(path=str(args.output.parent / "video-result.png"), full_page=True)
                        check("结果视频实际浏览器播放推进与本地解码", playback)

                        def mobile():
                            page.set_viewport_size({"width": 390, "height": 844})
                            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                            assert client.get("/api/v1/inspections").json()["total"] == 0, "Video-only feature unexpectedly created an image task"
                            assert not signals, "Browser reported an error"
                            page.screenshot(path=str(args.output.parent / "video-result-mobile.png"), full_page=True)
                        check("视频结果手机展示、无页面错误且不伪造图片归档", mobile)
                        browser.close()
            finally:
                for child in reversed(children):
                    child.terminate()
                    try:
                        child.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=15)
    report = {"verified_at": datetime.now(timezone.utc).isoformat(), "facts": facts, "cases": cases, "signals": signals,
              "passed": sum(item["passed"] for item in cases), "failed": sum(not item["passed"] for item in cases)}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
