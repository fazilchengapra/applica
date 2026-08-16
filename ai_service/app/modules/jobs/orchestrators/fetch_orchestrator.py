from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.jobs.sources import SOURCE_REGISTRY
from app.modules.jobs.services.ingestion_service import insert_raw_job
from app.modules.jobs.exceptions import JobSourceUnavailableError

async def run(source: str, query: str, db: AsyncSession):
    adapter_cls = SOURCE_REGISTRY.get(source)
    if adapter_cls is None:
        raise ValueError(f"Unknown job source: {source}")

    adapter = adapter_cls()
    try:
        raw_jobs = await adapter.fetch(query=query)
    except JobSourceUnavailableError:
        print(f"Fetch failed for source={source}, query={query}")
        raise

    for job in raw_jobs:
        await insert_raw_job(db, job)
    await db.commit()

    return len(raw_jobs)