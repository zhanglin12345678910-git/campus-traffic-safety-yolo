from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import cv2
import httpx
import numpy as np
import pytest
from qdrant_client import QdrantClient

from app.config import Settings
from app.schemas import KnowledgeHit, RiskResult
from app.services.llm import LLMService, LLMServiceError
from app.services.amap import AMapService, AMapServiceError
from app.services.rag import KnowledgeBaseService
from app.services.risk import RiskAssessmentService
from app.tools.image_quality import ImageQualityTool
from app.tools.yolo import TrafficSignDetectionTool
from app.tools.video_analytics import VideoAnalyticsError, VideoAnalyticsTool


def test_image_quality_detects_dark_and_small(settings: Settings):
    tool = ImageQualityTool(settings)
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    report = tool.analyze(image)
    assert report["dark"] is True
    assert report["too_small"] is True
    assert report["valid"] is False
    assert report["analyzable"] is True
    assert report["blur_normalized_long_side"] == settings.blur_normalize_long_side


def test_image_quality_normalizes_resolution_before_blur_scoring(settings: Settings):
    settings.blur_normalize_long_side = 256
    settings.blur_threshold = 10
    tool = ImageQualityTool(settings)
    image = np.zeros((512, 1024, 3), dtype=np.uint8)
    cv2.rectangle(image, (120, 120), (900, 390), (255, 255, 255), -1)

    report = tool.analyze(image)

    assert report["analyzable"] is True
    assert report["blur_normalized_long_side"] == 256
    assert report["blur_score_raw"] != report["blur_score"]


def test_yolo_model_is_loaded_once(settings: Settings, tmp_path: Path):
    settings.yolo_model_path.write_bytes(b"test")
    calls = []

    def factory(path: str):
        calls.append(path)
        return object()

    tool = TrafficSignDetectionTool(settings, yolo_factory=factory)
    assert tool.get_model() is tool.get_model()
    assert len(calls) == 1
    assert tool.load_count == 1


def test_yolo_detect_writes_result_in_unicode_path(settings: Settings, tmp_path: Path):
    settings.output_dir = tmp_path / "中文结果"
    settings.yolo_model_path.write_bytes(b"test")
    image = np.full((120, 160, 3), 128, dtype=np.uint8)
    image_path = tmp_path / "校园样例.jpg"
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    encoded.tofile(str(image_path))

    box = SimpleNamespace(
        cls=np.array([8.0]),
        conf=np.array([0.91]),
        xyxy=np.array([[10.0, 20.0, 80.0, 100.0]]),
    )
    result = SimpleNamespace(
        orig_img=image,
        names={8: "p10"},
        boxes=[box],
        speed={"preprocess": 1.0, "inference": 2.0, "postprocess": 1.0},
        plot=lambda: image,
    )
    model = SimpleNamespace(predict=lambda *_args, **_kwargs: [result])
    tool = TrafficSignDetectionTool(settings, yolo_factory=lambda _path: model)

    output = tool.detect(image_path)

    assert output["object_count"] == 1
    assert output["detections"][0]["class_name"] == "p10"
    assert Path(output["result_image_path"]).is_file()


def test_yolo_multimodel_filters_classes_and_builds_crowd_event(settings: Settings, tmp_path: Path):
    settings.yolo_model_path.write_bytes(b"traffic")
    settings.general_yolo_enabled = True
    settings.general_yolo_model_path = tmp_path / "yolo26n.pt"
    settings.general_yolo_model_path.write_bytes(b"general")
    settings.crowd_min_persons = 2

    image = np.full((240, 320, 3), 128, dtype=np.uint8)
    image_path = tmp_path / "宿舍区人群.jpg"
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    encoded.tofile(str(image_path))

    def box(class_id: int, confidence: float, coords: list[float]):
        return SimpleNamespace(
            cls=np.array([float(class_id)]),
            conf=np.array([confidence]),
            xyxy=np.array([coords]),
        )

    traffic_result = SimpleNamespace(
        names={11: "p11"},
        boxes=[box(11, 0.94, [10, 20, 60, 90])],
        speed={"inference": 2.0},
    )
    general_result = SimpleNamespace(
        names={0: "person", 11: "stop sign"},
        boxes=[
            box(0, 0.88, [100, 20, 150, 200]),
            box(0, 0.77, [160, 30, 210, 210]),
            box(11, 0.66, [220, 20, 280, 100]),
        ],
        speed={"inference": 3.0},
    )
    traffic_model = SimpleNamespace(predict=lambda *_args, **_kwargs: [traffic_result])
    general_model = SimpleNamespace(predict=lambda *_args, **_kwargs: [general_result])

    def factory(path: str):
        return general_model if Path(path).name == "yolo26n.pt" else traffic_model

    output = TrafficSignDetectionTool(settings, yolo_factory=factory).detect(image_path)

    assert [item["class_name"] for item in output["detections"]] == ["p11", "person", "person"]
    assert output["detections"][1]["display_name"] == "人员"
    assert output["detections"][1]["model_role"] == "general_object"
    assert output["vision_events"][0]["event_type"] == "personnel_gathering"
    assert output["vision_events"][0]["object_count"] == 2
    assert output["models"][1]["detections"] == 2


