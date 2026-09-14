"""Small-demo input guardrails; no real cloud calls or production writes."""
import pytest


@pytest.mark.parametrize("filename,size", [("empty.jpg", 0), ("large.jpg", 1024 * 1024 + 1)], ids=["empty", "oversize"])
def test_demo_image_empty_and_size_limit(client, filename, size):
    client.app.state.settings.max_upload_mb = 1
    response = client.post("/api/v1/inspections", data={"location": "隔离边界", "area_type": "校门口"},
                           files={"file": (filename, b"x" * size, "image/jpeg")})
    assert response.status_code == 400
    assert client.get("/api/v1/inspections").json()["total"] == 0


def test_demo_empty_video_is_rejected_before_analysis(client):
    response = client.post("/api/v1/video-analytics", data={"location": "隔离边界", "allowed_direction": "left_to_right"},
                           files={"file": ("empty.mp4", b"", "video/mp4")})
    assert response.status_code == 400
    assert not client.app.state.video_analytics.model_loaded
