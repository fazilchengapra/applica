"""HTTP API for the user dashboard aggregate."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.dashboard.schemas import DashboardResponse
from app.modules.dashboard.services.dashboard_service import build_dashboard

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
