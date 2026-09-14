from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.services.llm import LLMService
from app.services.rag import KnowledgeBaseService


class FakeYOLOTool:
    model_loaded = True
    load_count = 1

    def __init__(self, output_dir: Path, detections: list[dict] | None = None):
        self.output_dir = output_dir
        self.detections = detections if detections is not None else [
            {
                "class_id": 8,
                "class_name": "p10",
                "display_name": "p10",
                "confidence": 0.92,
                "bbox_xyxy": [100.0, 80.0, 240.0, 260.0],
                "model_role": "traffic_sign",
                "model_name": "test-best.pt",
            }
        ]

    def detect(self, image_path: str, conf=None, imgsz=None):
        image = cv2.imread(image_path)
        target_dir = self.output_dir / "detections"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "fake-result.jpg"
        cv2.imwrite(str(target), image)
        return {
            "success": True,
            "image_width": int(image.shape[1]),
            "image_height": int(image.shape[0]),
            "detections": self.detections,
            "vision_events": [],
            "object_count": len(self.detections),
            "model_name": "test-best.pt",
            "result_image_path": str(target),
            "result_image_url": "/outputs/detections/fake-result.jpg",
            "timing": {"preprocess_ms": 1.0, "inference_ms": 2.0, "postprocess_ms": 1.0, "total_ms": 4.0},
        }


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        output_dir=tmp_path / "outputs",
        yolo_model_path=tmp_path / "best.pt",
        yolo_device="cpu",
        general_yolo_enabled=False,
        qdrant_path=":memory:",
        llm_api_key=None,
        llm_required=False,
        amap_web_service_key=None,
        blur_threshold=30,
        dark_threshold=20,
        bright_threshold=245,
        min_image_width=64,
        min_image_height=64,
        # 钉死 VLM 环境：测试套件必须对 .env / 默认值变化保持密闭
        # （2026-09-14 默认启用 qwen3-vl-plus 后，未钉死的夹具会漏进真实提供方配置）
        vision_llm_enabled=False,
        vision_llm_base_url="https://api.deepseek.com/v1",
        vision_llm_model="deepseek-v4-flash-vision-exp",
        vision_llm_api_key=None,
    )


@pytest.fixture
def app(settings: Settings):
    database = Database(settings)
    knowledge_base = KnowledgeBaseService(settings, client=QdrantClient(":memory:"))
    yolo = FakeYOLOTool(settings.output_dir)
    return create_app(
        settings,
        database=database,
        yolo_tool=yolo,
        knowledge_base=knowledge_base,
        llm_service=LLMService(settings),
    )


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_image_bytes() -> bytes:
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    image[:] = (120, 120, 120)
    for x in range(0, 640, 32):
        color = (255, 255, 255) if (x // 32) % 2 else (0, 0, 0)
        cv2.rectangle(image, (x, 0), (min(x + 16, 639), 479), color, -1)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    return encoded.tobytes()


@pytest.fixture
def created_task(client: TestClient, valid_image_bytes: bytes) -> dict:
    response = client.post(
        "/api/v1/inspections",
        data={"location": "学校大门东侧", "area_type": "校门口", "description": "比赛演示样例"},
        files={"file": ("campus.jpg", valid_image_bytes, "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    return response.json()
