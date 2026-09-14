from __future__ import annotations

import asyncio
import json
import secrets
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from sqlalchemy import case, desc, func, select, text
from sqlalchemy.orm import Session, selectinload

from app.models import (
    AgentStep,
    DetectionResult,
    InspectionImage,
    InspectionTask,
    KnowledgeDocument,
    ManualReview,
    Report,
)
from app.schemas import FeedbackRequest, KnowledgeSearchRequest, ReviewRequest
from app.services.files import IMAGE_EXTENSIONS, KNOWLEDGE_EXTENSIONS, VIDEO_EXTENSIONS, UploadValidationError, store_upload
from app.services.amap import AMapServiceError
from app.tools.video_analytics import VideoAnalyticsError


router = APIRouter()
TREND_DAYS = 7


def db_session(request: Request):
    yield from request.app.state.database.dependency()


def require_api_key(request: Request) -> None:
    expected = request.app.state.settings.api_key
    if expected and not secrets.compare_digest(request.headers.get("X-API-Key", ""), expected):
        raise HTTPException(status_code=401, detail="API Key 无效或缺失")


def _task_query():
    return select(InspectionTask).options(
        selectinload(InspectionTask.images),
        selectinload(InspectionTask.detections),
        selectinload(InspectionTask.risk_assessments),
        selectinload(InspectionTask.reports),
        selectinload(InspectionTask.reviews),
    )


def _json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def task_to_dict(task: InspectionTask, detailed: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": task.id,
        "task_no": task.task_no,
        "location": task.location,
        "area_type": task.area_type,
        "description": task.description,
        "inspector_name": task.inspector_name,
        "status": task.status,
        "risk_level": task.risk_level,
        "review_required": task.review_required,
        "review_reasons": _json(task.review_reasons_json, []),
        "vision_events": _json(task.vision_events_json, []),
        "original_image_url": task.original_image_url,
        "result_image_url": task.result_image_url,
        "detection_count": len(task.detections),
        "max_confidence": max((item.confidence for item in task.detections), default=None),
        "total_duration_ms": task.total_duration_ms,
        "feedback_rating": task.feedback_rating,
        "feedback_text": task.feedback_text,
        "created_at": _iso(task.created_at),
        "updated_at": _iso(task.updated_at),
    }
    if not detailed:
        return data
    data["detections"] = [
        {
            "class_id": item.class_id,
            "class_name": item.class_name,
            "display_name": item.display_name or item.class_name,
            "model_role": item.model_role,
            "model_name": item.model_name,
            "confidence": item.confidence,
            "bbox_xyxy": [item.x1, item.y1, item.x2, item.y2],
            "inference_ms": item.inference_ms,
        }
        for item in task.detections
    ]
    risk = task.risk_assessments[-1] if task.risk_assessments else None
    data["risk_result"] = None if risk is None else {
        "risk_level": risk.risk_level,
        "risk_score": risk.risk_score,
        "problem_summary": risk.problem_summary,
        "evidence": _json(risk.evidence_json, []),
        "knowledge_references": _json(risk.knowledge_references_json, []),
        "recommendations": _json(risk.recommendations_json, []),
        "review_required": risk.review_required,
        "uncertainty_note": risk.uncertainty_note,
        "analysis_mode": risk.analysis_mode,
    }
    data["report_id"] = task.reports[-1].id if task.reports else None
    data["reviews"] = [
        {
            "id": item.id,
            "action": item.action,
            "reviewer": item.reviewer,
            "comment": item.comment,
            "modified_risk_level": item.modified_risk_level,
            "created_at": _iso(item.created_at),
        }
        for item in task.reviews
    ]
    return data


