"""Endpoint-level tests for GET /api/ai/v1/home.

These exercise the real FastAPI app, so they cover the gateway middleware, the
``X-User-Id`` dependency and the upstream-failure status mapping together.
Upstreams are stubbed at the client/repository boundary, so no network or
database is required.
"""

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import settings
from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.modules.home import clients, repository
from app.modules.home.exceptions import UserServiceError, UserServiceUnavailable
from app.modules.home.schemas import (
    AccountPayload,
    AccountStepFlags,
    HomeNotifications,
    HomeProfile,
    HomeUser,
)

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


def _valid_account() -> AccountPayload:
    return AccountPayload(
        user=HomeUser(
            id=7,
            email="me@example.com",
            is_email_verified=True,
            is_phone_verified=True,
            date_joined="2025-01-01T00:00:00Z",
            is_staff=False,
            roles=["user"],
        ),
        profile=HomeProfile(display_name="Fazil"),
        account_steps=AccountStepFlags(verify_email=True, verify_phone=True),
        notifications=HomeNotifications(unread=4),
        linked_accounts=[],
    )


async def _stub_upstreams(monkeypatch, account=None, error=None):
    async def fetch(user_id):
        if error is not None:
            raise error
        return account

    async def has_cv(db, user_id):
        return True

    monkeypatch.setattr(clients, "fetch_account", fetch)
    monkeypatch.setattr(repository, "has_uploaded_cv", has_cv)


async def test_home_returns_composed_payload(client, monkeypatch):
    _override_user()
    _override_db()
    await _stub_upstreams(monkeypatch, account=_valid_account())

    response = await client.get("/api/ai/v1/home", headers=GATEWAY_HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "user",
        "profile",
        "onboarding",
        "notifications",
        "linked_accounts",
        "generated_at",
    }
    assert body["user"]["email"] == "me@example.com"
    assert body["notifications"]["unread"] == 4
    # verify_email + verify_phone + upload_cv
    assert body["onboarding"]["percent"] == 60
    assert len(body["onboarding"]["steps"]) == 5


async def test_home_maps_upstream_error_to_502(client, monkeypatch):
    _override_user()
    _override_db()
    await _stub_upstreams(monkeypatch, error=UserServiceError("bad gateway"))

    response = await client.get("/api/ai/v1/home", headers=GATEWAY_HEADERS)

    assert response.status_code == 502


async def test_home_maps_upstream_timeout_to_504(client, monkeypatch):
    _override_user()
    _override_db()
    await _stub_upstreams(monkeypatch, error=UserServiceUnavailable("timeout"))

    response = await client.get("/api/ai/v1/home", headers=GATEWAY_HEADERS)

    assert response.status_code == 504


async def test_home_requires_the_gateway_secret(client):
    _override_user()
    _override_db()

    response = await client.get(
        "/api/ai/v1/home", headers={"X-User-Id": "7"}
    )

    assert response.status_code == 403


async def test_home_requires_the_user_header(client):
    # No dependency override: the real X-User-Id Header(...) dependency runs.
    _override_db()

    response = await client.get(
        "/api/ai/v1/home",
        headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
    )

    assert response.status_code == 422
