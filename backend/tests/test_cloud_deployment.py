from pathlib import Path

import httpx
import pytest

from app.cloud_admin import KNOWLEDGE_NAMES, api_client, cloud_guard, response_json, validate_login

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("username,password", [("operator", "test-password-123456"), ("operator_2", "安全演示密码足够长十二位以上")])
def test_cloud_login_valid(username, password):
    validate_login(username, password)


@pytest.mark.parametrize("username,password", [("a:b", "test-password-123456"), ("operator", "short"), ("operator", "password-long\ninvalid")])
def test_cloud_login_rejects_invalid(username, password):
    with pytest.raises(ValueError):
        validate_login(username, password)


def test_cloud_guard_prevents_local_execution(monkeypatch):
    monkeypatch.setenv("YOLO_DEVICE", "0")
    monkeypatch.setenv("QDRANT_PATH", "./data/qdrant")
    with pytest.raises(RuntimeError):
        cloud_guard()
    monkeypatch.setenv("YOLO_DEVICE", "cpu")
    monkeypatch.setenv("QDRANT_PATH", "/app/backend/data/qdrant")
    cloud_guard()


def test_cloud_retained_knowledge_not_fixture():
    assert len(set(KNOWLEDGE_NAMES)) == 5
    assert "校园交通巡检示例规范.md" not in KNOWLEDGE_NAMES
    assert all((ROOT / "knowledge" / name).is_file() for name in KNOWLEDGE_NAMES)


def test_cloud_response_error_does_not_echo_body():
    with pytest.raises(RuntimeError) as caught:
        response_json(httpx.Response(403, text="private-provider-token"))
    assert "private-provider-token" not in str(caught.value)
    assert response_json(httpx.Response(200, json={"status": "ok"})) == {"status": "ok"}


def test_cloud_anonymous_gateway_request_overrides_client_auth(monkeypatch):
    monkeypatch.setenv("DEMO_USER", "operator")
    monkeypatch.setenv("DEMO_PASSWORD", "test-password-123456")
    with api_client(gateway=True) as client:
        seen = []
        client._transport = httpx.MockTransport(lambda request: (seen.append(request.headers.get("authorization")), httpx.Response(200))[1])
        client.get("/api/v1/health", auth=None)
        client.get("/api/v1/health")
    assert seen[0] is None
    assert seen[1].startswith("Basic ")


def test_cloud_contract_prebuilt_cpu_no_public_backend():
    compose = (ROOT / "docker-compose.cloud.yml").read_text(encoding="utf-8")
    assert "YOLO_DEVICE: cpu" in compose and "Dockerfile.cloud" in compose
    assert "MYSQL" not in compose and "6333:" not in compose and "8000:" not in compose
    # The current dashboard uses live inspection results, not the retired raw
    # incident photos. Release only the three reviewed runtime UI assets.
    for asset in ("campus-gis-map.png", "campus-sidebar-skyline.png", "scmvc-official-logo.png"):
        assert (ROOT / "frontend/src/assets" / asset).is_file()
    assert not (ROOT / "frontend/src/assets/incidents/dormitory-road.jpg").exists()
    assert not (ROOT / "frontend/public/campus").exists()
    dockerfile = (ROOT / "frontend/Dockerfile.cloud").read_text(encoding="utf-8")
    assert "COPY dist" in dockerfile and "npm" not in dockerfile
    assert "dist" not in (ROOT / "frontend/.dockerignore").read_text().splitlines()
    nginx = (ROOT / "deploy/nginx.cloud.conf").read_text()
    assert 'auth_basic "Campus Safety"' in nginx
    assert "proxy_read_timeout 600s" in nginx
