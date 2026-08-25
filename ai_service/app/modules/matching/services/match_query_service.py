from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.matching.models.job_match import JobMatch, MatchStatus


async def get_matches_for_user(
    db: AsyncSession,
    user_id: int,
    status_filter: MatchStatus | None = None,
    min_score: float | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[JobMatch]:
    query = select(JobMatch).where(JobMatch.user_id == user_id)

    if status_filter is not None:
        query = query.where(JobMatch.status == status_filter)
    if min_score is not None:
        query = query.where(JobMatch.final_score >= min_score)

    query = query.order_by(JobMatch.final_score.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_match_by_id(db: AsyncSession, match_id: UUID, user_id: int) -> JobMatch | None:
    query = select(JobMatch).where(
        JobMatch.id == match_id,
        JobMatch.user_id == user_id,  # ownership check — never trust match_id alone
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_match_status(
    db: AsyncSession, match_id: UUID, user_id: int, new_status: MatchStatus
) -> JobMatch | None:
    match = await get_match_by_id(db, match_id, user_id)
    if match is None:
        return None

    match.status = new_status
    await db.commit()
    await db.refresh(match)
    return match


async def delete_match(db: AsyncSession, match_id: UUID, user_id: int) -> bool:
    stmt = delete(JobMatch).where(
        JobMatch.id == match_id,
        JobMatch.user_id == user_id,
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0