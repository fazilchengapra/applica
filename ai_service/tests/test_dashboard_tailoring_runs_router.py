"""Endpoint-level tests for GET /api/ai/v1/dashboard/tailoring-runs.

Real FastAPI app, so the gateway middleware and the ``X-User-Id`` dependency are
covered too; the repository is stubbed at its function boundary, so no database is
needed.
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

RUN_ID = uuid.UUID("11111111-2222-4333-8444-555555555555")
CV_ID = uuid.UUID("99999999-8888-4777-8666-555555555555")

T0 = datetime(2026, 10, 3, 9, 20, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 10, 3, 9, 25, 30, tzinfo=timezone.utc)


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


def _row(**overrides):
    base = dict(
        id=RUN_ID,
        run_status="processing",
        run_stage="write",
        created_at=T0,
        updated_at=T1,
        error_message=None,
        tailored_cv_id=None,
        job_title="Senior Frontend Engineer",
        company_display_name="Northstar Labs",
        company_normalized_name="northstar-labs",
    )
    base.update(overrides)
    return _Row(**base)


def _stub_repository(monkeypatch, rows=None, count=0, record=None):
    async def count_tailoring_runs(db, user_id):
        if record is not None:
            record["count_args"] = user_id
        return count

    async def get_tailoring_runs(db, user_id, limit=20, offset=0):
        if record is not None:
            record.update(page_args=(user_id, limit, offset))
        return rows or []

    monkeypatch.setattr(repository, "count_tailoring_runs", count_tailoring_runs)
    monkeypatch.setattr(repository, "get_tailoring_runs", get_tailoring_runs)


async def test_tailoring_runs_returns_the_documented_shape(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, count=4, rows=[_row()])

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    body = response.json()
    # count is the total, not the page length
    assert body["count"] == 4
    assert body["results"] == [
        {
            "id": str(RUN_ID),
            "job_title": "Senior Frontend Engineer",
            "company_name": "Northstar Labs",
            "status": "in_progress",
            "current_stage": "writer",
            "created_at": "2026-10-03T09:20:00Z",
            "updated_at": "2026-10-03T09:25:30Z",
            "error_message": None,
            "cv_id": None,
        }
    ]


async def test_tailoring_runs_response_keys_match_the_contract(client, monkeypatch):
    """Guards the exact key set, so a rename cannot pass a looser assertion."""
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, count=1, rows=[_row()])

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert sorted(response.json()["results"][0]) == [
        "company_name",
        "created_at",
        "current_stage",
        "cv_id",
        "error_message",
        "id",
        "job_title",
        "status",
        "updated_at",
    ]


async def test_tailoring_runs_is_empty_for_an_account_with_no_runs(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, count=0, rows=[])

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert response.json() == {"count": 0, "results": []}


async def test_tailoring_runs_collapses_pending_and_processing(client, monkeypatch):
    """The stored enum has four values; the response shows three."""
    _override_user()
    _override_db()

    async def get_tailoring_runs(db, user_id, limit=20, offset=0):
        return [
            _row(id=uuid.uuid4(), run_status=status)
            for status in ("pending", "processing", "completed", "failed")
        ]

    async def count_tailoring_runs(db, user_id):
        return 4

    monkeypatch.setattr(repository, "count_tailoring_runs", count_tailoring_runs)
    monkeypatch.setattr(repository, "get_tailoring_runs", get_tailoring_runs)

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert [r["status"] for r in response.json()["results"]] == [
        "in_progress",
        "in_progress",
        "completed",
        "failed",
    ]


async def test_tailoring_runs_maps_every_stage_to_a_label(client, monkeypatch):
    """Stored values are evidence_match/strategy/write/critic, not the labels."""
    _override_user()
    _override_db()

    async def get_tailoring_runs(db, user_id, limit=20, offset=0):
        return [
            _row(id=uuid.uuid4(), run_stage=stage)
            for stage in ("evidence_match", "strategy", "write", "critic")
        ]

    async def count_tailoring_runs(db, user_id):
        return 4

    monkeypatch.setattr(repository, "count_tailoring_runs", count_tailoring_runs)
    monkeypatch.setattr(repository, "get_tailoring_runs", get_tailoring_runs)

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert [r["current_stage"] for r in response.json()["results"]] == [
        "evidence_matcher",
        "strategist",
        "writer",
        "critic",
    ]


async def test_tailoring_runs_current_stage_is_never_null(client, monkeypatch):
    """A queued run still reports evidence_matcher: the column is NOT NULL."""
    _override_user()
    _override_db()
    _stub_repository(
        monkeypatch,
        count=1,
        rows=[_row(run_status="pending", run_stage="evidence_match")],
    )

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["status"] == "in_progress"
    assert row["current_stage"] == "evidence_matcher"


async def test_tailoring_runs_reports_cv_id_when_a_cv_exists(client, monkeypatch):
    _override_user()
    _override_db()
    _stub_repository(
        monkeypatch,
        count=1,
        rows=[_row(run_status="completed", tailored_cv_id=CV_ID)],
    )

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["cv_id"] == str(CV_ID)


async def test_tailoring_runs_returns_the_full_error_message(client, monkeypatch):
    """Untruncated by decision: critic failures store the whole verdict."""
    _override_user()
    _override_db()
    long_message = "Quality review completed.; " + ("detail " * 500)
    _stub_repository(
        monkeypatch,
        count=1,
        rows=[_row(run_status="failed", error_message=long_message)],
    )

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["error_message"] == long_message


async def test_tailoring_runs_falls_back_to_normalized_company_name(
    client, monkeypatch
):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch, count=1, rows=[_row(company_display_name=None)])

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["company_name"] == "northstar-labs"


async def test_tailoring_runs_passes_paging_through(client, monkeypatch):
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, count=30, rows=[], record=record)

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs?limit=5&offset=10",
        headers=GATEWAY_HEADERS,
    )

    assert response.status_code == 200
    assert record["count_args"] == 7
    assert record["page_args"] == (7, 5, 10)


async def test_tailoring_runs_defaults_to_a_full_page(client, monkeypatch):
    """Unlike /dashboard/top-matches (capped at 3), this is a table."""
    _override_user()
    _override_db()
    record = {}
    _stub_repository(monkeypatch, count=0, rows=[], record=record)

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 200
    assert record["page_args"] == (7, 20, 0)


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
async def test_tailoring_runs_rejects_out_of_range_params(client, monkeypatch, query):
    _override_user()
    _override_db()
    _stub_repository(monkeypatch)

    response = await client.get(
        f"/api/ai/v1/dashboard/tailoring-runs?{query}", headers=GATEWAY_HEADERS
    )

    assert response.status_code == 422


async def test_tailoring_runs_requires_the_gateway_secret(client):
    _override_user()
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs", headers={"X-User-Id": "7"}
    )

    assert response.status_code == 403


async def test_tailoring_runs_requires_the_user_header(client):
    # No dependency override: the real X-User-Id Header(...) dependency runs.
    _override_db()

    response = await client.get(
        "/api/ai/v1/dashboard/tailoring-runs",
        headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
    )

    assert response.status_code == 422