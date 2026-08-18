from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.jobs.models.raw_table import RawJob


async def link_raw_jobs_to_company(
    db: AsyncSession, raw_job_ids: list, company_id
) -> None:
    if not raw_job_ids:
        return
    await db.execute(
        update(RawJob).where(RawJob.id.in_(raw_job_ids)).values(company_id=company_id)
    )
