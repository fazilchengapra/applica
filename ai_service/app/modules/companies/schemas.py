from typing import Literal
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