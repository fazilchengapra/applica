"""Public, typed entry point for the CV writer LangGraph."""

from app.modules.tailoring.agents.cv_strategist.schemas import StrategyBrief
from app.modules.tailoring.agents.cv_writer.graph import cv_writer_graph
from app.modules.tailoring.agents.cv_writer.schemas import CVContent
from app.modules.tailoring.agents.evidence_matcher.schemas import EvidenceMatrixOutput
from app.modules.tailoring.helpers.cv_draft_helpers import upsert_cv_draft


async def run_cv_writer(
    *,
    evidence_matrix: dict,
    strategy_brief: dict,
    user_id: int,
    job_id: str,
    cv_version_id: str,
    critic_verdict: dict | None = None,
    previous_draft: dict | None = None,
) -> CVContent:
    """Generate a validated renderer-ready tailored CV document."""
    matrix = EvidenceMatrixOutput.model_validate(evidence_matrix)
    brief = StrategyBrief.model_validate(strategy_brief)
    result = await cv_writer_graph.ainvoke(
        {
            "messages": [],
            "tailoring_run_id": "",
            "user_id": user_id,
            "job_id": job_id,
            "cv_version_id": cv_version_id,
            "evidence_matrix": matrix,
            "strategy_brief": brief.model_dump(mode="json"),
            "cv_metadata": None,
            "cv_content": None,
            "validation_errors": [],
            "revision_count": 0,
            "critic_verdict": critic_verdict,
            "previous_draft": previous_draft,
        }
    )

    draft = await upsert_cv_draft(
        session,
        tailoring_run_id=tailoring_run_id,
        cv_template_id=cv_template_id,
        cv_structure=cv_content.model_dump(mode="json"),
    )
    await session.commit()

    return CVContent.model_validate(result["cv_content"])
