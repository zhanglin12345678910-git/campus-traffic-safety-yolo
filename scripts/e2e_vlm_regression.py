"""VLM 旁挂视觉研判（模式乙）隔离端到端回归。

验证目标（全部走真实 API，真实 YOLO 权重，隔离 DB/Qdrant/上传目录，不碰生产库）：

A. 无人物违停图：视觉模型真实出研判 → vision_assessment 真实并入 DeepSeek payload
   （模式乙：仅作证据，不产生策略字段）→ 巡检正常完成。
B. 含人物图：隐私闸门生效，视觉服务零调用（图片绝不上送云端）。

用法（仓库根目录）：
    <LOCAL_PATH> scripts/e2e_vlm_regression.py \
        --image "校园照片/新增照片/车/IMG_9759.JPG" \
        --image-person "校园照片/校园照片/IMG_9760.JPG" \
        --output outputs/vlm_e2e_regression_20260913.json
"""

from __future__ import annotations

import argparse
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
from app.services.llm import LLMService, VisionLLMService
from app.services.rag import KnowledgeBaseService

KNOWLEDGE_DOC = PROJECT_ROOT / "knowledge" / "校园交通安全巡检判定规范.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="VLM 模式乙隔离端到端回归")
    parser.add_argument("--image", required=True, type=Path, help="无人物的违停样例图")
    parser.add_argument("--image-person", required=True, type=Path, help="含人物的样例图")
    parser.add_argument("--knowledge", type=Path, default=KNOWLEDGE_DOC)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="campus-safety-vlm-e2e-") as temp:
        root = Path(temp)
        settings = Settings(
            database_url=f"sqlite:///{root / 'vlm_e2e.db'}",
            upload_dir=root / "uploads",
            output_dir=root / "outputs",
            # 权重默认路径相对 backend/ 目录，脚本从仓库根运行时必须显式指绝对路径
            yolo_model_path=(PROJECT_ROOT / "models" / "yolo26-tt100k-best.pt").resolve(),
            general_yolo_model_path=(PROJECT_ROOT / "models" / "yolo26m.pt").resolve(),
            qdrant_path=":memory:",
            blur_threshold=0,
            dark_threshold=0,
            bright_threshold=255,
            min_image_width=32,
            min_image_height=32,
            rag_score_threshold=0,
            vision_llm_enabled=True,  # 回归必须显式打开（生产默认 False 保回退）
        )
        database = Database(settings)
        knowledge = KnowledgeBaseService(settings, client=QdrantClient(":memory:"))
        llm = LLMService(settings)
        vision = VisionLLMService(settings)

        # --- 探针：记录视觉服务调用与 DeepSeek 实际收到的 payload ---
        probe: dict = {"vision_calls": [], "risk_payloads": []}
        orig_assess = vision.assess_image
        orig_generate = llm.generate_risk

        def spy_assess(*, image_path: str, context: dict) -> dict:
            probe["vision_calls"].append({"image_path": image_path})
            result = orig_assess(image_path=image_path, context=context)
            probe["vision_calls"][-1]["result"] = result
            return result

        def spy_generate(payload: dict):
            probe["risk_payloads"].append(payload)
            return orig_generate(payload)

        vision.assess_image = spy_assess  # type: ignore[method-assign]
        llm.generate_risk = spy_generate  # type: ignore[method-assign]

        app = create_app(
            settings,
            database=database,
            knowledge_base=knowledge,
            llm_service=llm,
            vision_llm=vision,
        )

        checks: list[dict] = []

        def check(name: str, ok: bool, detail: str = "") -> None:
            checks.append({"name": name, "passed": bool(ok), "detail": detail})

        try:
            assert vision.available, "VisionLLMService 不可用（检查 VISION_LLM_* 与 LLM_API_KEY）"
            assert llm.available, "LLMService 不可用（检查 LLM_API_KEY）"
            with TestClient(app) as client:
                with args.knowledge.open("rb") as stream:
                    resp = client.post(
                        "/api/v1/knowledge/documents",
                        files={"file": (args.knowledge.name, stream, "text/markdown")},
                    )
                resp.raise_for_status()

                def run_inspection(image: Path, location: str) -> dict:
                    with image.open("rb") as stream:
                        resp = client.post(
                            "/api/v1/inspections",
                            data={"location": location, "area_type": "校园主干道"},
                            files={"file": (image.name, stream, "image/jpeg")},
                        )
                    resp.raise_for_status()
                    task_id = resp.json()["id"]
                    resp = client.post(f"/api/v1/inspections/{task_id}/execute")
                    resp.raise_for_status()
                    return client.get(f"/api/v1/inspections/{task_id}").json()

                health = client.get("/api/v1/health").json()
                vision_health = health["services"].get("vision_llm", {})
                check(
                    "health 暴露 vision_llm 状态",
                    vision_health.get("enabled") is True and vision_health.get("configured") is True,
                    json.dumps(vision_health, ensure_ascii=False),
                )

                # ---- 用例 A：无人物违停图 → 视觉研判必须真实发生且并入 payload ----
                detail_a = run_inspection(args.image, "VLM回归验证点A-违停")
                check("A: 巡检完成", detail_a["status"] in {"completed", "review"}, detail_a["status"])
                check("A: 视觉服务恰好调用 1 次", len(probe["vision_calls"]) == 1,
                      f"calls={len(probe['vision_calls'])}")
                vision_result = probe["vision_calls"][0].get("result") if probe["vision_calls"] else None
                check("A: 视觉研判返回白名单字段", bool(vision_result) and
                      set(vision_result) <= {"model", "scene_description", "parking_assessment",
                                             "confidence", "visible_evidence",
                                             "legal_scenarios_checked", "notes"},
                      json.dumps(vision_result, ensure_ascii=False)[:300] if vision_result else "None")
                payload_a = probe["risk_payloads"][-1] if probe["risk_payloads"] else {}
                check("A: vision_assessment 真实并入 DeepSeek payload",
                      vision_result is not None
                      and payload_a.get("vision_assessment") == vision_result,
                      "并入一致" if (vision_result is not None
                                     and payload_a.get("vision_assessment") == vision_result)
                      else "未并入/不一致")
                check("A: payload 声明模式乙角色（仅证据、不得直接采用）",
                      "不得直接采用" in str(payload_a.get("vision_assessment_role", "")),
                      str(payload_a.get("vision_assessment_role", ""))[:80])
                check("A: risk_result 已生成", bool(detail_a.get("risk_result")),
                      (detail_a.get("risk_result") or {}).get("risk_level", "None"))

                # ---- 用例 B：含人物图 → 隐私闸门，视觉服务零新增调用 ----
                calls_before = len(probe["vision_calls"])
                detail_b = run_inspection(args.image_person, "VLM回归验证点B-含人物")
                person_hits = [d for d in detail_b.get("detections", []) if d["class_name"] == "person"]
                check("B: 巡检完成", detail_b["status"] in {"completed", "review"}, detail_b["status"])
                check("B: YOLO 确实检出 person（用例前提）", len(person_hits) >= 1,
                      f"person={len(person_hits)}")
                check("B: 隐私闸门生效，视觉服务零调用（图片未上送云端）",
                      len(probe["vision_calls"]) == calls_before,
                      f"calls={len(probe['vision_calls'])}（前={calls_before}）")

                result = {
                    "status": "passed" if all(c["passed"] for c in checks) else "failed",
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "vision_model": settings.vision_llm_model,
                    "vision_base_url": settings.vision_llm_base_url,
                    "checks": checks,
                    "case_a": {
                        "image": str(args.image.resolve()),
                        "status": detail_a["status"],
                        "risk_level": (detail_a.get("risk_result") or {}).get("risk_level"),
                        "vision_assessment": vision_result,
                    },
                    "case_b": {
                        "image": str(args.image_person.resolve()),
                        "status": detail_b["status"],
                        "person_detections": len(person_hits),
                        "vision_calls_total": len(probe["vision_calls"]),
                    },
                }
        finally:
            database.engine.dispose()
            knowledge.client.close()

        serialized = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized, encoding="utf-8")
        print(serialized)
        if result["status"] != "passed":
            sys.exit(1)


if __name__ == "__main__":
    main()
