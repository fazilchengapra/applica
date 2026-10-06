"""Endpoint-level tests for the ATS routes.

Real FastAPI app (so gateway middleware and the X-User-Id dependency are
covered); the analysis service is stubbed at its function boundary, so no
database, no model and no S3.
"""

import uuid
from datetime import datetime

import httpx
import pytest
from httpx import ASGITransport

from app.api.v1 import ats
from app.core.config import settings
from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.modules.ats.exceptions import ATSCVNotFoundError, ATSCVNotReadyError
from app.modules.ats.schemas import (
    ATSReportListOut,
    ATSReportListItem,
    ATSReportOut,
    InsightOut,
)

GATEWAY_HEADERS = {
    "X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET,
    "X-User-Id": "7",
}

REPORT_ID = uuid.UUID("11111111-2222-4333-8444-555555555555")
CV_VERSION_ID = uuid.UUID("33333333-4444-4555-8666-777777777777")

SAMPLE_INSIGHTS = [
    {"label": "Contact details", "value": "Complete", "done": True},
    {"label": "Role keywords", "value": "Add 3 more", "done": False},
    {"label": "Impact statements", "value": "Strong", "done": True},
]


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


def _override_user(user_id: int = 7):
    app.dependency_overrides[get_current_user_id] = lambda: user_id


def _override_db():
    async def _db():
        yield object()

    app.dependency_overrides[get_db] = _db


def _report(score=82, semantic_verified=True, insights=None):
    return ATSReportOut(
        id=REPORT_ID,
        cv_version_id=CV_VERSION_ID,
        score=score,
        insights=[InsightOut(**row) for row in (insights or SAMPLE_INSIGHTS)],
        checks=[],
        semantic_verified=semantic_verified,
        content_hash="a" * 64,
        ruleset_version=1,
        created_at=datetime(2026, 10, 6),
    )


