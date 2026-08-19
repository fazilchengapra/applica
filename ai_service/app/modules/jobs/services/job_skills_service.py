from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import JobSkill
from app.modules.jobs.services.job_skills_llm import get_skills_llm, extract_skills
from app.modules.jobs.services.lookup.skill_lookup_service import get_or_create_skill

import logging

logger = logging.getLogger(__name__)


async def generate_and_insert_skills(
    session: AsyncSession,
    job_id,
    description: str,
) -> int:

    llm = get_skills_llm()

    try:
        extracted = await extract_skills(llm, description)
    except Exception:
        logger.exception(f"Skill extraction failed for job_id={job_id}")
        return 0
    if not extracted.skills:
        return 0

    job_skill_rows = []

    for s in extracted.skills:
        try:
            skill_id = await get_or_create_skill(session, s.skill_name)
        except Exception:
            logger.exception(
                f"Skill lookup/create failed for job_id={job_id}, skill_name={s.skill_name}"
            )
            continue

        job_skill_rows.append(
            {
                "job_id": job_id,
                "skill_id": skill_id,
                "skill_type": s.skill_type,
            }
        )

    if not job_skill_rows:
        return 0

    stmt = (
        pg_insert(JobSkill)
        .values(job_skill_rows)
        .on_conflict_do_nothing(index_elements=["job_id", "skill_id"])
    )
    await session.execute(stmt)
    await session.commit()

    return len(job_skill_rows)
