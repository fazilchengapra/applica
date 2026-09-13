import asyncio
import logging
from typing import Any
from uuid import UUID

from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session
from app.modules.tailoring.agents.cv_strategist.agent import run_strategist
from app.modules.tailoring.agents.evidence_matcher.tools import (
    get_cv_metadata,
    get_job_requirement_detail,
)
from app.modules.tailoring.helpers.run_helpers import (
    advance_stage,
    fail_run,
    get_or_create_run,
    load_evidence_matrix,
    save_strategy_brief,
    try_claim_stage,
)
from app.modules.tailoring.models import TailoringStage

logger = logging.getLogger(__name__)


async def _prepare(
    user_id: int, job_id: UUID, cv_version_id: UUID, evidence_matrix: dict | None
):
    async with get_celery_db_session() as session:
        run, _ = await get_or_create_run(session, user_id, job_id, cv_version_id)
        claimed = await try_claim_stage(session, run.id, TailoringStage.strategy)

        matrix = evidence_matrix
        if claimed and matrix is None:
            matrix = await load_evidence_matrix(session, run.id)
            if matrix is None:
                await session.rollback()
                raise ValueError(f"No stored evidence matrix for run_id={run.id}")

        await session.commit()
        return run.id, run.stage, claimed, matrix


async def _persist_success(run_id: UUID, brief: dict) -> None:
    async with get_celery_db_session() as session:
        await save_strategy_brief(session, run_id, brief)
        await advance_stage(session, run_id)
        await session.commit()


async def _persist_failure(run_id: UUID, error_message: str) -> None:
    async with get_celery_db_session() as session:
        await fail_run(session, run_id, error_message)
        await session.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def strategize_task(
    self,
    user_id: int,
    job_id: str,
    cv_version_id: str,
    evidence_matrix: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Turn a completed evidence matrix into a CV strategy brief."""
    run_id, current_stage, claimed, matrix = asyncio.run(
        _prepare(user_id, UUID(job_id), UUID(cv_version_id), evidence_matrix)
    )

    if not claimed:
        logger.info(
            "Strategy run_id=%s not claimable (stage=%s) — already processing/completed.",
            run_id,
            current_stage,
        )
        return None

    async def _run() -> dict[str, Any]:
        job_detail = await get_job_requirement_detail.ainvoke({"job_id": job_id})
        candidate_metadata = await get_cv_metadata.ainvoke({"user_id": user_id})
        if not job_detail["found"]:
            raise ValueError(job_detail["error"])
        if not candidate_metadata["found"]:
            raise ValueError(candidate_metadata["error"])

        brief = await run_strategist(
            evidence_matrix=matrix,
            job_requirements=job_detail["requirements"],
            candidate_metadata=candidate_metadata,
        )
        return brief.model_dump(mode="json")

    try:
        strategy_brief = asyncio.run(_run())
        asyncio.run(_persist_success(run_id, strategy_brief))
        logger.info("Generated CV strategy for user_id=%s job_id=%s", user_id, job_id)
        # next: write_task.delay(user_id, job_id, cv_version_id, strategy_brief)
        return strategy_brief
    except Exception as exc:
        logger.exception(
            "CV strategy generation failed for user_id=%s job_id=%s", user_id, job_id
        )
        if self.request.retries >= self.max_retries:
            asyncio.run(_persist_failure(run_id, str(exc)))
        raise self.retry(exc=exc)
