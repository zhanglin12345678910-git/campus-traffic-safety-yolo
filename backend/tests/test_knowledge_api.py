from __future__ import annotations

from fastapi.testclient import TestClient


def test_upload_and_search_knowledge(client: TestClient):
    upload = client.post(
        "/api/v1/knowledge/documents",
        files={"file": ("parking.md", "停车场入口标志被遮挡时，应登记隐患并安排复查。".encode(), "text/markdown")},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["chunk_count"] == 1
    listing = client.get("/api/v1/knowledge/documents").json()
    assert listing["total"] == 1
    search = client.post("/api/v1/knowledge/search", json={"query": "停车场标志遮挡复查", "top_k": 3})
    assert search.status_code == 200
    assert search.json()["hits"]


def test_delete_knowledge_removes_chunks_and_stops_matching(client: TestClient):
    upload = client.post(
        "/api/v1/knowledge/documents",
        files={"file": ("fire.md", "消防车通道被占用时，应立即移除占道车辆并登记整改。".encode(), "text/markdown")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["id"]

    before = client.post("/api/v1/knowledge/search", json={"query": "消防车通道占用整改", "top_k": 3}).json()
    assert before["hits"], "删除前应能检索到该文档"

    deleted = client.delete(f"/api/v1/knowledge/documents/{document_id}")
    assert deleted.status_code == 200, deleted.text
    body = deleted.json()
    assert body["deleted"] is True
    assert body["removed_chunks"] >= 1
    assert client.get("/api/v1/knowledge/documents").json()["total"] == 0

    after = client.post("/api/v1/knowledge/search", json={"query": "消防车通道占用整改", "top_k": 3}).json()
    assert after["hits"] == [], "删除后不应再检索到该文档的分块"

    assert client.delete(f"/api/v1/knowledge/documents/{document_id}").status_code == 404
    assert client.delete("/api/v1/knowledge/documents/not-exists").status_code == 404

