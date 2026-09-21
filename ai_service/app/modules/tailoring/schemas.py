"""HTTP request/response schemas for tailored CV rendering."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RenderCVRequest(BaseModel):
    template_id: UUID = Field(..., description="Active CV template to render with")


class TailoredCVOut(BaseModel):
    id: UUID
    status: str
    render_status: str
    template_id: UUID | None
    critic_score: float | None
    file_url: str | None
    created_at: datetime


class RenderCVAccepted(BaseModel):
    id: UUID
    render_status: str