"""Cross-validate the LLM-produced ``parsed_data`` against the source text.

The structuring pass can hallucinate or drop fields.  Every claim that looks
like a strength here should be corroborated by the string actually appearing in
the extracted PDF text; when it does not, the real defect is our parsing, not
the candidate's CV -- so this carries weight 0 and is reported, never scored.
"""

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.text import normalize
from app.modules.ats.rules.types import CheckResult


def _claims(parsed: dict) -> list[tuple[str, str]]:
    claims: list[tuple[str, str]] = []
    summary = parsed.get("summary")
    if isinstance(summary, str) and summary.strip():
        claims.append(("summary", normalize(summary)[:120]))

    for index, entry in enumerate(parsed.get("experience") or []):
        if not isinstance(entry, dict):
            continue
        for key in ("company", "title"):
            value = normalize(entry.get(key))
            if value:
                claims.append((f"experience[{index}].{key}", value))

    for index, skill in enumerate(parsed.get("skills") or []):
        value = normalize(skill)
        if value and len(value) > 2:
            claims.append((f"skills[{index}]", value))

    return claims


def check_data_integrity(parsed: dict, raw_text: str) -> CheckResult:
    claims = _claims(parsed)
    if not claims:
        return CheckResult(
            id="data_integrity",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="Not checked",
            detail="No structured content was produced, so there is nothing to corroborate.",
        )

    haystack = normalize(raw_text)
    if not haystack:
        return CheckResult(
            id="data_integrity",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="Not checked",
            detail="The uploaded PDF produced no extractable text, so the source cannot be compared.",
        )

    unmatched = [path for path, value in claims if value not in haystack]
    matched_count = len(claims) - len(unmatched)
    score = matched_count / len(claims)

    if not unmatched:
        return CheckResult(
            id="data_integrity",
            status=CheckStatus.PASS,
            score=1.0,
            value="Consistent",
            detail="",
            evidence={"claims": len(claims)},
        )

    if score >= 0.7:
        status, value = CheckStatus.WARN, f"{matched_count} of {len(claims)} matched"
        detail = "Some parsed entries do not appear in the source text. Re-upload if the CV looks wrong after parsing."
    else:
        status = CheckStatus.FAIL
        value = f"Only {matched_count} of {len(claims)} matched"
        detail = "Most parsed content was not found in the source PDF. The parsing pass likely misread this file."

    return CheckResult(
        id="data_integrity",
        status=status,
        score=score,
        value=value,
        detail=detail,
        evidence={"unmatched": unmatched[:10], "claims": len(claims)},
    )
