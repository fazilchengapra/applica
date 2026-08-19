from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.services.promotion_fetch_service import (
    fetch_and_lock_verified_pending_jobs,
)
from app.modules.jobs.services.promotion_dedup_service import filter_duplicate_raw_jobs
from app.modules.jobs.services.promotion_insert_service import insert_structured_jobs

from app.modules.jobs.services.promotion_structuring import structure_batch
from app.modules.jobs.services.job_skills_service import generate_and_insert_skills

async def run(session: AsyncSession, batch_size: int = 50) -> dict:
    locked_rows = await fetch_and_lock_verified_pending_jobs(session, batch_size)
    if not locked_rows:
        return {"fetched": 0, "duplicates": 0, "to_structure": 0}

    survivors = await filter_duplicate_raw_jobs(session, locked_rows)
    structured_pairs = await structure_batch(session, survivors)
    insert_result = await insert_structured_jobs(session, structured_pairs)

    skills_inserted = 0
    for job_id, description in insert_result["inserted_jobs"]:
        skills_inserted += await generate_and_insert_skills(
            session, job_id, description
        )

    return {
        "fetched": len(locked_rows),
        "duplicates": len(locked_rows) - len(survivors),
        "structured": len(structured_pairs),
        "failed": len(survivors) - len(structured_pairs),
        "inserted": insert_result["inserted"],
        "duplicates_at_insert": insert_result["duplicates_at_insert"],
    }
