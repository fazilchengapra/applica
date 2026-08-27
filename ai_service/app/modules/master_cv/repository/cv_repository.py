from uuid import UUID
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.master_cv.models import MasterCVVersion, CVStatus, MasterCV


async def get_cv_status_counts(user_id: str, session: AsyncSession) -> dict:
    master_cv_id = await get_master_cv_id_by_user_id(user_id=user_id, session=session)
    stmt = select(
        func.count().label("total"),
        func.count(case((MasterCVVersion.status == CVStatus.COMPLETED, 1))).label(
            "ready"
        ),
        func.count(case((MasterCVVersion.status == CVStatus.PROCESSING, 1))).label(
            "processing"
        ),
        func.count(case((MasterCVVersion.status == CVStatus.FAILED, 1))).label(
            "failed"
        ),
    ).where(MasterCVVersion.master_cv_id == master_cv_id)

    result = await session.execute(stmt)
    row = result.one()

    return {
        "total": row.total,
        "ready": row.ready,
        "processing": row.processing,
        "failed": row.failed,
    }


async def get_master_cv_id_by_user_id(
    user_id: str, session: AsyncSession
) -> UUID | None:
    stmt = select(MasterCV.id).where(MasterCV.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
