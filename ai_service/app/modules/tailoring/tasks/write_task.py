"""Celery stage that generates and persists structured CV content."""

import asyncio
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session
from app.modules.cv_template.repository import get_default_active
from app.modules.tailoring.agents.cv_writer.agent import run_cv_writer
from app.modules.tailoring.helpers.run_helpers import (
    advance_stage,
    fail_run,
    get_or_create_run,
    load_evidence_matrix,
    load_strategy_brief,
    release_stage_for_retry,
    save_structured_cv_draft,
    try_claim_stage,
    load_structured_cv_draft,
    load_critic_verdict
)
from app.modules.tailoring.models import StructuredCVDraft, TailoringStage
from app.modules.tailoring.tasks.critique_task import critique_task

logger = logging.getLogger(__name__)


async def _prepare(
    user_id: int,
    job_id: UUID,
    cv_version_id: UUID,
    evidence_matrix: dict[str, Any] | None,
    strategy_brief: dict[str, Any] | None,
) -> tuple[UUID, object, bool, dict[str, Any] | None, dict[str, Any] | None]:
    """Claim the write stage and load durable inputs on retries/resumes."""
    async with get_celery_db_session() as session:
        run, _ = await get_or_create_run(session, user_id, job_id, cv_version_id)
        claimed = await try_claim_stage(session, run.id, TailoringStage.write)

        # Durable data is the contract between pipeline stages.  In particular,
        # only this matrix contains the evidence_item_id values assigned by DB.
        matrix = None
        brief = None
        previous_draft = None
        critic_verdict = None
        if claimed:
            matrix = await load_evidence_matrix(session, run.id)
            brief = await load_strategy_brief(session, run.id)
            previous_draft = await load_structured_cv_draft(session, run.id)
            critic_verdict= await load_critic_verdict(session, run.id)

            if matrix is None or brief is None:
                await session.rollback()
                missing = "evidence matrix" if matrix is None else "strategy brief"
                raise ValueError(f"No stored {missing} for run_id={run.id}")

        await session.commit()
        return run.id, run.stage, claimed, matrix, brief, previous_draft, critic_verdict


async def _persist_success(
    run_id: UUID, cv_content: dict[str, Any], template_id: UUID | None = None
) -> None:
    async with get_celery_db_session() as session:
        if template_id is None:
            # None means "keep the previous pass's choice" (see
            # save_structured_cv_draft), so only seed the default on the very
            # first write. A critic retry re-runs this task without a
            # template_id and must not reset an explicit selection to default.
            seeded = await session.scalar(
                select(StructuredCVDraft.cv_template_id).where(
                    StructuredCVDraft.tailoring_run_id == run_id
                )
            )
            if seeded is None:
                template = await get_default_active(session)
                template_id = template.id if template else None
        await save_structured_cv_draft(session, run_id, cv_content, template_id)
        await advance_stage(session, run_id)
        await session.commit()


async def _persist_failure(run_id: UUID, error_message: str) -> None:
    async with get_celery_db_session() as session:
        await fail_run(session, run_id, error_message)
        await session.commit()


async def _release_for_retry(run_id: UUID, error_message: str) -> None:
    async with get_celery_db_session() as session:
        await release_stage_for_retry(
            session, run_id, TailoringStage.write, error_message
        )
        await session.commit()


@celery_app.task(
    bind=True,
    name="app.modules.tailoring.tasks.write_task.write_task",
    max_retries=3,
    default_retry_delay=60,
)
def write_task(
    self,
    user_id: int,
    job_id: str,
    cv_version_id: str,
    evidence_matrix: dict[str, Any] | None = None,
    strategy_brief: dict[str, Any] | None = None,
    critic_verdict: dict[str, Any] | None = None,
    template_id: str | None = None,
) -> dict[str, Any] | None:
    """Generate a grounded JSON CV and move the run to the critic stage.

    Upstream stages may pass their JSON results directly. When a Celery retry or
    resumed pipeline omits them, the task rebuilds both inputs from the database.
    ``template_id`` is the caller's template choice; when omitted the newest
    active template is attached.
    """
    logger.info("triggered")
    parsed_job_id = UUID(job_id)
    parsed_cv_version_id = UUID(cv_version_id)
    run_id: UUID | None = None

    try:
        run_id, current_stage, claimed, matrix, brief, previous_draft, critic_verdict = asyncio.run(
            _prepare(
                user_id,
                parsed_job_id,
                parsed_cv_version_id,
                evidence_matrix,
                strategy_brief,
            )
        )
        if not claimed:
            logger.info(
                "Writer run_id=%s not claimable (stage=%s); skipping.",
                run_id,
                current_stage,
            )
            return None

        cv_content = asyncio.run(
            run_cv_writer(
                evidence_matrix=matrix or {},
                strategy_brief=brief or {},
                user_id=user_id,
                job_id=str(parsed_job_id),
                cv_version_id=str(parsed_cv_version_id),
                critic_verdict=critic_verdict,
                previous_draft=previous_draft
            )
        )
        result = cv_content.model_dump(mode="json")
        logger.warning(result)
        asyncio.run(
            _persist_success(
                run_id, result, UUID(template_id) if template_id else None
            )
        )
        critique_task.delay(user_id, job_id, cv_version_id)
        logger.info("Generated structured CV content for run_id=%s", run_id)
        return result
    except Exception as exc:
        logger.exception(
            "CV writer failed for user_id=%s job_id=%s cv_version_id=%s",
            user_id,
            job_id,
            cv_version_id,
        )
        if run_id is not None and self.request.retries >= self.max_retries:
            asyncio.run(_persist_failure(run_id, str(exc)))
        elif run_id is not None:
            asyncio.run(_release_for_retry(run_id, str(exc)))
        raise self.retry(exc=exc)
