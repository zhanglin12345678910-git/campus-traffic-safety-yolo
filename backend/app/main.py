from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agents.graph import InspectionWorkflow
from app.api.router import router
from app.config import Settings, get_settings
from app.database import Database
from app.services.llm import LLMService, VisionLLMService
from app.services.amap import AMapService
from app.services.rag import KnowledgeBaseService
from app.services.risk import RiskAssessmentService
from app.tools.image_quality import ImageQualityTool
from app.tools.yolo import TrafficSignDetectionTool
from app.tools.video_analytics import VideoAnalyticsTool


def create_app(
    settings: Settings | None = None,
    *,
    database: Database | None = None,
    yolo_tool: TrafficSignDetectionTool | None = None,
    knowledge_base: KnowledgeBaseService | None = None,
    llm_service: LLMService | None = None,
    amap_service: AMapService | None = None,
    video_analytics: VideoAnalyticsTool | None = None,
    vision_llm: VisionLLMService | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app_settings.ensure_directories()
    app_database = database or Database(app_settings)
    app_database.create_all()
    app_yolo = yolo_tool or TrafficSignDetectionTool(app_settings)
    app_knowledge = knowledge_base or KnowledgeBaseService(app_settings)
    app_llm = llm_service or LLMService(app_settings)
    app_amap = amap_service or AMapService(app_settings)
    app_video_analytics = video_analytics or VideoAnalyticsTool(app_settings, app_yolo)
    app_vision_llm = vision_llm or VisionLLMService(app_settings)
    quality_tool = ImageQualityTool(app_settings)
    risk_service = RiskAssessmentService(app_settings, app_llm)
    workflow = InspectionWorkflow(
        app_settings,
        app_database,
        quality_tool,
        app_yolo,
        app_knowledge,
        risk_service,
        app_vision_llm,
    )

    app = FastAPI(
        title=app_settings.app_name,
        version=app_settings.app_version,
        description="基于 LangGraph、RAG 与 YOLO 的校园交通安全智能巡检平台",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = app_settings
    app.state.database = app_database
    app.state.yolo_tool = app_yolo
    app.state.knowledge_base = app_knowledge
    app.state.llm_service = app_llm
    app.state.amap_service = app_amap
    app.state.video_analytics = app_video_analytics
    app.state.vision_llm_service = app_vision_llm
    app.state.workflow = workflow

    app.mount("/uploads", StaticFiles(directory=str(app_settings.upload_dir)), name="uploads")
    app.mount("/outputs", StaticFiles(directory=str(app_settings.output_dir)), name="outputs")
    app.include_router(router, prefix=app_settings.api_prefix)

    @app.get("/health", include_in_schema=False)
    def root_health():
        return {"status": "ok", "details": f"{app_settings.api_prefix}/health"}

    return app


app = create_app()
