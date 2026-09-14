"""旁挂视觉研判（模式乙）回归测试。

覆盖边界：开关门控、请求体纪律（关思维链/非流式/JSON）、输出白名单收敛、
人员隐私闸门、证据并入文字研判 payload、失败降级不阻断流程。
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.agents.graph import InspectionWorkflow
from app.config import Settings
from app.schemas import KnowledgeHit, RiskResult
from app.services.llm import VisionLLMService, VisionLLMServiceError, vision_person_gate
from app.services.risk import RiskAssessmentService

CANNED = {
    "scene_description": "一排车辆沿路边停放",
    "parking_assessment": "uncertain",
    "confidence": 0.6,
    "visible_evidence": ["路面潮湿", "未见车位线"],
    "legal_scenarios_checked": ["装卸货临时停靠"],
    "notes": "远景车辆无法判断状态",
    "_should_be_dropped": "not allowed",
}


def make_vision_settings(settings: Settings, **overrides) -> Settings:
    params = settings.model_dump()
    params.update(
        {
            "vision_llm_enabled": True,
            "vision_llm_base_url": "https://api.deepseek.com/v1",
            "vision_llm_model": "deepseek-v4-flash-vision-exp",
            "vision_llm_api_key": None,
            "llm_api_key": "test-key",
        }
    )
    params.update(overrides)
    return Settings(**params)


def fake_transport(payload: dict | None = None, status: int = 200, capture: dict | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture["body"] = json.loads(request.content.decode("utf-8"))
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "boom"}})
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(payload or CANNED, ensure_ascii=False)}}],
                "usage": {"prompt_tokens": 10},
            },
        )

    return httpx.MockTransport(handler)


class TestVisionLLMService:
    @pytest.mark.parametrize(
        "base_url,use_proxy,outbound_proxy,expected_proxy",
        [
            ("https://dashscope.aliyuncs.com/compatible-mode/v1", True, "http://127.0.0.1:7890", "http://127.0.0.1:7890"),
            ("https://api.deepseek.com/v1", True, "http://127.0.0.1:7890", "http://127.0.0.1:7890"),
            ("https://dashscope.aliyuncs.com/compatible-mode/v1", False, "http://127.0.0.1:7890", None),
            ("https://dashscope.aliyuncs.com/compatible-mode/v1", True, None, None),
        ],
    )
    def test_provider_independent_explicit_proxy_routing(
        self, settings: Settings, tmp_path, monkeypatch, base_url, use_proxy, outbound_proxy, expected_proxy
    ):
        import cv2
        import numpy as np

        # Ambient proxies must not override explicit direct mode or the
        # application's chosen proxy. TLS verification remains enabled.
        monkeypatch.setenv("HTTPS_PROXY", "http://unexpected.invalid:9999")
        monkeypatch.setenv("NO_PROXY", "*")
        capture: dict = {}
        client = httpx.Client(transport=fake_transport(capture=capture))
        client_options: dict = {}

        def client_factory(**kwargs):
            client_options.update(kwargs)
            return client

        monkeypatch.setattr(httpx, "Client", client_factory)
        service = VisionLLMService(make_vision_settings(
            settings,
            vision_llm_base_url=base_url,
            vision_llm_model="qwen3-vl-plus" if "dashscope" in base_url else "deepseek-v4-flash-vision-exp",
            vision_llm_use_outbound_proxy=use_proxy,
            outbound_http_proxy=outbound_proxy,
        ))
        image_path = tmp_path / "scene.jpg"
        cv2.imwrite(str(image_path), np.full((64, 96, 3), 128, dtype=np.uint8))
        result = service.assess_image(image_path=str(image_path), context={})
        assert client_options["proxy"] == expected_proxy
        assert client_options["trust_env"] is False
        assert client_options.get("verify", True) is True
        assert client.is_closed
        assert result["parking_assessment"] == "uncertain"
        if "dashscope" in base_url:
            assert capture["body"]["enable_thinking"] is False
            assert "thinking" not in capture["body"]

    def test_available_requires_enabled_flag_and_key(self, settings: Settings):
        assert not VisionLLMService(settings).available  # 夹具显式 vision_llm_enabled=False（与 .env 无关）
        enabled = make_vision_settings(settings)
        assert VisionLLMService(enabled).available
        no_key = make_vision_settings(settings, llm_api_key=None, vision_llm_api_key=None)
        assert not VisionLLMService(no_key).available

    def test_assess_image_contract_and_sanitization(self, settings: Settings, tmp_path):
        capture: dict = {}
        client = httpx.Client(transport=fake_transport(capture=capture))
        service = VisionLLMService(make_vision_settings(settings), client=client)
        image_path = tmp_path / "scene.jpg"
        import cv2
        import numpy as np

        cv2.imwrite(str(image_path), np.full((64, 96, 3), 128, dtype=np.uint8))
        result = service.assess_image(image_path=str(image_path), context={"location": "东门"})

        body = capture["body"]
        assert body["temperature"] == 0.0
        assert body["stream"] is False
        assert body["thinking"] == {"type": "disabled"}  # DeepSeek 显式关思维链
        assert body["response_format"] == {"type": "json_object"}
        assert body["model"] == "deepseek-v4-flash-vision-exp"
        # 图片以 base64 多模态消息上送
        assert body["messages"][1]["content"][1]["type"] == "image_url"

        assert "_should_be_dropped" not in result
        assert result["parking_assessment"] == "uncertain"
        assert result["confidence"] == 0.6
        assert result["model"] == "deepseek-v4-flash-vision-exp"

    def test_confidence_clamped(self, settings: Settings, tmp_path):
        client = httpx.Client(transport=fake_transport({**CANNED, "confidence": 7.5}))
        service = VisionLLMService(make_vision_settings(settings), client=client)
        import cv2
        import numpy as np

        image_path = tmp_path / "scene.jpg"
        cv2.imwrite(str(image_path), np.full((32, 32, 3), 0, dtype=np.uint8))
        result = service.assess_image(image_path=str(image_path), context={})
        assert result["confidence"] == 1.0

    def test_http_error_raises_after_retries(self, settings: Settings, tmp_path):
        client = httpx.Client(transport=fake_transport(status=500))
        service = VisionLLMService(make_vision_settings(settings), client=client)
        import cv2
        import numpy as np

        image_path = tmp_path / "scene.jpg"
        cv2.imwrite(str(image_path), np.full((32, 32, 3), 0, dtype=np.uint8))
        with pytest.raises(VisionLLMServiceError):
            service.assess_image(image_path=str(image_path), context={})

    def test_disabled_service_raises(self, settings: Settings, tmp_path):
        service = VisionLLMService(settings)
        with pytest.raises(VisionLLMServiceError):
            service.assess_image(image_path=str(tmp_path / "x.jpg"), context={})


class TestPersonGate:
    def test_person_detection_blocks_upload(self):
        detections = [{"class_name": "person"}, {"class_name": "car"}]
        assert vision_person_gate(detections, skip_with_person=True) is False

    def test_no_person_allows_upload(self):
        detections = [{"class_name": "car"}, {"class_name": "p11"}]
        assert vision_person_gate(detections, skip_with_person=True) is True

    def test_gate_disabled_allows_upload(self):
        assert vision_person_gate([{"class_name": "person"}], skip_with_person=False) is True

    def test_empty_detections_allows_upload(self):
        assert vision_person_gate([], skip_with_person=True) is True


class TestRiskMergesVisionAssessment:
    def test_assessment_enters_payload_and_evidence_without_decision_fields(self, settings: Settings):
        captured: dict = {}

        class FakeLLM:
            available = True

            @staticmethod
            def generate_risk(payload):
                captured["payload"] = payload
                return RiskResult(risk_level="low", risk_score=10, problem_summary="ok", analysis_mode="llm")

        service = RiskAssessmentService(settings, FakeLLM())
        assessment = {"parking_assessment": "uncertain", "confidence": 0.6, "scene_description": "路边车辆", "model": "v"}
        result = service.evaluate(
            location="东门",
            area_type="校门口",
            description=None,
            image_quality={"message": "ok"},
            detections=[{"class_name": "car", "confidence": 0.9, "bbox_xyxy": [1, 2, 3, 4]}],
            knowledge_hits=[KnowledgeHit(document_name="规范", chunk_id="c1", content="依据", score=0.8)],
            review_reasons=[],
            vision_assessment=assessment,
        )
        payload = captured["payload"]
        assert payload["vision_assessment"] == assessment
        assert "旁挂视觉模型" in payload["vision_assessment_role"]
        assert "review_required" not in payload["output_schema"]["properties"]
        assert "policy_reasons" not in payload["output_schema"]["properties"]
        assert any("视觉研判" in line for line in result.evidence)
        assert result.review_required is False  # 视觉证据不改变后端策略的唯一决策权

    def test_no_assessment_keeps_payload_identical_to_legacy(self, settings: Settings):
        captured: dict = {}

        class FakeLLM:
            available = True

            @staticmethod
            def generate_risk(payload):
                captured["payload"] = payload
                return RiskResult(risk_level="low", risk_score=10, problem_summary="ok", analysis_mode="llm")

        service = RiskAssessmentService(settings, FakeLLM())
        service.evaluate(
            location="东门",
            area_type="校门口",
            description=None,
            image_quality={},
            detections=[],
            knowledge_hits=[KnowledgeHit(document_name="规范", chunk_id="c1", content="依据", score=0.8)],
            review_reasons=[],
        )
        assert "vision_assessment" not in captured["payload"]


class _FakeVision:
    def __init__(self, *, result: dict | None = None, error: Exception | None = None):
        self.available = True
        self._result = result or {"parking_assessment": "uncertain"}
        self._error = error

    def assess_image(self, *, image_path: str, context: dict):
        if self._error:
            raise self._error
        return self._result


def _bare_workflow(settings: Settings, vision) -> InspectionWorkflow:
    wf = InspectionWorkflow.__new__(InspectionWorkflow)
    wf.settings = settings
    wf.vision_llm = vision
    return wf


class TestGraphVisionFallback:
    STATE = {"image_path": "/tmp/x.jpg", "location": "东门", "area_type": "校门口", "description": None}

    def test_no_service_returns_none(self, settings: Settings):
        reasons: list[str] = []
        assert _bare_workflow(settings, None)._run_vision_assessment(self.STATE, [], reasons) is None
        assert reasons == []

    def test_person_gate_skips_silently(self, settings: Settings):
        reasons: list[str] = []
        wf = _bare_workflow(settings, _FakeVision())
        result = wf._run_vision_assessment(self.STATE, [{"class_name": "person"}], reasons)
        assert result is None
        assert reasons == []  # 按设计静默跳过，不追加复核原因

    def test_failure_degrades_with_review_reason(self, settings: Settings):
        reasons: list[str] = []
        wf = _bare_workflow(settings, _FakeVision(error=VisionLLMServiceError("boom")))
        result = wf._run_vision_assessment(self.STATE, [], reasons)
        assert result is None
        assert reasons == ["视觉研判服务暂不可用，已降级为纯文本研判"]

    def test_success_returns_assessment(self, settings: Settings):
        reasons: list[str] = []
        wf = _bare_workflow(settings, _FakeVision(result={"parking_assessment": "violation"}))
        result = wf._run_vision_assessment(self.STATE, [{"class_name": "car"}], reasons)
        assert result == {"parking_assessment": "violation"}
        assert reasons == []
