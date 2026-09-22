from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class EvidenceBundle(BaseModel):
    company_name: str
    website_candidates: list[str] = Field(default_factory=list)
    linkedin_candidates: list[str] = Field(default_factory=list)
    reputation_snippets: list[str] = Field(default_factory=list)
    raw_results: dict = Field(default_factory=dict)


class VerificationResult(BaseModel):
    verdict: Literal["approved", "rejected", "needs_admin_review"]
    confidence: float
    website_url: str | None = None
    linkedin_url: str | None = None
    reasoning: str


class CompanyAdminOut(BaseModel):
    id: UUID
    normalized_name: str
    display_name: str
    status: str
    confidence_score: float | None = None
    verified_website_url: str | None = None
    verified_linkedin_url: str | None = None
    verification_reasoning: str | None = None
    verification_evidence: dict | None = None
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class CompanyAdminActionResponse(BaseModel):
    id: UUID
    status: str
    message: str