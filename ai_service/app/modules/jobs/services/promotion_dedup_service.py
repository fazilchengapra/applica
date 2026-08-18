from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import RawJob, Job
from app.modules.jobs.utils.hashing import compute_dedup_hash


async def filter_duplicate_raw_jobs(
    session: AsyncSession,
    raw_jobs: list[RawJob],
) -> list[RawJob]:
    
    if not raw_jobs:
        return []

    candidate_hashes = {
        row.id: compute_dedup_hash(row.title, str(row.company_name), row.location_raw)
        for row in raw_jobs
    }

    existing_hashes_result = await session.execute(
        select(Job.dedup_hash).where(Job.dedup_hash.in_(candidate_hashes.values()))
    )
    existing_hashes = {h for (h,) in existing_hashes_result.all()}

    duplicate_ids = [
        row_id
        for row_id, h in candidate_hashes.items()
        if h in existing_hashes
    ]

    if duplicate_ids:
        await session.execute(
            update(RawJob)
            .where(RawJob.id.in_(duplicate_ids))
            .values(processing_status="duplicate")
        )
        await session.commit()

    return [row for row in raw_jobs if row.id not in duplicate_ids]