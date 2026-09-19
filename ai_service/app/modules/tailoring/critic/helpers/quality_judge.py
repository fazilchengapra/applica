"""Pure-LLM CV quality reviewer for the writer<->critic loop.

No deterministic verification helpers. The critic observes the writer's draft
against the strategy (with evidence excerpts as grounding context) and decides
entirely by LLM judgment.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.modules.tailoring.agents.base.llm_client import get_llm
from app.modules.tailoring.critic.schemas import QualityJudgment

_SYSTEM_PROMPT = """You are a strict CV quality reviewer in a constant writer/review loop.

You will be given THREE inputs in every message:
1. cv_draft -- the exact structured CV the writer just produced. This is the
   object you are reviewing.
2. strategy -- the tailoring brief the writer was asked to follow.
3. evidence -- the real, verified evidence excerpts for the candidate.

Observe cv_draft closely and decide, on your own judgment, whether it satisfies
the strategy and is grounded in evidence. Return:

* quality_score: a single 0-to-1 number reflecting how well the draft meets the
  strategy and avoids defects.
* issues: a list of feedback items for the writer.

Rules for issues:
* Every issue must quote the exact section or bullet it refers to and state the
  concrete change to make. The writer receives only these issues as its revision
  instruction, so vague or hypothetical requests are useless.
* Never ask the writer to add information that is not present in both cv_draft
  and the evidence (URLs, dates, metrics, project details). Unavailable data is
  NOT a defect.
* Do not flag alternative-but-valid wording, section ordering, or presentation
  when the result is still clear, coherent, and valid.
* Do not demand repetition or "stronger emphasis" merely because something could
  be phrased more assertively. Only raise a deficiency you can concretely point to.
* Check grounding against the evidence: a claim that clearly outpaces what the
  cited evidence supports is a real defect.
* Flag malformed output: truncated sentences, placeholder text, stray markdown,
  or empty sections the strategy requires.

Score anchors:
* 0.90-1.00: strategy followed, complete, grounded, no malformed content -- approve.
* 0.80-0.89: minor fixable issues.
* 0.70-0.79: several meaningful issues.
* 0.50-0.69: major deviations or grounding problems.
* 0.00-0.49: fails to follow the strategy or has unsupported claims."""


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


async def judge_quality(
    cv_draft: dict, strategy: dict, evidence_items: list[dict] | None = None
) -> QualityJudgment:
    sections = [
        f"cv_draft (the object under review):\n{_json(cv_draft)}",
        f"strategy:\n{_json(strategy)}",
    ]
    if evidence_items:
        sections.append(
            "evidence (real, verified excerpts -- grounding context):\n"
            + _json(evidence_items)
        )

    llm = get_llm().with_structured_output(QualityJudgment)
    result = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content="\n\n".join(sections)),
        ]
    )
    return QualityJudgment.model_validate(result)