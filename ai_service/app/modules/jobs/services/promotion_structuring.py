# app/modules/jobs/services/promotion_structuring_service.py

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import RawJob
from app.modules.jobs.schemas import StructuredJob
from .job_structuring import structure_raw_job
from app.modules.jobs.llm_client import get_structuring_llm

import logging

logger = logging.getLogger(__name__)


async def structure_batch(
    session: AsyncSession,
    raw_jobs: list[RawJob],
) -> list[tuple[RawJob, StructuredJob]]:

    llm = get_structuring_llm()
    structured_pairs: list[tuple[RawJob, StructuredJob]] = []
    failed_ids: list = []

    for raw_job in raw_jobs:
        try:
            structured = await structure_raw_job(llm, raw_job)
            structured_pairs.append((raw_job, structured))
        except Exception:
            logger.exception(f"Structuring failed for raw_job_id={raw_job.id}")
            failed_ids.append(raw_job.id)

    if failed_ids:
        await session.execute(
            update(RawJob)
            .where(RawJob.id.in_(failed_ids))
            .values(processing_status="failed")
        )
        await session.commit()

    return structured_pairs
