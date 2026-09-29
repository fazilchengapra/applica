"""Queries backing the dashboard read model.

Each function owns one section of the aggregate so the service layer can stay a
pure assembler. Column selects (not ORM entities) keep every section to a single
round trip and avoid lazy loads on the async session.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import String, case, cast, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.companies.models import Company
from app.modules.cv_template.models import CVTemplate
from app.modules.jobs.models.jobs import Job
from app.modules.jobs.models.skills import Skill
from app.modules.master_cv.models import MasterCV, MasterCVVersion
from app.modules.master_cv.models.cv_skills import CVSkill
from app.modules.matching.models.job_match import JobMatch
from app.modules.tailoring.models import TailoredCV, TailoringRun

_RENDER_NOT_DONE = ("pending", "processing")

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


async def get_current_version(
    db: AsyncSession, user_id: int
) -> MasterCVVersion | None:
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
    counts = {status.value if hasattr(status, "value") else str(status): n for status, n in result.all()}
    counts["total"] = sum(counts.values())
    return counts


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


async def get_tailored_cv_counts(db: AsyncSession, user_id: int) -> dict[str, int]:
    # CASE (not ``count(col == 'x')``): a boolean comparison yields FALSE rather
    # than NULL for non-matching rows, so count() would tally every row into
    # every bucket. CASE yields NULL, which count() skips. Same pattern as
    # master_cv.repository.get_cv_status_counts.
    result = await db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((TailoredCV.status == "approved", 1))
            ).label("approved"),
            func.count(case((TailoredCV.status == "failed", 1))).label("failed"),
            func.count(
                case((TailoredCV.render_status.in_(_RENDER_NOT_DONE), 1))
            ).label("rendering"),
            func.count(
                case((TailoredCV.render_status == "completed", 1))
            ).label("rendered"),
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
    """Union of the three event sources, newest activity first.

    Timestamps are ``updated_at`` rather than ``created_at``: a run created three
    weeks ago that is still grinding through the critic must not sort above one
    created five minutes ago. Render events borrow the owning run's
    ``updated_at`` because ``tailored_cvs`` has no ``updated_at`` column of its
    own.

    The three sources disagree on timezone-awareness (``tailoring_runs`` is
    ``timestamptz``, ``master_cv_versions`` is naive). Postgres resolves the
    union to ``timestamptz`` by reading the naive values in the session timezone,
    which is UTC here and is the timezone their ``now()`` defaults were written
    in — so the ordering stays correct across sources.

    Every status column is cast to text: they are three unrelated Postgres enum
    types, and a UNION across them has no common type. ``stage`` needs the same
    treatment because the per-source literals ("render", "parse") are not members
    of the ``tailoring_stage`` enum the tailoring branch would otherwise force.
    """
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