class TestAnalyze:
    async def test_returns_the_documented_report_shape(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = {}

        async def _analyze(db, user_id, cv_version_id=None, force=False):
            calls.update(user_id=user_id, cv_version_id=cv_version_id, force=force)
            return _report()

        monkeypatch.setattr(ats, "analyze_cv_version", _analyze)

        response = await client.post(
            "/api/ai/v1/ats/analyze", json={}, headers=GATEWAY_HEADERS
        )

        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 82
        assert body["insights"] == SAMPLE_INSIGHTS
        for insight in body["insights"]:
            assert sorted(insight) == ["done", "label", "value"]
        assert body["semantic_verified"] is True
        assert calls == {"user_id": 7, "cv_version_id": None, "force": False}

    async def test_an_empty_body_is_accepted(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _analyze(db, user_id, cv_version_id=None, force=False):
            return _report()

        monkeypatch.setattr(ats, "analyze_cv_version", _analyze)

        response = await client.post(
            "/api/ai/v1/ats/analyze", headers=GATEWAY_HEADERS
        )

        assert response.status_code == 200

    async def test_force_and_cv_version_id_are_passed_through(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = {}

        async def _analyze(db, user_id, cv_version_id=None, force=False):
            calls.update(user_id=user_id, cv_version_id=cv_version_id, force=force)
            return _report()

        monkeypatch.setattr(ats, "analyze_cv_version", _analyze)

        response = await client.post(
            "/api/ai/v1/ats/analyze",
            json={"cv_version_id": str(CV_VERSION_ID), "force": True},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        assert calls == {"user_id": 7, "cv_version_id": CV_VERSION_ID, "force": True}

    async def test_no_completed_cv_is_a_404(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _analyze(db, user_id, cv_version_id=None, force=False):
            raise ATSCVNotFoundError("No completed CV found")

        monkeypatch.setattr(ats, "analyze_cv_version", _analyze)

        response = await client.post(
            "/api/ai/v1/ats/analyze", json={}, headers=GATEWAY_HEADERS
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "No completed CV found"

    async def test_a_cv_still_processing_is_a_409(self, client, monkeypatch):
        """Not an error to retry: the client should poll until parsing finishes."""
        _override_user()
        _override_db()

        async def _analyze(db, user_id, cv_version_id=None, force=False):
            raise ATSCVNotReadyError("CV is still processing")

        monkeypatch.setattr(ats, "analyze_cv_version", _analyze)

        response = await client.post(
            "/api/ai/v1/ats/analyze", json={}, headers=GATEWAY_HEADERS
        )

        assert response.status_code == 409

    async def test_an_unknown_cv_version_id_is_a_404(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _analyze(db, user_id, cv_version_id=None, force=False):
            raise ATSCVNotFoundError("No completed CV found")

        monkeypatch.setattr(ats, "analyze_cv_version", _analyze)

        response = await client.post(
            "/api/ai/v1/ats/analyze",
            json={"cv_version_id": str(uuid.uuid4())},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 404


class TestReports:
    async def test_reports_returns_the_trend_shape(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = {}

        async def _list(db, user_id, cv_version_id, limit, offset):
            calls.update(
                user_id=user_id, cv_version_id=cv_version_id, limit=limit, offset=offset
            )
            return ATSReportListOut(
                total=3,
                items=[
                    ATSReportListItem(
                        id=REPORT_ID,
                        cv_version_id=CV_VERSION_ID,
                        score=82,
                        semantic_verified=True,
                        created_at=datetime(2026, 10, 6),
                    )
                ],
            )

        monkeypatch.setattr(ats, "list_reports", _list)

        response = await client.get(
            "/api/ai/v1/ats/reports?limit=5&offset=10", headers=GATEWAY_HEADERS
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3, "total is the qualifying count, not the page length"
        assert len(body["items"]) == 1
        assert calls == {"user_id": 7, "cv_version_id": None, "limit": 5, "offset": 10}

    async def test_reports_filters_by_cv_version(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = {}

        async def _list(db, user_id, cv_version_id, limit, offset):
            calls["cv_version_id"] = cv_version_id
            return ATSReportListOut(total=0, items=[])

        monkeypatch.setattr(ats, "list_reports", _list)

        response = await client.get(
            f"/api/ai/v1/ats/reports?cv_version_id={CV_VERSION_ID}",
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        assert calls["cv_version_id"] == CV_VERSION_ID

    @pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
    async def test_reports_rejects_out_of_range_params(self, client, query):
        _override_user()
        _override_db()

        response = await client.get(
            f"/api/ai/v1/ats/reports?{query}", headers=GATEWAY_HEADERS
        )

        assert response.status_code == 422

    async def test_a_report_the_caller_does_not_own_is_a_404(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _get(db, report_id, user_id):
            return None

        monkeypatch.setattr(ats, "get_report_out", _get)

        response = await client.get(
            f"/api/ai/v1/ats/reports/{REPORT_ID}", headers=GATEWAY_HEADERS
        )

        assert response.status_code == 404

    async def test_a_stored_report_round_trips(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _get(db, report_id, user_id):
            assert report_id == REPORT_ID
            assert user_id == 7, "ownership must be checked against the caller"
            return _report(score=82)

        monkeypatch.setattr(ats, "get_report_out", _get)

        response = await client.get(
            f"/api/ai/v1/ats/reports/{REPORT_ID}", headers=GATEWAY_HEADERS
        )

        assert response.status_code == 200
        assert response.json()["insights"] == SAMPLE_INSIGHTS


class TestGatewayGuards:
    async def test_analyze_requires_the_gateway_secret(self, client):
        _override_user()
        _override_db()

        response = await client.post(
            "/api/ai/v1/ats/analyze", json={}, headers={"X-User-Id": "7"}
        )

        assert response.status_code == 403

    async def test_analyze_requires_the_user_header(self, client):
        _override_db()

        response = await client.post(
            "/api/ai/v1/ats/analyze",
            json={},
            headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
        )

        assert response.status_code == 422

    async def test_reports_are_not_reachable_without_the_gateway(self, client):
        _override_user()
        _override_db()

        response = await client.get(
            "/api/ai/v1/ats/reports", headers={"X-User-Id": "7"}
        )

        assert response.status_code == 403
