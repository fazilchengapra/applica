import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from uuid import UUID
from app.modules.jobs.models.jobs import Job, JobStatus
from app.modules.companies.models import Company, CompanyStatus
from ..schemas.user_profile import UserProfile
logger = logging.getLogger(__name__)


async def prefilter_jobs(db: AsyncSession, user: UserProfile) -> list[UUID]:
    title_conditions = []
    logger.info("================================== user ============================= %s", user)
    if user.target_role:
        title_conditions = [
            Job.title.ilike(f"%{term}%") for term in user.target_role.split()
        ]

    eligible_company_statuses = [
        status.value for status in CompanyStatus if status != CompanyStatus.REJECTED
    ]

    conditions = [
        Job.status == JobStatus.ACTIVE.value,
        Job.company_id == Company.id,
        Company.status.in_(eligible_company_statuses),
    ]
    if title_conditions:
        conditions.append(or_(*title_conditions))

    query = select(Job.id).where(*conditions)
    result = await db.execute(query)
    return [row[0] for row in result.all()]
