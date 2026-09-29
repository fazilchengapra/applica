"""Read queries for a user's tailored CVs and their pipeline context."""

from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.companies.models import Company
from app.modules.cv_template.models import CVTemplate
from app.modules.jobs.models.jobs import Job
from app.modules.tailoring.models import (
    CVRenderStatus,
    TailoredCV,
    TailoredCVStatus,
    TailoringRun,
)

# Explicit columns rather than ORM entities: the response nests template/run/job
# and every one of those may be missing, and column selects keep the whole row
# in a single round trip (no lazy loads on the async session).
_ITEM_COLUMNS = (
    TailoredCV.id,
    TailoredCV.created_at,
    TailoredCV.status.label("cv_status"),
    TailoredCV.render_status.label("cv_render_status"),
    TailoredCV.render_error_message,
    TailoredCV.critic_score,
    TailoredCV.critic_verdict,
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


def _filters(
    user_id: int,
    status_filter: TailoredCVStatus | None,
    render_status_filter: CVRenderStatus | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [TailoringRun.user_id == user_id]
    if status_filter is not None:
        conditions.append(TailoredCV.status == status_filter)
    if render_status_filter is not None:
        conditions.append(TailoredCV.render_status == render_status_filter)
    return conditions


def _page_stmt(
    conditions: list[ColumnElement[bool]],
    limit: int,
    offset: int,
) -> Select:
    return (
        select(*_ITEM_COLUMNS)
        .join(TailoringRun, TailoringRun.id == TailoredCV.tailoring_run_id)
        .join(Job, Job.id == TailoringRun.job_id)
        .join(Company, Company.id == Job.company_id)
        .outerjoin(CVTemplate, CVTemplate.id == TailoredCV.cv_template_id)
        .where(*conditions)
        # id breaks ties so paging stays stable when timestamps collide.
        .order_by(TailoredCV.created_at.desc(), TailoredCV.id.desc())
        .limit(limit)
        .offset(offset)
    )


async def list_tailored_cvs(
    db: AsyncSession,
    user_id: int,
    *,
    status_filter: TailoredCVStatus | None = None,
    render_status_filter: CVRenderStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[Any]]:
    """Newest-first page of a user's tailored CVs plus the total match count.

    ``total`` counts every row matching the filters, not just the current page.
    """
    conditions = _filters(user_id, status_filter, render_status_filter)

    total = await db.scalar(
        select(func.count())
        .select_from(TailoredCV)
        .join(TailoringRun, TailoringRun.id == TailoredCV.tailoring_run_id)
        .where(*conditions)
    )

    result = await db.execute(_page_stmt(conditions, limit, offset))

    return total or 0, result.all()
