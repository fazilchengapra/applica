import asyncio
import logging
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.celery_app import celery_app
from app.db.celery_db import get_celery_db_session
from app.modules.matching.repositories.profile_repository import (
    get_current_completed_cv,
)
from app.modules.tailoring.agents.evidence_matcher.agent import evidence_matcher_graph
from app.modules.tailoring.agents.evidence_matcher.prompts import SYSTEM_PROMPT
from app.modules.tailoring.helpers.run_helpers import (
    advance_stage,
    fail_run,
    get_or_create_run,
    save_evidence_matrix,
    try_claim_stage,
)
from app.modules.tailoring.models import TailoringStage
from app.modules.tailoring.tasks.strategize_task import strategize_task

logger = logging.getLogger(__name__)


async def _prepare(user_id: int, job_id: UUID):
    async with get_celery_db_session() as session:
        cv = await get_current_completed_cv(session, user_id)
        if cv is None:
            raise ValueError(f"No completed CV found for user_id={user_id}")

        run, _ = await get_or_create_run(session, user_id, job_id, cv.id)
        claimed = await try_claim_stage(session, run.id, TailoringStage.evidence_match)
        await session.commit()
        return run.id, run.stage, claimed, cv.id


async def _invoke_agent(user_id: int, job_id: str) -> dict:
    result = await evidence_matcher_graph.ainvoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "Evaluate the candidate's CV evidence against the job requirements.\n\n"
                        f"user_id={user_id}\n"
                        f"job_id={job_id}\n\n"
                        "IMPORTANT: Use exactly these IDs when calling tools. "
                        "Never guess, enumerate, or try different user IDs or job IDs."
                    )
                ),
            ],
            "user_id": user_id,
            "job_id": job_id,
            "tool_call_count": 0,
            "evidence_matrix": None,
        }
    )
    return result["evidence_matrix"].model_dump(mode="json")


async def _persist_success(run_id: UUID, evidence_matrix: dict) -> None:
    async with get_celery_db_session() as session:
        await save_evidence_matrix(session, run_id, evidence_matrix["items"])
        await advance_stage(session, run_id)
        await session.commit()


async def _persist_failure(run_id: UUID, error_message: str) -> None:
    async with get_celery_db_session() as session:
        await fail_run(session, run_id, error_message)
        await session.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def evidence_match_task(self, user_id: int, job_id: str) -> dict:
    """Build grounded CV evidence for one job, skipping if already done."""
    run_id, current_stage, claimed, cv_version_id = asyncio.run(
        _prepare(user_id, UUID(job_id))
    )

    if not claimed:
        if current_stage != TailoringStage.evidence_match:
            logger.info(
                "Evidence match already complete for run_id=%s (stage=%s); "
                "resuming downstream instead of re-running agent.",
                run_id,
                current_stage,
            )
            # A later stage previously failed and this task got redelivered.
            # Hand off to strategize_task, which will load the stored
            # evidence matrix and claim its own stage.
            strategize_task.delay(user_id, job_id, str(cv_version_id), None)
        else:
            logger.info(
                "Evidence match run_id=%s not claimable (already processing/completed).",
                run_id,
            )
        return {"skipped": True, "run_id": str(run_id)}

    try:
        evidence_matrix = asyncio.run(_invoke_agent(user_id, job_id))
        logger.info(
            "===================== evidence matrix =============================== %s",
            evidence_matrix,
        )
        asyncio.run(_persist_success(run_id, evidence_matrix))
        strategize_task.delay(user_id, job_id, str(cv_version_id), evidence_matrix)
        logger.info(
            "Generated evidence matrix and queued strategy for user_id=%s job_id=%s",
            user_id,
            job_id,
        )
        return evidence_matrix
    except Exception as exc:
        logger.exception(
            "Evidence matching failed for user_id=%s job_id=%s", user_id, job_id
        )
        if self.request.retries >= self.max_retries:
            asyncio.run(_persist_failure(run_id, str(exc)))
        raise self.retry(exc=exc)
