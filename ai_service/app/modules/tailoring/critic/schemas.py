from typing import Literal

from pydantic import BaseModel, Field


class FabricationFlag(BaseModel):
    claim: str
    field: Literal["evidence_ref", "bullet", "technology", "skill"]
    severity: Literal["low", "high"]
    context: str
    reason: str


class QualityJudgment(BaseModel):
    quality_score: float = Field(ge=0, le=1)
    issues: list[str]


class CriticVerdict(BaseModel):
    approved: bool
    fabrication_flags: list[FabricationFlag]
    quality_score: float
    issues: list[str]
    reasoning: str
