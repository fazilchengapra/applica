from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user_id
from app.modules.matching.schemas.job_match import JobMatchOut, MatchStatusUpdate
from app.modules.matching.models.job_match import MatchStatus
from app.modules.matching.services import (
    get_matches_for_user,
    get_match_by_id,
    update_match_status,
    delete_match,
)
from app.modules.matching.tasks import match_user_task

router = APIRouter(prefix="/matches", tags=["matching"])
