from pathlib import Path

from traffic_api.schemas import Detection, DetectionResult, ImageInfo
from traffic_api.serialization import result_to_contract_dict


def test_result_to_contract_dict_returns_sf_fastgpt_contract():
    result = DetectionResult(
        image=ImageInfo(width=640, height=480, channels=3),
        detections=[
            Detection(0, "warning", 0.72, (1, 2, 50, 60)),
            Detection(1, "stop", 0.91, (100, 120, 180, 220)),
        ],
        message="detected 2 traffic signs",
        elapsed_ms=18.456,
    )

    payload = result_to_contract_dict(
        result,
        task_id="task-123",
        model_path=Path("weights/best.pt"),
        device="0",
        img_size=640,
        conf_threshold=0.3,
        iou_threshold=0.5,
        result_image_url="/outputs/detections/task-123.jpg",
        filename="road.jpg",
        location="north gate",
        description="morning inspection",
    )

    assert payload == {
        "success": True,
        "task_id": "task-123",
        "image": {
            "filename": "road.jpg",
            "width": 640,
            "height": 480,
            "channels": 3,
        },
        "model": {
            "weights": "best.pt",
            "device": "0",
            "img_size": 640,
            "conf_threshold": 0.3,
            "iou_threshold": 0.5,
        },
        "detections": [
            {
                "class_id": 0,
                "class_name": "warning",
                "confidence": 0.72,
                "box_xyxy": [1.0, 2.0, 50.0, 60.0],
            },
            {
                "class_id": 1,
                "class_name": "stop",
                "confidence": 0.91,
                "box_xyxy": [100.0, 120.0, 180.0, 220.0],
            },
        ],
        "object_count": 2,
        "review_required": False,
        "review_reasons": [],
        "result_image_url": "/outputs/detections/task-123.jpg",
        "timing": {"elapsed_ms": 18.46},
        "location": "north gate",
        "description": "morning inspection",
        "error": None,
    }


def test_result_to_contract_dict_handles_empty_detections_and_missing_model():
    result = DetectionResult(
        image=ImageInfo(width=320, height=240, channels=3),
        detections=[],
        message="no traffic sign detected",
    )

    payload = result_to_contract_dict(result, task_id="task-empty")

    assert payload["success"] is True
    assert payload["task_id"] == "task-empty"
    assert payload["model"]["weights"] is None
    assert payload["object_count"] == 0
    assert payload["review_required"] is False
    assert payload["review_reasons"] == []
    assert payload["result_image_url"] is None
    assert payload["timing"]["elapsed_ms"] is None
    assert payload["error"] is None
