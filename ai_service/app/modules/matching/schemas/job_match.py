from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.modules.matching.models.job_match import MatchStatus


class JobMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    job_id: UUID

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