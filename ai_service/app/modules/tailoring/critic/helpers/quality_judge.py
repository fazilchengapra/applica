import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.modules.tailoring.agents.base.llm_client import get_llm
from app.modules.tailoring.critic.schemas import QualityJudgment

_SYSTEM_PROMPT = """You are a strict CV quality reviewer. Review cv_draft for quality and
completeness against the strategy and the candidate's real evidence.

Ground rules:

* The strategy guides content priorities, tone, emphasis, and required coverage, but it does
  NOT require any specific section ordering. Section order may vary freely as long as the CV
  remains coherent and complete.
* The strategy never authorizes fabrication. Never recommend content that the evidence does
  not support.
* NEVER ask the writer to add information that is absent from cv_draft AND the provided
  evidence (URLs, dates, specific numbers, project details). Unavailable data is NOT a defect.
* Never nitpick an alternative-but-valid presentation. Do not flag differences in section
  ordering, layout, wording, or presentation when the result is still clear, coherent, and valid.

Assess in priority order:

1. COMPLETENESS, STRUCTURE & SOUNDNESS (highest priority)

   * Do NOT evaluate or flag top-level section ordering. Any reasonable section order is valid.
   * Verify every relevant strategy expectation (lead_experiences, gaps_to_address,
     summary direction, and required content emphasis) is actually represented in the draft.
   * Catch hard defects: malformed, truncated, or placeholder output — stray markdown
     artifacts (e.g. "**"), a summary that cuts off mid-phrase, empty sections the strategy
     requires, canned/placeholder text. The deterministic artifact check and the deterministic
     keyword check below are authoritative — reflect them in your issues and score.

2. EVIDENCE GROUNDING & IMPACT

   * For each experience/project bullet, verify the claim (scope, numbers, outcome) is
     supported by the cited evidence excerpt. Flag overstatements and claims that outpace
     the evidence.
   * Value impact: bullets should state outcome/result where the evidence supports it.
     Flag bullets that merely restate duties when the evidence shows impact.

3. TONE, CONCISENESS, RELEVANCE

   * Identify repetition, verbosity, or off-strategy content. Do not penalize useful
     technical detail.
   * Do not request changes merely because another valid phrasing or presentation is possible.

4. KEYWORD COVERAGE (LAST resort, and only with factual backing)

   * Use ONLY the provided "Keyword verification" facts. A keyword listed as "already present"
     is covered — never report it as missing and never demand repetition.
   * Raise a keyword issue ONLY for keywords listed as "not found anywhere in draft", and only
     if that keyword can be grounded in the provided evidence.
   * Never recommend keyword stuffing or unnatural repetition.
   * Never report a keyword as missing if the same concept is already clearly represented
     elsewhere in the CV, even if the exact wording differs, unless the deterministic keyword
     verification explicitly says it is "not found anywhere in draft".

Every issue must be specific, actionable, supported, and fixable using only existing
draft and evidence content.

Do not flag:

* Section ordering differences.
* Alternative-but-valid wording.
* Alternative-but-valid formatting or presentation.
* Missing information that is unavailable in the draft and evidence.
* Repetition of information solely to satisfy a keyword when the concept is already clearly
  covered.

Gap handling role: 

* A strategy gap is considered addressed when the draft contains clear, relevant, evidence-supported content that covers the gap.
* Do NOT request additional emphasis, repetition, or stronger wording merely because a technology or theme could be mentioned more prominently.
* Once a gap is adequately represented in the summary, experience, projects, or skills, treat it as COVERED and do not raise another issue for it.
* Do not create subjective issues such as "could better emphasize", "could highlight more", or "could elaborate further" unless the strategy explicitly requires missing coverage that is not present in the draft.
* The critic must identify a concrete deficiency, not a hypothetical improvement.


Quality score anchors:

* 0.90-1.00: strategy followed, complete, grounded, no malformed content.
* 0.80-0.89: minor fixable issues.
* 0.70-0.79: several meaningful issues.
* 0.50-0.69: major deviations or grounding problems.
* 0.00-0.49: substantially fails to follow the strategy or has unverifiable claims.

Return the structured QualityJudgment with a 0-to-1 quality score and concise, actionable
issues."""


