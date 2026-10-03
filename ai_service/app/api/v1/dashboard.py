"""HTTP API for the user dashboard aggregate."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.dashboard.schemas import DashboardResponse, DashboardStatsResponse
from app.modules.dashboard.services.dashboard_service import (
    build_dashboard,
    build_dashboard_stats,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Everything the dashboard renders, scoped to the caller.

    Always 200: an account with no CV, matches or tailored CVs gets a fully
    shaped, zeroed response so the client never has to handle a 404 or a null
    section.
    """
    return await build_dashboard(db, user_id)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    top_n: int = Query(
        10,
        ge=1,
        le=100,
        description="Page size echoed back for the client's match-card fetch",
    ),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Headline counters for the dashboard tiles, scoped to the caller.

    The cheap sibling of ``GET /dashboard``: three aggregates, no cards and no
    activity feed, so a client can poll the counters without re-fetching the
    whole aggregate.

    Always 200, and zeroed rather than null: an account with no matches gets
    ``average_final_score`` of 0.0 and empty buckets.
    """
    return await build_dashboard_stats(db, user_id, top_n)