@router.get("/health")
def health(request: Request, db: Session = Depends(db_session)):
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    settings = request.app.state.settings
    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "services": {
            "database": database_status,
            "qdrant": request.app.state.knowledge_base.health(),
            "yolo": {
                "configured": settings.yolo_model_path.exists(),
                "loaded": request.app.state.yolo_tool.model_loaded,
                "model_name": settings.yolo_model_path.name,
                "load_count": request.app.state.yolo_tool.load_count,
            },
            "general_yolo": {
                "enabled": settings.general_yolo_enabled,
                "configured": settings.general_yolo_model_path.exists(),
                "loaded": getattr(request.app.state.yolo_tool, "general_model_loaded", False),
                "model_name": settings.general_yolo_model_path.name,
                "load_count": getattr(request.app.state.yolo_tool, "general_load_count", 0),
                # Video tracking runs on its own instance, never the image singleton.
                "tracking_loaded": getattr(request.app.state.video_analytics, "model_loaded", False),
                "tracking_load_count": getattr(request.app.state.video_analytics, "load_count", 0),
                "classes": sorted(settings.general_object_class_names),
                "crowd_threshold": settings.crowd_min_persons,
            },
            "llm": {"configured": request.app.state.llm_service.available, "model": settings.llm_model},
            "vision_llm": {
                # 旁挂视觉研判（模式乙证据侧车）：enabled 是开关，configured
                # 表示密钥与模型已就绪；未启用时其余字段只表达配置状态。
                "enabled": settings.vision_llm_enabled,
                "configured": request.app.state.vision_llm_service.available,
                "model": settings.vision_llm_model,
                "person_gate": settings.vision_skip_images_with_person,
            },
            "amap": {
                "configured": request.app.state.amap_service.available,
                "provider": "高德 Web 服务",
            },
            "network": {
                "outbound_proxy_configured": bool(settings.outbound_http_proxy),
            },
        },
    }


@router.get("/maps/geocode")
def geocode_address(
    request: Request,
    address: str = Query(min_length=2, max_length=200),
    city: str | None = Query(default="成都", max_length=80),
):
    try:
        return request.app.state.amap_service.geocode(address.strip(), city.strip() if city else None)
    except AMapServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/maps/static")
def campus_static_map(
    request: Request,
    lng: float = Query(default=103.997424, ge=-180, le=180),
    lat: float = Query(default=30.515862, ge=-90, le=90),
    zoom: int = Query(default=17, ge=1, le=17),
    width: int = Query(default=1024, ge=200, le=1024),
    height: int = Query(default=640, ge=200, le=1024),
    traffic: bool = Query(default=False),
):
    try:
        image = request.app.state.amap_service.static_map(
            lng=lng,
            lat=lat,
            zoom=zoom,
            width=width,
            height=height,
            traffic=traffic,
        )
    except AMapServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=image.content,
        media_type=image.content_type,
        headers={"Cache-Control": "public, max-age=300", "X-Map-Provider": "amap"},
    )


@router.get("/maps/weather")
def campus_weather(request: Request, adcode: str = Query(default="510116", pattern=r"^\d{6}$")):
    # The topbar polls this on every page, so an unavailable provider is
    # reported in the body instead of as an HTTP error.
    service = request.app.state.amap_service
    if not service.available:
        return {"available": False, "message": "高德 Web 服务 Key 尚未配置"}
    try:
        return {"available": True, **service.weather(adcode)}
    except AMapServiceError as exc:
        return {"available": False, "message": str(exc)}


def _daily_trend(db: Session, tz: tzinfo, days: int = TREND_DAYS) -> list[dict[str, Any]]:
    """Count tasks per local calendar day over a configurable recent window."""
    today = datetime.now(tz).date()
    first_day = today - timedelta(days=days - 1)
    buckets = {
        first_day + timedelta(days=offset): {"total": 0, "review_required": 0, "high_risk": 0}
        for offset in range(days)
    }
    # created_at is stored as naive UTC on both SQLite and MySQL.
    window_start = datetime.combine(first_day, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
    rows = db.execute(
        select(InspectionTask.created_at, InspectionTask.review_required, InspectionTask.risk_level).where(
            InspectionTask.created_at >= window_start.replace(tzinfo=None)
        )
    ).all()
    for created_at, review_required, risk_level in rows:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        bucket = buckets.get(created_at.astimezone(tz).date())
        if bucket is None:
            continue
        bucket["total"] += 1
        bucket["review_required"] += int(bool(review_required))
        bucket["high_risk"] += int(risk_level == "high")
    return [{"date": day.isoformat(), **counts} for day, counts in sorted(buckets.items())]


def _review_reason_category(reason: str) -> str:
    """Fold free-form review reasons into stable, explainable dashboard groups."""

    if any(word in reason for word in ("模糊", "过暗", "过曝", "尺寸", "图片", "无法解码")):
        return "图片质量"
    if any(word in reason for word in ("置信度", "检测结果", "未检测到")):
        return "检测可信度"
    if any(word in reason for word in ("人员聚集", "逆行", "视觉事件", "现场确认")):
        return "视觉事件"
    if any(word in reason for word in ("知识", "依据", "法规")):
        return "知识依据"
    if any(word in reason for word in ("风险等级", "复核策略")):
        return "风险策略"
    if any(word in reason for word in ("模型", "服务", "工具", "异常")):
        return "模型或服务"
    return "其他原因"


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(db_session)):
    total = db.scalar(select(func.count()).select_from(InspectionTask)) or 0
    review = db.scalar(
        select(func.count()).select_from(InspectionTask).where(InspectionTask.review_required.is_(True))
    ) or 0
    completed = db.scalar(
        select(func.count()).select_from(InspectionTask).where(InspectionTask.status == "completed")
    ) or 0
    risk_rows = db.execute(
        select(InspectionTask.risk_level, func.count()).group_by(InspectionTask.risk_level)
    ).all()
    recent = db.scalars(_task_query().order_by(desc(InspectionTask.created_at)).limit(8)).unique().all()
    trend = _daily_trend(db, request.app.state.settings.display_timezone)
    return {
        "total_tasks": total,
        "today_tasks": trend[-1]["total"],
        "review_required": review,
        "completed_tasks": completed,
        "risk_counts": {str(level or "pending"): count for level, count in risk_rows},
        "daily_trend": trend,
        "recent_tasks": [task_to_dict(task) for task in recent],
    }


