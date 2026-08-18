import asyncio
from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session

from app.modules.jobs.services.promotion_fetch_service import (
    fetch_and_lock_verified_pending_jobs,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def fetch_promotion_batch_task(self, batch_size: int = 50):
    async def _run():
        async with get_celery_db_session() as session:
            rows = await fetch_and_lock_verified_pending_jobs(session, batch_size)
            return [str(r.id) for r in rows]

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
