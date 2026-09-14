from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.models import InspectionTask
from app.services.amap import StaticMapImage


def test_health_reports_components(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["services"]["database"] == "ok"
    assert body["services"]["qdrant"]["status"] == "ok"
    assert body["services"]["llm"]["configured"] is False
    assert body["services"]["amap"]["configured"] is False
    assert body["services"]["general_yolo"]["tracking_loaded"] is False
    assert body["services"]["general_yolo"]["tracking_load_count"] == 0


def test_weather_reports_unavailable_without_provider_key(client: TestClient):
    response = client.get("/api/v1/maps/weather")

    assert response.status_code == 200
    assert response.json() == {"available": False, "message": "高德 Web 服务 Key 尚未配置"}


def test_weather_proxy_returns_live_report_without_key(client: TestClient):
    class FakeAMapService:
        available = True

        @staticmethod
        def weather(adcode: str):
            assert adcode == "510116"
            return {"provider": "amap", "adcode": adcode, "weather": "多云", "temperature": "22"}

    client.app.state.amap_service = FakeAMapService()
    response = client.get("/api/v1/maps/weather", params={"adcode": "510116"})

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["temperature"] == "22"
    assert client.get("/api/v1/maps/weather", params={"adcode": "not-a-code"}).status_code == 422


def test_amap_static_map_proxy_hides_provider_key(client: TestClient):
    class FakeAMapService:
        available = True

        @staticmethod
        def static_map(**kwargs):
            assert kwargs == {
                "lng": 103.997424,
                "lat": 30.515862,
                "zoom": 17,
                "width": 1024,
                "height": 640,
                "traffic": False,
            }
            return StaticMapImage(b"map-image", "image/png")

    client.app.state.amap_service = FakeAMapService()
    response = client.get("/api/v1/maps/static")

    assert response.status_code == 200
    assert response.content == b"map-image"
    assert response.headers["content-type"].startswith("image/png")
    assert response.headers["x-map-provider"] == "amap"
    assert "key" not in str(response.url).lower()


def test_amap_geocode_proxy_returns_normalized_coordinates(client: TestClient):
    class FakeAMapService:
        available = True

        @staticmethod
        def geocode(address: str, city: str | None):
            assert address == "四川现代职业学院"
            assert city == "成都"
            return {
                "provider": "amap",
                "formatted_address": "四川省成都市双流区四川现代职业学院",
                "province": "四川省",
                "city": "成都市",
                "district": "双流区",
                "adcode": "510116",
                "level": "兴趣点",
                "location": {"lng": 103.997424, "lat": 30.515862},
            }

    client.app.state.amap_service = FakeAMapService()
    response = client.get("/api/v1/maps/geocode", params={"address": "四川现代职业学院", "city": "成都"})

    assert response.status_code == 200
    assert response.json()["location"] == {"lng": 103.997424, "lat": 30.515862}
    assert "key" not in str(response.url).lower()


def test_rejects_corrupted_image(client: TestClient):
    response = client.post(
        "/api/v1/inspections",
        data={"location": "停车场", "area_type": "停车场"},
        files={"file": ("bad.jpg", b"not-an-image", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "无法解码" in response.json()["detail"]


def test_rejects_unsupported_file(client: TestClient):
    response = client.post(
        "/api/v1/inspections",
        data={"location": "停车场", "area_type": "停车场"},
        files={"file": ("bad.exe", b"payload", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_video_analytics_upload_and_direction_validation(client: TestClient):
    class FakeVideoAnalytics:
        DIRECTIONS = {"left_to_right": ((1.0, 0.0), "从左向右")}

        @staticmethod
        def analyze(path, allowed_direction):
            assert path.is_file()
            assert allowed_direction == "left_to_right"
            return {
                "success": True,
                "result_video_url": "/outputs/video-analytics/result.mp4",
                "processed_frames": 12,
                "wrong_way_count": 1,
                "events": [{"event_type": "wrong_way", "label": "逆行事件"}],
            }

    client.app.state.video_analytics = FakeVideoAnalytics()
    response = client.post(
        "/api/v1/video-analytics",
        data={"location": "校园东门", "allowed_direction": "left_to_right"},
        files={"file": ("camera.mp4", b"fake-video", "video/mp4")},
    )
    assert response.status_code == 200
    assert response.json()["location"] == "校园东门"
    assert response.json()["wrong_way_count"] == 1
    assert response.json()["source_video_url"].startswith("/uploads/videos/")

    invalid = client.post(
        "/api/v1/video-analytics",
        data={"location": "校园东门", "allowed_direction": "diagonal"},
        files={"file": ("camera.mp4", b"fake-video", "video/mp4")},
    )
    assert invalid.status_code == 400


def test_api_key_guards_writes_and_sse(client: TestClient, valid_image_bytes: bytes):
    client.app.state.settings.api_key = "test-secret"
    payload = {
        "data": {"location": "北门", "area_type": "校门口"},
        "files": {"file": ("campus.jpg", valid_image_bytes, "image/jpeg")},
    }

    denied = client.post("/api/v1/inspections", **payload)
    assert denied.status_code == 401

    created = client.post(
        "/api/v1/inspections",
        headers={"X-API-Key": "test-secret"},
        **payload,
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    denied_execute = client.post(f"/api/v1/inspections/{task_id}/execute")
    assert denied_execute.status_code == 401
    executed = client.post(
        f"/api/v1/inspections/{task_id}/execute",
        headers={"X-API-Key": "test-secret"},
    )
    assert executed.status_code == 202

    denied_stream = client.get(f"/api/v1/inspections/{task_id}/stream")
    assert denied_stream.status_code == 401
    with client.stream("GET", f"/api/v1/inspections/{task_id}/stream?api_key=test-secret") as response:
        text = "".join(response.iter_text())
    assert response.status_code == 200
    assert "event: done" in text


def test_full_inspection_workflow_and_report(client: TestClient, created_task: dict):
    task_id = created_task["id"]
    execute = client.post(f"/api/v1/inspections/{task_id}/execute")
    assert execute.status_code == 202

    detail = client.get(f"/api/v1/inspections/{task_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "review"
    assert body["detections"][0]["class_name"] == "p10"
    assert body["detections"][0]["model_role"] == "traffic_sign"
    assert body["vision_events"] == []
    assert body["risk_result"]["analysis_mode"] == "rules_only"
    assert body["risk_result"]["review_required"] is True
    assert body["report_id"]

    trace = client.get(f"/api/v1/inspections/{task_id}/trace").json()["steps"]
    names = [item["node_name"] for item in trace]
    assert names == [
        "validate_input",
        "check_image_quality",
        "detect_traffic_signs",
        "check_detection_result",
        "retrieve_knowledge",
        "evaluate_risk",
        "generate_recommendations",
        "generate_report",
        "save_result",
    ]
    assert all(item["status"] == "success" for item in trace)

    report = client.get(f"/api/v1/reports/{body['report_id']}")
    assert report.status_code == 200
    assert "校园交通安全智能巡检报告" in report.json()["html_content"]


def test_quality_warning_continues_detection_and_analysis(client: TestClient, created_task: dict):
    workflow = client.app.state.workflow
    workflow.image_quality_tool.analyze_path = lambda _path: {
        "blurred": True,
        "dark": False,
        "overexposed": False,
        "too_small": False,
        "valid": False,
        "analyzable": True,
        "width": 640,
        "height": 480,
        "blur_score": 120.0,
        "blur_score_raw": 10.0,
        "blur_normalized_long_side": 1024,
        "mean_brightness": 120.0,
        "message": "图片可能模糊",
    }

    response = client.post(f"/api/v1/inspections/{created_task['id']}/execute")
    assert response.status_code == 202
    detail = client.get(f"/api/v1/inspections/{created_task['id']}").json()
    trace_names = [
        item["node_name"]
        for item in client.get(f"/api/v1/inspections/{created_task['id']}/trace").json()["steps"]
    ]

    assert detail["status"] == "review"
    assert "图片可能模糊" in detail["review_reasons"]
    assert "detect_traffic_signs" in trace_names
    assert "retrieve_knowledge" in trace_names
    assert "evaluate_risk" in trace_names


def test_low_confidence_candidates_only_force_review_when_all_are_unreliable(client: TestClient):
    workflow = client.app.state.workflow
    mixed = [
        {"confidence": 0.91, "model_role": "traffic_sign"},
        {"confidence": 0.22, "model_role": "general_object"},
    ]
    all_low = [
        {"confidence": 0.31, "model_role": "traffic_sign"},
        {"confidence": 0.22, "model_role": "general_object"},
    ]

    assert workflow._confidence_review_reason(mixed) is None
    assert "全部 2 个检测结果" in workflow._confidence_review_reason(all_low)


def test_duplicate_execution_is_rejected_while_queued(client: TestClient, created_task: dict):
    task_id = created_task["id"]
    with client.app.state.database.session() as db:
        task = db.get(InspectionTask, task_id)
        assert task is not None
        task.status = "queued"
        db.commit()

    response = client.post(f"/api/v1/inspections/{task_id}/execute")
    assert response.status_code == 409
    assert "执行队列" in response.json()["detail"]


def test_sse_replays_real_steps(client: TestClient, created_task: dict):
    task_id = created_task["id"]
    client.post(f"/api/v1/inspections/{task_id}/execute")
    with client.stream("GET", f"/api/v1/inspections/{task_id}/stream") as response:
        text = "".join(response.iter_text())
    assert response.status_code == 200
    assert "event: step" in text
    assert "validate_input" in text
    assert "event: done" in text


def test_manual_review_closes_task(client: TestClient, created_task: dict):
    task_id = created_task["id"]
    client.post(f"/api/v1/inspections/{task_id}/execute")
    response = client.post(
        f"/api/v1/inspections/{task_id}/review",
        json={"action": "confirm", "reviewer": "保卫处测试员", "comment": "已核对现场"},
    )
    assert response.status_code == 200
    assert response.json()["review_required"] is False
    assert client.get(f"/api/v1/inspections/{task_id}").json()["status"] == "completed"


def test_dashboard_and_pagination(client: TestClient, created_task: dict):
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["total_tasks"] == 1
    listing = client.get("/api/v1/inspections?page=1&page_size=10").json()
    assert listing["total"] == 1
    assert listing["items"][0]["id"] == created_task["id"]


def test_dashboard_trend_uses_local_days_and_real_confidence(client: TestClient, created_task: dict):
    client.post(f"/api/v1/inspections/{created_task['id']}/execute")
    now = datetime.now(timezone.utc)
    with client.app.state.database.session() as db:
        for days_ago, risk_level in ((2, "high"), (10, "high")):
            db.add(
                InspectionTask(
                    task_no=f"AX-TREND-{days_ago}",
                    location="趋势测试点",
                    area_type="校门口",
                    status="completed",
                    risk_level=risk_level,
                    created_at=now - timedelta(days=days_ago),
                )
            )
        db.commit()

    dashboard = client.get("/api/v1/dashboard").json()
    trend = dashboard["daily_trend"]

    assert len(trend) == 7
    today = datetime.now(client.app.state.settings.display_timezone).date()
    assert trend[-1]["date"] == today.isoformat()
    assert dashboard["today_tasks"] == trend[-1]["total"] == 1
    assert trend[-1]["review_required"] == 1
    assert trend[-3]["total"] == 1 and trend[-3]["high_risk"] == 1
    assert sum(item["total"] for item in trend) == 2  # the 10-day-old task is outside the window
    assert dashboard["total_tasks"] == 3
    executed = next(item for item in dashboard["recent_tasks"] if item["id"] == created_task["id"])
    assert executed["detection_count"] == 1
    assert executed["max_confidence"] == 0.92
    untouched = next(item for item in dashboard["recent_tasks"] if item["task_no"] == "AX-TREND-2")
    assert untouched["detection_count"] == 0
    assert untouched["max_confidence"] is None


def test_analytics_overview_uses_persisted_tasks_detections_and_agent_steps(
    client: TestClient,
    created_task: dict,
):
    client.post(f"/api/v1/inspections/{created_task['id']}/execute")

    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    body = response.json()

    assert body["summary"] == {
        "total_tasks": 1,
        "completed_tasks": 0,
        "review_required": 1,
        "completion_rate": 0.0,
        "review_rate": 100.0,
        "average_duration_ms": body["summary"]["average_duration_ms"],
    }
    assert len(body["daily_trend"]) == 30
    assert body["daily_trend"][-1]["total"] == 1
    assert body["risk_counts"] == {"review": 1}
    assert body["status_counts"] == {"review": 1}
    assert body["area_breakdown"][0]["area_type"] == "校门口"
    assert body["area_breakdown"][0]["review_required"] == 1
    reason_counts = {item["category"]: item["count"] for item in body["review_reason_counts"]}
    assert reason_counts == {"知识依据": 1, "风险策略": 1}
    assert body["model_breakdown"][0]["model_role"] == "traffic_sign"
    assert body["model_breakdown"][0]["detection_count"] == 1
    assert body["class_breakdown"] == [{"class_name": "p10", "detection_count": 1}]
    assert any(item["node_name"] == "detect_traffic_signs" for item in body["agent_performance"])
    assert all(item["run_count"] >= 1 for item in body["agent_performance"])


def test_feedback_is_persisted(client: TestClient, created_task: dict):
    task_id = created_task["id"]
    response = client.post(f"/api/v1/inspections/{task_id}/feedback", json={"rating": 5, "comment": "节省整理时间"})
    assert response.status_code == 200
    detail = client.get(f"/api/v1/inspections/{task_id}").json()
    assert detail["feedback_rating"] == 5
