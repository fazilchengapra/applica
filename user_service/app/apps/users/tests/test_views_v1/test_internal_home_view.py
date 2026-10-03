"""Tests for the internal home-account aggregate consumed by the ai_service BFF.

These exercise the service-to-service contract, not the public home screen: the
endpoint must reject callers without the shared secret, must always return the
full shape, and must compute the four account-side onboarding steps correctly.
"""

import pytest
from django.test import Client
from django.utils import timezone

from app.apps.authentication.models import AuthMethod
from app.apps.profiles.models import Profile
from app.apps.users.models import User
from app.apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

SECRET_HEADER = "HTTP_X_INTERNAL_SECRET"


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def secret(settings):
    return "test-internal-secret"


@pytest.fixture
def internal_client(client, secret, settings):
    settings.GATEWAY_INTERNAL_SECRET = secret
    return client


def _url(user_id):
    return f"/internal/v1/users/home/{user_id}/"


def _get(internal_client, user_id, secret):
    return internal_client.get(_url(user_id), **{SECRET_HEADER: secret})


def test_internal_home_rejects_missing_secret(internal_client, user):
    assert internal_client.get(_url(user.id)).status_code == 403


def test_internal_home_rejects_empty_secret(internal_client, user, secret):
    assert _get(internal_client, user.id, "").status_code == 403


def test_internal_home_rejects_wrong_secret(internal_client, user):
    assert _get(internal_client, user.id, "not-the-secret").status_code == 403


def test_internal_home_allows_correct_secret(internal_client, user, secret):
    assert _get(internal_client, user.id, secret).status_code == 200


def test_internal_home_does_not_accept_browser_jwt(internal_client, user, secret):
    """No session auth on this route: a valid user must not be enough.

    Guards against someone re-exposing it as a public endpoint by relying on
    IsAuthenticated instead of the internal secret.
    """
    response = internal_client.force_login(user)
    assert response is None
    assert internal_client.get(_url(user.id)).status_code == 403


def test_internal_home_returns_full_shape_for_bare_user(internal_client, secret):
    """A user with no Profile and no AuthMethods still gets every section."""
    user = UserFactory()

    data = _get(internal_client, user.id, secret).json()

    assert set(data) == {
        "user",
        "profile",
        "account_steps",
        "linked_accounts",
    }
    assert data["profile"] == {
        "display_name": "",
        "avatar_url": "",
        "bio": "",
        "country": "",
        "city": "",
        "timezone": "",
        "locale": "",
    }
    assert data["linked_accounts"] == []
    # Nothing done yet.
    assert data["account_steps"] == {
        "verify_email": False,
        "verify_phone": False,
        "add_photo": False,
        "complete_profile": False,
    }


def test_internal_home_reports_roles_from_flags(internal_client, secret):
    plain = UserFactory()
    staff = UserFactory(is_staff=True)
    admin = UserFactory(is_staff=True, is_superuser=True)

    assert _get(internal_client, plain.id, secret).json()["user"]["roles"] == ["user"]
    assert _get(internal_client, staff.id, secret).json()["user"]["roles"] == [
        "user",
        "staff",
    ]
    assert _get(internal_client, admin.id, secret).json()["user"]["roles"] == [
        "user",
        "staff",
        "admin",
    ]


def test_internal_home_includes_last_login_and_verification_flags(
    internal_client, secret
):
    user = UserFactory(is_email_verified=True, is_phone_verified=True)
    last_login = timezone.now()
    User.objects.filter(id=user.id).update(last_login=last_login)

    data = _get(internal_client, user.id, secret).json()["user"]

    assert data["is_email_verified"] is True
    assert data["is_phone_verified"] is True
    assert data["last_login"] is not None
    assert data["is_staff"] is False


def test_internal_home_phone_number_is_a_string(internal_client, secret):
    user = UserFactory(phone_number="+917736077648")

    data = _get(internal_client, user.id, secret).json()["user"]

    assert data["phone_number"] == "+917736077648"


def test_internal_home_null_phone_number(internal_client, secret):
    user = UserFactory()

    data = _get(internal_client, user.id, secret).json()["user"]

    assert data["phone_number"] is None


def test_internal_home_lists_linked_accounts_in_provider_order(internal_client, secret):
    user = UserFactory()
    AuthMethod.objects.create(
        user=user, provider=AuthMethod.GOOGLE, is_verified=True, is_active=True
    )
    AuthMethod.objects.create(
        user=user, provider=AuthMethod.EMAIL, is_verified=True, is_active=False
    )

    accounts = _get(internal_client, user.id, secret).json()["linked_accounts"]

    assert [a["provider"] for a in accounts] == ["email", "google"]
    assert accounts[0]["is_active"] is False
    assert accounts[1]["is_active"] is True
    assert all(a["linked_at"] for a in accounts)


def test_internal_home_excludes_notifications(internal_client, secret):
    """The payload must not carry a notifications key at all.

    The unread count moved to notification_service, which owns the table. Leaving
    the key behind would let the BFF keep reading a stale local count, which is
    exactly the bug this migration is meant to prevent.
    """
    user = UserFactory()

    assert "notifications" not in _get(internal_client, user.id, secret).json()


@pytest.mark.parametrize(
    "profile_kwargs,expected",
    [
        (
            {
                "display_name": "Fazil",
                "bio": "dev",
                "country": "IN",
                "city": "Kochi",
            },
            True,
        ),
        ({"display_name": "Fazil", "bio": "dev", "country": "IN"}, False),
        ({"display_name": "   ", "bio": "x", "country": "IN", "city": "K"}, False),
        ({}, False),
    ],
)
def test_complete_profile_step_requires_all_four_fields(
    internal_client, secret, profile_kwargs, expected
):
    user = UserFactory()
    Profile.objects.create(user=user, **profile_kwargs)

    steps = _get(internal_client, user.id, secret).json()["account_steps"]

    assert steps["complete_profile"] is expected


def test_add_photo_step_tracks_avatar_url(internal_client, secret):
    without = UserFactory()
    Profile.objects.create(user=without)

    with_photo = UserFactory()
    Profile.objects.create(user=with_photo, avatar_url="https://example.com/a.png")

    assert (
        _get(internal_client, without.id, secret).json()["account_steps"]["add_photo"]
        is False
    )
    assert (
        _get(internal_client, with_photo.id, secret).json()["account_steps"][
            "add_photo"
        ]
        is True
    )


def test_internal_home_returns_404_for_unknown_user(internal_client, user, secret):
    missing_id = user.id + 1000

    assert _get(internal_client, missing_id, secret).status_code == 404


def test_internal_home_query_count_stays_low(
    internal_client, secret, django_assert_max_num_queries
):
    """Two queries: the user+profile join, then auth methods and unread count."""
    user = UserFactory()
    Profile.objects.create(
        user=user,
        display_name="Fazil",
        bio="dev",
        country="IN",
        city="Kochi",
    )
    AuthMethod.objects.create(user=user, provider=AuthMethod.EMAIL)

    with django_assert_max_num_queries(3):
        response = _get(internal_client, user.id, secret)

    assert response.status_code == 200
