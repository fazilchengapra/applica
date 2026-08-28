from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.master_cv.models import MasterCV


async def get_master_cv(user_id: int, session: AsyncSession):
    return await session.scalar(select(MasterCV).where(MasterCV.user_id == user_id))


async def get_master_cv_id_by_user_id(
    user_id: int, session: AsyncSession
) -> UUID | None:
    stmt = select(MasterCV.id).where(MasterCV.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
