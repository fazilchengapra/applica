from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.dependencies.admin import require_admin
from app.modules.jobs.tasks.fetch_promotion_batch_task import (
    fetch_promotion_batch_task,
)

router = APIRouter(prefix="/admin/jobs", tags=["Admin Jobs"])


class PromoteJobsRequest(BaseModel):
    batch_size: int = Field(
        50, ge=1, le=500, description="Max verified pending raw jobs to promote in one batch"
    )


class PromoteJobsAccepted(BaseModel):
    task_id: str
    status: str
    batch_size: int


@router.post(
    "/promotion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PromoteJobsAccepted,
)
async def promote_jobs(
    payload: PromoteJobsRequest | None = None,
    _admin=Depends(require_admin),
):
    batch_size = payload.batch_size if payload else 50
    task = fetch_promotion_batch_task.delay(batch_size=batch_size)
    return PromoteJobsAccepted(
        task_id=task.id,
        status="queued",
        batch_size=batch_size,
    )