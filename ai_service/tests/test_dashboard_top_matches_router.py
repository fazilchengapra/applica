"""Endpoint-level tests for GET /api/ai/v1/dashboard/top-matches.

These exercise the real FastAPI app, so they cover the gateway middleware and
the ``X-User-Id`` dependency as well as the response shape. The repository is
stubbed at its function boundary, so no database is required.
"""

import uuid

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

MATCH_ID = uuid.UUID("a1b2c3d4-0000-4000-8000-000000000001")


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
    """Stand-in for a repository row; only the mapped attributes are read."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def _row(**overrides):
    base = dict(
        id=MATCH_ID,
        match_status="new",
        final_score=7.8,
        vector_score=0.82,
        lexical_score=0.61,
        rrf_score=0.74,
        key_matches=["React", "TypeScript"],
        key_gaps=["GraphQL"],
        job_title="Senior Frontend Engineer",
        company_display_name="Northstar Labs",
        company_normalized_name="northstar-labs",
        tailored_cv_status=None,
    )
    base.update(overrides)
    return _Row(**base)


def _stub_repository(monkeypatch, rows=None, count=0, record=None):
    """Pin both queries the builder makes and capture the paging it asked for."""

    async def count_top_matches(db, user_id, min_score=None):
        if record is not None:
            record["min_score"] = min_score
        return count

    async def get_top_match_results(db, user_id, min_score=None, limit=20, offset=0):
        if record is not None:
            record.update(min_score=min_score, limit=limit, offset=offset)
        return rows or []

    monkeypatch.setattr(repository, "count_top_matches", count_top_matches)
    monkeypatch.setattr(repository, "get_top_match_results", get_top_match_results)


async def test_top_matches_returns_the_documented_shape(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(
        monkeypatch,
        count=12,
        rows=[
            _row(),
            _row(
                id=uuid.UUID("e5f6a7b8-0000-4000-8000-000000000002"),
                job_title="Product Designer",
                company_display_name="Brightline",
                company_normalized_name="brightline",
                match_status="shortlisted",
                final_score=6.2,
                vector_score=0.68,
                lexical_score=0.55,
                rrf_score=0.63,
                key_matches=["Figma"],
                key_gaps=["Motion Design"],
                tailored_cv_status="processing",
            ),
        ],
    )

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    body = response.json()
    # count is the total qualifying, not the page length
    assert body["count"] == 12
    assert body["results"][0] == {
        "id": str(MATCH_ID),
        "job_title": "Senior Frontend Engineer",
        "company_name": "Northstar Labs",
        "match_status": "new",
        "final_score": 7.8,
        "vector_score": 0.82,
        "lexical_score": 0.61,
        "rrf_score": 0.74,
        "key_matches": ["React", "TypeScript"],
        "key_gaps": ["GraphQL"],
        "tailored_cv_status": "none",
    }
    assert body["results"][1]["tailored_cv_status"] == "in_progress"
    assert body["results"][1]["match_status"] == "shortlisted"


async def test_top_matches_is_empty_for_an_account_with_no_matches(
    client, monkeypatch
):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, count=0, rows=[])

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert response.json() == {"count": 0, "results": []}


async def test_top_matches_maps_run_status_to_progress(client, monkeypatch):
    """pending and processing both collapse to in_progress; the rest pass through."""
    _override_user()
    _override_db()

    async def get_top_match_results(db, user_id, min_score=None, limit=20, offset=0):
        return [
            _row(id=uuid.uuid4(), tailored_cv_status=status)
            for status in ("pending", "processing", "completed", "failed", None)
        ]

    async def count_top_matches(db, user_id, min_score=None):
        return 5

    monkeypatch.setattr(repository, "count_top_matches", count_top_matches)
    monkeypatch.setattr(repository, "get_top_match_results", get_top_match_results)

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert [r["tailored_cv_status"] for r in response.json()["results"]] == [
        "in_progress",
        "in_progress",
        "completed",
        "failed",
        "none",
    ]


async def test_top_matches_falls_back_to_normalized_company_name(
    client, monkeypatch
):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, count=1, rows=[_row(company_display_name=None)])

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["company_name"] == "northstar-labs"


async def test_top_matches_passes_paging_and_filter_through(client, monkeypatch):
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, count=30, rows=[], record=record)

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches?limit=3&offset=10&min_score=4.5",
        headers=GATEWAY_HEADERS,
    )

    assert response.status_code == 200
    assert record == {"min_score": 4.5, "limit": 3, "offset": 10}


async def test_top_matches_sends_no_min_score_by_default(client, monkeypatch):
    """A 0-1 floor would exclude nearly everything stored on the 0-100 scale."""
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, count=0, rows=[], record=record)

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert record["min_score"] is None
    assert (record["limit"], record["offset"]) == (3, 0)


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=4", "offset=-1", "min_score=-0.5"]
)
async def test_top_matches_rejects_out_of_range_params(client, monkeypatch, query):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch)

    response = await client.get(
        f"/api/ai/v1/dashboard/top-matches?{query}", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 422


async def test_top_matches_requires_the_gateway_secret(client):
    _override_user()
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches", headers={"X-User-Id": "7"}
    )

    assert response.status_code == 403


async def test_top_matches_requires_the_user_header(client):
    # No dependency override: the real X-User-Id Header(...) dependency runs.
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/top-matches",
        headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
    )

    assert response.status_code == 422