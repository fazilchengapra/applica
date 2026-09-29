"""Read-only aggregate response schemas for the user dashboard.

Every section is always present. A user with no CV, no matches and no tailored
CVs gets a fully-populated response of zeros/empty lists rather than nulls, so
the client can bind to the shape without existence checks.
"""

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.matching.models.job_match import MatchStatus
from app.modules.tailoring.schemas import (
    TailoredCVTemplateOut,
    TailoringRunOut,
)


class MasterCVState(str, enum.Enum):
    """Presentation state of the user's master CV.

    ``ready`` is a presentation alias for the stored ``completed`` status; there
    is no ``ready`` value in the database enum.
    """

    none = "none"
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class ActivityType(str, enum.Enum):
    tailoring = "tailoring"
    render = "render"
    master_cv = "master_cv"


class DashboardSkill(BaseModel):
    name: str
    skill_type: str = Field(description="required | preferred, from cv_skills")


class DashboardProfile(BaseModel):
    """Parsed master CV summary.

    Zeroed (not null) when the current CV version has not finished processing —
    the section keeps its shape so the client never has to null-check it.
    """

    summary: str | None = None
    skills: list[DashboardSkill] = Field(default_factory=list)
    experience_count: int = 0
    education_count: int = 0
    project_count: int = 0
    certification_count: int = 0
    language_count: int = 0


class DashboardCurrentVersion(BaseModel):
    version_id: UUID
    version: int
    target_role: str
    status: str
    created_at: datetime


class DashboardVersionItem(BaseModel):
    id: UUID
    version: int
    status: str
    is_current: bool
    created_at: datetime


class DashboardCVStats(BaseModel):
    total: int
    ready: int
    processing: int
    failed: int
    pending: int


class DashboardMasterCV(BaseModel):
    state: MasterCVState
    current: DashboardCurrentVersion | None = None
    versions: list[DashboardVersionItem] = Field(default_factory=list)
    stats: DashboardCVStats
    profile: DashboardProfile = Field(default_factory=DashboardProfile)


class MatchCardJob(BaseModel):
    id: UUID
    title: str
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None


class MatchCardCompany(BaseModel):
    id: UUID
    name: str = Field(description="display_name, falling back to normalized_name")


class JobMatchCard(BaseModel):
    """Narrow match projection for the dashboard grid.

    Deliberately omits the full job description and the sub-scores carried by
    ``JobMatchOut``; this is a card, not a detail view.
    """

    id: UUID
    status: MatchStatus
    final_score: float
    matched_at: datetime
    key_matches: list[str] | None = None
    key_gaps: list[str] | None = None
    job: MatchCardJob
    company: MatchCardCompany


class DashboardMatchCounts(BaseModel):
    new: int
    viewed: int
    saved: int
    applied: int
    dismissed: int
    total: int


class DashboardMatches(BaseModel):
    counts: DashboardMatchCounts
    top: list[JobMatchCard] = Field(default_factory=list)


class TailoredCVDashboardCard(BaseModel):
    """Lighter sibling of ``TailoredCVListItem`` — drops critic_verdict."""

    id: UUID
    created_at: datetime
    status: str
    render_status: str
    critic_score: float | None = None
    file_url: str | None = None
    template: TailoredCVTemplateOut | None = None
    run: TailoringRunOut


class DashboardTailoredCVCounts(BaseModel):
    """Two orthogonal axes, so these do not sum to ``total``.

    ``approved``/``failed`` partition the CV content outcome, so
    ``approved + failed == total``. ``rendering``/``rendered`` partition the
    render outcome, so ``rendering + rendered + render_failed == total``.
    """

    total: int
    approved: int
    failed: int
    rendering: int
    rendered: int


class DashboardTailoredCVs(BaseModel):
    counts: DashboardTailoredCVCounts
    items: list[TailoredCVDashboardCard] = Field(default_factory=list)


class DashboardActivityItem(BaseModel):
    type: ActivityType
    run_id: UUID = Field(description="TailoringRun id, or CV version id for master_cv")
    stage: str
    status: str
    error_message: str | None = None
    created_at: datetime = Field(
        description="Last activity time, not creation time, for this item"
    )


class DashboardResponse(BaseModel):
    master_cv: DashboardMasterCV
    matches: DashboardMatches
    tailored_cvs: DashboardTailoredCVs
    activity: list[DashboardActivityItem] = Field(default_factory=list)
    generated_at: datetime
