# app/modules/matching/services.py
from uuid import UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.matching.models.job_match import JobMatch
from app.modules.matching.schemas.match_evaluation import MatchEvaluation


async def save_matches(
    db: AsyncSession, user_id: int, evaluated: list[tuple[UUID, MatchEvaluation]]
) -> None:
    for job_id, evaluation in evaluated:
        stmt = (
            pg_insert(JobMatch)
            .values(
                user_id=user_id,
                job_id=job_id,
                final_score=evaluation.relevance_score,
                llm_reasoning=evaluation.reasoning,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "job_id"],
                set_={
                    "final_score": evaluation.relevance_score,
                    "llm_reasoning": evaluation.reasoning,
                },
            )
        )
        await db.execute(stmt)
    await db.commit()
