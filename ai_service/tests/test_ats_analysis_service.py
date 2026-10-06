"""Orchestration tests for ATS analysis -- no database, no model, no S3.

The scenario that matters most is total model outage: every model layer must
degrade to ``skipped`` and the report must still be produced, carrying
``semantic_verified: false`` so nobody mistakes the fallback for a verdict.
"""

import uuid
from datetime import datetime, timezone

import fitz
import pytest

from app.modules.ats.services import analysis_service
from app.modules.ats.constants import CHECK_SPECS, CheckStatus, RULESET_VERSION
from app.modules.ats.exceptions import ATSCVNotFoundError, ATSCVNotReadyError
from app.modules.ats.models import ATSReport
from app.modules.ats.services.analysis_service import analyze_cv_version, content_hash
from app.modules.ats.services.semantic_judge import (
    BulletVerdict,
    SemanticJudgment,
)

SAMPLE_INSIGHTS = [
    {"label": "Contact details", "value": "Complete", "done": True},
    {"label": "Role keywords", "value": "Add 3 more", "done": False},
    {"label": "Impact statements", "value": "Strong", "done": True},
]


def _parsed() -> dict:
    return {
        "contact": {
            "full_name": "Ada Lovelace",
            "email": "ada@example.com",
            "phone": "+44 20 7946 0018",
            "location": "London, UK",
            "linkedin": "https://linkedin.com/in/ada",
        },
        "summary": "Backend engineer in London",
        "experience": [
            {
                "title": "Backend Engineer",
                "company": "Acme",
                "location": "London",
                "start_date": "2023-01",
                "is_current": True,
                "description": (
                    "- Reduced p95 latency by 40% with a new cache\n"
                    "- Led the migration to Kubernetes\n"
                    "- Rewrote the ingestion pipeline"
                ),
                "technologies": ["Python", "Kubernetes"],
            }
        ],
        "education": [{"institution": "UCL", "degree": "BSc", "field_of_study": "CS"}],
        "skills": ["Python", "Django", "Kubernetes"],
        "projects": [],
        "certifications": [],
        "languages": ["English"],
    }


def _version(**overrides):
    defaults = dict(
        id=uuid.uuid4(),
        parsed_data=_parsed(),
        raw_text=(
            "Ada Lovelace\nada@example.com\n+44 20 7946 0018\nLondon, UK\n"
            "Backend engineer in London\n"
            "Backend Engineer, Acme, 2023-present\n"
            "Reduced p95 latency by 40% with a new cache\n"
            "Led the migration to Kubernetes\n"
            "Rewrote the ingestion pipeline\n"
            "UCL BSc Computer Science\n"
            "Python Django Kubernetes"
        ),
        target_role="Backend Engineer",
        s3_key=None,
        status="completed",
    )
    defaults.update(overrides)
    return type("Version", (), defaults)()


def _text_based_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page()
    for index in range(40):
        page.insert_text((60, 80 + index * 16), f"Experience line {index} with body words")
    payload = document.tobytes()
    document.close()
    return payload


class _FakeDB:
    def __init__(self):
        self.added: list = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime(2026, 10, 6, tzinfo=timezone.utc)


def _stored_report(version_id, digest, semantic_verified=True, score=82, summary=None):
    return ATSReport(
        id=uuid.uuid4(),
        user_id=7,
        cv_version_id=version_id,
        score=score,
        checks=[
            {
                "id": spec.id,
                "label": spec.label,
                "category": spec.category,
                "weight": spec.weight,
                "kind": spec.kind.value,
                "status": "pass",
                "score": 1.0,
                "value": "ok",
                "detail": "",
                "evidence": {},
            }
            for spec in CHECK_SPECS
        ],
        summary=summary if summary is not None else SAMPLE_INSIGHTS,
        semantic_verified=semantic_verified,
        content_hash=digest,
        ruleset_version=RULESET_VERSION,
        created_at=datetime(2026, 10, 6, tzinfo=timezone.utc),
    )


_MISSING = object()


def _stub(
    monkeypatch,
    *,
    version=_MISSING,
    cached=None,
    vocabulary=None,
    judgment=None,
    pdf=None,
    error=None,
):
    if version is _MISSING:
        version = _version()
    calls = {"vocab": 0, "judge": 0, "pdf": 0}

    async def _find_current(db, user_id):
        if error or version is None:
            return None, error or "not_found"
        return version, None

    async def _find_owned(db, user_id, cv_version_id):
        if error or version is None:
            return None, error or "not_found"
        return version, None

    async def _get_report(db, cv_version_id, digest, ruleset):
        return cached

    async def _delete_report(db, cv_version_id, digest, ruleset):
        return None

    async def _vocab(db, target_role):
        calls["vocab"] += 1
        return vocabulary

    async def _judge(target_role, summary, bullets):
        calls["judge"] += 1
        return judgment

    def _pdf_fetch(s3_key):
        calls["pdf"] += 1
        return pdf

    monkeypatch.setattr(analysis_service, "find_current_cv_version", _find_current)
    monkeypatch.setattr(analysis_service, "find_owned_cv_version", _find_owned)
    monkeypatch.setattr(analysis_service, "get_report", _get_report)
    monkeypatch.setattr(analysis_service, "delete_report", _delete_report)
    monkeypatch.setattr(analysis_service, "resolve_role_vocabulary", _vocab)
    monkeypatch.setattr(analysis_service, "judge_semantics", _judge)
    monkeypatch.setattr(analysis_service, "_download_source_pdf", _pdf_fetch)

    return calls


