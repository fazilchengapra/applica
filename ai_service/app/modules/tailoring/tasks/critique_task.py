"""Celery critic stage for approving or regenerating a structured CV draft."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.celery_db import get_celery_db_session
from app.modules.tailoring.critic.orchestrator import run_critic
from app.modules.tailoring.helpers.run_helpers import (
    fail_run,
    get_or_create_run,
    load_strategy_brief,
    load_structured_cv_draft,
    persist_critic_verdict,
    queue_writer_retry,
    release_stage_for_retry,
    try_claim_stage,
)
from app.modules.tailoring.models import TailoringRunStatus, TailoringStage

logger = logging.getLogger(__name__)


async def _prepare(user_id: int, job_id: UUID, cv_version_id: UUID):
    async with get_celery_db_session() as session:
        run, _ = await get_or_create_run(session, user_id, job_id, cv_version_id)
        claimed = await try_claim_stage(session, run.id, TailoringStage.critic)
        draft = strategy = None
        if claimed:
            draft = await load_structured_cv_draft(session, run.id)
            strategy = await load_strategy_brief(session, run.id)
            if draft is None or strategy is None:
                raise ValueError(
                    f"No stored {'CV draft' if draft is None else 'strategy brief'} for run_id={run.id}"
                )
        await session.commit()
        return run.id, run.stage, claimed, draft, strategy


async def _critique(run_id: UUID, draft: dict, strategy: dict) -> tuple[dict, int]:
    async with get_celery_db_session() as session:
        verdict = await run_critic(session, run_id, draft, strategy)
        retry_count = await persist_critic_verdict(
            session, run_id, verdict.model_dump(mode="json")
        )
        await session.commit()
        return verdict.model_dump(mode="json"), retry_count


async def _complete(run_id: UUID) -> None:
    async with get_celery_db_session() as session:
        # The verdict was persisted before this terminal transition.
        from sqlalchemy import update
        from app.modules.tailoring.models import TailoringRun

        await session.execute(
            update(TailoringRun)
            .where(
                TailoringRun.id == run_id, TailoringRun.stage == TailoringStage.critic
            )
            .values(status=TailoringRunStatus.completed)
        )
        await session.commit()


async def _retry_writer(run_id: UUID) -> None:
    async with get_celery_db_session() as session:
        await queue_writer_retry(session, run_id)
        await session.commit()


async def _fail(run_id: UUID, issues: list[str], reasoning: str = "") -> None:
    async with get_celery_db_session() as session:
        message = "; ".join(part for part in [reasoning, "; ".join(issues)] if part)
        await fail_run(session, run_id, message)
        await session.commit()


async def _release(run_id: UUID, error: str) -> None:
    async with get_celery_db_session() as session:
        await release_stage_for_retry(session, run_id, TailoringStage.critic, error)
        await session.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def critique_task(
    self, user_id: int, job_id: str, cv_version_id: str
) -> dict[str, Any] | None:
    run_id: UUID | None = None
    try:
        run_id, stage, claimed, draft, strategy = asyncio.run(
            _prepare(user_id, UUID(job_id), UUID(cv_version_id))
        )
        if not claimed:
            logger.info(
                "Critic run_id=%s not claimable (stage=%s); skipping.", run_id, stage
            )
            return None

        verdict, critic_passes = asyncio.run(
            _critique(run_id, draft or {}, strategy or {})
        )
        logger.info("==================verdict==================== %s", verdict)
        if verdict["approved"]:
            asyncio.run(_complete(run_id))
            return verdict

        logger.info("====================== draft ============= %s", draft)

        # `critic_passes - 1` is the number of writer regenerations already
        # issued before this verdict; this permits exactly MAX_WRITER_RETRIES.
        if critic_passes - 1 < settings.MAX_WRITER_RETRIES:
            asyncio.run(_retry_writer(run_id))
            from app.modules.tailoring.tasks.write_task import write_task

            write_task.delay(user_id, job_id, cv_version_id, None, None, verdict)
        else:
            asyncio.run(_fail(run_id, verdict["issues"], verdict["reasoning"]))
        return verdict
    except Exception as exc:
        logger.exception("CV critic failed for run_id=%s", run_id)
        if run_id is not None and self.request.retries >= self.max_retries:
            asyncio.run(_fail(run_id, [str(exc)]))
        elif run_id is not None:
            asyncio.run(_release(run_id, str(exc)))
        raise self.retry(exc=exc)
