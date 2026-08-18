# app/modules/jobs/services/promotion_fetch_service.py

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.jobs.models import RawJob


# fetch_and_lock_verified_pending_jobs fetches a batch of verified pending jobs and locks them for processing.
async def fetch_and_lock_verified_pending_jobs(
    session: AsyncSession,
    batch_size: int = 50,
) -> list[RawJob]:
    stmt = (
        select(RawJob)
        .where(
            RawJob.processing_status == "pending",
            RawJob.company_id.is_not(None),
        )
        .order_by(RawJob.fetched_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )

    result = await session.execute(stmt)
    rows = result.scalars().all()

    if not rows:
        return []

    ids = [row.id for row in rows]

    await session.execute(
        update(RawJob).where(RawJob.id.in_(ids)).values(processing_status="processing")
    )
    await session.commit()

    # refresh in-memory objects to reflect committed status
    for row in rows:
        row.processing_status = "processing"

    return rows