class TestTotalModelOutage:
    async def test_the_report_is_still_produced(self, monkeypatch):
        db = _FakeDB()
        _stub(monkeypatch, vocabulary=None, judgment=None)

        report = await analyze_cv_version(db, 7)

        assert db.added, "the report must be persisted even when every model fails"
        assert report.semantic_verified is False
        assert 0 <= report.score <= 100

    async def test_unavailable_model_layers_are_skipped_not_penalised(self, monkeypatch):
        db = _FakeDB()
        _stub(monkeypatch, vocabulary=None, judgment=None)

        report = await analyze_cv_version(db, 7)
        checks = {check.id: check for check in report.checks}

        assert checks["role_keyword_coverage"].status == "skipped"
        assert checks["role_alignment"].status == "skipped"
        assert checks["parsable_text_layer"].status == "skipped"
        assert checks["impact_statements"].evidence["verified"] is False

    async def test_the_impact_check_admits_it_is_only_a_lower_bound(self, monkeypatch):
        db = _FakeDB()
        _stub(monkeypatch, vocabulary=["python"], judgment=None)

        report = await analyze_cv_version(db, 7)
        impact = next(c for c in report.checks if c.id == "impact_statements")

        assert "not confirmed as real achievements" in impact.detail

    async def test_a_nil_role_vocabulary_skips_only_the_keyword_check(self, monkeypatch):
        db = _FakeDB()
        _stub(monkeypatch, vocabulary=None, judgment=None)

        report = await analyze_cv_version(db, 7)
        checks = {check.id: check for check in report.checks}

        assert checks["role_alignment"].status == "skipped"
        assert checks["section_experience"].status == "pass"


class TestVerifiedPath:
    async def test_model_verdicts_mark_the_report_verified(self, monkeypatch):
        db = _FakeDB()
        judgment = SemanticJudgment(
            role_aligned=True,
            role_alignment_reason="Backend role with matching stack",
            bullet_verdicts=[
                BulletVerdict(ref="experience[0].bullet[0]", real_impact=True),
                BulletVerdict(ref="experience[0].bullet[1]", real_impact=False),
                BulletVerdict(ref="experience[0].bullet[2]", real_impact=False),
            ],
        )
        _stub(monkeypatch, vocabulary=["python", "kubernetes"], judgment=judgment)

        report = await analyze_cv_version(db, 7)
        checks = {check.id: check for check in report.checks}

        assert report.semantic_verified is True
        assert checks["role_keyword_coverage"].status != "skipped"
        assert checks["role_alignment"].status == "pass"
        assert checks["impact_statements"].evidence["verified"] is True

    async def test_a_verdict_for_an_unknown_bullet_ref_is_ignored(self, monkeypatch):
        """A model that invents refs must not be able to inflate the score."""
        db = _FakeDB()
        judgment = SemanticJudgment(
            role_aligned=True,
            bullet_verdicts=[BulletVerdict(ref="experience[9].bullet[9]", real_impact=True)],
        )
        _stub(monkeypatch, vocabulary=["python"], judgment=judgment)

        report = await analyze_cv_version(db, 7)
        checks = {check.id: check for check in report.checks}

        assert checks["impact_statements"].score == 0.0
        assert checks["impact_statements"].evidence["verified_refs"] == []


class TestCaching:
    async def test_a_verified_cached_report_is_returned_untouched(self, monkeypatch):
        version = _version()
        digest = content_hash(version.raw_text, version.parsed_data)
        cached = _stored_report(version.id, digest, semantic_verified=True, score=82)
        calls = _stub(monkeypatch, version=version, cached=cached)

        report = await analyze_cv_version(db := _FakeDB(), 7)

        assert report.id == cached.id
        assert report.score == 82
        assert db.added == []
        assert calls["vocab"] == 0, "an identical report must not cost another model call"
        assert [row.model_dump() for row in report.insights] == SAMPLE_INSIGHTS

    async def test_a_degraded_cached_report_is_recomputed(self, monkeypatch):
        """A model outage must not leave a permanently degraded result behind."""
        version = _version()
        digest = content_hash(version.raw_text, version.parsed_data)
        cached = _stored_report(version.id, digest, semantic_verified=False, score=82)
        calls = _stub(monkeypatch, version=version, cached=cached, vocabulary=["python"])

        report = await analyze_cv_version(db := _FakeDB(), 7)

        assert db.added, "the degraded report should have been replaced"
        assert calls["vocab"] == 1
        assert report.id != cached.id

    async def test_force_recomputes_even_a_fresh_verified_report(self, monkeypatch):
        version = _version()
        digest = content_hash(version.raw_text, version.parsed_data)
        cached = _stored_report(version.id, digest, semantic_verified=True)
        calls = _stub(monkeypatch, version=version, cached=cached, vocabulary=["python"])

        db = _FakeDB()
        await analyze_cv_version(db, 7, force=True)

        assert db.added
        assert calls["vocab"] == 1