def test_video_tracking_never_shares_the_image_general_model(settings: Settings, tmp_path: Path):
    # model.track() leaves ByteTrack callbacks on the model it runs on, so the
    # video tool must track on its own instance, never the image singleton.
    settings.video_frame_stride = 1
    settings.wrong_way_min_track_points = 3
    video_path = tmp_path / "东门机位.avi"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (320, 240))
    assert writer.isOpened()
    for _ in range(6):
        writer.write(np.full((240, 320, 3), 90, dtype=np.uint8))
    writer.release()

    class FakeTrackingModel:
        names = {0: "person"}
        predictor = None

        def __init__(self):
            self.frames = 0

        def track(self, frame, **kwargs):
            assert kwargs["persist"] is True
            left = 220.0 - self.frames * 25.0  # moves right-to-left every frame
            self.frames += 1
            boxes = SimpleNamespace(
                id=np.array([1.0]),
                xyxy=np.array([[left, 60.0, left + 30.0, 150.0]]),
                cls=np.array([0.0]),
                conf=np.array([0.9]),
            )
            return [SimpleNamespace(boxes=boxes, names=self.names, plot=lambda: frame)]

    class FakeYOLOTool:
        def __init__(self):
            self.created: list[FakeTrackingModel] = []

        def get_general_model(self):
            raise AssertionError("video tracking must not use the image-inference singleton")

        def create_general_model(self):
            model = FakeTrackingModel()
            self.created.append(model)
            return model

    yolo = FakeYOLOTool()
    tool = VideoAnalyticsTool(settings, yolo)

    first = tool.analyze(video_path, "left_to_right")
    second = tool.analyze(video_path, "left_to_right")

    assert first["wrong_way_count"] == 1
    assert first["events"][0]["event_type"] == "wrong_way"
    assert second["processed_frames"] == 6
    assert len(yolo.created) == 1
    assert tool.model_loaded is True
    assert tool.load_count == 1
    assert Path(first["result_video_path"]).is_file()


def test_video_analysis_downscales_4k_portrait_and_rejects_parallel_work(settings: Settings, tmp_path: Path):
    assert VideoAnalyticsTool._analysis_dimensions(2160, 3840, 960) == (540, 960)
    assert VideoAnalyticsTool._analysis_dimensions(960, 540, 960) == (960, 540)

    settings.video_frame_stride = 2
    settings.video_target_fps = 10
    stride_tool = VideoAnalyticsTool(settings, SimpleNamespace())
    assert stride_tool._effective_frame_stride(60.13) == 6
    assert stride_tool._effective_frame_stride(25.0) == 2

    video_path = tmp_path / "正在分析.mp4"
    video_path.write_bytes(b"placeholder")
    tool = VideoAnalyticsTool(settings, SimpleNamespace())
    assert tool._lock.acquire(blocking=False)
    try:
        with pytest.raises(VideoAnalyticsError, match="已有视频正在分析"):
            tool.analyze(video_path, "left_to_right")
    finally:
        tool._lock.release()


def test_general_model_singleton_and_tracking_instance_are_distinct(settings: Settings, tmp_path: Path):
    settings.general_yolo_enabled = True
    settings.general_yolo_model_path = tmp_path / "yolo26n.pt"
    settings.general_yolo_model_path.write_bytes(b"general")
    loaded = []

    def factory(path: str):
        loaded.append(path)
        return SimpleNamespace(path=path)

    yolo = TrafficSignDetectionTool(settings, yolo_factory=factory)
    video = VideoAnalyticsTool(settings, yolo)

    image_model = yolo.get_general_model()
    tracking_model = video._tracking_model()

    assert tracking_model is not image_model
    assert yolo.get_general_model() is image_model
    assert video._tracking_model() is tracking_model
    assert yolo.general_load_count == 1
    assert len(loaded) == 2


