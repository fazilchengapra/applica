"""The single model call that judges the two genuinely semantic checks.

Everything else in this module is decided by rules.  These two questions --
"does this CV read as a fit for the role" and "is this figure an actual
achievement" -- have no reliable deterministic formulation, so they are asked
once per analysis as a batched structured call.

Every failure path returns ``None``; callers degrade instead of raising.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.llm_client import get_structured_llm
from app.modules.ats.rules.text import Bullet

logger = logging.getLogger(__name__)

_SYSTEM = """You are auditing one resume for one target role.

You will receive:
* target_role
* summary -- the candidate's own opening paragraph
* bullets -- the candidate's experience bullets, each with a unique ref

Return a verdict on two things.

1) role_aligned
true when the summary and the bullets together present a plausible fit for
target_role, judged only on the text supplied. false when the CV is plainly
aimed at a different field or level. Do not be generous: an unrelated role with
a few overlapping tools is false.

2) bullet_verdicts -- one entry for every ref you were given, and no others
real_impact is true only when the bullet attaches a specific measurable figure
to the OUTCOME or SCALE of the work: what improved and by how much, or how much
revenue, cost, time, traffic, latency or volume was involved.

real_impact is false when:
* the bullet contains no number at all
* the number is incidental -- a date, a product version, a page or ticket count,
  a years-of-experience claim
* the number is a headcount or team size with no outcome attached to it
* the figure is something the person did not influence

Never invent a figure that is not in the bullet. When genuinely uncertain, false.

Output one BulletVerdict per ref, in the order given."""


class BulletVerdict(BaseModel):
    ref: str
    real_impact: bool = Field(description="Whether the bullet quantifies a real outcome or scale.")
    reason: str = ""


class SemanticJudgment(BaseModel):
    role_aligned: bool
    role_alignment_reason: str = ""
    bullet_verdicts: list[BulletVerdict] = Field(default_factory=list)


async def judge_semantics(
    target_role: str,
    summary: str,
    bullets: list[Bullet],
) -> SemanticJudgment | None:
    bullet_lines = "\n".join(f"- ref={b.ref} :: {b.text}" for b in bullets)
    human = (
        f"target_role: {target_role}\n\n"
        f"summary: {summary or '(none)'}\n\n"
        f"bullets:\n{bullet_lines}"
    )

    try:
        llm = get_structured_llm(SemanticJudgment)
        result = await llm.ainvoke(
            [
                SystemMessage(content=_SYSTEM),
                HumanMessage(content=human),
            ]
        )
        judgment = SemanticJudgment.model_validate(result)
    except Exception as exc:
        logger.warning("Semantic judgment failed: %s", exc)
        return None

    valid_refs = {bullet.ref for bullet in bullets}
    judgment.bullet_verdicts = [
        verdict for verdict in judgment.bullet_verdicts if verdict.ref in valid_refs
    ]
    return judgment
