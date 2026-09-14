"""Browser/API regression for the existing Campus Safety Agent features.

The script intentionally exercises only functionality exposed by the current
application.  It creates one real inspection from the review demo queue and
one knowledge document so that the complete persistence path is verified.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Callable

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


FRONTEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = FRONTEND_ROOT.parent
BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:5175").rstrip("/")
OUTPUT_DIR = FRONTEND_ROOT / "output" / "playwright" / "standard-test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

results: list[dict[str, object]] = []
runtime: dict[str, object] = {}
browser_signals: dict[str, list[str]] = {
    "page_errors": [],
    "console_errors": [],
    "failed_requests": [],
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_case(name: str, action: Callable[[], None]) -> None:
    started = time.perf_counter()
    try:
        action()
    except Exception as exc:  # keep running so the report includes every area
        results.append(
            {
                "name": name,
                "status": "failed",
                "duration_seconds": round(time.perf_counter() - started, 3),
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=8),
            }
        )
    else:
        results.append(
            {
                "name": name,
                "status": "passed",
                "duration_seconds": round(time.perf_counter() - started, 3),
            }
        )


def attach_browser_observers(page: Page) -> None:
    page.on("pageerror", lambda error: browser_signals["page_errors"].append(str(error)))

    def on_console(message: object) -> None:
        if getattr(message, "type", "") == "error":
            browser_signals["console_errors"].append(str(getattr(message, "text", message)))

    def on_request_failed(request: object) -> None:
        url = str(getattr(request, "url", ""))
        failure = str(getattr(request, "failure", ""))
        browser_signals["failed_requests"].append(f"{url} :: {failure}")

    page.on("console", on_console)
    page.on("requestfailed", on_request_failed)


def goto(page: Page, path: str) -> None:
    response = page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=60_000)
    check(response is not None, f"{path} did not return a document response")
    check(response.status < 400, f"{path} returned HTTP {response.status}")


def wait_for_terminal_task(context: BrowserContext, task_id: str, timeout_seconds: int = 300) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = context.request.get(f"{BASE_URL}/api/v1/inspections/{task_id}", timeout=30_000)
        check(response.ok, f"inspection polling returned HTTP {response.status}")
        last = response.json()
        if last.get("status") in {"completed", "review", "error", "rejected"}:
            return last
        time.sleep(1.5)
    raise TimeoutError(f"inspection did not reach a terminal state; last={last.get('status')}")


def test_health_and_api_contract(context: BrowserContext) -> None:
    health_response = context.request.get(f"{BASE_URL}/api/v1/health")
    check(health_response.status == 200, f"health returned HTTP {health_response.status}")
    health = health_response.json()
    check(health.get("status") == "ok", "health status is not ok")
    check(health["services"]["database"] == "ok", "database health is not ok")
    check(health["services"]["qdrant"]["status"] == "ok", "Qdrant health is not ok")
    check(health["services"]["yolo"]["configured"] is True, "YOLO26 is not configured")
    check(health["services"]["general_yolo"]["enabled"] is True, "general YOLO26 is not enabled")
    check(health["services"]["general_yolo"]["configured"] is True, "general YOLO26 is not configured")
    check(health["services"]["amap"]["configured"] is True, "AMap is not configured")
    check("key" not in json.dumps(health, ensure_ascii=False).lower(), "health response exposes a key field")

    invalid_map = context.request.get(
        f"{BASE_URL}/api/v1/maps/static?lng=104&lat=30.5&zoom=18&width=1024&height=640"
    )
    check(invalid_map.status == 422, f"invalid map query should be 422, got {invalid_map.status}")

    static_map = context.request.get(
        f"{BASE_URL}/api/v1/maps/static?lng=103.997424&lat=30.515862&zoom=17&width=1024&height=640"
    )
    check(static_map.status in {200, 503}, f"static map returned unexpected HTTP {static_map.status}")
    if static_map.status == 200:
        check(static_map.headers.get("content-type", "").startswith("image/"), "static map is not an image")
        runtime["amap_live_status"] = "available"
    else:
        runtime["amap_live_status"] = "provider_unreachable_with_controlled_503"

    missing_task = context.request.get(f"{BASE_URL}/api/v1/inspections/not-a-real-task")
    check(missing_task.status == 404, f"missing inspection should be 404, got {missing_task.status}")


def test_dashboard(page: Page) -> None:
    goto(page, "/dashboard")
    page.get_by_text("风险事件队列", exact=False).first.wait_for(state="visible", timeout=30_000)
    page.get_by_text("今日巡检", exact=True).wait_for(state="visible", timeout=15_000)
    page.locator(".map-mode").wait_for(state="visible", timeout=15_000)
    page.wait_for_timeout(12_000)
    mode_text = page.locator(".map-mode").inner_text()
    check(mode_text in {"校园 GIS 备用图", "高德底图 · 实时态势"}, f"unexpected map mode: {mode_text}")
    runtime["dashboard_map_mode"] = mode_text
    check(page.locator("nav.primary-nav a").count() == 7, "sidebar should expose seven current feature routes")
    page.screenshot(path=str(OUTPUT_DIR / "01-dashboard-desktop.png"), full_page=True)


def test_analytics(page: Page, context: BrowserContext) -> None:
    response = context.request.get(f"{BASE_URL}/api/v1/analytics/overview")
    check(response.status == 200, f"analytics API returned HTTP {response.status}")
    payload = response.json()
    check(payload.get("summary", {}).get("total_tasks", 0) >= 1, "analytics summary contains no persisted tasks")
    check(len(payload.get("daily_trend", [])) == 30, "analytics trend should contain 30 calendar days")
    check(bool(payload.get("area_breakdown")), "analytics area breakdown is empty")
    check(bool(payload.get("agent_performance")), "analytics agent performance is empty")

    goto(page, "/analytics")
    page.get_by_role("heading", name="巡检数据分析", exact=True).wait_for(state="visible", timeout=20_000)
    page.locator(".chart-panel").first.wait_for(state="visible", timeout=20_000)
    page.wait_for_timeout(1_500)
    check(page.locator(".chart-panel").count() == 7, "analytics page should expose seven decision panels")
    check(page.locator(".data-chart canvas").count() >= 7, "analytics charts did not render to canvas")
    check(page.get_by_text("累计巡检", exact=True).count() == 1, "analytics KPI strip is missing")
    metrics = page.evaluate(
        """() => ({
          viewport: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          panelWidths: [...document.querySelectorAll('.chart-panel')].map((node) => node.getBoundingClientRect().width)
        })"""
    )
    check(metrics["documentWidth"] <= metrics["viewport"] + 1, f"analytics page overflows horizontally: {metrics}")
    check(min(metrics["panelWidths"]) >= 300, f"analytics contains an unusably narrow panel: {metrics}")
    runtime["analytics_summary"] = payload["summary"]
    runtime["analytics_desktop_metrics"] = metrics
    page.screenshot(path=str(OUTPUT_DIR / "02-analytics-desktop.png"), full_page=True)


def test_navigation_and_empty_form(page: Page) -> None:
    expected_pages = {
        "/analytics": "巡检数据分析",
        "/inspection/new": "创建现场巡检",
        "/inspections": "历史巡检记录",
        "/reviews": "人工复核队列",
        "/knowledge": "校园交通安全知识库",
        "/settings": "服务与访问配置",
    }
    for path, heading in expected_pages.items():
        goto(page, path)
        page.get_by_role("heading", name=heading, exact=True).wait_for(state="visible", timeout=20_000)

    goto(page, "/inspection/new")
    page.get_by_role("button", name="开始智能巡检", exact=True).click()
    page.get_by_text("请填写地点并选择巡检图片", exact=True).wait_for(state="visible", timeout=10_000)


def test_review_end_to_end(page: Page, context: BrowserContext) -> None:
    goto(page, "/reviews")
    page.get_by_role("heading", name="人工复核队列", exact=True).wait_for(state="visible", timeout=20_000)
    page.locator(".review-list article").first.wait_for(state="visible", timeout=20_000)
    demo_button = page.get_by_role("button", name="生成并复核", exact=True).first
    if demo_button.count():
        action_button = demo_button
        runtime["review_queue_source"] = "demo_materialized"
    else:
        action_button = page.get_by_role("button", name="进入复核", exact=True).first
        action_button.wait_for(state="visible", timeout=20_000)
        runtime["review_queue_source"] = "persisted_task"
    page.screenshot(path=str(OUTPUT_DIR / "03-review-queue-before.png"), full_page=True)
    action_button.click()
    page.wait_for_url(re.compile(r"/inspection/[0-9a-f-]{36}$"), timeout=90_000)
    task_id = page.url.rsplit("/", 1)[-1]
    check(bool(re.fullmatch(r"[0-9a-f-]{36}", task_id)), f"unexpected inspection id: {task_id}")
    runtime["inspection_task_id"] = task_id

    # A repeated acceptance run can start with a persisted review task.  Opening
    # that task does not exercise inference in the fresh backend process, so
    # explicitly use the product's existing "重新执行" capability before making
    # model-retention assertions.  Demo-materialized tasks already auto-execute.
    if runtime["review_queue_source"] == "persisted_task":
        execute_response = context.request.post(f"{BASE_URL}/api/v1/inspections/{task_id}/execute")
        check(execute_response.status == 202, f"persisted task re-execution returned HTTP {execute_response.status}")

    task = wait_for_terminal_task(context, task_id)
    runtime["inspection_task_no"] = task.get("task_no")
    runtime["inspection_location"] = task.get("location")
    runtime["inspection_terminal_status"] = task.get("status")
    runtime["inspection_analysis_mode"] = (task.get("risk_result") or {}).get("analysis_mode")
    check(task.get("status") == "review", f"new review task ended as {task.get('status')}")
    check(task.get("review_required") is True, "new review task did not request human confirmation")
    check(bool(task.get("report_id")), "workflow did not generate a report")

    trace_response = context.request.get(f"{BASE_URL}/api/v1/inspections/{task_id}/trace")
    check(trace_response.status == 200, f"trace API returned HTTP {trace_response.status}")
    trace_steps = trace_response.json().get("steps", [])
    detect_steps = [step for step in trace_steps if step.get("node_name") == "detect_traffic_signs"]
    check(detect_steps, "workflow never invoked the YOLO26 detection node")
    check(detect_steps[-1].get("status") == "success", f"YOLO26 detection failed: {detect_steps[-1].get('error_message')}")
    check(not [step for step in trace_steps if step.get("status") == "error"], "workflow trace contains an error step")
    check(
        runtime["inspection_analysis_mode"] not in {"error_guardrail", "fatal_error_guardrail", "manual_review_guardrail"},
        f"workflow used an error-protection analysis mode: {runtime['inspection_analysis_mode']}",
    )

    post_run_health = context.request.get(f"{BASE_URL}/api/v1/health").json()
    check(post_run_health["services"]["yolo"]["loaded"] is True, "YOLO26 was not retained in process memory")
    check(post_run_health["services"]["yolo"]["load_count"] >= 1, "YOLO26 has no successful load")
    check(post_run_health["services"]["general_yolo"]["loaded"] is True, "general YOLO26 was not retained in memory")
    check(post_run_health["services"]["general_yolo"]["load_count"] >= 1, "general YOLO26 has no successful load")
    runtime["yolo_model_name"] = post_run_health["services"]["yolo"]["model_name"]
    runtime["yolo_load_count"] = post_run_health["services"]["yolo"]["load_count"]

    page.reload(wait_until="domcontentloaded")
    confirm = page.get_by_role("button", name="人工确认", exact=True)
    confirm.wait_for(state="visible", timeout=30_000)
    page.get_by_text("AI Agent 执行轨迹", exact=True).wait_for(state="visible", timeout=20_000)
    check(page.locator(".trace-item").count() >= 4, "agent execution trace has fewer than four recorded steps")
    uncertainty = page.locator(".uncertainty").inner_text()
    check("WinError" not in uncertainty, "raw LLM transport details leaked into the user interface")
    if runtime["inspection_analysis_mode"] == "rules_only":
        check("已自动切换为规则保守模式" in uncertainty, "rules-only fallback is not explained to the user")
    page.screenshot(path=str(OUTPUT_DIR / "04-inspection-before-confirm.png"), full_page=True)

    report_response = context.request.get(f"{BASE_URL}/api/v1/reports/{task['report_id']}")
    check(report_response.status == 200, f"report API returned HTTP {report_response.status}")
    report = report_response.json()
    check("校园交通安全智能巡检报告" in report.get("html_content", ""), "report content is incomplete")

    confirm.click()
    page.get_by_text("人工复核已确认", exact=True).wait_for(state="visible", timeout=15_000)
    page.wait_for_timeout(1_000)
    confirmed_response = context.request.get(f"{BASE_URL}/api/v1/inspections/{task_id}")
    check(confirmed_response.status == 200, "confirmed inspection could not be fetched")
    confirmed = confirmed_response.json()
    check(confirmed.get("status") == "completed", "manual confirmation did not complete the task")
    check(confirmed.get("review_required") is False, "manual confirmation did not clear review_required")
    page.screenshot(path=str(OUTPUT_DIR / "05-inspection-confirmed.png"), full_page=True)


def test_archive_persistence(page: Page) -> None:
    task_id = str(runtime.get("inspection_task_id", ""))
    check(bool(task_id), "review flow did not produce a task id")
    goto(page, "/inspections")
    page.get_by_role("heading", name="历史巡检记录", exact=True).wait_for(state="visible", timeout=20_000)
    task_no = str(runtime.get("inspection_task_no", ""))
    location = str(runtime.get("inspection_location", ""))
    lookup_text = task_no or location
    check(bool(lookup_text), "review flow did not retain an archive lookup value")
    page.get_by_text(lookup_text, exact=True).first.wait_for(state="visible", timeout=20_000)
    row = page.locator(".el-table__body tr").filter(has_text=task_no) if task_no else page.locator(".missing-row")
    if row.count() == 0 and location:
        row = page.locator(".el-table__body tr").filter(has_text=location)
    check(row.count() >= 1, "newly confirmed inspection is missing from the archive")
    check("已完成" in row.first.inner_text(), "archive row does not show completed status")


def test_knowledge_upload_and_search(page: Page) -> None:
    source = PROJECT_ROOT / "docs" / "DEMO_GUIDE.md"
    check(source.is_file(), f"knowledge fixture is missing: {source}")
    goto(page, "/knowledge")
    page.locator('input[type="file"]').set_input_files(str(source))
    page.get_by_role("button", name="解析并入库", exact=True).click()
    page.get_by_text("知识文档已入库", exact=True).wait_for(state="visible", timeout=60_000)
    page.get_by_text("DEMO_GUIDE.md", exact=True).first.wait_for(state="visible", timeout=20_000)

    search_input = page.get_by_placeholder("例如：停车场标志被遮挡如何处置？")
    search_input.fill("人工复核和巡检图片应如何处理")
    page.get_by_role("button", name="检索", exact=True).click()
    page.locator(".hit-list article").first.wait_for(state="visible", timeout=30_000)
    check(page.locator(".hit-list article").count() >= 1, "knowledge search returned no visible results")
    page.screenshot(path=str(OUTPUT_DIR / "06-knowledge-search.png"), full_page=True)


def test_settings(page: Page) -> None:
    goto(page, "/settings")
    page.get_by_text("高德地图", exact=True).wait_for(state="visible", timeout=20_000)
    page.get_by_text("Web 服务已配置", exact=True).wait_for(state="visible", timeout=20_000)
    page.get_by_text(re.compile(r"deepseek-v4-flash.*已配置", re.IGNORECASE)).wait_for(
        state="visible", timeout=20_000
    )
    check(page.locator("text=离线预览").count() == 0, "settings unexpectedly entered offline preview")


def test_mobile_layout(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN")
    page = context.new_page()
    try:
        goto(page, "/dashboard")
        page.get_by_text("风险事件队列", exact=False).first.wait_for(state="visible", timeout=30_000)
        page.wait_for_timeout(1_000)
        metrics = page.evaluate(
            """() => ({
              viewport: window.innerWidth,
              documentWidth: document.documentElement.scrollWidth,
              bodyWidth: document.body.scrollWidth,
              sidebarPosition: getComputedStyle(document.querySelector('.sidebar')).position
            })"""
        )
        check(metrics["documentWidth"] <= metrics["viewport"] + 1, f"mobile page overflows: {metrics}")
        check(metrics["bodyWidth"] <= metrics["viewport"] + 1, f"mobile body overflows: {metrics}")
        page.screenshot(path=str(OUTPUT_DIR / "07-dashboard-mobile.png"), full_page=True)
        runtime["mobile_metrics"] = metrics

        goto(page, "/analytics")
        page.get_by_role("heading", name="巡检数据分析", exact=True).wait_for(state="visible", timeout=20_000)
        page.wait_for_timeout(1_000)
        analytics_metrics = page.evaluate(
            """() => ({
              viewport: window.innerWidth,
              documentWidth: document.documentElement.scrollWidth,
              navItems: document.querySelectorAll('nav.primary-nav a').length,
              panels: document.querySelectorAll('.chart-panel').length
            })"""
        )
        check(analytics_metrics["documentWidth"] <= analytics_metrics["viewport"] + 1, f"mobile analytics overflows: {analytics_metrics}")
        check(analytics_metrics["navItems"] == 7, "mobile navigation is missing the analytics route")
        check(analytics_metrics["panels"] == 7, "mobile analytics panel count is incorrect")
        runtime["analytics_mobile_metrics"] = analytics_metrics
        page.screenshot(path=str(OUTPUT_DIR / "08-analytics-mobile.png"), full_page=True)
    finally:
        context.close()
        browser.close()


def main() -> int:
    started = time.perf_counter()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1492, "height": 1072}, locale="zh-CN")
        page = context.new_page()
        attach_browser_observers(page)
        try:
            run_case("API health, dependency state, map validation, and 404 boundary", lambda: test_health_and_api_contract(context))
            run_case("Dashboard desktop rendering and AMap/local-map fallback", lambda: test_dashboard(page))
            run_case("Analytics API, seven chart panels, and desktop layout", lambda: test_analytics(page, context))
            run_case("All current routes and new-inspection empty-form validation", lambda: test_navigation_and_empty_form(page))
            run_case("Review queue to real YOLO/Agent task to manual confirmation", lambda: test_review_end_to_end(page, context))
            run_case("Confirmed inspection persists in archive", lambda: test_archive_persistence(page))
            run_case("Knowledge document upload, indexing, and semantic search", lambda: test_knowledge_upload_and_search(page))
            run_case("Settings reports DeepSeek and AMap server configuration", lambda: test_settings(page))
            run_case("Mobile dashboard layout has no document-level overflow", lambda: test_mobile_layout(playwright))
        finally:
            context.close()
            browser.close()

    expected_console_errors = [
        item for item in browser_signals["console_errors"]
        if "503 (Service Unavailable)" in item
    ]
    unexpected_console_errors = [
        item for item in browser_signals["console_errors"]
        if item not in expected_console_errors
    ]
    expected_request_failures = [
        item for item in browser_signals["failed_requests"]
        if "ERR_ABORTED" in item
    ]
    unexpected_request_failures = [
        item for item in browser_signals["failed_requests"]
        if item not in expected_request_failures
    ]
    runtime["expected_browser_fallback_signals"] = {
        "map_503_console_errors": len(expected_console_errors),
        "navigation_or_closed_stream_aborts": len(expected_request_failures),
    }
    unexpected_browser_errors = (
        browser_signals["page_errors"] + unexpected_console_errors + unexpected_request_failures
    )
    if unexpected_browser_errors:
        results.append(
            {
                "name": "No unexpected browser runtime, console, or network errors",
                "status": "failed",
                "duration_seconds": 0,
                "error": "; ".join(unexpected_browser_errors),
            }
        )
    else:
        results.append(
            {
                "name": "No unexpected browser runtime, console, or network errors",
                "status": "passed",
                "duration_seconds": 0,
            }
        )

    report = {
        "base_url": BASE_URL,
        "started_at_epoch": time.time() - (time.perf_counter() - started),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "summary": {
            "passed": sum(item["status"] == "passed" for item in results),
            "failed": sum(item["status"] == "failed" for item in results),
            "total": len(results),
        },
        "runtime": runtime,
        "browser_signals": browser_signals,
        "cases": results,
    }
    report_path = OUTPUT_DIR / "e2e-result.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), **report["summary"]}, ensure_ascii=False))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
