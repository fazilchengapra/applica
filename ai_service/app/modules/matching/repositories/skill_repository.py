from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.modules.jobs.models import JobSkill

async def lexical_score(db: AsyncSession, user_skills: set[str], job_ids: list[UUID]):
    query = select(JobSkill.job_id, JobSkill.skill_name).where(JobSkill.job_id.in_(job_ids))
    result = await db.execute(query)
    job_skill_map: dict[UUID, set[str]] = {}
    for row in result.all():
        job_skill_map.setdefault(row.job_id, set()).add(row.skill_name.lower())

    scores = {}
    for job_id, skills in job_skill_map.items():
        overlap = len(user_skills & skills)
        scores[job_id] = overlap / max(len(skills), 1)  # simple overlap ratio
    return scores