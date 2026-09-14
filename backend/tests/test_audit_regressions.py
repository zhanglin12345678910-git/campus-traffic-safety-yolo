"""Regression anchors for the independent 2026-09-12 audit."""
import importlib.util
from pathlib import Path

import pytest

from app.agents.graph import InspectionWorkflow
from app.api.router import _review_reason_category
from app.config import Settings
from app.schemas import KnowledgeHit, RiskResult
from app.services.llm import LLMServiceError
from app.services.risk import RiskAssessmentService


@pytest.mark.parametrize("quality,route", [({}, "review"), ({"analyzable": None}, "review"),
    ({"analyzable": False}, "review"), ({"analyzable": True}, "detect")])
def test_quality_route_fails_closed(quality, route):
    assert InspectionWorkflow._route_quality({"image_quality": quality}) == route
    assert InspectionWorkflow._route_quality({"image_quality": quality, "error": "failure"}) == "error"


def test_undecodable_input_short_circuits_workflow(client, created_task):
    workflow = client.app.state.workflow
    workflow.image_quality_tool.analyze_path = lambda _: {
        "valid": False, "analyzable": False, "message": "图片无法解码"
    }
    assert client.post(f"/api/v1/inspections/{created_task['id']}/execute").status_code == 202
    detail = client.get(f"/api/v1/inspections/{created_task['id']}").json()
    names = [step['node_name'] for step in client.get(f"/api/v1/inspections/{created_task['id']}/trace").json()['steps']]
    assert detail['review_required'] and detail['review_reasons']
    assert 'manual_review' in names
    assert not {'detect_traffic_signs', 'retrieve_knowledge', 'evaluate_risk'} & set(names)


@pytest.mark.parametrize("reason,category", [
    ('图片可能模糊', '图片质量'), ('全部检测结果低于置信度', '检测可信度'),
    ('人员聚集需确认', '视觉事件'), ('未检索到知识依据', '知识依据'),
    ('风险等级为 medium', '风险策略'), ('大模型服务暂不可用', '模型或服务'), ('未填写地点', '其他原因'),
])
def test_review_reason_categories(reason, category):
    assert _review_reason_category(reason) == category


def test_medium_default_is_anchored():
    # Inspect the declared default, not a local .env override.
    assert Settings.model_fields['general_yolo_model_path'].default.name == 'yolo26m.pt'


@pytest.mark.parametrize('event', [
    {'requires_manual_review': True, 'evidence': '现场确认'},
    {'requires_manual_review': True, 'label': '视觉事件'}, None,
])
def test_visual_event_requires_review(event):
    assert RiskAssessmentService.review_policy_reasons(risk_level='low', review_reasons=[], vision_events=[event])


def test_non_review_visual_event_does_not_force_review():
    assert RiskAssessmentService.review_policy_reasons(
        risk_level='low', review_reasons=[], vision_events=[{'requires_manual_review': False}]
    ) == []


def test_model_failure_reason_survives_graph_and_persistence(client, created_task):
    class FailingLLM:
        available = True
        def generate_risk(self, payload):
            raise LLMServiceError('controlled offline failure')

    client.app.state.workflow.risk_service.llm = FailingLLM()
    assert client.post(f"/api/v1/inspections/{created_task['id']}/execute").status_code == 202
    body = client.get(f"/api/v1/inspections/{created_task['id']}").json()
    assert body['review_required'] is True and body['status'] == 'review'
    # policy_reasons is intentionally internal; review_reasons is the persisted
    # API contract and must keep the fallback evidence after a fresh GET.
    assert 'policy_reasons' not in body['risk_result']
    assert any('大模型服务暂不可用' in item for item in body['review_reasons'])
    counts = client.get('/api/v1/analytics/overview').json()['review_reason_counts']
    assert {'category': '模型或服务', 'count': 1} in counts


def test_policy_cannot_be_injected_by_llm(settings):
    class FakeLLM:
        available = True
        def generate_risk(self, payload):
            assert 'policy_reasons' not in payload['output_schema']['properties']
            return RiskResult(risk_level='low', risk_score=15, problem_summary='test',
                              review_required=True, policy_reasons=['injected'])

    result = RiskAssessmentService(settings, FakeLLM()).evaluate(
        location='test', area_type='test', description=None, image_quality={}, detections=[],
        knowledge_hits=[KnowledgeHit(document_name='test', chunk_id='1', content='test', score=.9)],
        review_reasons=[],
    )
    assert result.review_required is False and result.policy_reasons == []


def test_deduplication_is_content_based_and_keeps_aliases(tmp_path):
    script = Path(__file__).resolve().parents[2] / 'scripts/compare_general_models.py'
    spec = importlib.util.spec_from_file_location('compare_models_audit', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / 'a.jpg').write_bytes(b'same image')
    (tmp_path / 'b.png').write_bytes(b'same image')
    (tmp_path / 'c.JPG').write_bytes(b'another image')
    (tmp_path / 'notes.txt').write_text('not an image')
    (tmp_path / 'directory.jpg').mkdir()
    images, manifest = module.unique_images(tmp_path)
    assert [p.name for p in images] == ['a.jpg', 'c.JPG']
    assert manifest[0]['files'] == ['a.jpg', 'b.png']
    assert len(manifest[0]['sha256']) == 64
    assert module.summarize({'a': [], 'c': [{'class': 'car', 'confidence': .35}]}, .2)['below_review_threshold'] == 0
