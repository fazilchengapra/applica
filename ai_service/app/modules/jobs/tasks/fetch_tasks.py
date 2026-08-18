import asyncio
from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session
from app.modules.jobs.orchestrators import fetch_orchestrator


@celery_app.task
def fetch_jobs_task(source: str, query: str):
    asyncio.run(_fetch_jobs_async(source, query))


async def _fetch_jobs_async(source: str, query: str):
    async with get_celery_db_session() as db:
        count = await fetch_orchestrator.run(source, query, db)
        print(f"Fetched {count} raw jobs from {source} for query='{query}'")
