"""Queries backing the home aggregate's CV-side step.

Only ``upload_cv`` needs data from this service; everything else in the home
payload is account state owned by user_service. Soft-deleted master CVs
(``deleted_at`` set) do not count as an uploaded CV.
"""

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.master_cv.models import MasterCV, MasterCVVersion


async def has_uploaded_cv(db: AsyncSession, user_id: int) -> bool:
    """Whether the user has a master CV with at least one uploaded version.

    A single ``EXISTS`` rather than a count, so the common "no CV" case reads
    one index entry and stops.
    """
    stmt = select(
        exists().where(
            MasterCVVersion.master_cv_id == MasterCV.id,
            MasterCV.user_id == user_id,
            MasterCV.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    return bool(result.scalar())