def test_video_wrong_way_rule_requires_sustained_opposite_motion(settings: Settings):
    settings.wrong_way_min_track_points = 4
    settings.wrong_way_min_displacement_ratio = 0.03
    tool = VideoAnalyticsTool(settings, SimpleNamespace())

    opposite = deque([(180.0, 50.0), (150.0, 50.0), (120.0, 50.0), (80.0, 50.0)])
    allowed = deque([(80.0, 50.0), (110.0, 50.0), (140.0, 50.0), (180.0, 50.0)])
    jitter = deque([(100.0, 50.0), (101.0, 50.0), (99.0, 51.0), (101.0, 49.0)])

    assert tool._is_wrong_way(opposite, "left_to_right", diagonal=400.0) is True
    assert tool._is_wrong_way(allowed, "left_to_right", diagonal=400.0) is False
    assert tool._is_wrong_way(jitter, "left_to_right", diagonal=400.0) is False


def test_rag_ingest_search_and_no_result(settings: Settings, tmp_path: Path):
    settings.rag_score_threshold = 0.0
    service = KnowledgeBaseService(settings, client=QdrantClient(":memory:"))
    assert service.search("停车场") == []
    source = tmp_path / "rule.md"
    source.write_text("停车场入口应保持清晰可见，巡检发现遮挡时应记录并安排复查。", encoding="utf-8")
    assert service.ingest("doc-1", "停车场管理规定", source) == 1
    hits = service.search("停车场遮挡复查")
    assert hits
    assert hits[0].document_name == "停车场管理规定"
    assert "遮挡" in hits[0].content


def test_llm_structured_output(settings: Settings):
    settings.llm_base_url = "https://example.test/v1"
    settings.llm_api_key = "secret"
    settings.llm_model = "demo-model"
    expected = RiskResult(
        risk_level="medium",
        risk_score=60,
        problem_summary="存在需要核对的标志设置问题",
        evidence=["真实检测证据"],
        recommendations=["现场复核"],
        review_required=False,
        analysis_mode="llm",
    ).model_dump()

    def handler(request: httpx.Request):
        assert request.headers["Authorization"] == "Bearer secret"
        assert str(request.url) == "https://example.test/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "demo-model"
        assert body["temperature"] == 0.0
        assert "thinking" not in body
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(expected, ensure_ascii=False)}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = LLMService(settings, client=client).generate_risk({"detections": []})
    assert result.risk_level == "medium"
    assert result.analysis_mode == "llm"


def test_risk_review_policy_is_deterministic_and_ignores_llm_boolean(settings: Settings):
    class FakeLLM:
        available = True

        @staticmethod
        def generate_risk(_payload):
            return RiskResult(
                risk_level="low",
                risk_score=15,
                problem_summary="低风险且证据充足",
                review_required=True,
                analysis_mode="llm",
            )

    service = RiskAssessmentService(settings, FakeLLM())
    clean = service.evaluate(
        location="东门",
        area_type="校门口",
        description=None,
        image_quality={"message": "图片质量检查通过"},
        detections=[{"class_name": "p11", "confidence": 0.94, "bbox_xyxy": [1, 2, 3, 4]}],
        knowledge_hits=[KnowledgeHit(document_name="规范", chunk_id="c1", content="禁鸣区域", score=0.8)],
        review_reasons=[],
    )
    forced = service.evaluate(
        location="东门",
        area_type="校门口",
        description=None,
        image_quality={"message": "图片可能模糊"},
        detections=[{"class_name": "p11", "confidence": 0.94, "bbox_xyxy": [1, 2, 3, 4]}],
        knowledge_hits=[KnowledgeHit(document_name="规范", chunk_id="c1", content="禁鸣区域", score=0.8)],
        review_reasons=["图片可能模糊"],
    )

    assert clean.review_required is False
    assert forced.review_required is True


@pytest.mark.parametrize("risk_level", ["medium", "high", "review"])
def test_risk_review_policy_requires_confirmation_for_non_low_levels(risk_level: str):
    reasons = RiskAssessmentService.review_policy_reasons(
        risk_level=risk_level,
        review_reasons=[],
        vision_events=[],
    )

    assert len(reasons) == 1
    assert risk_level in reasons[0]


