from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.master_cv.models.master_cv import MasterCVVersion, MasterCV, CVStatus


async def get_current_completed_cv(
    db: AsyncSession,
    user_id: int,
) -> MasterCVVersion | None:

    query = select(MasterCV).where(MasterCV.user_id == user_id)

    result = await db.execute(query)

    master_cv = result.scalar_one_or_none()

    if master_cv is None:
        return None

    query = select(MasterCVVersion).where(
        MasterCVVersion.master_cv == master_cv,
        MasterCVVersion.is_current.is_(True),
        MasterCVVersion.status == CVStatus.COMPLETED.value,
    )

    result = await db.execute(query)

    return result.scalar_one_or_none()
