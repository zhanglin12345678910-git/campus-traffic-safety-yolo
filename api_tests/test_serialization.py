from traffic_api.schemas import Detection, DetectionResult, ImageInfo
from traffic_api.serialization import detection_to_dict, result_to_dict


def test_detection_to_dict_returns_json_friendly_payload():
    detection = Detection(
        class_id=3,
        class_name="speed_limit",
        confidence=0.875,
        box_xyxy=(10, 20, 30, 40),
    )

    assert detection_to_dict(detection) == {
        "class_id": 3,
        "class_name": "speed_limit",
        "confidence": 0.875,
        "box_xyxy": [10.0, 20.0, 30.0, 40.0],
    }


def test_result_to_dict_wraps_success_data_and_top_class_summary():
    result = DetectionResult(
        image=ImageInfo(width=640, height=480, channels=3),
        detections=[
            Detection(0, "warning", 0.72, (1, 2, 50, 60)),
            Detection(1, "stop", 0.91, (100, 120, 180, 220)),
        ],
        message="detected 2 traffic signs",
    )

    payload = result_to_dict(result)

    assert payload["success"] is True
    assert payload["message"] == "detected 2 traffic signs"
    assert payload["data"]["image"] == {"width": 640, "height": 480, "channels": 3}
    assert payload["data"]["detections"] == [
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
    ]
    assert payload["data"]["summary"] == {"total": 2, "top_class": "stop"}


def test_result_to_dict_reports_no_top_class_for_empty_detections():
    result = DetectionResult(
        image=ImageInfo(width=320, height=240, channels=1),
        detections=[],
        message="no traffic sign detected",
    )

    payload = result_to_dict(result)

    assert payload["success"] is True
    assert payload["message"] == "no traffic sign detected"
    assert payload["data"]["summary"] == {"total": 0, "top_class": None}
