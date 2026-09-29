from fastapi import APIRouter, Depends
from app.modules.jobs.tasks.fetch_tasks import fetch_jobs_task
from app.modules.jobs.schemas import FetchJobsRequest
from app.core.dependencies import get_current_user_id

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/fetch/{source}")
async def trigger_fetch(
    source: str,
    payload: FetchJobsRequest,
    user_id: int = Depends(get_current_user_id),
):
    task = fetch_jobs_task.delay(source=source, query=payload.query)
    return {"task_id": task.id, "status": "queued"}
