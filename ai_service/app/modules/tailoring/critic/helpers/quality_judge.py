import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.modules.tailoring.agents.base.llm_client import get_llm
from app.modules.tailoring.critic.schemas import QualityJudgment


_SYSTEM_PROMPT = """You are a strict CV quality reviewer. Assess the draft only for
the requested strategy: tone, section ordering, keyword coverage, conciseness, and
relevance. Do not assess factual grounding; that is performed separately. Return the
structured QualityJudgment with a 0-to-1 score and concise, actionable issues."""


async def judge_quality(cv_draft: dict, strategy: dict) -> QualityJudgment:
    llm = get_llm().with_structured_output(QualityJudgment)
    result = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"cv_draft:\n{json.dumps(cv_draft, indent=2)}\n\n"
                    f"strategy:\n{json.dumps(strategy, indent=2)}"
                )
            ),
        ]
    )
    return QualityJudgment.model_validate(result)
