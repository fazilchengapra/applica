"""Endpoint-level tests for GET /api/ai/v1/dashboard/stats.

These exercise the real FastAPI app, so they cover the gateway middleware and
the ``X-User-Id`` dependency as well as the response shape. The repository is
stubbed at its function boundary, so no database is required.
"""

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


def _stub_repository(
    monkeypatch,
    match_counts=None,
    average=0.0,
    rendered=0,
    rendering=0,
):
    """Pin every query the stats builder makes.

    ``match_counts`` defaults to an all-zero breakdown, which is what the
    aggregate returns for a user with no matches.
    """

    async def get_match_pipeline_counts(db, user_id):
        return match_counts or {
            "new": 0,
            "shortlisted": 0,
            "applied": 0,
            "interviewing": 0,
            "rejected": 0,
            "total": 0,
        }

    async def get_average_final_score(db, user_id):
        return average

    async def get_tailored_cv_counts(db, user_id):
        return {
            "total": rendered + rendering,
            "approved": 0,
            "failed": 0,
            "rendering": rendering,
            "rendered": rendered,
        }

    monkeypatch.setattr(
        repository, "get_match_pipeline_counts", get_match_pipeline_counts
    )
    monkeypatch.setattr(repository, "get_average_final_score", get_average_final_score)
    monkeypatch.setattr(repository, "get_tailored_cv_counts", get_tailored_cv_counts)


async def test_stats_returns_the_documented_shape(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(
        monkeypatch,
        match_counts={
            "new": 5,
            "shortlisted": 3,
            "applied": 8,
            "interviewing": 2,
            "rejected": 1,
            "total": 19,
        },
        average=74.3,
        rendered=8,
        rendering=3,
    )

    response = await client.get("/api/ai/v1/dashboard/stats", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "match_status_breakdown": {
            "new": 5,
            "shortlisted": 3,
            "applied": 8,
            "interviewing": 2,
            "rejected": 1,
            "total": 19,
        },
        "average_final_score": 74.3,
        "top_n": 10,
        "tailored_cvs_completed": 8,
        "tailored_cvs_in_progress": 3,
    }


async def test_stats_is_zeroed_for_an_empty_account(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch)

    response = await client.get("/api/ai/v1/dashboard/stats", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["match_status_breakdown"] == {
        "new": 0,
        "shortlisted": 0,
        "applied": 0,
        "interviewing": 0,
        "rejected": 0,
        "total": 0,
    }
    # AVG over no rows is NULL in SQL; the repository turns that into 0.0 so the
    # client never null-checks the tile.
    assert body["average_final_score"] == 0.0
    assert body["tailored_cvs_completed"] == 0
    assert body["tailored_cvs_in_progress"] == 0


async def test_stats_echoes_the_requested_top_n(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch)

    response = await client.get(
        "/api/ai/v1/dashboard/stats?top_n=25", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert response.json()["top_n"] == 25


@pytest.mark.parametrize("top_n", [0, -1, 101])
async def test_stats_rejects_an_out_of_range_top_n(client, monkeypatch, top_n):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch)

    response = await client.get(
        f"/api/ai/v1/dashboard/stats?top_n={top_n}", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 422


async def test_stats_requires_the_gateway_secret(client):
    _override_user()
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/stats", headers={"X-User-Id": "7"}
    )

    assert response.status_code == 403


async def test_stats_requires_the_user_header(client):
    # No dependency override: the real X-User-Id Header(...) dependency runs.
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/stats",
        headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
    )

    assert response.status_code == 422