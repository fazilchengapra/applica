from __future__ import annotations
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# ---- Fetched context (deterministic, pre-LLM) ----

class StrategyBriefDTO(BaseModel):
    id: UUID
    tone: str | None = None
    section_order: list[str] | None = None
    lead_experiences: list[str] | None = None
    gaps_to_address: list[str] | None = None
    keywords_to_weave: list[str] | None = None
    reasoning: str | None = None


class EvidenceItemDTO(BaseModel):
    id: UUID
    requirement: str
    status: str
    confidence: float
    evidence_chunk_ids: list[UUID] = Field(default_factory=list)
    excerpt: str | None = None
    reasoning: str | None = None


class CVChunkDTO(BaseModel):
    id: UUID
    section_type: str          # e.g. "experience", "project", "education"
    content: str
    metadata: dict = Field(default_factory=dict)  # company, dates, role, etc.


class JobDTO(BaseModel):
    id: UUID
    title: str
    company: str | None = None
    description: str
    requirements: list[str] = Field(default_factory=list)


class CVTemplateDTO(BaseModel):
    id: UUID
    title: str
    tex: str


class WriterContext(BaseModel):
    """Everything gathered deterministically before the LLM call."""
    tailoring_run_id: UUID
    strategy_brief: StrategyBriefDTO
    evidence_items: list[EvidenceItemDTO]
    resolved_chunks: dict[UUID, CVChunkDTO]   # keyed by chunk id
    job: JobDTO
    template: CVTemplateDTO


# ---- LLM structured output ----

class CVSectionContent(BaseModel):
    section_name: str
    content: str                # rendered text/bullets for this section, not raw LaTeX
    source_chunk_ids: list[UUID] = Field(default_factory=list)  # for critic traceability


class CVWriterOutput(BaseModel):
    sections: list[CVSectionContent]
    summary_line: str | None = None
    notes: str | None = None    # LLM's own caveats, e.g. "no evidence found for X, omitted"


# ---- Persisted draft ----

class CVDraftDTO(BaseModel):
    id: UUID
    tailoring_run_id: UUID
    cv_template_id: UUID
    tex_content: str
    created_at: datetime
    updated_at: datetime


# ---- LangGraph state ----

class WriterState(BaseModel):
    tailoring_run_id: UUID
    context: WriterContext | None = None
    output: CVWriterOutput | None = None
    tex_content: str | None = None
    draft: CVDraftDTO | None = None
    error: str | None = None