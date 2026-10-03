"""Assembles the dashboard read model from per-section queries.

Kept separate from ``repository`` so the queries stay declarative and all the
row-to-schema mapping (and the zeroing rules for an empty account) lives in one
reviewable place.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard import repository
from app.modules.dashboard.schemas import (
    DashboardActivityItem,
    DashboardCVStats,
    DashboardCurrentVersion,
    DashboardMatchCounts,
    DashboardMatches,
    DashboardMasterCV,
    DashboardProfile,
    DashboardResponse,
    DashboardSkill,
    DashboardStatsResponse,
    DashboardTailoredCVCounts,
    DashboardTailoredCVs,
    DashboardVersionItem,
    JobMatchCard,
    MasterCVState,
    MatchCardCompany,
    MatchCardJob,
    MatchStatusBreakdown,
    TailoredCVDashboardCard,
    TailoredCVProgress,
    TopMatchListOut,
    TopMatchResult,
)
from app.modules.master_cv.models import CVStatus, MasterCVVersion
from app.modules.master_cv.repository import get_cv_status_counts
from app.modules.matching.models.job_match import MatchStatus
from app.modules.tailoring.models import TailoringRunStatus
from app.modules.tailoring.schemas import (
    TailoredCVTemplateOut,
    TailoringRunOut,
)
from app.shared.utils.s3 import get_public_url

# Matches scoring below this are noise on a dashboard grid; the full paginated
# list (GET /job-matches) still exposes everything.
TOP_MATCH_MIN_SCORE = 0.5
TOP_MATCH_LIMIT = 10
RECENT_VERSIONS_LIMIT = 5
RECENT_TAILORED_CVS_LIMIT = 12

# Stored status -> presentation state. ``completed`` is renamed to ``ready``;
# every other value passes through unchanged.
_STATUS_TO_STATE = {
    CVStatus.COMPLETED.value: MasterCVState.ready,
    CVStatus.PENDING.value: MasterCVState.pending,
    CVStatus.PROCESSING.value: MasterCVState.processing,
    CVStatus.FAILED.value: MasterCVState.failed,
}


def _status_value(status: Any) -> str:
    """Unwrap a SQLAlchemy Enum column result to its stored lowercase value."""
    return getattr(status, "value", status)


def _count_list(parsed: Any, key: str) -> int:
    """Length of a ``parsed_data`` array, tolerating absent or malformed data.

    ``parsed_data`` is free-form JSONB written by an LLM extractor, so a partial
    or hand-edited document must not 500 the whole dashboard.
    """
    if not isinstance(parsed, dict):
        return 0
    value = parsed.get(key)
    return len(value) if isinstance(value, list) else 0


async def _build_master_cv(db: AsyncSession, user_id: int) -> DashboardMasterCV:
    current: MasterCVVersion | None = await repository.get_current_version(db, user_id)
    versions = await repository.get_recent_versions(
        db, user_id, limit=RECENT_VERSIONS_LIMIT
    )
    raw_stats = await get_cv_status_counts(user_id=user_id, session=db)

    stats = DashboardCVStats(**{k: (v or 0) for k, v in raw_stats.items()})
    if current is None:
        return DashboardMasterCV(
            state=MasterCVState.none,
            current=None,
            versions=[],
            stats=stats,
            profile=DashboardProfile(),
        )

    current_status = _status_value(current.status)
    state = _STATUS_TO_STATE.get(current_status, MasterCVState.processing)

    # The parsed body and extracted skills only exist once the extractor has
    # finished, so an in-flight or failed version reports a zeroed profile.
    parsed = current.parsed_data if state is MasterCVState.ready else None
    skills: list[DashboardSkill] = []
    if current.parsed_data is not None:
        skills = [
            DashboardSkill(name=name, skill_type=skill_type)
            for name, skill_type in await repository.get_skills_for_version(
                db, current.id
            )
        ]

    profile = DashboardProfile(
        summary=parsed.get("summary") if isinstance(parsed, dict) else None,
        skills=skills,
        experience_count=_count_list(parsed, "experience"),
        education_count=_count_list(parsed, "education"),
        project_count=_count_list(parsed, "projects"),
        certification_count=_count_list(parsed, "certifications"),
        language_count=_count_list(parsed, "languages"),
    )

    return DashboardMasterCV(
        state=state,
        current=DashboardCurrentVersion(
            version_id=current.id,
            version=current.version,
            target_role=current.target_role,
            status=current_status,
            created_at=current.created_at,
        ),
        versions=[
            DashboardVersionItem(
                id=version.id,
                version=version.version,
                status=_status_value(version.status),
                is_current=version.is_current,
                created_at=version.created_at,
            )
            for version in versions
        ],
        stats=stats,
        profile=profile,
    )


def _to_match_card(row) -> JobMatchCard:
    return JobMatchCard(
        id=row.id,
        status=_status_value(row.status),
        final_score=float(row.final_score),
        matched_at=row.matched_at,
        key_matches=row.key_matches,
        key_gaps=row.key_gaps,
        job=MatchCardJob(
            id=row.job_id,
            title=row.job_title,
            location=row.job_location,
            remote_type=_status_value(row.job_remote_type),
            employment_type=_status_value(row.job_employment_type),
            salary_min=float(row.job_salary_min) if row.job_salary_min is not None else None,
            salary_max=float(row.job_salary_max) if row.job_salary_max is not None else None,
            salary_currency=row.job_salary_currency,
            salary_period=row.job_salary_period,
        ),
        company=MatchCardCompany(
            id=row.company_id,
            name=row.company_display_name or row.company_normalized_name,
        ),
    )


async def _build_matches(db: AsyncSession, user_id: int) -> DashboardMatches:
    raw_counts = await repository.get_match_counts(db, user_id)
    rows = await repository.get_top_match_cards(
        db, user_id, min_score=TOP_MATCH_MIN_SCORE, limit=TOP_MATCH_LIMIT
    )
    # get_match_counts only returns buckets that exist; normalize so the schema
    # always carries all five statuses.
    counts = DashboardMatchCounts(
        **{
            "new": raw_counts.get(MatchStatus.NEW.value, 0),
            "viewed": raw_counts.get(MatchStatus.VIEWED.value, 0),
            "saved": raw_counts.get(MatchStatus.SAVED.value, 0),
            "applied": raw_counts.get(MatchStatus.APPLIED.value, 0),
            "dismissed": raw_counts.get(MatchStatus.DISMISSED.value, 0),
            "total": raw_counts.get("total", 0),
        }
    )
    return DashboardMatches(counts=counts, top=[_to_match_card(row) for row in rows])


def _to_tailored_card(row) -> TailoredCVDashboardCard:
    template = None
    if row.template_id is not None:
        template = TailoredCVTemplateOut(
            id=row.template_id,
            title=row.template_title,
            image_url=(
                get_public_url(row.template_image_s3_key)
                if row.template_image_s3_key
                else None
            ),
        )

    return TailoredCVDashboardCard(
        id=row.id,
        created_at=row.created_at,
        status=_status_value(row.cv_status),
        render_status=_status_value(row.cv_render_status),
        critic_score=(
            float(row.critic_score) if row.critic_score is not None else None
        ),
        file_url=get_public_url(row.file_s3_key) if row.file_s3_key else None,
        template=template,
        run=TailoringRunOut(
            id=row.run_id,
            stage=_status_value(row.run_stage),
            status=_status_value(row.run_status),
            error_message=row.run_error_message,
            critic_retry_count=row.critic_retry_count,
            job={
                "id": row.job_id,
                "title": row.job_title,
                "company_name": row.company_display_name or row.company_normalized_name,
            },
        ),
    )


async def _build_tailored_cvs(db: AsyncSession, user_id: int) -> DashboardTailoredCVs:
    raw_counts = await repository.get_tailored_cv_counts(db, user_id)
    rows = await repository.get_recent_tailored_cv_cards(
        db, user_id, limit=RECENT_TAILORED_CVS_LIMIT
    )
    return DashboardTailoredCVs(
        counts=DashboardTailoredCVCounts(**raw_counts),
        items=[_to_tailored_card(row) for row in rows],
    )


async def _build_activity(db: AsyncSession, user_id: int) -> list[DashboardActivityItem]:
    rows = await repository.get_activity(db, user_id)
    return [
        DashboardActivityItem(
            type=row.type,
            run_id=row.run_id,
            stage=row.stage,
            status=row.status,
            error_message=row.error_message,
            created_at=row.at,
        )
        for row in rows
    ]


async def build_dashboard(db: AsyncSession, user_id: int) -> DashboardResponse:
    """Full dashboard aggregate for one user.

    Sections are fetched in order of usefulness rather than in parallel: the
    shared AsyncSession is not safe for concurrent statements, and each query is
    an indexed lookup, so the sequence costs a handful of local round trips.
    """
    return DashboardResponse(
        master_cv=await _build_master_cv(db, user_id),
        matches=await _build_matches(db, user_id),
        tailored_cvs=await _build_tailored_cvs(db, user_id),
        activity=await _build_activity(db, user_id),
        generated_at=datetime.now(timezone.utc),
    )


async def build_dashboard_stats(
    db: AsyncSession, user_id: int, top_n: int
) -> DashboardStatsResponse:
    match_counts = await repository.get_match_pipeline_counts(db, user_id)
    average_score = await repository.get_average_final_score(db, user_id)
    # Reuses the existing tailored-CV aggregate rather than adding a third
    # variant of the same query: ``rendered``/``rendering`` are already exactly
    # the completed/in-progress split this endpoint reports.
    tailored_counts = await repository.get_tailored_cv_counts(db, user_id)

    return DashboardStatsResponse(
        match_status_breakdown=MatchStatusBreakdown(**match_counts),
        average_final_score=average_score,
        top_n=top_n,
        tailored_cvs_completed=tailored_counts["rendered"],
        tailored_cvs_in_progress=tailored_counts["rendering"],
    )


# Tailoring run status -> the coarser progress the table shows. The run enum
# splits the early pipeline into pending/processing; the table collapses those
# into one ``in_progress`` because a user cannot act on the difference.
_RUN_STATUS_TO_PROGRESS = {
    TailoringRunStatus.pending: TailoredCVProgress.in_progress,
    TailoringRunStatus.processing: TailoredCVProgress.in_progress,
    TailoringRunStatus.completed: TailoredCVProgress.completed,
    TailoringRunStatus.failed: TailoredCVProgress.failed,
}


def _to_top_match_result(row) -> TopMatchResult:
    # The subquery yields NULL for a job the user never tailored, and
    # TailoringRunStatus for one they did.
    run_status = row.tailored_cv_status
    return TopMatchResult(
        id=row.id,
        job_title=row.job_title,
        company_name=row.company_display_name or row.company_normalized_name,
        match_status=_status_value(row.match_status),
        final_score=float(row.final_score),
        vector_score=row.vector_score,
        lexical_score=row.lexical_score,
        rrf_score=row.rrf_score,
        key_matches=row.key_matches,
        key_gaps=row.key_gaps,
        tailored_cv_status=_RUN_STATUS_TO_PROGRESS.get(
            run_status, TailoredCVProgress.none
        ),
    )


async def build_top_matches(
    db: AsyncSession,
    user_id: int,
    min_score: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> TopMatchListOut:
    """One page of the top-matches table.

    ``count`` is the total qualifying matches, so it is fetched separately from
    the page and reflects the same ``min_score`` filter. Sequential awaits, for
    the shared-AsyncSession reason documented on :func:`build_dashboard`.
    """
    count = await repository.count_top_matches(db, user_id, min_score=min_score)
    rows = await repository.get_top_match_results(
        db, user_id, min_score=min_score, limit=limit, offset=offset
    )
    return TopMatchListOut(
        count=count, results=[_to_top_match_result(row) for row in rows]
    )
