"""Endpoint-level tests for GET /api/ai/v1/dashboard/insights.

Real FastAPI app (so gateway middleware and the X-User-Id dependency are covered
too); the repository is stubbed at its function boundary, so no database.
"""

import uuid
from datetime import datetime, timezone

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import settings
from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.modules.dashboard import repository

GATEWAY_HEADERS = {
    "X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET,
    "X-User-Id": "7",
}

CV_ID = uuid.UUID("33333333-4444-4555-8666-777777777777")


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


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _gap_row(skill="GraphQL", job_count=9, category=None):
    return _Row(skill=skill, job_count=job_count, category=category)


def _trend_row(week_iso="2026-10-06", avg_score=4.2):
    return _Row(week=datetime.fromisoformat(week_iso), avg_score=float(avg_score))


def _stub_repository(monkeypatch, gaps=None, trend=None, cv_id=CV_ID, record=None):
    async def get_current_completed_cv_id(db, user_id):
        if record is not None:
            record["cv_args"] = user_id
        return cv_id

    async def get_missing_skills(db, user_id, cv_id, limit=10):
        if record is not None:
            record["gap_args"] = (user_id, cv_id, limit)
        return gaps or []

    async def get_score_trend(db, user_id, since):
        if record is not None:
            record["trend_args"] = (user_id, since)
        return trend or []

    monkeypatch.setattr(
        repository, "get_current_completed_cv_id", get_current_completed_cv_id
    )
    monkeypatch.setattr(repository, "get_missing_skills", get_missing_skills)
    monkeypatch.setattr(repository, "get_score_trend", get_score_trend)


async def test_insights_returns_the_documented_shape(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(
        monkeypatch,
        gaps=[_gap_row("GraphQL", 9, "API")],
        trend=[_trend_row("2026-10-06", 4.2)],
    )

    response = await client.get("/api/ai/v1/dashboard/insights", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "missing_skills": [{"skill": "GraphQL", "count": 9, "category": "API"}],
        "score_trend": [{"date": "Oct 6", "score": 4.2}],
    }


async def test_insights_response_keys_match_the_contract(client, monkeypatch):
    """Both top-level keys are always present; the client never null-checks."""
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, gaps=[_gap_row()], trend=[_trend_row()])

    response = await client.get("/api/ai/v1/dashboard/insights", headers=GATEWAY_HEADERS)

    body = response.json()
    assert sorted(body) == ["missing_skills", "score_trend"]
    assert sorted(body["missing_skills"][0]) == ["category", "count", "skill"]
    assert sorted(body["score_trend"][0]) == ["date", "score"]


async def test_insights_is_empty_without_a_completed_cv(client, monkeypatch):
    """A CV still parsing would report every skill the user has as a gap."""
    _override_user()
    _override_db()
    _stub_repository(
        monkeypatch,
        gaps=[_gap_row("GraphQL", 9)],
        trend=[_trend_row()],
        cv_id=None,
    )

    response = await client.get("/api/ai/v1/dashboard/insights", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["missing_skills"] == []
    # The trend does not depend on the CV, so it still reports.
    assert len(body["score_trend"]) == 1


async def test_insights_omits_the_gap_query_when_there_is_no_cv(
    client, monkeypatch
):
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, cv_id=None, record=record)

    response = await client.get("/api/ai/v1/dashboard/insights", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    assert "gap_args" not in record, "queried gaps without a CV to diff against"
    assert "trend_args" in record


async def test_insights_allows_a_null_category(client, monkeypatch):
    """skills.category has never been backfilled, so null is the normal case."""
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, gaps=[_gap_row("ADK", 14)], cv_id=CV_ID)

    response = await client.get("/api/ai/v1/dashboard/insights", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    assert response.json()["missing_skills"][0] == {
        "skill": "ADK",
        "count": 14,
        "category": None,
    }


async def test_insights_labels_weeks_for_a_chart_axis(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(
        monkeypatch,
        trend=[
            _trend_row("2026-10-01", 3.5),
            _trend_row("2026-10-08", 4.2),
            _trend_row("2026-10-15", 4.8),
            _trend_row("2026-10-22", 6.1),
        ],
    )

    response = await client.get("/api/ai/v1/dashboard/insights", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    assert response.json()["score_trend"] == [
        {"date": "Oct 1", "score": 3.5},
        {"date": "Oct 8", "score": 4.2},
        {"date": "Oct 15", "score": 4.8},
        {"date": "Oct 22", "score": 6.1},
    ]


async def test_insights_passes_weeks_and_limit_through(client, monkeypatch):
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, record=record)

    response = await client.get(
        "/api/ai/v1/dashboard/insights?weeks=12&limit=4", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert record["cv_args"] == 7
    assert record["gap_args"] == (7, CV_ID, 4)


async def test_insights_defaults(client, monkeypatch):
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, record=record)

    response = await client.get("/api/ai/v1/dashboard/insights", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    # limit defaults to 10
    assert record["gap_args"][2] == 10
    # and the trend defaults to an 8-week window ending now
    since = record["trend_args"][1]
    age_days = (datetime.now(timezone.utc).replace(tzinfo=None) - since).days
    assert 55 <= age_days <= 57, age_days


async def test_insights_trend_cutoff_is_naive(client, monkeypatch):
    """job_matches.matched_at is timestamp without time zone.

    A tz-aware cutoff would be cast to timestamptz and compared against a naive
    column, shifting the window boundary by the session offset.
    """
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, record=record)

    response = await client.get(
        "/api/ai/v1/dashboard/insights?weeks=3", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    since = record["trend_args"][1]
    assert since.tzinfo is None, f"cutoff must be naive, got {since!r}"


async def test_insights_trend_window_shrinks_with_weeks(client, monkeypatch):
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, record=record)

    await client.get("/api/ai/v1/dashboard/insights?weeks=1", headers=GATEWAY_HEADERS)
    narrow = record["trend_args"][1]
    await client.get("/api/ai/v1/dashboard/insights?weeks=52", headers=GATEWAY_HEADERS)
    wide = record["trend_args"][1]

    # A wider window reaches further back, so its cutoff is the earlier one.
    assert (narrow - wide).days == pytest.approx(51 * 7, abs=2)


@pytest.mark.parametrize(
    "query", ["weeks=0", "weeks=53", "limit=0", "limit=51"]
)
async def test_insights_rejects_out_of_range_params(client, monkeypatch, query):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch)

    response = await client.get(
        f"/api/ai/v1/dashboard/insights?{query}", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 422


async def test_insights_requires_the_gateway_secret(client):
    _override_user()
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/insights", headers={"X-User-Id": "7"}
    )

    assert response.status_code == 403


async def test_insights_requires_the_user_header(client):
    # No dependency override: the real X-User-Id Header(...) dependency runs.
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/insights",
        headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
    )

    assert response.status_code == 422