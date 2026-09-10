import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.celery_app import celery_app
from app.modules.tailoring.agents.evidence_matcher.agent import evidence_matcher_graph
from app.modules.tailoring.agents.evidence_matcher.prompts import SYSTEM_PROMPT
from app.modules.tailoring.tasks.strategize_task import strategize_task

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def evidence_match_task(self, user_id: int, job_id: str) -> dict:
    """Build grounded CV evidence for one persisted job match."""

    async def _run() -> dict:
        result = await evidence_matcher_graph.ainvoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(
                        content=(
                            "Evaluate the candidate's CV evidence against the "
                            f"requirements for job_id={job_id}."
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

    try:
        evidence_matrix = asyncio.run(_run())
        strategize_task.delay(user_id, job_id, evidence_matrix)
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
        raise self.retry(exc=exc)