class TestContentHash:
    def test_the_hash_is_stable_for_identical_content(self):
        first = content_hash("text", {"a": 1})
        second = content_hash("text", {"a": 1})
        assert first == second
        assert len(first) == 64

    def test_the_hash_changes_when_either_input_changes(self):
        baseline = content_hash("text", {"a": 1})
        assert content_hash("other", {"a": 1}) != baseline
        assert content_hash("text", {"a": 2}) != baseline

    def test_the_hash_tolerates_a_missing_cv(self):
        assert content_hash(None, None) == content_hash("", {})


class TestErrors:
    async def test_a_user_with_no_cv_gets_a_not_found(self, monkeypatch):
        _stub(monkeypatch, version=None, error="not_found")
        with pytest.raises(ATSCVNotFoundError):
            await analyze_cv_version(_FakeDB(), 7)

    async def test_a_cv_still_processing_gets_a_not_ready(self, monkeypatch):
        _stub(monkeypatch, error="not_ready")
        with pytest.raises(ATSCVNotReadyError):
            await analyze_cv_version(_FakeDB(), 7)

    async def test_a_version_without_parsed_content_is_not_ready(self, monkeypatch):
        _stub(monkeypatch, version=_version(parsed_data=None))
        with pytest.raises(ATSCVNotReadyError):
            await analyze_cv_version(_FakeDB(), 7)

    async def test_the_caller_id_is_passed_to_the_version_lookup(self, monkeypatch):
        record = {}

        async def _find_current(db, user_id):
            record["user_id"] = user_id
            return None, "not_found"

        monkeypatch.setattr(analysis_service, "find_current_cv_version", _find_current)
        with pytest.raises(ATSCVNotFoundError):
            await analyze_cv_version(_FakeDB(), 42)
        assert record["user_id"] == 42


class TestReportShape:
    async def test_every_catalogue_check_is_reported_exactly_once(self, monkeypatch):
        db = _FakeDB()
        _stub(monkeypatch, vocabulary=["python"])

        report = await analyze_cv_version(db, 7)

        assert [check.id for check in report.checks] == [
            spec.id for spec in CHECK_SPECS
        ]
        assert len({check.id for check in report.checks}) == len(CHECK_SPECS)

    async def test_checks_carry_their_weight_and_kind(self, monkeypatch):
        _stub(monkeypatch, vocabulary=["python"])

        report = await analyze_cv_version(_FakeDB(), 7)
        specs = {spec.id: spec for spec in CHECK_SPECS}

        for check in report.checks:
            assert check.weight == specs[check.id].weight
            assert check.kind == specs[check.id].kind.value
            assert check.label == specs[check.id].label

    async def test_a_result_is_json_serialisable_for_the_jsonb_column(self, monkeypatch):
        import json

        _stub(monkeypatch, vocabulary=["python"])
        report = await analyze_cv_version(_FakeDB(), 7)

        json.dumps([check.model_dump() for check in report.checks])
        json.dumps([insight.model_dump() for insight in report.insights])

    async def test_the_integrity_check_is_reported_but_scored_at_zero(self, monkeypatch):
        _stub(monkeypatch, vocabulary=["python"])
        report = await analyze_cv_version(_FakeDB(), 7)

        integrity = next(c for c in report.checks if c.id == "data_integrity")
        assert integrity.weight == 0
        assert integrity.status in {CheckStatus.PASS.value, CheckStatus.WARN.value, CheckStatus.FAIL.value}


class TestSourcePdF:
    async def test_a_fetched_pdf_runs_the_layout_checks(self, monkeypatch):
        _stub(monkeypatch, vocabulary=["python"], pdf=_text_based_pdf())

        report = await analyze_cv_version(_FakeDB(), 7)
        text_layer = next(c for c in report.checks if c.id == "parsable_text_layer")

        assert text_layer.status == "pass"
        assert text_layer.value == "Text based"

    async def test_an_unfetched_pdf_skips_layout_without_failing_the_score(self, monkeypatch):
        _stub(monkeypatch, vocabulary=["python"], pdf=None)

        report = await analyze_cv_version(_FakeDB(), 7)
        layout = [c for c in report.checks if c.category == "parsability"]

        assert all(c.status == "skipped" for c in layout)
        assert 0 <= report.score <= 100