def test_deepseek_flash_defaults_only_require_api_key(settings: Settings):
    settings.llm_base_url = "https://api.deepseek.com"
    settings.llm_api_key = "secret"
    settings.llm_model = "deepseek-v4-flash"
    expected = RiskResult(
        risk_level="review",
        risk_score=50,
        problem_summary="需要人工复核",
        review_required=True,
        analysis_mode="llm",
    ).model_dump()

    def handler(request: httpx.Request):
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["Authorization"] == "Bearer secret"
        body = json.loads(request.content)
        assert body["model"] == "deepseek-v4-flash"
        assert body["thinking"] == {"type": "disabled"}
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(expected, ensure_ascii=False)}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = LLMService(settings, client=client).generate_risk({"detections": []})

    assert result.problem_summary == "需要人工复核"
    assert result.analysis_mode == "llm"


def test_llm_error_is_explicit(settings: Settings):
    settings.llm_base_url = "https://example.test/v1"
    settings.llm_api_key = "secret"
    settings.llm_model = "demo-model"
    settings.llm_max_retries = 0
    client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(500, text="failed")))
    with pytest.raises(LLMServiceError, match="LLM 调用失败"):
        LLMService(settings, client=client).generate_risk({"detections": []})


def test_risk_fallback_hides_transport_details_from_user(settings: Settings):
    class FailingLLM:
        available = True

        @staticmethod
        def generate_risk(_payload):
            raise LLMServiceError("LLM 调用失败：[WinError 10013] private transport detail")

    result = RiskAssessmentService(settings, FailingLLM()).evaluate(
        location="东门",
        area_type="校门口",
        description=None,
        image_quality={"message": "图片质量正常"},
        detections=[],
        knowledge_hits=[],
        review_reasons=[],
    )

    assert result.analysis_mode == "rules_only"
    assert "已自动切换为规则保守模式" in result.uncertainty_note
    assert "WinError" not in result.uncertainty_note


def test_amap_geocode_and_static_map(settings: Settings):
    settings.amap_web_service_key = "amap-test-secret"

    def handler(request: httpx.Request):
        assert request.url.params["key"] == "amap-test-secret"
        if request.url.path.endswith("/geocode/geo"):
            return httpx.Response(200, json={
                "status": "1",
                "geocodes": [{
                    "formatted_address": "四川省成都市四川现代职业学院",
                    "province": "四川省",
                    "city": "成都市",
                    "district": "双流区",
                    "adcode": "510116",
                    "level": "兴趣点",
                    "location": "103.997424,30.515862",
                }],
            })
        assert request.url.path.endswith("/staticmap")
        assert request.url.params["location"] == "103.997424,30.515862"
        assert request.url.params["size"] == "1024*640"
        return httpx.Response(200, content=b"fake-map", headers={"content-type": "image/png"})

    service = AMapService(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))
    location = service.geocode("四川现代职业学院", "成都")
    image = service.static_map(lng=103.997424, lat=30.515862, zoom=17, width=1024, height=640)

    assert location["location"] == {"lng": 103.997424, "lat": 30.515862}
    assert image.content == b"fake-map"
    assert image.content_type == "image/png"


def test_amap_weather_parses_live_report_and_caches(settings: Settings):
    settings.amap_web_service_key = "amap-test-secret"
    calls = []

    def handler(request: httpx.Request):
        calls.append(request)
        assert request.url.path.endswith("/v3/weather/weatherInfo")
        assert request.url.params["city"] == "510116"
        assert request.url.params["key"] == "amap-test-secret"
        return httpx.Response(200, json={
            "status": "1",
            "lives": [{
                "province": "四川",
                "city": "双流区",
                "adcode": "510116",
                "weather": "多云",
                "temperature": "22",
                "winddirection": "北",
                "windpower": "≤3",
                "humidity": "71",
                "reporttime": "2026-09-11 18:00:00",
            }],
        })

    service = AMapService(settings, client=httpx.Client(transport=httpx.MockTransport(handler)))
    first = service.weather("510116")
    second = service.weather("510116")

    assert first["weather"] == "多云"
    assert first["temperature"] == "22"
    assert first["report_time"] == "2026-09-11 18:00:00"
    assert "key" not in first
    assert second == first
    assert len(calls) == 1


def test_amap_weather_rejects_empty_live_report(settings: Settings):
    settings.amap_web_service_key = "amap-test-secret"
    client = httpx.Client(transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"status": "1", "lives": []})))

    with pytest.raises(AMapServiceError, match="实况天气"):
        AMapService(settings, client=client).weather("510116")
