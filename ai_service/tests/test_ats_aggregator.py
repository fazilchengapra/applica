"""Score arithmetic and the insight-card contract.

The score is the product: a weighted sum on a single 0-100 scale. Three
properties are cheap to break and impossible to notice from the UI, so they are
pinned here -- skipped checks must not lower the score, the weight-zero integrity
check must not move it either, and the insight rows must keep exactly the
``{label, value, done}`` shape the client renders.
"""

from app.modules.ats.constants import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    CHECK_SPECS,
    CheckStatus,
)
from app.modules.ats.rules.types import CheckResult, skipped
from app.modules.ats.services.score_aggregator import aggregate, compute_score


def _pass(check_id: str) -> CheckResult:
    return CheckResult(id=check_id, status=CheckStatus.PASS, score=1.0, value="ok")


def _all_passing():
    return [_pass(spec.id) for spec in CHECK_SPECS]


def _find(results, check_id):
    return next(r for r in results if r.id == check_id)


def test_weights_add_up_to_exactly_one_hundred():
    """A drifted weight changes every stored score without any code changing."""
    assert sum(spec.weight for spec in CHECK_SPECS) == 100
    assert sum(spec.weight for spec in CHECK_SPECS if spec.category != "integrity") == 100


def test_every_catalogue_check_is_reachable_from_the_insight_categories():
    categories = {spec.category for spec in CHECK_SPECS}
    assert categories == set(CATEGORY_ORDER)
    assert all(label for label in CATEGORY_LABELS.values())


def test_a_fully_passing_cv_scores_one_hundred():
    score, insights = aggregate(_all_passing())
    assert score == 100
    assert all(insight.done for insight in insights)


def test_insight_rows_match_the_ui_contract():
    _, insights = aggregate(_all_passing())

    assert [insight.label for insight in insights] == [
        CATEGORY_LABELS[category] for category in CATEGORY_ORDER
    ]
    for insight in insights:
        assert set(insight.model_dump()) == {"label", "value", "done"}
        assert isinstance(insight.done, bool)
        assert insight.value


def test_skipped_checks_are_excluded_from_the_denominator():
    """A PDF that could not be fetched must cost the user nothing."""
    baseline, _ = aggregate(_all_passing())

    degraded = [r for r in _all_passing() if r.category != "parsability"]
    degraded += [
        skipped("parsable_text_layer", "no pdf"),
        skipped("single_column", "no pdf"),
        skipped("page_count", "no pdf"),
    ]

    score, insights = aggregate(degraded)
    assert score == baseline == 100
    parsability = next(i for i in insights if i.label == CATEGORY_LABELS["parsability"])
    assert parsability.value == "Not checked"
    assert parsability.done is False


def test_an_everything_skipped_report_scores_zero_rather_than_one_hundred():
    results = [skipped(spec.id, "unavailable") for spec in CHECK_SPECS]
    score, _ = aggregate(results)
    assert score == 0


def test_the_weight_zero_integrity_check_never_moves_the_score():
    baseline, _ = aggregate(_all_passing())

    broken = [r for r in _all_passing() if r.id != "data_integrity"]
    broken.append(
        CheckResult(
            id="data_integrity",
            status=CheckStatus.FAIL,
            score=0.0,
            value="Only 1 of 4 matched",
        )
    )

    score, insights = aggregate(broken)
    assert score == baseline
    integrity = next(i for i in insights if i.label == CATEGORY_LABELS["integrity"])
    assert integrity.done is False
    assert integrity.value == "Only 1 of 4 matched"


def test_a_failure_costs_exactly_its_weight():
    results = _all_passing()
    contact_email = _find(results, "contact_email")
    results[results.index(contact_email)] = CheckResult(
        id="contact_email", status=CheckStatus.FAIL, score=0.0, value="Email missing"
    )

    assert compute_score(results) == 98


def test_contact_value_names_the_single_field_that_is_wrong():
    results = _all_passing()
    results[results.index(_find(results, "contact_phone"))] = CheckResult(
        id="contact_phone", status=CheckStatus.FAIL, score=0.0, value="Phone missing"
    )

    _, insights = aggregate(results)
    contact = next(i for i in insights if i.label == CATEGORY_LABELS["contact"])
    assert contact.value == "Phone missing"
    assert contact.done is False


def test_contact_value_counts_when_several_fields_are_wrong():
    results = [
        CheckResult(id=spec.id, status=CheckStatus.FAIL, score=0.0, value="missing")
        for spec in CHECK_SPECS
        if spec.category == "contact"
    ] + [r for r in _all_passing() if r.category != "contact"]

    _, insights = aggregate(results)
    contact = next(i for i in insights if i.label == CATEGORY_LABELS["contact"])
    assert contact.value == "5 fields need attention"


def test_keyword_value_states_how_many_terms_are_missing():
    results = _all_passing()
    results[results.index(_find(results, "role_keyword_coverage"))] = CheckResult(
        id="role_keyword_coverage",
        status=CheckStatus.FAIL,
        score=0.5,
        value="Add 3 more",
    )

    _, insights = aggregate(results)
    keywords = next(i for i in insights if i.label == CATEGORY_LABELS["keywords"])
    assert keywords.value == "Add 3 more"
    assert keywords.done is False


def test_a_weak_role_fit_overrides_a_perfect_keyword_score():
    """100% keyword coverage with a failed alignment is still a bad match."""
    results = _all_passing()
    results[results.index(_find(results, "role_alignment"))] = CheckResult(
        id="role_alignment", status=CheckStatus.FAIL, score=0.0, value="Weak role fit"
    )

    _, insights = aggregate(results)
    keywords = next(i for i in insights if i.label == CATEGORY_LABELS["keywords"])
    assert keywords.value == "Weak role fit"
    assert keywords.done is False


def test_semantic_verdicts_drive_the_impact_value():
    results = _all_passing()
    results[results.index(_find(results, "impact_statements"))] = CheckResult(
        id="impact_statements", status=CheckStatus.PASS, score=0.8, value="Strong"
    )

    _, insights = aggregate(results)
    impact = next(i for i in insights if i.label == CATEGORY_LABELS["impact"])
    assert impact.value == "Strong"
    assert impact.done is True


def test_the_score_stays_on_a_single_zero_to_one_hundred_scale():
    """JobMatch.final_score is documented as both 0-1 and 0-100; do not repeat it."""
    worst = [
        CheckResult(id=spec.id, status=CheckStatus.FAIL, score=0.0, value="bad")
        for spec in CHECK_SPECS
    ]
    assert compute_score(worst) == 0

    half = []
    for spec in CHECK_SPECS:
        half.append(
            CheckResult(id=spec.id, status=CheckStatus.WARN, score=0.5, value="meh")
        )
    assert 0 < compute_score(half) < 100
