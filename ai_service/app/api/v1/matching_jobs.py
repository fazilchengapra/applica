from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.matching.models.job_match import MatchStatus
from app.modules.matching.schemas.job_match import JobMatchOut, MatchStatusUpdate
from app.modules.matching.services import (
    get_match_by_id,
    get_matches_for_user,
    update_match_status,
)
from app.modules.matching.tasks import match_user_task

router = APIRouter(prefix="/job-matches", tags=["matching"])


@router.get("", response_model=list[JobMatchOut])
async def list_matches(
    user_id: int = Depends(get_current_user_id),
    status_filter: MatchStatus | None = Query(None, alias="status"),
    min_score: float | None = Query(None, ge=0, le=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await get_matches_for_user(
        db,
        user_id,
        status_filter=status_filter,
        min_score=min_score,
        limit=limit,
        offset=offset,
    )


@router.get("/{match_id}", response_model=JobMatchOut)
async def get_match(
    match_id: UUID,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    match = await get_match_by_id(db, match_id, user_id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    return match


@router.patch("/{match_id}/status", response_model=JobMatchOut)
async def patch_match_status(
    match_id: UUID,
    payload: MatchStatusUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    match = await update_match_status(db, match_id, user_id, payload.status)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")
    return match


@router.post("/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_matches(
    user_id: int = Depends(get_current_user_id),
):
    match_user_task.delay(str(user_id))
    return {"detail": "Matching started", "user_id": user_id}
