import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import RawJob
from app.modules.jobs.schemas import RawJobInput
from app.modules.jobs.utils.hashing import compute_dedup_hash

logger = logging.getLogger(__name__)


async def insert_raw_job(db: AsyncSession, job: RawJobInput) -> RawJob:
    dedup_hash = compute_dedup_hash(
        title=job.title or "",
        company=job.company_name or "",
        location=job.location_raw,
    )

    raw = RawJob(
        source_type=job.source_type,
        source_name=job.source_name,
        external_id=job.external_id,
        source_url=job.source_url,
        title=job.title,
        company_name=job.company_name,
        description_raw=job.description_raw,
        location_raw=job.location_raw,
        salary_raw=job.salary_raw,
        posted_at_raw=job.posted_at_raw,
        dedup_hash=dedup_hash,
        raw_payload=job.model_dump(),
    )

    db.add(raw)
    logger.debug(f"Staged raw job: source={job.source_name} external_id={job.external_id}")
    return raw