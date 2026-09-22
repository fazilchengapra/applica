from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.admin import require_admin
from app.modules.companies.exceptions import CompanyNotFoundError
from app.modules.companies.schemas import (
    CompanyAdminActionResponse,
    CompanyAdminOut,
)
from app.modules.companies.services import admin_review
from app.modules.companies.tasks import (
    collect_pending_companies_task,
    verify_company_task,
    verify_pending_batch_task,
)

router = APIRouter(prefix="/companies/admin", tags=["jobs"])


@router.post("/collect-pending")
async def trigger_collect_pending(
    _admin=Depends(require_admin),
):
    task = collect_pending_companies_task.delay()
    return {"status": "ok", "task_id": task.id}


@router.post("/verify-pending")
async def trigger_verify_pending_batch(
    batch_limit: int = Query(50, ge=1, le=500),
    _admin=Depends(require_admin),
):
    task = verify_pending_batch_task.delay(batch_limit=batch_limit)
    return {"status": "ok", "task_id": task.id, "batch_limit": batch_limit}


@router.get("/review-queue", response_model=list[CompanyAdminOut])
async def list_review_queue(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    return await admin_review.list_companies(
        db, limit=limit, offset=offset, status="pending_review"
    )


@router.get("/{company_id}", response_model=CompanyAdminOut)
async def get_company_detail(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        return await admin_review.get_company_detail(db, company_id)
    except CompanyNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")


@router.post("/{company_id}/verify")
async def trigger_verify_pending(
    company_id: UUID,
    force_refresh: bool = False,
    _admin=Depends(require_admin),
):
    task = verify_company_task.delay(str(company_id), force_refresh=force_refresh)
    return {"status": "ok", "task_id": task.id, "force_refresh": force_refresh}


@router.post("/{company_id}/approve", response_model=CompanyAdminActionResponse)
async def approve_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        company = await admin_review.admin_approve_company(db, company_id)
    except CompanyNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return CompanyAdminActionResponse(
        id=company.id,
        status=company.status,
        message="Company approved",
    )


@router.post("/{company_id}/reject", response_model=CompanyAdminActionResponse)
async def reject_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        company = await admin_review.admin_reject_company(db, company_id)
    except CompanyNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return CompanyAdminActionResponse(
        id=company.id,
        status=company.status,
        message="Company rejected",
    )