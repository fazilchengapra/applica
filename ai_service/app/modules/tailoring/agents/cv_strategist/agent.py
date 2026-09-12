import json

from langchain_core.messages import SystemMessage, HumanMessage

from ..base.llm_client import get_llm
from ..evidence_matcher.schemas import EvidenceMatrixOutput
from .schemas import StrategyBrief
from .prompts import STRATEGIST_SYSTEM_PROMPT


def _build_user_message(evidence_matrix: dict, job_requirements: list[dict], candidate_metadata: dict) -> str:
    return (
        f"Evidence matrix:\n{json.dumps(evidence_matrix, indent=2)}\n\n"
        f"Job requirements:\n{json.dumps(job_requirements, indent=2)}\n\n"
        f"Candidate metadata:\n{json.dumps(candidate_metadata, indent=2)}"
    )


async def run_strategist(
    evidence_matrix: dict,
    job_requirements: list[dict],
    candidate_metadata: dict,
) -> StrategyBrief:
    # The evidence matcher is the source of truth for claims the strategist may
    # surface. Validate its payload before it reaches the LLM.
    validated_evidence = EvidenceMatrixOutput.model_validate(evidence_matrix)
    llm = get_llm().with_structured_output(StrategyBrief)

    messages = [
        SystemMessage(content=STRATEGIST_SYSTEM_PROMPT),
        HumanMessage(
            content=_build_user_message(
                validated_evidence.model_dump(mode="json"),
                job_requirements,
                candidate_metadata,
            )
        ),
    ]

    result = await llm.ainvoke(messages)
    return StrategyBrief.model_validate(result)
