"""Read-only demo checks: live maps, data consistency and minimal secret hygiene.

Never prints credentials and never writes to production APIs or databases.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    settings = Settings()
    credentials = [str(value) for value in (settings.llm_api_key, settings.vision_llm_api_key, settings.amap_web_service_key, settings.api_key) if value and len(str(value)) >= 8]
    cases = []
    facts = {}

    def check(name, action):
        try:
            action()
            cases.append({"name": name, "passed": True})
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            for credential in credentials:
                message = message.replace(credential, "[REDACTED]")
            cases.append({"name": name, "passed": False, "error": message})

    with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=60) as client:
        def runtime():
            responses = {name: client.get(f"/api/v1/{route}") for name, route in {
                "health": "health", "tasks": "inspections", "knowledge": "knowledge/documents",
                "analytics": "analytics/overview", "dashboard": "dashboard",
            }.items()}
            for response in responses.values():
                response.raise_for_status()
                assert not any(key in response.text for key in credentials), "Provider credential exposed in public response"
            values = {name: response.json() for name, response in responses.items()}
            health, tasks, knowledge = values["health"], values["tasks"], values["knowledge"]
            assert health["status"] == "ok"
            assert health["services"]["yolo"]["loaded"] and health["services"]["general_yolo"]["loaded"]
            assert all(item["status"] == "ready" for item in knowledge["items"])
            facts.update(tasks=tasks["total"], knowledge_documents=knowledge["total"], knowledge_chunks=sum(item["chunk_count"] for item in knowledge["items"]),
                         vision_model=health["services"]["vision_llm"]["model"])
            snapshot = {"tasks": sorted(tasks["items"], key=lambda item: item["id"]), "knowledge": sorted(knowledge["items"], key=lambda item: item["id"])}
            facts["production_fingerprint"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            assert values["analytics"]["summary"]["total_tasks"] == tasks["total"] == values["dashboard"]["total_tasks"]
        check("正式服务、双模型、知识状态、统计一致且响应无提供方密钥", runtime)

        def weather():
            response = client.get("/api/v1/maps/weather")
            response.raise_for_status()
            value = response.json()
            assert value.get("available") is True, "Weather provider unavailable"
            assert value.get("weather") and value.get("temperature") is not None
            facts["weather_available"] = True
        check("高德实际天气服务", weather)

        def geocode():
            response = client.get("/api/v1/maps/geocode", params={"address": "四川现代职业学院", "city": "成都"})
            response.raise_for_status()
            value = response.json()
            assert 103 < value["location"]["lng"] < 105 and 29 < value["location"]["lat"] < 32
            facts["school_coordinates"] = value["location"]
        check("高德实际学校地理编码", geocode)

        def static_map():
            response = client.get("/api/v1/maps/static")
            response.raise_for_status()
            assert response.headers.get("content-type", "").startswith("image/")
            decoded = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)
            assert decoded is not None and min(decoded.shape[:2]) >= 200
            facts["map_dimensions"] = [decoded.shape[1], decoded.shape[0]]
        check("高德实际静态底图可解码", static_map)

    def bundle():
        files = [path for path in (ROOT / "frontend/dist").rglob("*") if path.suffix in {".js", ".css", ".html", ".map"}]
        assert files, "No production frontend bundle"
        assert credentials, "No configured credentials to check"
        for path in files:
            assert not any(key in path.read_text(encoding="utf-8", errors="replace") for key in credentials), "Provider credential exposed in frontend build"
        tracked = subprocess.run(["git", "ls-files", ".env", ".env.*"], cwd=ROOT, capture_output=True, text=True, check=True)
        assert not [name for name in tracked.stdout.splitlines() if name != ".env.example"], "Real environment file tracked by Git"
        facts["bundle_files_checked"] = len(files)
    check("已配置密钥不在前端产物及Git环境文件索引", bundle)

    if args.baseline:
        def unchanged():
            baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
            assert facts.get("production_fingerprint") == baseline["facts"]["production_fingerprint"], "Production task/knowledge snapshot changed; inspect user activity before attributing to tests"
        check("测试前后正式任务与知识快照一致", unchanged)

    result = {"verified_at": datetime.now(timezone.utc).isoformat(), "read_only": True, "facts": facts, "cases": cases,
              "passed": sum(item["passed"] for item in cases), "failed": sum(not item["passed"] for item in cases)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
