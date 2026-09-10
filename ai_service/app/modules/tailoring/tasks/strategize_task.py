import logging
import asyncio
from typing import Any

from app.core.celery_app import celery_app
from app.modules.tailoring.agents.cv_strategist.agent import run_strategist
from app.modules.tailoring.agents.evidence_matcher.tools import (
    get_cv_metadata,
    get_job_requirement_detail,
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def strategize_task(
    self, user_id: int, job_id: str, evidence_matrix: dict[str, Any]
) -> dict[str, Any]:
    """Turn a completed evidence matrix into a CV strategy brief.

    Job and candidate inputs are read for this exact user/job pair rather than
    supplied by the caller, preventing mismatched evidence and metadata.
    """

    async def _run() -> dict[str, Any]:
        job_detail = await get_job_requirement_detail.ainvoke({"job_id": job_id})
        candidate_metadata = await get_cv_metadata.ainvoke({"user_id": user_id})
        if not job_detail["found"]:
            raise ValueError(job_detail["error"])
        if not candidate_metadata["found"]:
            raise ValueError(candidate_metadata["error"])

        brief = await run_strategist(
            evidence_matrix=evidence_matrix,
            job_requirements=job_detail["requirements"],
            candidate_metadata=candidate_metadata,
        )
        return brief.model_dump(mode="json")

    try:
        strategy_brief = asyncio.run(_run())
        logger.info(
            "Generated CV strategy for user_id=%s job_id=%s", user_id, job_id
        )
        return strategy_brief
    except Exception as exc:
        logger.exception(
            "CV strategy generation failed for user_id=%s job_id=%s", user_id, job_id
        )
        raise self.retry(exc=exc)
