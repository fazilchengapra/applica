"""HTTP API for the composed home aggregate (BFF).

Public entry point for the home screen. It fans out internally: account state
comes from user_service over the gateway, and the CV-side onboarding step is
resolved from this service's own database.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.home.exceptions import UserServiceError, UserServiceUnavailable
from app.modules.home.schemas import HomeResponse
from app.modules.home.services.home_service import build_home

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("", response_model=HomeResponse)
async def get_home(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Everything the home screen renders, scoped to the caller.

    The response always has the same shape. Unlike the dashboard, this does not
    degrade to a zeroed payload when an upstream is down: the account sections
    are the point of the endpoint, so a user_service failure surfaces as 502/504
    rather than a silently empty home page.
    """
    try:
        return await build_home(db, user_id)
    except UserServiceUnavailable as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Account service is unavailable. Please retry.",
        ) from e
    except UserServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not load account details.",
        ) from e