def _flatten_draft_text(cv_draft: dict) -> str:
    """Normalized lowercase text of every free-text field in the draft."""
    texts: list[str] = []

    def collect(value):
        if isinstance(value, str):
            texts.append(re.sub(r"\s+", " ", value).strip().casefold())
        elif isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(cv_draft)
    return " ".join(texts)


def verify_keywords(cv_draft: dict, strategy: dict) -> tuple[list[str], list[str]]:
    """Determine, deterministically, which strategy keywords appear literally in the
    draft text. Returns (already_present, not_found) so the reviewer never hallucinates
    a missing keyword that is actually in the CV."""
    keywords = [
        str(kw).casefold().strip()
        for kw in (strategy.get("keywords_to_weave") or [])
        if str(kw).strip()
    ]
    if not keywords:
        return [], []
    text = _flatten_draft_text(cv_draft)
    present = [kw for kw in keywords if kw in text]
    missing = [kw for kw in keywords if kw not in text]
    return present, missing


_ARTIFACT_PATTERNS = (
    (r"\*\*", "stray markdown artifact '**'"),
    (r"#{1,6}\S*", "markdown heading artifact"),
    (r"\{\{[^}]*\}\}", "template placeholder '{{...}}'"),
    (r"\b(TODO|TBD|XXX|lorem ipsum|lorem)\b", "placeholder text"),
)


def verify_artifacts(cv_draft: dict) -> list[str]:
    """Deterministic scan for malformed/truncated content the reviewer must not miss."""
    issues: list[str] = []
    for kind in ("summary",):
        value = cv_draft.get(kind)
        if isinstance(value, str) and value.strip():
            for pattern, label in _ARTIFACT_PATTERNS:
                if re.search(pattern, value, flags=re.IGNORECASE):
                    issues.append(f"summary contains {label}: {value.strip()[:120]!r}")
            if re.search(r"[,;:><|\-]$", value.strip()) or value.strip().endswith("**"):
                issues.append(
                    f"summary appears truncated (ends mid-phrase): {value.strip()[-80:]!r}"
                )
    for kind in ("experience", "projects"):
        for index, entry in enumerate(cv_draft.get(kind, []) or []):
            name = entry.get("company") or entry.get("name") or f"entry[{index}]"
            for bullet in entry.get("bullets") or []:
                if not bullet or not isinstance(bullet, str):
                    continue
                if bullet.strip().endswith("**") or re.search(r"\*\*", bullet):
                    issues.append(
                        f"{kind}[{index}] {name} bullet contains stray '**' artifact: "
                        f"{bullet.strip()[:120]!r}"
                    )
    return issues


async def judge_quality(
    cv_draft: dict, strategy: dict, evidence_items: list[dict] | None = None
) -> QualityJudgment:
    present_keywords, missing_keywords = verify_keywords(cv_draft, strategy)
    artifacts = verify_artifacts(cv_draft)

    sections = [
        f"cv_draft:\n{json.dumps(cv_draft, indent=2)}",
        f"strategy:\n{json.dumps(strategy, indent=2)}",
    ]
    if evidence_items:
        sections.append(
            "evidence (authoritative for factual grounding):\n"
            + json.dumps(evidence_items, indent=2)
        )
    sections.append(
        "Keyword verification (deterministic, authoritative):\n"
        f"- already present in draft: {present_keywords or 'none'}\n"
        f"- not found anywhere in draft text: {missing_keywords or 'none'}"
    )
    sections.append(
        "Deterministic artifact check (authoritative; reflect in issues/score):\n"
        + (json.dumps(artifacts, indent=2) if artifacts else "no artifacts found")
    )

    llm = get_llm().with_structured_output(QualityJudgment)
    result = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content="\n\n".join(sections)),
        ]
    )
    return QualityJudgment.model_validate(result)
