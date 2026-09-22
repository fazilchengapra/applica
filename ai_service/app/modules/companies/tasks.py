import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID
from celery import shared_task
from sqlalchemy import func, select
from app.core.config import settings
from app.db.celery_db import get_celery_db_session
from app.modules.companies.models import Company
from app.modules.companies.services.admin_review import list_companies
from app.modules.companies.services.collect_pending_companies import (
    collect_pending_companies,
)
from app.modules.companies.services.get_or_create_company import get_or_create_company
from app.modules.jobs.services.link_raw_jobs import link_raw_jobs_to_company
from app.modules.companies.services.verify_company import verify_company
from app.modules.companies.exceptions import (
    CompanyNotFoundError,
    EvidenceGatheringError,
    VerificationDecisionError,
)


async def _count_verifications_since(db, hours: int = 24) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    count = await db.scalar(
        select(func.count(Company.id)).where(Company.verified_at >= cutoff)
    )
    return int(count or 0)


async def _can_auto_verify(db) -> bool:
    if not settings.COMPANY_AUTO_VERIFY_ENABLED:
        return False
    count = await _count_verifications_since(db)
    return count < settings.COMPANY_AUTO_VERIFY_DAILY_LIMIT


async def _collect_pending_companies_async(batch_limit: int):
    async with get_celery_db_session() as db:
        groups = await collect_pending_companies(db, batch_limit=batch_limit)
        dispatched = 0
        for norm_name, group in groups.items():
            company, was_created = await get_or_create_company(
                db, norm_name, group.display_name
            )
            await link_raw_jobs_to_company(db, group.raw_job_ids, company.id)

            if was_created and await _can_auto_verify(db):
                verify_company_task.delay(str(company.id))
                dispatched += 1

        await db.commit()
        return {"groups_found": len(groups), "verifications_dispatched": dispatched}


@shared_task(name="companies.collect_pending")
def collect_pending_companies_task(batch_limit: int = 500):
    return asyncio.run(_collect_pending_companies_async(batch_limit))


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def verify_company_task(self, company_id: str, force_refresh: bool = False):
    async def _run():
        async with get_celery_db_session() as session:
            await verify_company(session, UUID(company_id), force_refresh=force_refresh)

    try:
        asyncio.run(_run())
    except CompanyNotFoundError:
        # not retryable — company was deleted or bad id, log and drop
        raise
    except (EvidenceGatheringError, VerificationDecisionError) as e:
        raise self.retry(exc=e)


@shared_task(name="companies.verify_pending_batch")
def verify_pending_batch_task(batch_limit: int = 50):
    async def _run():
        async with get_celery_db_session() as session:
            pending = await list_companies(
                session, limit=batch_limit, offset=0, status="pending"
            )
            dispatched = 0
            for company in pending:
                verify_company_task.delay(str(company.id))
                dispatched += 1
            return {"selected": len(pending), "dispatched": dispatched}

    return asyncio.run(_run())