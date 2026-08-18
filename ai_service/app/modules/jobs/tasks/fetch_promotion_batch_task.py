import asyncio
from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session

from app.modules.jobs.orchestrators import promotion_orchestrator
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def fetch_promotion_batch_task(self, batch_size: int = 50):
    async def _run():
        async with get_celery_db_session() as session:
            result = await promotion_orchestrator.run(session, batch_size)
            logger.info(f"Promotion batch result: {result}")
            return result

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
