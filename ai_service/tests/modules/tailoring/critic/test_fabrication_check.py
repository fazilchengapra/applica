from app.modules.tailoring.critic.helpers.fabrication_check import check_fabrication


MET_ITEM = {
    "id": "11111111-1111-1111-1111-111111111111",
    "requirement": "Build REST APIs",
    "status": "met",
    "confidence": 0.95,
    "excerpt": "Built REST APIs using FastAPI.",
}
PARTIAL_ITEM = {
    "id": "22222222-2222-2222-2222-222222222222",
    "requirement": "Kubernetes production operations",
    "status": "partial",
    "confidence": 0.5,
    "excerpt": "Had limited exposure to Kubernetes.",
}
NOT_MET_ITEM = {
    "id": "33333333-3333-3333-3333-333333333333",
    "requirement": "AWS architecture",
    "status": "not_met",
    "confidence": 0.0,
    "excerpt": None,
}


def _draft(ids, bullet="Built REST APIs.", *, skills=None, technologies=None):
    return {
        "experience": [
            {
                "company": "Bridgeon Solutions LLP",
                "bullets": [bullet],
                "evidence_item_ids": ids,
                "technologies": technologies or [],
            }
        ],
        "projects": [],
        "skills": skills or [],
    }


def test_empty_evidence_ids_is_a_high_severity_reference_flag():
    flags = check_fabrication(_draft([]), [MET_ITEM], {})
    assert any(flag.field == "evidence_ref" and flag.severity == "high" for flag in flags)


def test_nonexistent_evidence_id_is_a_high_severity_flag():
    flags = check_fabrication(_draft(["missing-id"]), [MET_ITEM], {})
    assert any(flag.claim == "missing-id" and flag.severity == "high" for flag in flags)


def test_not_met_evidence_cannot_support_a_bullet():
    flags = check_fabrication(_draft([NOT_MET_ITEM["id"]]), [NOT_MET_ITEM], {})
    assert any(flag.field == "bullet" and flag.severity == "high" for flag in flags)


def test_unhedged_partial_gap_claim_is_high_severity():
    flags = check_fabrication(
        _draft([PARTIAL_ITEM["id"]], "Led Kubernetes production operations."),
        [PARTIAL_ITEM],
        {"gaps_to_address": [PARTIAL_ITEM["requirement"]]},
    )
    assert any(flag.field == "bullet" and flag.severity == "high" for flag in flags)


def test_hedged_partial_gap_claim_is_allowed():
    flags = check_fabrication(
        _draft([PARTIAL_ITEM["id"]], "Gained exposure to Kubernetes production operations."),
        [PARTIAL_ITEM],
        {"gaps_to_address": [PARTIAL_ITEM["requirement"]]},
    )
    assert not any(flag.field == "bullet" for flag in flags)


def test_met_evidence_supports_a_bullet():
    flags = check_fabrication(_draft([MET_ITEM["id"]]), [MET_ITEM], {})
    assert not flags


def test_skills_and_technologies_are_not_checked_until_evidence_supports_them():
    flags = check_fabrication(_draft([MET_ITEM["id"]], skills=["Terraform"]), [MET_ITEM], {})
    assert flags == []


def test_clean_draft_has_zero_flags():
    flags = check_fabrication(
        _draft([MET_ITEM["id"]], skills=["Python"], technologies=["FastAPI"]),
        [MET_ITEM],
        {},
    )
    assert flags == []


def test_bullet_ignores_an_unrelated_not_met_citation_in_the_same_entry():
    flags = check_fabrication(
        _draft(
            [MET_ITEM["id"], NOT_MET_ITEM["id"]],
            "Built REST APIs for authentication services.",
        ),
        [MET_ITEM, NOT_MET_ITEM],
        {},
    )
    assert not any(flag.field == "bullet" for flag in flags)
