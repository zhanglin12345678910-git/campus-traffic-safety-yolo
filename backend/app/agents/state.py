from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict


class InspectionState(TypedDict, total=False):
    task_id: str
    run_id: str
    location: str
    area_type: str
    description: str | None
    image_path: str
    image_quality: dict[str, Any]
    detections: list[dict[str, Any]]
    vision_events: list[dict[str, Any]]
    detection_output: dict[str, Any]
    knowledge_results: list[Any]
    knowledge_elapsed_ms: float
    risk_result: dict[str, Any]
    recommendations: list[str]
    report_html: str
    review_required: bool
    review_reasons: list[str]
    error: str | None
    report_id: str
    saved: bool
    total_duration_ms: float
