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


class MatchStatusBreakdown(BaseModel):
    """Matches grouped into the five application-pipeline stages.

    The buckets are a *rollup*, not the raw enum: the stored statuses
    ``NEW``/``VIEWED`` both count as ``new``, ``SAVED``/``SHORTLISTED`` as
    ``shortlisted``, and ``DISMISSED``/``REJECTED`` as ``rejected``. Every
    ``MatchStatus`` value falls in exactly one bucket, so the five always sum to
    ``total`` — which is why a row can never be counted twice or dropped.
    """

    new: int = 0
    shortlisted: int = 0
    applied: int = 0
    interviewing: int = 0
    rejected: int = 0
    total: int = 0


class DashboardStatsResponse(BaseModel):
    """Headline counters for the dashboard's stat tiles.

    A deliberately flat, cheap read model — one aggregate per figure, no cards
    and no activity feed — so a client can poll it for the counters without
    paying for the full ``GET /dashboard`` aggregate.
    """

    match_status_breakdown: MatchStatusBreakdown = Field(
        default_factory=MatchStatusBreakdown
    )
    average_final_score: float = Field(
        default=0.0,
        description=(
            "Mean job_matches.final_score across all of the user's matches, "
            "rounded to 1dp; 0.0 when the user has no matches. Carries the "
            "known 0-1 vs 0-100 scoring-scale inconsistency, so the value may "
            "exceed 1."
        ),
    )
    top_n: int = Field(
        description=(
            "Echo of the requested top-N page size, so the client knows what to "
            "ask for when it fetches the match cards from GET /dashboard"
        )
    )
    tailored_cvs_completed: int = Field(
        default=0,
        description="Tailored CVs whose PDF render finished (render_status=completed)",
    )
    tailored_cvs_in_progress: int = Field(
        default=0,
        description="Tailored CVs still rendering (render_status pending or processing)",
    )


class TailoredCVProgress(str, enum.Enum):
    """How far the user's tailoring for a job has got.

    ``none`` is not stored anywhere — it is what the endpoint reports when the
    job has no tailoring run at all, so the client can render a "Tailor CV"
    affordance without a separate existence check.
    """

    none = "none"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class TopMatchResult(BaseModel):
    """One row of the top-matches table.

    Deliberately flat — ``job_title``/``company_name`` are plain strings rather
    than the nested job/company objects ``JobMatchCard`` carries — because this
    is a table row, not a card. It also surfaces the three stage-level scores
    that the card omits, so a client can explain *why* a row scored as it did.
    """

    id: UUID
    job_title: str
    company_name: str = Field(
        description="Company display_name, falling back to normalized_name"
    )
    match_status: MatchStatus
    final_score: float
    vector_score: float | None = None
    lexical_score: float | None = None
    rrf_score: float | None = None
    key_matches: list[str] | None = None
    key_gaps: list[str] | None = None
    tailored_cv_status: TailoredCVProgress = Field(
        default=TailoredCVProgress.none,
        description=(
            "State of the most recent tailoring run for this job: none, "
            "in_progress (pending or processing), completed or failed"
        ),
    )


class TopMatchListOut(BaseModel):
    """``{count, results}`` page envelope.

    ``count`` is the total number of qualifying matches, not the length of this
    page, so a client can compute the page count without a second request.
    """

    count: int
    results: list[TopMatchResult] = Field(default_factory=list)
