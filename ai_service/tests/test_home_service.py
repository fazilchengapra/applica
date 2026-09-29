"""Tests for the composed home aggregate (the BFF).

Covers the three pieces that can break without any real upstream:
- ``_build_onboarding``: the step list, labels and percent arithmetic.
- ``build_home``: that account data and the CV step are merged correctly.
- ``fetch_account``: how user_service responses and failures are classified.

The public endpoint's own request/response behaviour is covered in
``test_home_router.py``.
"""

from datetime import datetime, timezone

import httpx
import pytest

from app.modules.home import clients, repository
from app.modules.home.exceptions import UserServiceError, UserServiceUnavailable
from app.modules.home.schemas import (
    AccountPayload,
    AccountStepFlags,
    HomeNotifications,
    HomeProfile,
    HomeUser,
    OnboardingStepKey,
)
from app.modules.home.services.home_service import _build_onboarding, build_home


def _user(**overrides) -> HomeUser:
    base = dict(
        id=1,
        email="a@example.com",
        phone_number=None,
        is_email_verified=False,
        is_phone_verified=False,
        date_joined=datetime(2025, 1, 1, tzinfo=timezone.utc),
        last_login=None,
        is_staff=False,
        roles=["user"],
    )
    base.update(overrides)
    return HomeUser(**base)


def _account(**overrides) -> AccountPayload:
    base = dict(
        user=_user(),
        profile=HomeProfile(),
        account_steps=AccountStepFlags(),
        notifications=HomeNotifications(),
        linked_accounts=[],
    )
    base.update(overrides)
    return AccountPayload(**base)


# --- _build_onboarding --------------------------------------------------------


def test_onboarding_has_five_steps_in_display_order():
    onboarding = _build_onboarding(AccountStepFlags(), has_cv=False)

    assert [s.key for s in onboarding.steps] == [
        OnboardingStepKey.verify_email,
        OnboardingStepKey.verify_phone,
        OnboardingStepKey.add_photo,
        OnboardingStepKey.complete_profile,
        OnboardingStepKey.upload_cv,
    ]


def test_onboarding_every_step_has_a_label():
    onboarding = _build_onboarding(AccountStepFlags(), has_cv=False)

    assert all(step.label for step in onboarding.steps)


@pytest.mark.parametrize(
    "steps,has_cv,expected_done,expected_percent",
    [
        (AccountStepFlags(), False, 0, 0),
        (AccountStepFlags(verify_email=True), False, 1, 20),
        (AccountStepFlags(verify_email=True, verify_phone=True), False, 2, 40),
        (AccountStepFlags(verify_email=True, verify_phone=True), True, 3, 60),
        (
            AccountStepFlags(
                verify_email=True,
                verify_phone=True,
                add_photo=True,
                complete_profile=True,
            ),
            False,
            4,
            80,
        ),
        (
            AccountStepFlags(
                verify_email=True,
                verify_phone=True,
                add_photo=True,
                complete_profile=True,
            ),
            True,
            5,
            100,
        ),
    ],
)
def test_onboarding_percent(steps, has_cv, expected_done, expected_percent):
    onboarding = _build_onboarding(steps, has_cv)

    assert sum(1 for s in onboarding.steps if s.done) == expected_done
    assert onboarding.percent == expected_percent


def test_onboarding_upload_cv_comes_from_has_cv():
    onboarding = _build_onboarding(AccountStepFlags(), has_cv=True)

    upload = next(s for s in onboarding.steps if s.key == OnboardingStepKey.upload_cv)
    assert upload.done is True


# --- build_home ---------------------------------------------------------------


async def test_build_home_merges_account_state_and_cv_step(monkeypatch):
    account = _account(
        user=_user(id=7, email="me@example.com", roles=["user", "staff"]),
        account_steps=AccountStepFlags(verify_email=True, add_photo=True),
        notifications=HomeNotifications(unread=3),
    )

    async def fetch(user_id):
        assert user_id == 7
        return account

    async def has_cv(db, user_id):
        return True

    monkeypatch.setattr(clients, "fetch_account", fetch)
    monkeypatch.setattr(repository, "has_uploaded_cv", has_cv)

    result = await build_home(db=object(), user_id=7)

    assert result.user.id == 7
    assert result.user.email == "me@example.com"
    assert result.notifications.unread == 3
    # verify_email + add_photo + upload_cv
    assert result.onboarding.percent == 60
    assert result.generated_at is not None


async def test_build_home_propagates_upstream_failure(monkeypatch):
    async def boom(user_id):
        raise UserServiceUnavailable("nope")

    async def no_cv(db, user_id):
        return False

    monkeypatch.setattr(clients, "fetch_account", boom)
    monkeypatch.setattr(repository, "has_uploaded_cv", no_cv)

    with pytest.raises(UserServiceUnavailable):
        await build_home(db=object(), user_id=1)


# --- fetch_account ------------------------------------------------------------


def _mock_transport(monkeypatch, handler):
    """Force the client module's AsyncClient to use an in-process transport.

    ``clients.httpx`` is the real httpx module object, so patching the attribute
    there is global; the real class is captured first to avoid the factory
    calling itself.
    """
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(clients.httpx, "AsyncClient", factory)


async def test_fetch_account_parses_a_valid_reply(monkeypatch):
    def handler(request):
        assert request.headers["X-Internal-Secret"] == clients.settings.GATEWAY_INTERNAL_SECRET
        assert request.url.path == "/internal/v1/users/home/7/"
        return httpx.Response(
            200,
            json=_account(user=_user(id=7), notifications=HomeNotifications(unread=2)).model_dump(
                mode="json"
            ),
        )

    _mock_transport(monkeypatch, handler)

    account = await clients.fetch_account(7)

    assert account.user.id == 7
    assert account.notifications.unread == 2


async def test_fetch_account_maps_5xx_to_userserviceerror(monkeypatch):
    _mock_transport(monkeypatch, lambda request: httpx.Response(500, text="boom"))

    with pytest.raises(UserServiceError):
        await clients.fetch_account(7)


async def test_fetch_account_maps_404_to_userserviceerror(monkeypatch):
    _mock_transport(monkeypatch, lambda request: httpx.Response(404, json={}))

    with pytest.raises(UserServiceError):
        await clients.fetch_account(7)


async def test_fetch_account_maps_timeout_to_unavailable(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("too slow")

    _mock_transport(monkeypatch, handler)

    with pytest.raises(UserServiceUnavailable):
        await clients.fetch_account(7)


async def test_fetch_account_maps_connect_error_to_unavailable(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    _mock_transport(monkeypatch, handler)

    with pytest.raises(UserServiceUnavailable):
        await clients.fetch_account(7)


async def test_fetch_account_rejects_a_malformed_body(monkeypatch):
    _mock_transport(monkeypatch, lambda request: httpx.Response(200, json={"nope": 1}))

    with pytest.raises(UserServiceError):
        await clients.fetch_account(7)
