from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.modules.jobs.models.jobs import Job, JobStatus
from ..schemas.user_profile import UserProfile


async def prefilter_jobs(db: AsyncSession, user: UserProfile) -> list[UUID]:
    query = select(Job.id).where(
        Job.status == JobStatus.ACTIVE.value,
        # Job.location.in_(user.preferred_locations) if user.preferred_locations else True,
        Job.title == user.target_role if user.target_role else True,
    )
    result = await db.execute(query)
    return [row[0] for row in result.all()]
