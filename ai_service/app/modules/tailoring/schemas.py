"""HTTP request/response schemas for tailored CV rendering."""

from datetime import datetime
from typing import Any
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


class TailoredCVTemplateOut(BaseModel):
    id: UUID
    title: str
    image_url: str | None = None


class TailoredCVJobOut(BaseModel):
    id: UUID
    title: str
    company_name: str | None = None


class TailoringRunOut(BaseModel):
    id: UUID
    stage: str
    status: str
    error_message: str | None = None
    critic_retry_count: int
    job: TailoredCVJobOut | None = None


class TailoredCVListItem(BaseModel):
    id: UUID
    created_at: datetime
    status: str
    render_status: str
    render_error_message: str | None = None
    critic_score: float | None = None
    critic_verdict: dict[str, Any] | None = None
    file_url: str | None = None
    template: TailoredCVTemplateOut | None = None
    run: TailoringRunOut


class TailoredCVListOut(BaseModel):
    total: int
    items: list[TailoredCVListItem]


class CreateTailoredCVRequest(BaseModel):
    match_id: UUID = Field(
        ..., description="Job match to tailor the CV for (must belong to the caller)"
    )
    template_id: UUID | None = Field(
        default=None,
        description="Active CV template to attach once the run is approved. "
        "Defaults to the newest active template at write time.",
    )


class CreateTailoredCVAccepted(BaseModel):
    run_id: UUID
    detail: str
