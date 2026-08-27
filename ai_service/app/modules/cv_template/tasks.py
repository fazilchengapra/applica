import asyncio

from celery import shared_task
from app.db.celery_db import get_celery_db_session
from app.modules.cv_template.services.orchestrator import process_cv_template


async def _run(template_id: str) -> None:
    async with get_celery_db_session() as session:
        try:
            await process_cv_template(template_id, session)
        except Exception:
            await session.rollback()
            raise


@shared_task(
    name="cv_templates.process_cv_template",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def process_cv_template_task(self, template_id: str) -> None:
    try:
        asyncio.run(_run(template_id))
    except Exception as exc:
        raise self.retry(exc=exc)
