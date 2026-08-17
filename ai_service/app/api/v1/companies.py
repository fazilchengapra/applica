from uuid import UUID
from fastapi import APIRouter, Depends
from app.modules.companies.tasks import (
    collect_pending_companies_task,
    verify_company_task,
)

router = APIRouter(prefix="/companies/admin", tags=["jobs"])


# admin route TODO: add the admin middleware
@router.post("/collect-pending")
async def trigger_collect_pending():
    task = collect_pending_companies_task.delay()
    return {"status": "ok"}


# admin route TODO: add the admin middleware
@router.post("/{company_id}/verify")
async def trigger_verify_pending(company_id: UUID):
    task = verify_company_task.delay(str(company_id))
    return {"status": "ok"}
