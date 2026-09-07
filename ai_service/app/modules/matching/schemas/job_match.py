from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.modules.matching.models.job_match import MatchStatus


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    normalized_name: str
    status: str
    verified_website_url: str | None = None
    verified_linkedin_url: str | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    title: str
    normalized_title: str | None = None
    description: str
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    source_type: str
    source_url: str
    source_name: str
    external_id: str | None = None
    external_url: str | None = None
    status: str
    posted_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    company: CompanyOut


class JobMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    job_id: UUID
    job: JobOut

    vector_score: float | None = None
    lexical_score: float | None = None
    rrf_score: float | None = None
    final_score: float

    llm_reasoning: str | None = None
    key_matches: list[str] | None = None
    key_gaps: list[str] | None = None

    status: MatchStatus
    matched_at: datetime
    updated_at: datetime


class MatchStatusUpdate(BaseModel):
    status: MatchStatus
