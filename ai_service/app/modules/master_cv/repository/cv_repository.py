from uuid import UUID
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.master_cv.repository.master_cv_repo import get_master_cv_id_by_user_id
from app.modules.master_cv.models import MasterCVVersion, CVStatus
from app.modules.master_cv.models.cv_skills import CVSkill
from app.modules.jobs.models.skills import Skill


async def get_cv_status_counts(user_id: str, session: AsyncSession) -> dict:
    master_cv_id = await get_master_cv_id_by_user_id(user_id=user_id, session=session)
    stmt = select(
        func.count().label("total"),
        func.count(case((MasterCVVersion.status == CVStatus.COMPLETED.value, 1))).label(
            "ready"
        ),
        func.count(
            case((MasterCVVersion.status == CVStatus.PROCESSING.value, 1))
        ).label("processing"),
        func.count(case((MasterCVVersion.status == CVStatus.PENDING.value, 1))).label(
            "pending"
        ),
        func.count(case((MasterCVVersion.status == CVStatus.FAILED.value, 1))).label(
            "failed"
        ),
    ).where(MasterCVVersion.master_cv_id == master_cv_id)

    result = await session.execute(stmt)
    row = result.one()

    return {
        "total": row.total,
        "ready": row.ready,
        "pending": row.pending,
        "processing": row.processing,
        "failed": row.failed,
    }


async def get_all_cv_versions(master_cv_id: UUID, session: AsyncSession):
    cvs = (
        await session.scalars(
            select(MasterCVVersion).where(MasterCVVersion.master_cv_id == master_cv_id)
        )
    ).all()

    return cvs


async def get_current_cv_version(
    user_id: str, session: AsyncSession
) -> MasterCVVersion | None:
    master_cv_id = await get_master_cv_id_by_user_id(user_id=user_id, session=session)
    if master_cv_id is None:
        return None

    stmt = select(MasterCVVersion).where(
        MasterCVVersion.master_cv_id == master_cv_id,
        MasterCVVersion.is_current.is_(True),
    )
    result = await session.execute(stmt)

    return result.scalar_one_or_none()


async def get_skills_for_cv(cv_id: UUID, session: AsyncSession) -> list[tuple]:
    stmt = (
        select(Skill.name, Skill.normalized_name, CVSkill.skill_type)
        .join(CVSkill, CVSkill.skill_id == Skill.id)
        .where(CVSkill.cv_id == cv_id)
        .order_by(CVSkill.skill_type, Skill.normalized_name)
    )
    result = await session.execute(stmt)

    return [(row.name, row.normalized_name, row.skill_type) for row in result.all()]
