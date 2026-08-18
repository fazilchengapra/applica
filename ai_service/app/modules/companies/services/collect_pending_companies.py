from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.jobs.models.raw_table import RawJob
from app.modules.companies.utils.normalize import group_raw_jobs_by_company


async def collect_pending_companies(db: AsyncSession, batch_limit: int = 500):
    stmt = (
        select(RawJob.id, RawJob.company_name, RawJob.source_type)
        .where(RawJob.company_id.is_(None))
        .limit(batch_limit)
    )
    result = await db.execute(stmt)
    rows = result.mappings().all()
    raw_jobs = [dict(r) for r in rows]

    groups = group_raw_jobs_by_company(raw_jobs)
    return groups
