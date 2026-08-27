from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.master_cv.models import MasterCVVersion, CVStatus
from app.modules.master_cv.repository import get_cv_status_counts
from app.modules.master_cv.schemas import CVStatsResponse


async def get_cv_stats(user_id: str, session: AsyncSession) -> dict:
    return await get_cv_status_counts(user_id=user_id, session=session)
