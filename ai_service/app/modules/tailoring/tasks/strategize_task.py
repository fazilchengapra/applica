"""Celery stage that turns grounded evidence into a CV tailoring strategy."""

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
    release_stage_for_retry,
    save_strategy_brief,
    try_claim_stage,
)
from app.modules.tailoring.models import TailoringStage
from app.modules.tailoring.tasks.write_task import write_task

logger = logging.getLogger(__name__)


async def _prepare(
    user_id: int, job_id: UUID, cv_version_id: UUID, evidence_matrix: dict | None
):
    async with get_celery_db_session() as session:
        run, _ = await get_or_create_run(session, user_id, job_id, cv_version_id)
        claimed = await try_claim_stage(session, run.id, TailoringStage.strategy)

        # Evidence IDs are assigned only by save_evidence_matrix.  Always use
        # the committed copy, never an upstream Celery payload.
        matrix = None
        if claimed:
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


async def _release_for_retry(run_id: UUID, error_message: str) -> None:
    async with get_celery_db_session() as session:
        await release_stage_for_retry(session, run_id, TailoringStage.strategy, error_message)
        await session.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def strategize_task(
    self,
    user_id: int,
    job_id: str,
    cv_version_id: str,
    evidence_matrix: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Turn a completed evidence matrix into a persisted CV strategy brief."""
    run_id, current_stage, claimed, matrix = asyncio.run(
        _prepare(user_id, UUID(job_id), UUID(cv_version_id), evidence_matrix)
    )

    if not claimed:
        logger.info(
            "Strategy run_id=%s not claimable (stage=%s); skipping.",
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
            evidence_matrix=matrix or {},
            job_requirements=job_detail["requirements"],
            candidate_metadata=candidate_metadata,
        )
        return brief.model_dump(mode="json")

    try:
        strategy_brief = asyncio.run(_run())
        asyncio.run(_persist_success(run_id, strategy_brief))
        # The writer consumes the database snapshots, which include persisted
        # evidence-item IDs needed by its citation audit.
        write_task.delay(user_id, job_id, cv_version_id, None, None)
        logger.info("Generated strategy brief for run_id=%s", run_id)
        return strategy_brief
    except Exception as exc:
        logger.exception("CV strategy generation failed for run_id=%s", run_id)
        if self.request.retries >= self.max_retries:
            asyncio.run(_persist_failure(run_id, str(exc)))
        else:
            asyncio.run(_release_for_retry(run_id, str(exc)))
        raise self.retry(exc=exc)
