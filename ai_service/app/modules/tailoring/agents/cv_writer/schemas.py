"""Validated response contract and state for the CV writer graph."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

from app.modules.master_cv.schemas import ContactInfo, Education
from app.modules.tailoring.agents.evidence_matcher.schemas import EvidenceMatrixOutput


class StrictResponseModel(BaseModel):
    """Reject undeclared keys so the persisted payload stays renderer-safe."""

    model_config = ConfigDict(extra="forbid")


class TailoredExperience(StrictResponseModel):
    title: str
    company: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    bullets: list[str] = Field(min_length=1, max_length=6)
    evidence_item_ids: list[str] = Field(min_length=1)
    technologies: list[str] = Field(default_factory=list)


class TailoredProject(StrictResponseModel):
    name: str
    bullets: list[str] = Field(min_length=1, max_length=5)
    evidence_item_ids: list[str] = Field(min_length=1)
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None
    date: str | None = None


class CVContent(StrictResponseModel):
    """The renderer-facing JSON document; no prose wrapper is returned."""

    contact: ContactInfo
    summary: str = Field(min_length=1, max_length=700)
    experience: list[TailoredExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[TailoredProject] = Field(default_factory=list)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    tailoring_run_id: str
    user_id: int
    job_id: str
    cv_version_id: str
    evidence_matrix: EvidenceMatrixOutput
    strategy_brief: dict
    cv_metadata: dict | None
    cv_content: CVContent | None
    validation_errors: list[str]
    revision_count: int
