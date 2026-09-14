"""Capture the current business pages at desktop and mobile viewports.

This is a visual-regression aid, not a product feature.  It also records
console, page and request failures so screenshots are never treated as the
only proof that a page rendered correctly.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:5173").rstrip("/")
OUTPUT_DIR = FRONTEND_ROOT / "output" / "playwright" / "ui-density-audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP_ROUTES = [
    ("01-dashboard-after", "/dashboard"),
    ("02-new-inspection-after", "/inspection/new"),
    ("03-inspections-after", "/inspections"),
    ("04-reviews-after", "/reviews"),
    ("05-knowledge-after", "/knowledge"),
    ("06-settings-after", "/settings"),
]
MOBILE_ROUTES = [
    ("m01-new-inspection", "/inspection/new"),
    ("m02-inspections", "/inspections"),
    ("m03-reviews", "/reviews"),
    ("m04-knowledge", "/knowledge"),
    ("m05-settings", "/settings"),
]
WIDE_ROUTES = [
    ("w01-new-inspection", "/inspection/new"),
    ("w02-inspections", "/inspections"),
    ("w03-reviews", "/reviews"),
    ("w04-knowledge", "/knowledge"),
    ("w05-settings", "/settings"),
]


def capture(page, name: str, path: str) -> None:
    response = page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=60_000)
    if response is None or response.status >= 400:
        raise RuntimeError(f"{path} returned {None if response is None else response.status}")
    page.screenshot(path=str(OUTPUT_DIR / f"{name}.png"), full_page=True)


def main() -> None:
    signals: dict[str, list[str]] = {"page_errors": [], "console_errors": [], "failed_requests": []}
    captured: list[dict[str, object]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda error: signals["page_errors"].append(str(error)))
        page.on("console", lambda message: signals["console_errors"].append(message.text) if message.type == "error" else None)
        page.on("requestfailed", lambda request: signals["failed_requests"].append(f"{request.method} {request.url}: {request.failure}"))

        for name, path in DESKTOP_ROUTES:
            capture(page, name, path)
            captured.append({"name": name, "path": path, "viewport": "1440x1000"})

        inspections = context.request.get(f"{BASE_URL}/api/v1/inspections", timeout=30_000)
        if inspections.ok:
            records = inspections.json().get("items", [])
            if records:
                detail_path = f"/inspection/{records[0]['id']}"
                capture(page, "07-detail-after", detail_path)
                captured.append({"name": "07-detail-after", "path": detail_path, "viewport": "1440x1000"})

        page.set_viewport_size({"width": 1920, "height": 1080})
        for name, path in WIDE_ROUTES:
            capture(page, name, path)
            captured.append({"name": name, "path": path, "viewport": "1920x1080"})

        page.set_viewport_size({"width": 390, "height": 844})
        for name, path in MOBILE_ROUTES:
            capture(page, name, path)
            captured.append({"name": name, "path": path, "viewport": "390x844"})

        browser.close()

    report = {"base_url": BASE_URL, "captured": captured, "signals": signals}
    (OUTPUT_DIR / "capture-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(signals.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
