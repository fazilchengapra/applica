from sqlalchemy import select

from app.db.celery_db import get_celery_db_session as get_session_context
from app.modules.master_cv.models import (
    MasterCVVersion,
)
from app.modules.master_cv.schemas import (
    StructuredCV,
)
from app.modules.master_cv.repository.master_cv_repo import get_master_cv

async def get_cv_metadata(user_id: int, cv_version_id: str) -> StructuredCV:
    """
    Fetches and parses the MasterCVVersion.parsed_data jsonb column into StructuredCV.
    Writer uses .contact, .education, .certifications for static sections.
    """
    async with get_session_context() as session:
        master_cv = await get_master_cv(session=session, user_id=user_id)
        if master_cv is None:
            raise ValueError(f"No master CV found for user {user_id}")

        stmt = select(MasterCVVersion).where(
            MasterCVVersion.id == cv_version_id,
            MasterCVVersion.master_cv_id == master_cv.id,
        )
        result = await session.execute(stmt)
        cv_version = result.scalar_one_or_none()

        if cv_version is None:
            raise ValueError(
                f"MasterCVVersion {cv_version_id} not found for user {user_id}"
            )

        if cv_version.parsed_data is None:
            raise ValueError(
                f"MasterCVVersion {cv_version_id} has no parsed_data — CV processing may still be pending"
            )

        return StructuredCV.model_validate(cv_version.parsed_data)
