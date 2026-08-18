# quick shell test — python -m app.modules.jobs.tasks.promotion_tasks_test
import asyncio
from app.db.celery_db import get_celery_db_session
from app.modules.jobs.services.promotion_fetch_service import fetch_and_lock_verified_pending_jobs

async def main():
    async with get_celery_db_session() as session:
        rows = await fetch_and_lock_verified_pending_jobs(session, batch_size=10)
        print(f"Locked {len(rows)} rows")
        for r in rows:
            print(r.id, r.company_id, r.processing_status)

asyncio.run(main())