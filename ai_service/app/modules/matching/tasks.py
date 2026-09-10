import asyncio
import logging

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session
from app.modules.master_cv.models.master_cv import CVStatus, MasterCV, MasterCVVersion

logger = logging.getLogger(__name__)

from app.modules.matching.services.profile_service import get_user_profile
from app.modules.matching.services.filter_jobs import prefilter_jobs
from app.modules.matching.repositories.vector_repository import (
    vector_retrieve,
    get_top_chunks_for_reranking,
)
from app.modules.matching.repositories.skill_repository import lexical_score
from app.modules.matching.services.fusion import reciprocal_rank_fusion
from app.modules.matching.services.reranking_service import rerank_with_llm
from app.modules.matching.services.save_matches_service import save_matches
from app.modules.tailoring.tasks.evidence_match_task import evidence_match_task


@celery_app.task()
def match_user_task(user_id: int):
    asyncio.run(_match_user(user_id))


@celery_app.task()
def daily_job_matching_task(batch_size: int = 50):
    asyncio.run(_dispatch_daily_job_matching(batch_size))


async def _dispatch_daily_job_matching(batch_size: int):
    offset = 0
    dispatched = 0

    async with get_celery_db_session() as db:
        while True:
            result = await db.execute(
                select(MasterCV.user_id)
                .join(MasterCVVersion, MasterCVVersion.master_cv_id == MasterCV.id)
                .where(
                    MasterCV.deleted_at.is_(None),
                    MasterCVVersion.is_current.is_(True),
                    MasterCVVersion.status == CVStatus.COMPLETED.value,
                )
                .distinct()
                .order_by(MasterCV.user_id)
                .limit(batch_size)
                .offset(offset)
            )
            user_ids = [row[0] for row in result.all()]
            if not user_ids:
                break

            for user_id in user_ids:
                match_user_task.delay(user_id)

            dispatched += len(user_ids)
            offset += len(user_ids)

    logger.info("Dispatched daily job matching for %s users", dispatched)


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

            top_20 = reciprocal_rank_fusion(vector_results, lexical_scores)

            chunks = await get_top_chunks_for_reranking(
                db, user.cv_embedding, [j for j, _ in top_20]
            )
            evaluated = [
                (job_id, await rerank_with_llm(user.cv_text, chunks[job_id]))
                for job_id, _ in top_20
                if job_id in chunks
            ]
            logger.info("evaluated: %s", evaluated)
            await save_matches(db, user_id, evaluated)
            logger.info(f"Matched user {user_id} against {len(evaluated)} jobs")

            for job_id, _ in evaluated:
                evidence_match_task.delay(user_id, str(job_id))

        except Exception as e:
            await db.rollback()
            logger.exception(f"Matching failed for user {user_id} error is: {e}")
            raise
