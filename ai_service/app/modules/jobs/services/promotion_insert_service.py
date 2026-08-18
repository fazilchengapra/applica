from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.modules.jobs.models import RawJob, Job
from app.modules.jobs.schemas import StructuredJob
from app.modules.jobs.utils.hashing import compute_dedup_hash

import logging

logger = logging.getLogger(__name__)

from datetime import datetime


def parse_posted_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


async def insert_structured_jobs(
    session: AsyncSession,
    structured_pairs: list[tuple[RawJob, StructuredJob]],
) -> dict:

    inserted_count = 0
    duplicate_ids = []
    processed_ids = []

    for raw_job, structured in structured_pairs:
        location_str = f"{structured.location_city or ''} {structured.location_country or ''}".strip()

        final_hash = compute_dedup_hash(
            structured.normalized_title,
            str(raw_job.company_id),
            location_str,
        )

        stmt = (
            pg_insert(Job)
            .values(
                raw_job_id=raw_job.id,
                company_id=raw_job.company_id,
                source_type=raw_job.source_type,
                source_name=raw_job.source_name,
                external_id=raw_job.external_id,
                source_url=raw_job.source_url,
                title=raw_job.title,
                normalized_title=structured.normalized_title,
                description=structured.description,
                location=location_str or None,
                remote_type=structured.remote_type,
                employment_type=structured.employment_type,
                salary_min=structured.salary_min,
                salary_max=structured.salary_max,
                salary_currency=structured.salary_currency,
                salary_period=structured.salary_period,
                dedup_hash=final_hash,
                posted_at=parse_posted_at(structured.posted_at),
            )
            .on_conflict_do_nothing(index_elements=["dedup_hash"])
            .returning(Job.id)
        )

        result = await session.execute(stmt)
        row = result.first()

        if row is None:
            duplicate_ids.append(raw_job.id)
        else:
            inserted_count += 1
            processed_ids.append(raw_job.id)

    if processed_ids:
        await session.execute(
            update(RawJob)
            .where(RawJob.id.in_(processed_ids))
            .values(processing_status="processed")
        )
    if duplicate_ids:
        await session.execute(
            update(RawJob)
            .where(RawJob.id.in_(duplicate_ids))
            .values(processing_status="duplicate")
        )

    await session.commit()

    return {"inserted": inserted_count, "duplicates_at_insert": len(duplicate_ids)}
