# app/modules/companies/tasks.py
import asyncio
from celery import shared_task
from app.db.celery_db import get_celery_db_session
from app.modules.companies.services.collect_pending_companies import (
    collect_pending_companies,
)
from app.modules.companies.services.get_or_create_company import get_or_create_company
from app.modules.jobs.services.link_raw_jobs import link_raw_jobs_to_company


async def _collect_pending_companies_async(batch_limit: int):
    async with get_celery_db_session() as db:
        groups = await collect_pending_companies(db, batch_limit=batch_limit)

        dispatched = 0
        for norm_name, group in groups.items():
            company, was_created = await get_or_create_company(
                db, norm_name, group.display_name
            )
            await link_raw_jobs_to_company(db, group.raw_job_ids, company.id)

            # if was_created:  # only verify brand-new companies
            #     verify_company.delay(str(company.id))
            #     dispatched += 1

        await db.commit()
        return {"groups_found": len(groups), "verifications_dispatched": dispatched}


@shared_task(name="companies.collect_pending")
def collect_pending_companies_task(batch_limit: int = 500):
    return asyncio.run(_collect_pending_companies_async(batch_limit))
