import importlib.util

import pytest

from traffic_api.config import AppSettings
from traffic_api.inference_core import PredictionOutput
from traffic_api.schemas import Detection, DetectionResult, ImageInfo


FASTAPI_AVAILABLE = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI is not installed in this environment")

if FASTAPI_AVAILABLE:
    from fastapi.testclient import TestClient

    from traffic_api.main import create_app


class ShapeOnlyImage:
    shape = (80, 120, 3)


class FakeDetector:
    def __init__(self):
        self.images = []
        self.load_count = 0

    def detect_image(self, image):
        self.images.append(image)
        detection_result = DetectionResult(
            image=ImageInfo(width=120, height=80, channels=3),
            detections=[Detection(1, "stop", 0.94, (1, 2, 30, 40))],
            message="detected 1 traffic signs",
            elapsed_ms=7.5,
        )
        return PredictionOutput(
            detection_result=detection_result,
            visual_image=None,
            raw_result=object(),
            elapsed_ms=7.5,
        )


def make_settings(tmp_path):
    return AppSettings(
        app_name="Anxun API",
        api_prefix="/api/v1",
        infer_device="cpu",
        img_size=640,
        conf_threshold=0.3,
        iou_threshold=0.5,
        save_dir=tmp_path,
        model_path=tmp_path / "best.pt",
        api_key="secret",
    )


def test_health_route_returns_settings(tmp_path):
    app = create_app(settings=make_settings(tmp_path), detector=FakeDetector())
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["app_name"] == "Anxun API"


def test_detect_image_requires_api_key(tmp_path):
    app = create_app(settings=make_settings(tmp_path), detector=FakeDetector())
    client = TestClient(app)

    response = client.post("/api/v1/detect/image", files={"file": ("sign.jpg", b"fake", "image/jpeg")})

    assert response.status_code == 401


def test_detect_image_returns_sf_fastgpt_friendly_payload(monkeypatch, tmp_path):
    detector = FakeDetector()
    app = create_app(settings=make_settings(tmp_path), detector=detector)
    client = TestClient(app)
    monkeypatch.setattr("traffic_api.main.decode_image_bytes", lambda _data: ShapeOnlyImage())

    response = client.post(
        "/api/v1/detect/image",
        headers={"X-API-Key": "secret"},
        files={"file": ("sign.jpg", b"fake", "image/jpeg")},
        data={"location": "north gate", "description": "morning inspection"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["task_id"]
    assert payload["image"]["filename"] == "sign.jpg"
    assert payload["detections"][0]["class_name"] == "stop"
    assert payload["object_count"] == 1
    assert payload["review_required"] is False
    assert payload["result_image_url"] is None
    assert payload["timing"]["elapsed_ms"] == 7.5
    assert payload["model"]["weights"] == "best.pt"
    assert payload["location"] == "north gate"
    assert payload["description"] == "morning inspection"
    assert detector.images and detector.images[0].shape == (80, 120, 3)
