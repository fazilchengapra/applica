"""HTTP API for ATS readiness reports on the caller's master CV."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.ats.exceptions import ATSCVNotFoundError, ATSCVNotReadyError
from app.modules.ats.schemas import (
    AnalyzeRequest,
    ATSReportListOut,
    ATSReportOut,
)
from app.modules.ats.services.analysis_service import (
    analyze_cv_version,
    get_report_out,
    list_reports,
)

router = APIRouter(prefix="/ats", tags=["ATS"])


@router.post(
    "/analyze",
    response_model=ATSReportOut,
    responses={
        404: {"description": "The caller has no CV version matching the request"},
        409: {"description": "The CV is still processing and cannot be scored yet"},
    },
)
async def analyze(
    body: AnalyzeRequest | None = None,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    request = body or AnalyzeRequest()
    try:
        return await analyze_cv_version(
            db, user_id, request.cv_version_id, request.force
        )
    except ATSCVNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ATSCVNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get("/reports", response_model=ATSReportListOut)
async def reports(
    cv_version_id: UUID | None = Query(None, description="Restrict to one CV version"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """The caller's report history, newest first, for score-trend charts.

    ``total`` is the number of qualifying reports, not the length of this page.
    """
    return await list_reports(db, user_id, cv_version_id, limit, offset)


@router.get("/reports/{report_id}", response_model=ATSReportOut)
async def report(
    report_id: UUID,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    stored = await get_report_out(db, report_id, user_id)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found"
        )
    return stored