@router.get("/analytics/overview")
def analytics_overview(request: Request, db: Session = Depends(db_session)):
    """Return read-only, database-backed statistics for the analysis workspace."""

    total = db.scalar(select(func.count()).select_from(InspectionTask)) or 0
    completed = db.scalar(
        select(func.count()).select_from(InspectionTask).where(InspectionTask.status == "completed")
    ) or 0
    review = db.scalar(
        select(func.count()).select_from(InspectionTask).where(InspectionTask.review_required.is_(True))
    ) or 0
    average_duration = db.scalar(
        select(func.avg(InspectionTask.total_duration_ms)).where(InspectionTask.total_duration_ms.is_not(None))
    )

    status_rows = db.execute(
        select(InspectionTask.status, func.count()).group_by(InspectionTask.status)
    ).all()
    risk_rows = db.execute(
        select(InspectionTask.risk_level, func.count()).group_by(InspectionTask.risk_level)
    ).all()
    area_rows = db.execute(
        select(
            InspectionTask.area_type,
            func.count().label("total"),
            func.sum(case((InspectionTask.review_required.is_(True), 1), else_=0)).label("review"),
            func.sum(case((InspectionTask.risk_level == "high", 1), else_=0)).label("high"),
            func.avg(InspectionTask.total_duration_ms).label("average_duration_ms"),
        )
        .group_by(InspectionTask.area_type)
        .order_by(desc("total"), InspectionTask.area_type)
    ).all()

    reason_counts: Counter[str] = Counter()
    for reasons_json in db.scalars(
        select(InspectionTask.review_reasons_json).where(InspectionTask.review_required.is_(True))
    ):
        categories = {
            _review_reason_category(str(reason))
            for reason in _json(reasons_json, [])
            if str(reason).strip()
        }
        reason_counts.update(categories)

    model_rows = db.execute(
        select(
            DetectionResult.model_role,
            DetectionResult.model_name,
            func.count().label("detection_count"),
            func.avg(DetectionResult.confidence).label("average_confidence"),
        )
        .group_by(DetectionResult.model_role, DetectionResult.model_name)
        .order_by(desc("detection_count"))
    ).all()
    class_name = func.coalesce(func.nullif(DetectionResult.display_name, ""), DetectionResult.class_name)
    class_rows = db.execute(
        select(class_name.label("class_name"), func.count().label("detection_count"))
        .group_by(class_name)
        .order_by(desc("detection_count"), class_name)
        .limit(10)
    ).all()
    node_rows = db.execute(
        select(
            AgentStep.node_name,
            func.count().label("run_count"),
            func.avg(AgentStep.duration_ms).label("average_duration_ms"),
            func.sum(case((AgentStep.status == "error", 1), else_=0)).label("error_count"),
        )
        .group_by(AgentStep.node_name)
        .order_by(desc("average_duration_ms"))
    ).all()

    return {
        "summary": {
            "total_tasks": total,
            "completed_tasks": completed,
            "review_required": review,
            "completion_rate": round(completed / total * 100, 1) if total else 0,
            "review_rate": round(review / total * 100, 1) if total else 0,
            "average_duration_ms": round(float(average_duration or 0), 2),
        },
        "daily_trend": _daily_trend(db, request.app.state.settings.display_timezone, days=30),
        "configured_models": {
            "traffic_sign": request.app.state.settings.yolo_model_path.name,
            "general_object": request.app.state.settings.general_yolo_model_path.name
            if request.app.state.settings.general_yolo_enabled else None,
        },
        "risk_counts": {str(level or "pending"): int(count) for level, count in risk_rows},
        "status_counts": {str(status or "pending"): int(count) for status, count in status_rows},
        "area_breakdown": [
            {
                "area_type": str(area_type or "未分类"),
                "total": int(area_total or 0),
                "review_required": int(area_review or 0),
                "high_risk": int(area_high or 0),
                "average_duration_ms": round(float(area_duration or 0), 2),
            }
            for area_type, area_total, area_review, area_high, area_duration in area_rows
        ],
        "review_reason_counts": [
            {"category": category, "count": count}
            for category, count in reason_counts.most_common()
        ],
        "model_breakdown": [
            {
                "model_role": str(role or "unknown"),
                "model_name": str(model_name or "未记录"),
                "detection_count": int(count or 0),
                "average_confidence": round(float(confidence or 0), 4),
            }
            for role, model_name, count, confidence in model_rows
        ],
        "class_breakdown": [
            {"class_name": str(name or "未命名"), "detection_count": int(count or 0)}
            for name, count in class_rows
        ],
        "agent_performance": [
            {
                "node_name": str(name),
                "run_count": int(count or 0),
                "average_duration_ms": round(float(duration or 0), 2),
                "error_count": int(errors or 0),
            }
            for name, count, duration, errors in node_rows
        ],
    }


