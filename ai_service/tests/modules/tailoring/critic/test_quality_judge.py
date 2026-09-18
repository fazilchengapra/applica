from app.modules.tailoring.critic.helpers.quality_judge import (
    verify_artifacts,
    verify_keywords,
)


def _draft(**overrides):
    base = {
        "summary": "Software engineer focused on backend systems.",
        "skills": ["Python"],
        "experience": [
            {"company": "Acme Inc", "bullets": ["Built REST APIs in Python."]}
        ],
        "projects": [],
    }
    base.update(overrides)
    return base


def test_present_keyword_is_not_reported_missing():
    draft = _draft()
    strategy = {"keywords_to_weave": ["Python", "backend systems"]}
    present, missing = verify_keywords(draft, strategy)
    assert "python" in present
    assert "backend systems" in present
    assert missing == []


def test_absent_keyword_is_reported_missing():
    draft = _draft()
    strategy = {"keywords_to_weave": ["Python", "AI Engineer"]}
    present, missing = verify_keywords(draft, strategy)
    assert "python" in present
    assert missing == ["ai engineer"]


def test_truncated_summary_artifact_is_detected():
    draft = _draft(summary="Software engineer with a solid foundation in **")
    issues = verify_artifacts(draft)
    assert any("**" in issue for issue in issues)
    assert any("truncated" in issue for issue in issues)


def test_placeholder_template_is_detected():
    draft = _draft(summary="Led teams {{add_achievement}}.")
    issues = verify_artifacts(draft)
    assert any("placeholder" in issue for issue in issues)


def test_stray_markdown_in_experience_bullet_is_detected():
    draft = _draft(
        experience=[
            {"company": "Acme Inc", "bullets": ["Led platform **migration**."]}
        ]
    )
    issues = verify_artifacts(draft)
    assert any("experience" in issue and "**" in issue for issue in issues)


def test_clean_draft_has_no_artifacts():
    draft = _draft()
    assert verify_artifacts(draft) == []