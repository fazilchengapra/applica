"""Queries backing the dashboard read model.

Each function owns one section of the aggregate so the service layer can stay a
pure assembler. Column selects (not ORM entities) keep every section to a single
round trip and avoid lazy loads on the async session.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    String,
    case,
    cast,
    distinct,
    func,
    literal,
    literal_column,
    select,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.companies.models import Company
from app.modules.cv_template.models import CVTemplate
from app.modules.jobs.models.job_skills import JobSkill
from app.modules.jobs.models.jobs import Job
from app.modules.jobs.models.skills import Skill
from app.modules.master_cv.models import MasterCV, MasterCVVersion
from app.modules.master_cv.models.cv_skills import CVSkill
from app.modules.master_cv.models.master_cv import CVStatus
from app.modules.matching.models.job_match import JobMatch, MatchStatus
from app.modules.tailoring.models import TailoredCV, TailoringRun

_RENDER_NOT_DONE = ("pending", "processing")

# Monday-aligned week bucket for job_matches.matched_at. Raw SQL text so the same
# expression appears verbatim in the select list, GROUP BY and ORDER BY — see
# _score_trend_stmt for why func.date_trunc cannot be used here.
_WEEK_BUCKET = literal_column("date_trunc('week', job_matches.matched_at)")

_MATCH_CARD_COLUMNS = (
    JobMatch.id,
    JobMatch.status,
    JobMatch.final_score,
    JobMatch.matched_at,
    JobMatch.key_matches,
    JobMatch.key_gaps,
    Job.id.label("job_id"),
    Job.title.label("job_title"),
    Job.location.label("job_location"),
    Job.remote_type.label("job_remote_type"),
    Job.employment_type.label("job_employment_type"),
    Job.salary_min.label("job_salary_min"),
    Job.salary_max.label("job_salary_max"),
    Job.salary_currency.label("job_salary_currency"),
    Job.salary_period.label("job_salary_period"),
    Company.id.label("company_id"),
    Company.display_name.label("company_display_name"),
    Company.normalized_name.label("company_normalized_name"),
)

_TAILORED_CARD_COLUMNS = (
    TailoredCV.id,
    TailoredCV.created_at,
    TailoredCV.status.label("cv_status"),
    TailoredCV.render_status.label("cv_render_status"),
    TailoredCV.critic_score,
    TailoredCV.file_s3_key,
    CVTemplate.id.label("template_id"),
    CVTemplate.title.label("template_title"),
    CVTemplate.image_s3_key.label("template_image_s3_key"),
    TailoringRun.id.label("run_id"),
    TailoringRun.stage.label("run_stage"),
    TailoringRun.status.label("run_status"),
    TailoringRun.error_message.label("run_error_message"),
    TailoringRun.critic_retry_count,
    Job.id.label("job_id"),
    Job.title.label("job_title"),
    Company.display_name.label("company_display_name"),
    Company.normalized_name.label("company_normalized_name"),
)


async def get_current_version(db: AsyncSession, user_id: int) -> MasterCVVersion | None:
    """The single ``is_current`` version, or None when the user has no master CV.

    Joined through ``master_cvs`` so no separate id lookup is needed. Returns
    whatever the current version is — including a pending/failed one, because
    the dashboard must be able to render that state rather than 404 on it.
    """
    result = await db.execute(
        select(MasterCVVersion)
        .join(MasterCV, MasterCV.id == MasterCVVersion.master_cv_id)
        .where(
            MasterCV.user_id == user_id,
            MasterCVVersion.is_current.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_recent_versions(
    db: AsyncSession, user_id: int, limit: int = 5
) -> list[MasterCVVersion]:
    result = await db.execute(
        select(MasterCVVersion)
        .join(MasterCV, MasterCV.id == MasterCVVersion.master_cv_id)
        .where(MasterCV.user_id == user_id)
        .order_by(MasterCVVersion.version.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_skills_for_version(
    db: AsyncSession, cv_version_id: UUID
) -> list[tuple[str, str]]:
    """(skill name, skill_type) pairs for one CV version.

    A local join instead of ``master_cv.repository.get_skills_for_cv`` because
    the dashboard needs only name + skill_type, and that helper pulls the
    normalized name too.
    """
    result = await db.execute(
        select(Skill.name, CVSkill.skill_type)
        .join(CVSkill, CVSkill.skill_id == Skill.id)
        .where(CVSkill.cv_id == cv_version_id)
        .order_by(CVSkill.skill_type, Skill.name)
    )
    return [(row.name, row.skill_type) for row in result.all()]


async def get_match_counts(db: AsyncSession, user_id: int) -> dict[str, int]:
    """Per-status match counts plus the unfiltered total.

    ``GROUP BY`` returns only the buckets that exist, so the caller must treat
    a missing key as zero rather than assume every status is present.
    """
    result = await db.execute(
        select(JobMatch.status, func.count())
        .where(JobMatch.user_id == user_id)
        .group_by(JobMatch.status)
    )
    counts = {
        status.value if hasattr(status, "value") else str(status): n
        for status, n in result.all()
    }
    counts["total"] = sum(counts.values())
    return counts


# Stored status -> pipeline bucket shown on the dashboard. The buckets partition
# ``MatchStatus``: every member appears exactly once, so the five counts always
# sum to the total. The coarse pre-pipeline statuses fold into the bucket that
# supersedes them (``VIEWED`` is still unactioned, ``SAVED`` is a shortlist,
# ``DISMISSED`` is a rejection), which is why this exists instead of grouping by
# the raw status. Values are enum *members*, not strings: ``MatchStatus`` names
# are uppercase and values lowercase, and the column is an SAEnum keyed on the
# name, so a lowercase string would not match the stored labels.
_MATCH_PIPELINE_BUCKETS: dict[str, tuple[MatchStatus, ...]] = {
    "new": (MatchStatus.NEW, MatchStatus.VIEWED),
    "shortlisted": (MatchStatus.SAVED, MatchStatus.SHORTLISTED),
    "applied": (MatchStatus.APPLIED,),
    "interviewing": (MatchStatus.INTERVIEWING,),
    "rejected": (MatchStatus.DISMISSED, MatchStatus.REJECTED),
}


async def get_match_pipeline_counts(db: AsyncSession, user_id: int) -> dict[str, int]:
    """Match counts per pipeline bucket plus the unfiltered total.

    One conditional aggregate rather than a ``GROUP BY`` so empty buckets come
    back as a real ``0`` instead of a missing key — the caller splats the dict
    straight into the schema.

    CASE (not ``count(col.in_(...))``): a boolean comparison yields FALSE rather
    than NULL for non-matching rows, so count() would tally every row into every
    bucket. CASE yields NULL, which count() skips. Same pattern as
    ``get_tailored_cv_counts``.
    """
    result = await db.execute(
        select(
            func.count().label("total"),
            *[
                func.count(case((JobMatch.status.in_(statuses), 1))).label(bucket)
                for bucket, statuses in _MATCH_PIPELINE_BUCKETS.items()
            ],
        ).where(JobMatch.user_id == user_id)
    )
    row = result.one()
    counts = {bucket: row._mapping[bucket] for bucket in _MATCH_PIPELINE_BUCKETS}
    counts["total"] = row.total
    return counts


async def get_average_final_score(db: AsyncSession, user_id: int) -> float:
    """Mean ``final_score`` across all of the user's matches, 0.0 when there are none.

    ``AVG`` over an empty set is NULL, which would serialise as ``null`` and
    leave the client null-checking a tile; 0.0 keeps the stat tile plain.

    Rounded to 1dp here rather than in the schema so the stored float keeps full
    precision for anything that needs it. Note the scale is inconsistent — the
    column is documented as 0-1 but the LLM writes 0-100 — so the mean can
    exceed 1.
    """
    result = await db.execute(
        select(func.avg(JobMatch.final_score)).where(JobMatch.user_id == user_id)
    )
    average = result.scalar_one()
    return round(float(average), 1) if average is not None else 0.0


async def get_top_match_cards(
    db: AsyncSession, user_id: int, min_score: float = 0.5, limit: int = 10
) -> list[Any]:
    """Highest-scoring matches at or above ``min_score``."""
    result = await db.execute(
        select(*_MATCH_CARD_COLUMNS)
        .join(Job, Job.id == JobMatch.job_id)
        .join(Company, Company.id == Job.company_id)
        .where(JobMatch.user_id == user_id, JobMatch.final_score >= min_score)
        .order_by(JobMatch.final_score.desc(), JobMatch.matched_at.desc())
        .limit(limit)
    )
    return result.all()


_TOP_MATCH_BASE_COLUMNS = (
    JobMatch.id,
    JobMatch.status.label("match_status"),
    JobMatch.final_score,
    JobMatch.vector_score,
    JobMatch.lexical_score,
    JobMatch.rrf_score,
    JobMatch.key_matches,
    JobMatch.key_gaps,
    Job.title.label("job_title"),
    Company.display_name.label("company_display_name"),
    Company.normalized_name.label("company_normalized_name"),
)


def _latest_run_status(user_id: int):
    """Correlated subquery: this job's most recent tailoring run status.

    ``tailoring_runs`` is unique on ``(user_id, job_id, cv_version_id)``, not on
    ``(user_id, job_id)`` — re-tailoring after a new master CV adds a second run
    for the same job. A plain LEFT JOIN would then emit one match row per run,
    inflating both the page and ``count`` and making ``limit``/``offset`` paging
    walk a join with duplicates. Taking the newest run per job in a scalar
    subquery keeps the match row count exact.

    Ordered by ``created_at`` then ``id`` so "most recent" is total: two runs
    created in the same transaction can share a timestamp, and without the id
    tie-breaker the pick would be arbitrary between requests.

    Returns NULL when the job has no run; the caller maps that to
    ``TailoredCVProgress.none``.
    """
    return (
        select(TailoringRun.status)
        .where(
            TailoringRun.user_id == user_id,
            TailoringRun.job_id == JobMatch.job_id,
        )
        .order_by(TailoringRun.created_at.desc(), TailoringRun.id.desc())
        .limit(1)
        .scalar_subquery()
    )


async def count_top_matches(
    db: AsyncSession, user_id: int, min_score: float | None = None
) -> int:
    """Total matches qualifying for the top-matches list, ignoring paging.

    Counted independently of the page query so the two can never disagree about
    the total. Deliberately does *not* touch the tailoring runs, for the reason
    given on :func:`_latest_run_status`.
    """
    stmt = select(func.count()).select_from(JobMatch).where(JobMatch.user_id == user_id)
    if min_score is not None:
        stmt = stmt.where(JobMatch.final_score >= min_score)
    result = await db.execute(stmt)
    return result.scalar_one()


def _top_matches_stmt(
    user_id: int, min_score: float | None = None
) -> Select[tuple[Any, ...]]:
    """The top-matches SELECT, ordered but unpaged.

    Split out from :func:`get_top_match_results` so the SQL shape can be asserted
    in tests without a session — the scalar-subquery-not-join choice and the
    tie-break ordering are both invisible in the response, and a test that
    re-implemented the statement instead of calling this would drift silently.
    """
    stmt = (
        select(
            *_TOP_MATCH_BASE_COLUMNS,
            _latest_run_status(user_id).label("tailored_cv_status"),
        )
        .join(Job, Job.id == JobMatch.job_id)
        .join(Company, Company.id == Job.company_id)
        .where(JobMatch.user_id == user_id)
    )
    if min_score is not None:
        stmt = stmt.where(JobMatch.final_score >= min_score)

    # matched_at breaks ties so paging is stable when scores are equal —
    # otherwise rows at a page boundary can repeat or drop between requests.
    return stmt.order_by(JobMatch.final_score.desc(), JobMatch.matched_at.desc())


async def get_top_match_results(
    db: AsyncSession,
    user_id: int,
    min_score: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Any]:
    """Highest-scoring matches as flat table rows, with tailoring progress."""
    result = await db.execute(
        _top_matches_stmt(user_id, min_score).offset(offset).limit(limit)
    )
    return result.all()


async def get_tailored_cv_counts(db: AsyncSession, user_id: int) -> dict[str, int]:
    # CASE (not ``count(col == 'x')``): a boolean comparison yields FALSE rather
    # than NULL for non-matching rows, so count() would tally every row into
    # every bucket. CASE yields NULL, which count() skips. Same pattern as
    # master_cv.repository.get_cv_status_counts.
    result = await db.execute(
        select(
            func.count().label("total"),
            func.count(case((TailoredCV.status == "approved", 1))).label("approved"),
            func.count(case((TailoredCV.status == "failed", 1))).label("failed"),
            func.count(case((TailoredCV.render_status.in_(_RENDER_NOT_DONE), 1))).label(
                "rendering"
            ),
            func.count(case((TailoredCV.render_status == "completed", 1))).label(
                "rendered"
            ),
        )
        .select_from(TailoredCV)
        .join(TailoringRun, TailoringRun.id == TailoredCV.tailoring_run_id)
        .where(TailoringRun.user_id == user_id)
    )
    row = result.one()
    return {
        "total": row.total,
        "approved": row.approved,
        "failed": row.failed,
        "rendering": row.rendering,
        "rendered": row.rendered,
    }


async def get_recent_tailored_cv_cards(
    db: AsyncSession, user_id: int, limit: int = 12
) -> list[Any]:
    result = await db.execute(
        select(*_TAILORED_CARD_COLUMNS)
        .join(TailoringRun, TailoringRun.id == TailoredCV.tailoring_run_id)
        .join(Job, Job.id == TailoringRun.job_id)
        .join(Company, Company.id == Job.company_id)
        .outerjoin(CVTemplate, CVTemplate.id == TailoredCV.cv_template_id)
        .where(TailoringRun.user_id == user_id)
        .order_by(TailoredCV.created_at.desc(), TailoredCV.id.desc())
        .limit(limit)
    )
    return result.all()


def _activity_stmt(user_id: int) -> Select:
    tailoring_events = select(
        literal("tailoring").label("type"),
        TailoringRun.id.label("run_id"),
        cast(TailoringRun.stage, String).label("stage"),
        cast(TailoringRun.status, String).label("status"),
        TailoringRun.error_message.label("error_message"),
        TailoringRun.updated_at.label("at"),
    ).where(TailoringRun.user_id == user_id)

    render_events = (
        select(
            literal("render").label("type"),
            TailoringRun.id.label("run_id"),
            literal("render").label("stage"),
            cast(TailoredCV.render_status, String).label("status"),
            TailoredCV.render_error_message.label("error_message"),
            TailoringRun.updated_at.label("at"),
        )
        .join(TailoringRun, TailoringRun.id == TailoredCV.tailoring_run_id)
        .where(TailoringRun.user_id == user_id)
    )

    master_cv_events = (
        select(
            literal("master_cv").label("type"),
            MasterCVVersion.id.label("run_id"),
            literal("parse").label("stage"),
            cast(MasterCVVersion.status, String).label("status"),
            literal(None).label("error_message"),
            MasterCVVersion.updated_at.label("at"),
        )
        .join(MasterCV, MasterCV.id == MasterCVVersion.master_cv_id)
        .where(MasterCV.user_id == user_id)
    )

    events = union_all(tailoring_events, render_events, master_cv_events).subquery()
    return (
        select(events)
        .order_by(
            events.c.at.desc(),
            events.c.type.asc(),
            events.c.run_id.desc(),
        )
        .limit(20)
    )


async def get_activity(db: AsyncSession, user_id: int) -> list[Any]:
    result = await db.execute(_activity_stmt(user_id))
    return result.all()


_TAILORING_RUN_COLUMNS = (
    TailoringRun.id,
    TailoringRun.status.label("run_status"),
    TailoringRun.stage.label("run_stage"),
    TailoringRun.created_at,
    TailoringRun.updated_at,
    TailoringRun.error_message,
    TailoredCV.id.label("tailored_cv_id"),
    Job.title.label("job_title"),
    Company.display_name.label("company_display_name"),
    Company.normalized_name.label("company_normalized_name"),
)


def _tailoring_runs_stmt(user_id: int) -> Select[tuple[Any, ...]]:
    """Newest-first page of a user's tailoring runs, ordered but unpaged.

    ``TailoredCV`` is joined with an outer join on purpose: it is the table that
    says whether a run got as far as producing a CV, and a run that has not (still
    queued, or failed in the evidence/strategy stage) must still appear with
    ``cv_id`` null rather than vanish from the list. ``tailored_cvs.tailoring_run_id``
    is unique, so this cannot fan out the way the top-matches latest-run subquery
    had to guard against.
    """
    return (
        select(*_TAILORING_RUN_COLUMNS)
        .join(Job, Job.id == TailoringRun.job_id)
        .join(Company, Company.id == Job.company_id)
        .outerjoin(TailoredCV, TailoredCV.tailoring_run_id == TailoringRun.id)
        .where(TailoringRun.user_id == user_id)
        # id breaks ties so paging stays stable when two runs share a created_at,
        # which is reachable since the column defaults to now() per statement.
        .order_by(TailoringRun.created_at.desc(), TailoringRun.id.desc())
    )


async def count_tailoring_runs(db: AsyncSession, user_id: int) -> int:
    """Total runs for the user, so ``count`` outlives the current page."""
    return (
        await db.scalar(
            select(func.count())
            .select_from(TailoringRun)
            .where(TailoringRun.user_id == user_id)
        )
    ) or 0


async def get_tailoring_runs(
    db: AsyncSession,
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[Any]:
    result = await db.execute(
        _tailoring_runs_stmt(user_id).limit(limit).offset(offset)
    )
    return result.all()


async def get_current_completed_cv_id(db: AsyncSession, user_id: int) -> UUID | None:
    """Id of the current *completed* CV version, or None.

    Deliberately narrower than :func:`get_current_version`: skill-gap detection
    compares a job's skills against ``cv_skills``, and a version that is still
    parsing has only partially populated that table. Treating its missing entries
    as gaps would report every skill the user does have.
    """
    return await db.scalar(
        select(MasterCVVersion.id)
        .join(MasterCV, MasterCV.id == MasterCVVersion.master_cv_id)
        .where(
            MasterCV.user_id == user_id,
            MasterCVVersion.is_current.is_(True),
            MasterCVVersion.status == CVStatus.COMPLETED.value,
        )
    )


def _missing_skills_stmt(user_id: int, cv_id: UUID) -> Select[tuple[Any, ...]]:
    """Skills the user's matched jobs require that their CV does not list.

    Scoped to the user's *matched* jobs rather than every job in the table, since
    the insight is about gaps in the applications they are actually pursuing.
    The subquery cannot fan out: it only filters ``job_skills`` rows, and the
    outer query groups by skill.
    """
    return (
        select(
            Skill.name.label("skill"),
            func.count(distinct(JobSkill.job_id)).label("job_count"),
            Skill.category.label("category"),
        )
        .join(Skill, Skill.id == JobSkill.skill_id)
        .where(
            JobSkill.job_id.in_(
                select(JobMatch.job_id).where(JobMatch.user_id == user_id)
            ),
            ~JobSkill.skill_id.in_(select(CVSkill.skill_id).where(CVSkill.cv_id == cv_id)),
        )
        .group_by(Skill.id, Skill.name, Skill.category)
        # name breaks ties so equal counts come back in a stable order.
        .order_by(func.count(distinct(JobSkill.job_id)).desc(), Skill.name.asc())
    )


async def get_missing_skills(
    db: AsyncSession, user_id: int, cv_id: UUID, limit: int = 10
) -> list[Any]:
    """Highest-impact skill gaps, most widely required first."""
    result = await db.execute(_missing_skills_stmt(user_id, cv_id).limit(limit))
    return result.all()


def _score_trend_stmt(user_id: int, since: datetime) -> Select[tuple[Any, ...]]:
    """Weekly average match score since ``since``.

    The bucket expression is a ``literal_column`` rather than
    ``func.date_trunc('week', ...)`` on purpose. ``func.date_trunc`` binds the
    ``'week'`` argument as a *parameter*, and Postgres matches GROUP BY against
    the select list by comparing expression trees — a parameter there is not the
    same expression as the one in the select list, so the query fails with
    "column must appear in the GROUP BY clause". Inlining the text makes all
    three occurrences identical.

    ``date_trunc('week', ...)`` buckets Monday-aligned in the server's time zone.
    The cutoff is passed in as a naive datetime rather than computed with
    ``now()`` because ``job_matches.matched_at`` is ``timestamp without time
    zone``: binding naive-to-naive avoids a timestamptz cast that would silently
    shift the boundary if the database session time zone were ever not UTC.
    """
    week = _WEEK_BUCKET
    return (
        select(
            week.label("week"),
            func.avg(JobMatch.final_score).label("avg_score"),
        )
        .where(JobMatch.user_id == user_id, JobMatch.matched_at >= since)
        .group_by(week)
        .order_by(week.asc())
    )


async def get_score_trend(
    db: AsyncSession, user_id: int, since: datetime
) -> list[Any]:
    """Weekly average match score. Weeks with no matches are absent, not null."""
    result = await db.execute(_score_trend_stmt(user_id, since))
    return result.all()
