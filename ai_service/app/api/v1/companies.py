from fastapi import APIRouter, Depends
from app.modules.companies.tasks import collect_pending_companies_task

router = APIRouter(prefix="/companies/admin", tags=["jobs"])

# admin route TODO: add the admin middleware
@router.post("/collect-pending")
async def trigger_collect_pending():
    task = collect_pending_companies_task.delay()
    return {"status":"ok"}
