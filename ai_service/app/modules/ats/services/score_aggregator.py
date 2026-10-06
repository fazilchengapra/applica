"""Fold individual check results into the report score and the insight card.

The score is a plain weighted sum over checks that actually ran: a skipped
check contributes nothing to the numerator *and* is removed from the
denominator, so degrading gracefully costs the user nothing. Nothing here
touches a model or the database -- given the same results this always produces
the same number.
"""

from app.modules.ats.constants import CATEGORY_LABELS, CATEGORY_ORDER, CheckStatus, CHECKS_BY_ID
from app.modules.ats.rules.types import CheckResult
from app.modules.ats.schemas import InsightOut

_SEVERITY = {
    CheckStatus.FAIL: 3,
    CheckStatus.WARN: 2,
    CheckStatus.PASS: 1,
    CheckStatus.SKIPPED: 0,
}


def compute_score(results: list[CheckResult]) -> int:
    scored = [r for r in results if r.status is not CheckStatus.SKIPPED]
    denominator = sum(r.weight for r in scored)
    if denominator <= 0:
        return 0
    earned = sum(r.weight * r.score for r in scored)
    return round(100 * earned / denominator)


def _worst(results: list[CheckResult]) -> CheckStatus | None:
    active = [r for r in results if r.status is not CheckStatus.SKIPPED]
    if not active:
        return None
    return max((r.status for r in active), key=lambda s: _SEVERITY[s])


def _group(results: list[CheckResult]) -> dict[str, list[CheckResult]]:
    grouped: dict[str, list[CheckResult]] = {}
    for result in results:
        grouped.setdefault(result.category, []).append(result)
    return grouped


def _contact_value(results: list[CheckResult]) -> str:
    bad = [r for r in results if r.status in (CheckStatus.FAIL, CheckStatus.WARN)]
    if not bad:
        return "Complete"
    if len(bad) == 1:
        return bad[0].value
    return f"{len(bad)} fields need attention"


def _count_value(results: list[CheckResult], complete: str, noun: str) -> str:
    bad = [r for r in results if r.status in (CheckStatus.FAIL, CheckStatus.WARN)]
    if not bad:
        return complete
    if len(bad) == 1:
        return bad[0].value
    return f"{len(bad)} {noun}"


def _keywords_value(results: list[CheckResult]) -> str:
    coverage = next((r for r in results if r.id == "role_keyword_coverage"), None)
    alignment = next((r for r in results if r.id == "role_alignment"), None)

    if coverage is not None and coverage.status is not CheckStatus.SKIPPED:
        if alignment is not None and alignment.status is CheckStatus.FAIL:
            return "Weak role fit"
        return coverage.value
    if alignment is not None and alignment.status is not CheckStatus.SKIPPED:
        return alignment.value
    return "Not checked"


def _category_value(category: str, results: list[CheckResult]) -> str:
    if not results or _worst(results) is None:
        return "Not checked"

    if category == "contact":
        return _contact_value(results)
    if category == "keywords":
        return _keywords_value(results)
    if category == "sections":
        return _count_value(results, "All sections", "sections need attention")
    if category == "structure":
        return _count_value(results, "Clean", "issues")
    if category == "impact":
        primary = next((r for r in results if r.id == "impact_statements"), None)
        return primary.value if primary else "Not checked"
    if category == "parsability":
        if _worst(results) is CheckStatus.PASS:
            return "Parseable"
        bad = [r for r in results if r.status in (CheckStatus.FAIL, CheckStatus.WARN)]
        if len(bad) == 1:
            return bad[0].value
        return f"{len(bad)} layout issues"
    if category == "integrity":
        primary = next((r for r in results if r.id == "data_integrity"), None)
        return primary.value if primary else "Not checked"
    return "Not checked"


def build_insights(results: list[CheckResult]) -> list[InsightOut]:
    grouped = _group(results)
    insights: list[InsightOut] = []
    for category in CATEGORY_ORDER:
        category_results = grouped.get(category, [])
        if not category_results:
            continue
        status = _worst(category_results)
        insights.append(
            InsightOut(
                label=CATEGORY_LABELS[category],
                value=_category_value(category, category_results),
                done=status is CheckStatus.PASS,
            )
        )
    return insights


def aggregate(results: list[CheckResult]) -> tuple[int, list[InsightOut]]:
    return compute_score(results), build_insights(results)


_CHECK_ORDER = {spec.id: index for index, spec in enumerate(CHECKS_BY_ID.values())}


def check_sort_key(result: CheckResult) -> tuple[int, int]:
    return _CHECK_ORDER.get(result.id, len(_CHECK_ORDER)), len(result.id)
