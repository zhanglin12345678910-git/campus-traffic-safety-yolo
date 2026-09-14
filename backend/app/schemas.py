from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high", "review"]


class DetectionItem(BaseModel):
    class_id: int
    class_name: str
    confidence: float = Field(ge=0, le=1)
    bbox_xyxy: list[float] = Field(min_length=4, max_length=4)


class KnowledgeHit(BaseModel):
    document_name: str
    chunk_id: str
    content: str
    score: float


class RiskResult(BaseModel):
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    problem_summary: str
    evidence: list[str] = Field(default_factory=list)
    knowledge_references: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    review_required: bool = False
    # Internal hand-off from the policy service to the workflow.  The durable,
    # public copy lives on InspectionTask.review_reasons_json.
    policy_reasons: list[str] = Field(default_factory=list, exclude=True)
    uncertainty_note: str = ""
    analysis_mode: str = "rules_only"


class ReviewRequest(BaseModel):
    action: Literal["confirm", "modify", "reject"]
    reviewer: str = Field(min_length=1, max_length=100)
    comment: str | None = Field(default=None, max_length=2000)
    risk_level: RiskLevel | None = None


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
