"""Keyword-coverage scoring against the expected vocabulary for a target role.

Matching stays fully deterministic.  The vocabulary itself comes from the role
expansion service (an LLM call, cached per role); everything here is set
membership so the same inputs always yield the same score.
"""

import re

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.text import normalize
from app.modules.ats.rules.types import CheckResult


def _matcher(term: str):
    """Lookahead that tolerates punctuation-heavy terms such as ``C++``.

    ``\\b`` is unusable: ``C++`` ends on a non-word character, so the trailing
    boundary never matches and the term is reported as missing forever.
    """
    return re.compile(rf"(?<!\w){re.escape(term.strip())}(?!\w)", re.IGNORECASE)


def match_terms(terms: list[str], *corpora: str) -> tuple[list[str], list[str]]:
    """Split ``terms`` into the ones present in any corpus and the rest."""
    haystack = " \u2022 ".join(normalize(part) for part in corpora)
    matched, missing_terms = [], []
    for term in terms:
        cleaned = term.strip()
        if not cleaned:
            continue
        if _matcher(cleaned).search(haystack):
            matched.append(cleaned)
        else:
            missing_terms.append(cleaned)
    return matched, missing_terms


def check_keyword_coverage(
    expected_terms: list[str],
    raw_text: str,
    structured_skills: list[str],
) -> CheckResult:
    if not expected_terms:
        return CheckResult(
            id="role_keyword_coverage",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="Not checked",
            detail="No expected vocabulary could be built for this target role.",
        )

    matched, missing_terms = match_terms(expected_terms, raw_text, " \n ".join(structured_skills or []))
    score = len(matched) / len(expected_terms)
    missing_count = len(missing_terms)

    if missing_count == 0:
        value, detail = f"All {len(expected_terms)} matched", ""
    else:
        value = f"Add {missing_count} more"
        preview = ", ".join(missing_terms[:8])
        if missing_count > 8:
            preview += ", …"
        detail = f"Terms the role asks for that the CV never mentions: {preview}."

    if score >= 0.9:
        status = CheckStatus.PASS
    elif score >= 0.6:
        status = CheckStatus.WARN
    else:
        status = CheckStatus.FAIL

    return CheckResult(
        id="role_keyword_coverage",
        status=status,
        score=score,
        value=value,
        detail=detail,
        evidence={"matched": matched, "missing": missing_terms, "expected": len(expected_terms)},
    )
