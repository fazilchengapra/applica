"""HTTP request/response shapes for ATS readiness reports."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    cv_version_id: UUID | None = Field(
        default=None,
        description="Master CV version to analyse. Defaults to the caller's current completed version.",
    )
    force: bool = Field(
        default=False,
        description="Re-run even when an identical report for this content and ruleset exists.",
    )


class CheckOut(BaseModel):
    id: str
    label: str
    category: str
    weight: int = Field(..., description="Points this check contributes when fully passed.")
    kind: str = Field(..., description="rule | hybrid | llm")
    status: str = Field(..., description="pass | warn | fail | skipped")
    score: float = Field(..., ge=0, le=1, description="Fraction of the weight earned.")
    value: str = Field(..., description="Short human-readable verdict for the UI.")
    detail: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class InsightOut(BaseModel):
    label: str
    value: str
    done: bool


class ATSReportOut(BaseModel):
    id: UUID
    cv_version_id: UUID
    score: int = Field(..., ge=0, le=100, description="Weighted score on a single 0-100 scale.")
    insights: list[InsightOut]
    checks: list[CheckOut]
    semantic_verified: bool = Field(
        ...,
        description="False when the semantic model was unavailable, so impact verdicts are regex-based lower bounds.",
    )
    content_hash: str
    ruleset_version: int
    created_at: datetime


class ATSReportListItem(BaseModel):
    id: UUID
    cv_version_id: UUID
    score: int
    semantic_verified: bool
    created_at: datetime


class ATSReportListOut(BaseModel):
    total: int
    items: list[ATSReportListItem]
