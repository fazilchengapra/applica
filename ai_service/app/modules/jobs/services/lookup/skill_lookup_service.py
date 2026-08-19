from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import Skill
from app.modules.jobs.utils.hashing import normalize_text

import logging

logger = logging.getLogger(__name__)


async def get_or_create_skill(session: AsyncSession, skill_name: str) -> str:
    norm = normalize_text(skill_name)

    # find the skill is exist if yes return it.
    existing = await session.execute(
        select(Skill.id).where(Skill.normalized_name == norm)
    )
    row = existing.first()
    if row:
        return row[0]

    # Not found -> create it
    stmt = (
        pg_insert(Skill)
        .values(name=skill_name, normalized_name=norm)
        .on_conflict_do_nothing(index_elements=["normalized_name"])
        .returning(Skill.id)
    )
    result = await session.execute(stmt)
    row = result.first()

    if row is not None:
        return row[0]

    # conflict happened — another concurrent task inserted this skill
    #    between our SELECT and INSERT. Re-fetch to get its id.
    existing = await session.execute(
        select(Skill.id).where(Skill.normalized_name == norm)
    )
    row = existing.first()

    if row is None:
        logger.error(
            f"get_or_create_skill: failed to resolve skill_id for '{skill_name}' after conflict"
        )
        raise RuntimeError(f"Could not resolve skill_id for skill_name={skill_name!r}")

    return row[0]
