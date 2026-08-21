import asyncio
import logging

from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session

logger = logging.getLogger(__name__)

from app.modules.matching.service.profile_service import get_user_profile
from app.modules.matching.service.filter_jobs import prefilter_jobs
from app.modules.matching.repositories.vector_repository import (
    vector_retrieve,
    get_top_chunks_for_reranking,
)
from app.modules.matching.repositories.skill_repository import lexical_score
from app.modules.matching.service.fusion import reciprocal_rank_fusion
from app.modules.matching.service.reranking_service import rerank_with_llm


@celery_app.task()
def match_user_task(user_id: int):
    asyncio.run(_match_user(user_id))


async def _match_user(user_id: int):
    async with get_celery_db_session() as db:
        try:
            user = await get_user_profile(db, user_id)
            job_ids = await prefilter_jobs(db, user)

            if not job_ids:
                logger.info(f"No jobs survived pre-filter for user {user_id}")
                return

            vector_results = await vector_retrieve(db, user.cv_embedding, job_ids)
            lexical_scores = await lexical_score(
                db, user.skills, [j for j, _ in vector_results]
            )
            logger.info("lexical_scores: %s", lexical_scores)
            # top_20 = reciprocal_rank_fusion(vector_results, lexical_scores)

            # chunks = await get_top_chunks_for_reranking(
            #     db, user.cv_embedding, [j for j, _ in top_20]
            # )
            # evaluated = [
            #     (job_id, await rerank_with_llm(user.cv_text, chunks[job_id]))
            #     for job_id, _ in top_20
            #     if job_id in chunks
            # ]
            # print(evaluated)
            # await save_matches(db, user_id, evaluated)
            # logger.info(f"Matched user {user_id} against {len(evaluated)} jobs")

        except Exception:
            await db.rollback()
            logger.exception(f"Matching failed for user {user_id}")
            raise