@router.post("/inspections", status_code=201, dependencies=[Depends(require_api_key)])
async def create_inspection(
    request: Request,
    file: UploadFile = File(...),
    location: str = Form(..., min_length=1, max_length=200),
    area_type: str = Form(..., min_length=1, max_length=80),
    description: str | None = Form(default=None, max_length=2000),
    inspector_name: str | None = Form(default=None, max_length=100),
    db: Session = Depends(db_session),
):
    settings = request.app.state.settings
    try:
        stored = await store_upload(
            file,
            settings.upload_dir / "inspections",
            settings.max_upload_bytes,
            IMAGE_EXTENSIONS,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        decoded = cv2.imdecode(np.fromfile(str(stored.stored_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    except (OSError, ValueError):
        decoded = None
    if decoded is None:
        stored.stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="图片内容无法解码")

    now_text = datetime.now().strftime("%Y%m%d")
    task = InspectionTask(
        task_no=f"AX-{now_text}-{uuid.uuid4().hex[:6].upper()}",
        location=location.strip(),
        area_type=area_type.strip(),
        description=description.strip() if description else None,
        inspector_name=inspector_name.strip() if inspector_name else None,
        original_image_url=f"/uploads/inspections/{stored.stored_path.name}",
    )
    db.add(task)
    db.flush()
    db.add(
        InspectionImage(
            task_id=task.id,
            original_name=stored.original_name,
            stored_path=str(stored.stored_path),
            mime_type=stored.mime_type,
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
        )
    )
    db.commit()
    db.refresh(task)
    return task_to_dict(task)


@router.post("/video-analytics", dependencies=[Depends(require_api_key)])
async def analyze_video(
    request: Request,
    file: UploadFile = File(...),
    location: str = Form(..., min_length=1, max_length=200),
    allowed_direction: str = Form(...),
):
    if allowed_direction not in request.app.state.video_analytics.DIRECTIONS:
        raise HTTPException(status_code=400, detail="允许方向参数无效")
    settings = request.app.state.settings
    try:
        stored = await store_upload(
            file,
            settings.upload_dir / "videos",
            settings.video_max_upload_bytes,
            VIDEO_EXTENSIONS,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = await asyncio.to_thread(
            request.app.state.video_analytics.analyze,
            stored.stored_path,
            allowed_direction,
        )
    except VideoAnalyticsError as exc:
        stored.stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result.update(
        {
            "location": location.strip(),
            "source_video_url": f"/uploads/videos/{stored.stored_path.name}",
            "source_name": stored.original_name,
            "source_size_bytes": stored.size_bytes,
        }
    )
    return result


@router.post("/inspections/{task_id}/execute", status_code=202, dependencies=[Depends(require_api_key)])
def execute_inspection(
    task_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_session),
):
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    if task.status in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="巡检任务已进入执行队列或正在执行")
    task.status = "queued"
    db.commit()
    background_tasks.add_task(request.app.state.workflow.run, task_id)
    return {"accepted": True, "task_id": task_id, "status": "queued"}


@router.get("/inspections")
def list_inspections(
    status: str | None = None,
    risk_level: str | None = None,
    review_required: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(db_session),
):
    filters = []
    if status:
        filters.append(InspectionTask.status == status)
    if risk_level:
        filters.append(InspectionTask.risk_level == risk_level)
    if review_required is not None:
        filters.append(InspectionTask.review_required.is_(review_required))
    total = db.scalar(select(func.count()).select_from(InspectionTask).where(*filters)) or 0
    query = _task_query().where(*filters).order_by(desc(InspectionTask.created_at)).offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(query).unique().all()
    return {"items": [task_to_dict(item) for item in items], "total": total, "page": page, "page_size": page_size}


@router.get("/inspections/{task_id}")
def get_inspection(task_id: str, db: Session = Depends(db_session)):
    task = db.scalars(_task_query().where(InspectionTask.id == task_id)).unique().first()
    if task is None:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    return task_to_dict(task, detailed=True)


@router.get("/inspections/{task_id}/trace")
def get_trace(task_id: str, db: Session = Depends(db_session)):
    if db.get(InspectionTask, task_id) is None:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    steps = db.scalars(
        select(AgentStep).where(AgentStep.task_id == task_id).order_by(AgentStep.started_at, AgentStep.sequence)
    ).all()
    return {"task_id": task_id, "steps": [_step_to_dict(item) for item in steps]}


@router.get("/inspections/{task_id}/stream")
async def stream_trace(task_id: str, request: Request, api_key: str | None = None):
    expected = request.app.state.settings.api_key
    if expected and not secrets.compare_digest(api_key or "", expected):
        raise HTTPException(status_code=401, detail="API Key 无效或缺失")

    async def events():
        sent_ids: set[str] = set()
        idle_after_done = 0
        while True:
            if await request.is_disconnected():
                break
            with request.app.state.database.session() as db:
                task = db.get(InspectionTask, task_id)
                if task is None:
                    yield _sse("error", {"message": "巡检任务不存在"})
                    break
                steps = db.scalars(
                    select(AgentStep).where(AgentStep.task_id == task_id).order_by(AgentStep.started_at, AgentStep.sequence)
                ).all()
                for step in steps:
                    if step.id not in sent_ids:
                        sent_ids.add(step.id)
                        yield _sse("step", _step_to_dict(step))
                if task.status in {"completed", "review", "error", "rejected"}:
                    idle_after_done += 1
                    if idle_after_done >= 2:
                        yield _sse("done", {"task_id": task_id, "status": task.status})
                        break
            await asyncio.sleep(0.35)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/inspections/{task_id}/review", dependencies=[Depends(require_api_key)])
def review_inspection(task_id: str, payload: ReviewRequest, db: Session = Depends(db_session)):
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    review = ManualReview(
        task_id=task.id,
        action=payload.action,
        reviewer=payload.reviewer,
        comment=payload.comment,
        modified_risk_level=payload.risk_level,
    )
    db.add(review)
    if payload.risk_level:
        task.risk_level = payload.risk_level
    if payload.action in {"confirm", "modify"}:
        task.review_required = False
        task.status = "completed"
    else:
        task.status = "rejected"
        task.review_required = True
    db.commit()
    return {"success": True, "task_id": task.id, "status": task.status, "review_required": task.review_required}


@router.post("/inspections/{task_id}/feedback", dependencies=[Depends(require_api_key)])
def save_feedback(task_id: str, payload: FeedbackRequest, db: Session = Depends(db_session)):
    task = db.get(InspectionTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="巡检任务不存在")
    task.feedback_rating = payload.rating
    task.feedback_text = payload.comment
    db.commit()
    return {"success": True}


@router.get("/reports/{report_id}")
def get_report(report_id: str, db: Session = Depends(db_session)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {
        "id": report.id,
        "task_id": report.task_id,
        "title": report.title,
        "html_content": report.html_content,
        "generation_status": report.generation_status,
        "created_at": _iso(report.created_at),
    }


@router.get("/reports/{report_id}/view", response_class=HTMLResponse)
def view_report(report_id: str, db: Session = Depends(db_session)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="报告不存在")
    return HTMLResponse(
        "<html><head><meta charset='utf-8'><title>巡检报告</title>"
        "<style>body{font-family:Arial,'Microsoft YaHei';max-width:920px;margin:40px auto;color:#172033}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #dbe3ee;padding:10px;text-align:left}"
        "th{background:#eef5ff}h1,h2{color:#123b6d}</style></head><body>"
        + report.html_content
        + "</body></html>"
    )


@router.post("/knowledge/documents", status_code=201, dependencies=[Depends(require_api_key)])
async def upload_knowledge(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
):
    settings = request.app.state.settings
    try:
        stored = await store_upload(
            file,
            settings.upload_dir / "knowledge",
            settings.max_upload_bytes,
            KNOWLEDGE_EXTENSIONS,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document = KnowledgeDocument(
        name=stored.original_name,
        stored_path=str(stored.stored_path),
        mime_type=stored.mime_type,
        status="processing",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    try:
        count = request.app.state.knowledge_base.ingest(document.id, document.name, document.stored_path)
        document.chunk_count = count
        document.status = "ready"
    except Exception as exc:
        document.status = "error"
        document.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=422, detail=f"知识文档解析或入库失败：{exc}") from exc
    db.commit()
    return _document_to_dict(document)


@router.delete("/knowledge/documents/{document_id}", dependencies=[Depends(require_api_key)])
def delete_knowledge(document_id: str, request: Request, db: Session = Depends(db_session)):
    """删除知识文档：同时清除向量库分块、数据库记录与已上传的源文件。

    没有这个接口时知识库只能新增不能删除，写错的文档与历史测试残留的演示文档
    会永久留在库里参与召回。向量库为嵌入模式时目录被后端进程独占，
    无法从外部脚本清理，因此必须由后端提供删除能力。
    """
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="知识文档不存在")

    try:
        removed = request.app.state.knowledge_base.delete_document(document_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"向量库删除失败：{exc}") from exc

    stored_path = document.stored_path
    document_name = document.name
    db.delete(document)
    db.commit()

    file_removed = False
    try:
        path = Path(stored_path)
        if path.is_file():
            path.unlink()
            file_removed = True
    except OSError:
        # 源文件删除失败不影响知识库一致性，仅记录在响应里
        file_removed = False

    return {
        "deleted": True,
        "id": document_id,
        "name": document_name,
        "removed_chunks": removed,
        "file_removed": file_removed,
    }


@router.get("/knowledge/documents")
def list_knowledge(db: Session = Depends(db_session)):
    documents = db.scalars(select(KnowledgeDocument).order_by(desc(KnowledgeDocument.created_at))).all()
    return {"items": [_document_to_dict(item) for item in documents], "total": len(documents)}


@router.post("/knowledge/search")
def search_knowledge(request: Request, payload: KnowledgeSearchRequest):
    try:
        hits = request.app.state.knowledge_base.search(payload.query, payload.top_k)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"知识库检索失败：{exc}") from exc
    return {"query": payload.query, "hits": [item.model_dump() for item in hits], "total": len(hits)}


def _document_to_dict(document: KnowledgeDocument) -> dict[str, Any]:
    return {
        "id": document.id,
        "name": document.name,
        "mime_type": document.mime_type,
        "status": document.status,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
        "created_at": _iso(document.created_at),
    }


def _step_to_dict(step: AgentStep) -> dict[str, Any]:
    return {
        "id": step.id,
        "sequence": step.sequence,
        "node_name": step.node_name,
        "status": step.status,
        "started_at": _iso(step.started_at),
        "finished_at": _iso(step.finished_at),
        "duration_ms": step.duration_ms,
        "input_summary": _json(step.input_summary, step.input_summary),
        "output_summary": _json(step.output_summary, step.output_summary),
        "error_message": step.error_message,
    }


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
