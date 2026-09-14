from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InspectionTask(Base):
    __tablename__ = "inspection_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    location: Mapped[str] = mapped_column(String(200))
    area_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    inspector_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    risk_level: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    vision_events_json: Mapped[str] = mapped_column(Text, default="[]")
    original_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    images: Mapped[list[InspectionImage]] = relationship(back_populates="task", cascade="all, delete-orphan")
    detections: Mapped[list[DetectionResult]] = relationship(back_populates="task", cascade="all, delete-orphan")
    runs: Mapped[list[AgentRun]] = relationship(back_populates="task", cascade="all, delete-orphan")
    steps: Mapped[list[AgentStep]] = relationship(back_populates="task", cascade="all, delete-orphan")
    risk_assessments: Mapped[list[RiskAssessment]] = relationship(back_populates="task", cascade="all, delete-orphan")
    reports: Mapped[list[Report]] = relationship(back_populates="task", cascade="all, delete-orphan")
    reviews: Mapped[list[ManualReview]] = relationship(back_populates="task", cascade="all, delete-orphan")


class InspectionImage(Base):
    __tablename__ = "inspection_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("inspection_tasks.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped[InspectionTask] = relationship(back_populates="images")


class DetectionResult(Base):
    __tablename__ = "detection_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("inspection_tasks.id", ondelete="CASCADE"), index=True)
    class_id: Mapped[int] = mapped_column(Integer)
    class_name: Mapped[str] = mapped_column(String(160))
    display_name: Mapped[str] = mapped_column(String(160), default="")
    model_role: Mapped[str] = mapped_column(String(40), default="traffic_sign", index=True)
    model_name: Mapped[str] = mapped_column(String(255), default="")
    confidence: Mapped[float] = mapped_column(Float)
    x1: Mapped[float] = mapped_column(Float)
    y1: Mapped[float] = mapped_column(Float)
    x2: Mapped[float] = mapped_column(Float)
    y2: Mapped[float] = mapped_column(Float)
    inference_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    task: Mapped[InspectionTask] = relationship(back_populates="detections")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("inspection_tasks.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[InspectionTask] = relationship(back_populates="runs")


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("inspection_tasks.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer)
    node_name: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[InspectionTask] = relationship(back_populates="steps")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="ready")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("inspection_tasks.id", ondelete="CASCADE"), index=True)
    risk_level: Mapped[str] = mapped_column(String(30))
    risk_score: Mapped[int] = mapped_column(Integer)
    problem_summary: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    knowledge_references_json: Mapped[str] = mapped_column(Text, default="[]")
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]")
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    uncertainty_note: Mapped[str] = mapped_column(Text, default="")
    analysis_mode: Mapped[str] = mapped_column(String(40), default="rules_only")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped[InspectionTask] = relationship(back_populates="risk_assessments")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("inspection_tasks.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    html_content: Mapped[str] = mapped_column(Text)
    generation_status: Mapped[str] = mapped_column(String(30), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped[InspectionTask] = relationship(back_populates="reports")


class ManualReview(Base):
    __tablename__ = "manual_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    task_id: Mapped[str] = mapped_column(ForeignKey("inspection_tasks.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(30))
    reviewer: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    modified_risk_level: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped[InspectionTask] = relationship(back_populates="reviews")
