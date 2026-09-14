from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.config import Settings
from app.database import Database
from app.main import create_app
from app.services.llm import LLMService
from app.services.rag import KnowledgeBaseService


def main() -> None:
    parser = argparse.ArgumentParser(description="使用真实 YOLO26 权重验证完整巡检链路")
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--knowledge", required=True, type=Path)
    parser.add_argument("--device", default="0")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="campus-safety-e2e-") as temp:
        root = Path(temp)
        settings = Settings(
            database_url=f"sqlite:///{root / 'e2e.db'}",
            upload_dir=root / "uploads",
            output_dir=root / "outputs",
            yolo_model_path=args.weights.resolve(),
            yolo_device=args.device,
            qdrant_path=":memory:",
            blur_threshold=0,
            dark_threshold=0,
            bright_threshold=255,
            min_image_width=32,
            min_image_height=32,
            rag_score_threshold=0,
        )
        database = Database(settings)
        knowledge = KnowledgeBaseService(settings, client=QdrantClient(":memory:"))
        app = create_app(
            settings,
            database=database,
            knowledge_base=knowledge,
            llm_service=LLMService(settings),
        )
        try:
            with TestClient(app) as client:
                with args.knowledge.open("rb") as stream:
                    response = client.post(
                        "/api/v1/knowledge/documents",
                        files={"file": (args.knowledge.name, stream, "text/markdown")},
                    )
                response.raise_for_status()
                with args.image.open("rb") as stream:
                    response = client.post(
                        "/api/v1/inspections",
                        data={"location": "TT100K 样例验证点", "area_type": "校园主干道"},
                        files={"file": (args.image.name, stream, "image/jpeg")},
                    )
                response.raise_for_status()
                task_id = response.json()["id"]
                execute = client.post(f"/api/v1/inspections/{task_id}/execute")
                execute.raise_for_status()
                detail = client.get(f"/api/v1/inspections/{task_id}").json()
                trace = client.get(f"/api/v1/inspections/{task_id}/trace").json()["steps"]
                health = client.get("/api/v1/health").json()
                assert detail["status"] in {"completed", "review"}
                assert detail["report_id"]
                assert detail["risk_result"]
                report = client.get(f"/api/v1/reports/{detail['report_id']}").json()
                assert report["id"] == detail["report_id"]
                assert len(report["html_content"]) > 50
                assert any(item["node_name"] == "detect_traffic_signs" and item["status"] == "success" for item in trace)
                assert health["services"]["yolo"]["loaded"] is True
                assert health["services"]["yolo"]["load_count"] == 1
                assert health["services"]["yolo"]["model_name"] == args.weights.name
                digest = hashlib.sha256(args.weights.read_bytes()).hexdigest()
                result = {
                    "status": "passed",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "task_id": task_id,
                    "inspection_status": detail["status"],
                    "detections": len(detail["detections"]),
                    "analysis_mode": detail["risk_result"]["analysis_mode"],
                    "risk_level": detail["risk_result"]["risk_level"],
                    "review_required": detail["review_required"],
                    "trace_nodes": [item["node_name"] for item in trace],
                    "report_id": detail["report_id"],
                    "report_length": len(report["html_content"]),
                    "yolo_model": health["services"]["yolo"]["model_name"],
                    "yolo_load_count": health["services"]["yolo"]["load_count"],
                    "weights": str(args.weights.resolve()),
                    "weights_size_bytes": args.weights.stat().st_size,
                    "weights_sha256": digest,
                    "sample_image": str(args.image.resolve()),
                }
                serialized = json.dumps(result, ensure_ascii=False, indent=2)
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(serialized, encoding="utf-8")
                print(serialized)
        finally:
            database.engine.dispose()
            knowledge.client.close()


if __name__ == "__main__":
    main()
