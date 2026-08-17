from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.jobs.sources import SOURCE_REGISTRY
from app.modules.jobs.services.ingestion_service import insert_raw_job
from app.modules.jobs.exceptions import JobSourceUnavailableError

async def run(source: str, query: str, db: AsyncSession):
    adapter = SOURCE_REGISTRY[source]()
    raw_jobs = await adapter.fetch(query=query)

    inserted_count = 0
    for job in raw_jobs:
        was_inserted = await insert_raw_job(db, job)
        if was_inserted:
            inserted_count += 1

    await db.commit()
    return inserted_count