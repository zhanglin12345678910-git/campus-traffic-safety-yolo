"""Explicit cloud-only setup and acceptance; never targets the local production API.

Run via docker-compose.cloud.yml. Seed is idempotent and excludes the historical
example fixture. Verify creates one clearly labelled cloud acceptance task.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

import httpx

KNOWLEDGE_NAMES = (
    "交通标志类别释义（TT100K 45 类）.md",
    "校园交通安全管理实践（学校公开材料）.md",
    "校园交通安全巡检判定规范.md",
    "校园交通隐患整改建议库.md",
    "校园交通与消防安全法规依据摘录.md",
)


def validate_login(username: str, password: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", username):
        raise ValueError("DEMO_USER must contain 1-32 ASCII letters, digits, _ or -")
    if len(password) < 12 or any(c in password for c in "\r\n\x00"):
        raise ValueError("DEMO_PASSWORD must be at least 12 characters without line breaks")


def cloud_guard() -> None:
    # Prevent accidental execution against Windows/local production paths.
    if os.environ.get("YOLO_DEVICE") != "cpu" or os.environ.get("QDRANT_PATH") != "/app/backend/data/qdrant":
        raise RuntimeError("Run this utility only inside the cloud CPU container")


def setup() -> None:
    username, password = os.environ.get("DEMO_USER", "operator"), os.environ.get("DEMO_PASSWORD", "")
    validate_login(username, password)
    for name in ("LLM_API_KEY", "VISION_LLM_API_KEY", "AMAP_WEB_SERVICE_KEY"):
        if not os.environ.get(name, "").strip():
            raise ValueError(f"Fill {name} in .env.cloud; configuration is not network acceptance")
    if os.environ.get("API_KEY", ""):
        raise ValueError("Leave API_KEY empty: this cloud profile uses gateway authentication")
    # Linux Python 3.10 supports SHA-512 crypt; no password enters logs or images.
    import crypt
    hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    if not hashed or not hashed.startswith("$6$"):
        raise RuntimeError("Host crypt implementation cannot create SHA-512 htpasswd")
    target = Path("/app/deploy-runtime/demo.htpasswd")
    target.write_text(f"{username}:{hashed}\n", encoding="utf-8")
    # Nginx workers need read permission; host directory remains private.
    target.chmod(0o644)
    print("Gateway password hash prepared (password not printed).")


def api_client(*, gateway: bool = False) -> httpx.Client:
    auth = (os.environ.get("DEMO_USER", "operator"), os.environ.get("DEMO_PASSWORD", "")) if gateway else None
    return httpx.Client(base_url="http://frontend" if gateway else "http://127.0.0.1:8000",
                        auth=auth, timeout=30, trust_env=False)


def response_json(response: httpx.Response):
    if not response.is_success:
        # Do not echo upstream response bodies, URLs or configured credentials.
        raise RuntimeError(f"Cloud API returned HTTP {response.status_code}")
    return response.json()


def seed() -> None:
    with api_client() as client:
        documents = response_json(client.get("/api/v1/knowledge/documents"))["items"]
        existing = {d["name"]: d for d in documents}
        unexpected = set(existing) - set(KNOWLEDGE_NAMES)
        if unexpected or len(existing) != len(documents):
            raise RuntimeError("Cloud knowledge contains unexpected/duplicate documents; inspect without deleting")
        for name in KNOWLEDGE_NAMES:
            if name in existing:
                if existing[name]["status"] != "ready":
                    raise RuntimeError("Existing cloud document is not ready; inspect before retrying")
                continue
            with (Path("/app/knowledge") / name).open("rb") as source:
                result = response_json(client.post("/api/v1/knowledge/documents", files={"file": (name, source, "text/markdown")}))
            if result["status"] != "ready":
                raise RuntimeError("Knowledge ingestion did not finish")
    print("Five retained source documents seeded; example fixture was not uploaded.")


def check() -> dict:
    from sqlalchemy import create_engine
    from app.docker_probe import inspect_database
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        schema = inspect_database(engine, required_dialect="sqlite")
    finally:
        engine.dispose()
    if schema["status"] != "passed":
        raise RuntimeError("Cloud SQLite migration/schema check failed")
    with api_client(gateway=True) as client:
        for path in ("/", "/api/v1/health", "/uploads/missing", "/outputs/missing"):
            if client.get(path, auth=None).status_code != 401:
                raise RuntimeError("Anonymous gateway access was not rejected")
        client.get("/inspection/new").raise_for_status()
        health = response_json(client.get("/api/v1/health"))
        services = health["services"]
        if health["status"] != "ok" or services["qdrant"]["status"] != "ok":
            raise RuntimeError("Backend or embedded Qdrant is not healthy")
        if not all(services[name]["configured"] for name in ("yolo", "general_yolo")):
            raise RuntimeError("A deployed weight is missing")
        documents = response_json(client.get("/api/v1/knowledge/documents"))["items"]
        if len(documents) != 5 or {d["name"] for d in documents} != set(KNOWLEDGE_NAMES):
            raise RuntimeError("Expected exactly five retained knowledge documents")
        if not all(d["status"] == "ready" and d["chunk_count"] > 0 for d in documents):
            raise RuntimeError("Knowledge indexing is incomplete")
    result = {"schema": "passed", "gateway_auth": "passed", "knowledge_documents": len(documents),
              "knowledge_chunks": sum(d["chunk_count"] for d in documents), "device": "cpu",
              "provider_network": "not tested by health/configuration checks"}
    print(json.dumps(result, ensure_ascii=False))
    return result


def verify() -> None:
    result = check()
    # Explicitly creates only a new cloud acceptance task, not a local task.
    with api_client(gateway=True) as client:
        with Path("/app/acceptance-data/acceptance.jpg").open("rb") as image:
            task = response_json(client.post("/api/v1/inspections", data={
                "location": "CPU功能验证（授权测试素材）", "area_type": "校园主干道",
                "inspector_name": "部署验收脚本", "description": "仅验证功能闭环，不是真实事件或准确率真值"},
                files={"file": ("acceptance.jpg", image, "image/jpeg")}))
        task_id = task["id"]
        response_json(client.post(f"/api/v1/inspections/{task_id}/execute"))
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            task = response_json(client.get(f"/api/v1/inspections/{task_id}"))
            if task["status"] in {"completed", "review", "failed", "error", "rejected"}:
                break
            time.sleep(2)
        if task["status"] not in {"completed", "review"} or not task.get("report_id"):
            raise RuntimeError("CPU image analysis/report did not complete within 600s; inspect cloud logs")
        if not task.get("detections"):
            raise RuntimeError("Acceptance image produced no real detections")
        risk = task.get("risk_result") or {}
        if risk.get("analysis_mode") != "llm":
            raise RuntimeError("DeepSeek did not actually analyse this task; fallback is not network success")
        report = client.get(f"/api/v1/reports/{task['report_id']}/view")
        if report.status_code != 200 or "text/html" not in report.headers.get("content-type", ""):
            raise RuntimeError("HTML report is unavailable through the gateway")
        for field in ("original_image_url", "result_image_url"):
            if not task.get(field) or client.get(task[field]).status_code != 200:
                raise RuntimeError("Acceptance media is unavailable through the gateway")
        health = response_json(client.get("/api/v1/health"))["services"]
        if not all(health[n]["loaded"] for n in ("yolo", "general_yolo")):
            raise RuntimeError("Both real CPU models must be loaded after inference")
        # Synthetic confirmation exercises persistence, not a real human judgment.
        response_json(client.post(f"/api/v1/inspections/{task_id}/review", json={"action": "confirm",
            "reviewer": "部署验收脚本", "comment": "功能验收自动确认；不表示现场事实已经人工核实"}))
        final = response_json(client.get(f"/api/v1/inspections/{task_id}"))
        if final["status"] != "completed" or final["review_required"]:
            raise RuntimeError("Review persistence failed")
    result.update({"cpu_image_report_review": "passed", "deepseek_actual_task": "passed", "task_id": task_id,
                   "qwen_actual_call": "not certified by this fixture (person privacy gate may skip it)",
                   "amap_actual_call": "requires browser/provider acceptance", "video": "requires CPU timing/browser acceptance"})
    Path("/app/deploy-runtime/acceptance-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("setup", "seed", "check", "verify"))
    args = parser.parse_args()
    cloud_guard()
    try:
        {"setup": setup, "seed": seed, "check": check, "verify": verify}[args.action]()
    except (ValueError, RuntimeError, OSError, httpx.HTTPError) as exc:
        # Upstream exceptions might contain proxy URLs/credentials; only emit type.
        print(f"Cloud {args.action} failed ({type(exc).__name__}); inspect environment, resources and redacted logs.")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
