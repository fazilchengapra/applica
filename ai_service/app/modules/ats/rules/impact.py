"""Action-verb and metric-candidate detection.

The metric patterns only *find* candidates; deciding whether a figure is real
impact is a semantic judgement and lives in the semantic judge service.  When
that model is unavailable the candidate ratio is reported as an explicit lower
bound instead of being presented as a verified answer.
"""

import re

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.text import Bullet
from app.modules.ats.rules.types import CheckResult

METRIC_PATTERNS = (
    re.compile(r"\d+(?:\.\d+)?\s?%"),
    re.compile(r"[$€£]\s?\d[\d,.]*"),
    re.compile(r"\b\d[\d,.]*\s?(?:k|m|bn|x)\b", re.IGNORECASE),
    re.compile(r"\b\d{1,3}(?:,\d{3})+\b"),
    re.compile(r"\b\d+\+"),
    re.compile(r"\bin \d+(?:\.\d+)?\s?(?:ms|s|sec|hours?|days?|weeks?|months?|years?)\b", re.IGNORECASE),
)

ACTION_VERB_PREFIX = re.compile(r"^[A-Za-z]+")

ACTION_VERBS = frozenset(
    """
    achieved acquired adapted administered advanced architected authored automated
    accelerated analyzed architected audited built benchmarked briefed brought
    calibrated championed cleared coached compiled completed composed conceived
    conducted configured consolidated constructed consulted containerized converted
    coordinated corrected cut delivered deployed deprecated designed detected
    determined developed directed discovered dispatched documented drove doubled
    engineered enhanced ensured established evaluated evolved exceeded executed
    expanded expedited facilitated fixed forecast formulated founded generated
    launched led migrated modeled negotiated normalized onboarded optimized
    orchestrated overhauled partnered piloted pitched planned predicted prevented
    presented prioritized produced programmed proposed published quantified reduced
    rebuilt recommended reconstructed recovered refactored regulated released
    reorganized replaced rescued resolved restructured revitalized rewrote
    scaled secured shipped simplified solved spearheaded standardised standardized
    streamlined strengthened structured supervised surveyed sustained tackled
    tested trained transferred transformed unified united updated upgraded validated
    verified won wrote
    """.split()
)


def metric_candidate_bullets(bullets: list[Bullet]) -> list[Bullet]:
    return [bullet for bullet in bullets if any(p.search(bullet.text) for p in METRIC_PATTERNS)]


def _first_word(text: str) -> str:
    match = ACTION_VERB_PREFIX.match(text.strip())
    return match.group(0).lower() if match else ""


def check_action_verbs(bullets: list[Bullet]) -> CheckResult:
    if not bullets:
        return CheckResult(
            id="action_verbs",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="No bullets",
            detail="No experience bullets were parsed, so verb usage cannot be measured.",
        )

    weak = [b.ref for b in bullets if _first_word(b.text) not in ACTION_VERBS]
    strong_ratio = (len(bullets) - len(weak)) / len(bullets)

    if not weak:
        value, detail, status = "All bullets", "", CheckStatus.PASS
    elif strong_ratio >= 0.7:
        value = f"{len(bullets) - len(weak)} of {len(bullets)}"
        detail = "Most bullets open with a strong verb; the rest start with filler such as 'Responsible for' or 'Worked on'."
        status = CheckStatus.WARN
    else:
        value = f"Only {len(bullets) - len(weak)} of {len(bullets)}"
        detail = "Bullets should open with a result verb. Passive openings are parsed but read as filler."
        status = CheckStatus.FAIL if strong_ratio < 0.5 else CheckStatus.WARN

    return CheckResult(
        id="action_verbs",
        status=status,
        score=strong_ratio,
        value=value,
        detail=detail,
        evidence={"weak_refs": weak[:10]},
    )
