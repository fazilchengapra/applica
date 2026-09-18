"""Celery critic stage for approving or regenerating a structured CV draft."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import update

from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.celery_db import get_celery_db_session
from app.modules.tailoring.critic.orchestrator import run_critic
from app.modules.tailoring.helpers.run_helpers import (
    fail_run,
    get_or_create_run,
    get_structured_cv_draft,
    load_strategy_brief,
    persist_critic_verdict,
    queue_writer_retry,
    release_stage_for_retry,
    try_claim_stage,
)
from app.modules.tailoring.helpers.upsert_tailored_cv import upsert_tailored_cv
from app.modules.tailoring.models import (
    StructuredCVDraft,
    TailoredCVStatus,
    TailoringRun,
    TailoringRunStatus,
    TailoringStage,
)

logger = logging.getLogger(__name__)


async def _prepare(user_id: int, job_id: UUID, cv_version_id: UUID):
    async with get_celery_db_session() as session:
        run, _ = await get_or_create_run(session, user_id, job_id, cv_version_id)
        claimed = await try_claim_stage(session, run.id, TailoringStage.critic)
        draft = strategy = None
        if claimed:
            draft = await get_structured_cv_draft(
                session, run.id
            )  # full row: cv_structure + cv_template_id
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


async def _complete(run_id: UUID, draft: StructuredCVDraft, verdict: dict) -> None:
    async with get_celery_db_session() as session:
        await upsert_tailored_cv(
            session,
            run_id=run_id,
            cv_structure=draft.content,
            critic_verdict=verdict,
            status=TailoredCVStatus.approved,
        )
        await session.execute(
            update(TailoringRun)
            .where(
                TailoringRun.id == run_id, TailoringRun.stage == TailoringStage.critic
            )
            .values(status=TailoringRunStatus.completed)
        )
        await session.commit()


async def _retry_writer(run_id: UUID, draft, verdict) -> None:
    async with get_celery_db_session() as session:
        await queue_writer_retry(session, run_id)
        await upsert_tailored_cv(
            session,
            run_id=run_id,
            cv_structure=draft.content,
            critic_verdict=verdict,
            status=TailoredCVStatus.approved,
        )
        await session.commit()


async def _fail_exhausted(
    run_id: UUID, draft: StructuredCVDraft, verdict: dict
) -> None:
    """Writer retries exhausted — persist the last rejected draft as a failed tailored_cv."""
    async with get_celery_db_session() as session:
        await upsert_tailored_cv(
            session,
            run_id=run_id,
            cv_structure=draft.content,
            critic_verdict=verdict,
            status=TailoredCVStatus.failed,
        )
        message = "; ".join(
            part
            for part in [
                verdict.get("reasoning", ""),
                "; ".join(verdict.get("issues", [])),
            ]
            if part
        )
        await fail_run(session, run_id, message)
        await session.commit()


async def _fail_crash(run_id: UUID, error_message: str) -> None:
    """Unhandled exception path — no reliable draft/verdict to persist, so just mark the run failed."""
    async with get_celery_db_session() as session:
        await fail_run(session, run_id, error_message)
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
            _critique(run_id, draft.content or {}, strategy or {})
        )
        logger.info("==================verdict==================== %s", verdict)
        if verdict["approved"]:
            asyncio.run(_complete(run_id, draft, verdict))
            return verdict

        # `critic_passes - 1` is the number of writer regenerations already
        # issued before this verdict; this permits exactly MAX_WRITER_RETRIES.
        if critic_passes - 1 < settings.MAX_WRITER_RETRIES:
            asyncio.run(_retry_writer(run_id, draft, verdict))
            from app.modules.tailoring.tasks.write_task import write_task

            write_task.delay(user_id, job_id, cv_version_id, None, None, verdict)
        else:
            asyncio.run(_fail_exhausted(run_id, draft, verdict))
        return verdict
    except Exception as exc:
        logger.exception("CV critic failed for run_id=%s", run_id)
        if run_id is not None and self.request.retries >= self.max_retries:
            asyncio.run(_fail_crash(run_id, str(exc)))
        elif run_id is not None:
            asyncio.run(_release(run_id, str(exc)))
        raise self.retry(exc=exc)
