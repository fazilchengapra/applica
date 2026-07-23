import pytest
from django.db import IntegrityError

from app.apps.authentication.constants import verification_type
from app.apps.authentication.models.auth_method import AuthMethod
from app.apps.authentication.models.verification_token import VerificationToken
from app.apps.profiles.models import Profile
from app.apps.users.models import User
from app.apps.users.services.register_service import register_user

pytestmark = pytest.mark.django_db


def _valid_payload(**overrides):
    payload = {
        "first_name": "Fazil",
        "last_name": "Chengapra",
        "email": "fazil@example.com",
        "phone_number": "+919876543210",
        "password": "StrongPass123!",
    }
    payload.update(overrides)
    return payload


def test_register_creates_user(mailoutbox):
    user = register_user(**_valid_payload())

    assert User.objects.filter(pk=user.pk).exists()
    assert user.email == "fazil@example.com"
    assert user.check_password("StrongPass123!")
    assert user.is_email_verified is False
    assert user.is_phone_verified is False


def test_register_creates_profile_with_names(mailoutbox):
    user = register_user(**_valid_payload(first_name="Fazil", last_name="Chengapra"))

    profile = Profile.objects.get(user=user)
    assert profile.first_name == "Fazil"
    assert profile.last_name == "Chengapra"
    assert profile.display_name == "Fazil"


def test_register_creates_email_and_mobile_auth_methods(mailoutbox):
    user = register_user(**_valid_payload())

    providers = set(
        AuthMethod.objects.filter(user=user).values_list("provider", flat=True)
    )
    assert providers == {AuthMethod.EMAIL, AuthMethod.MOBILE}

    email_method = AuthMethod.objects.get(user=user, provider=AuthMethod.EMAIL)
    assert email_method.is_verified is False


def test_register_creates_verification_token_linked_to_email_auth_method(mailoutbox):
    user = register_user(**_valid_payload())

    email_method = AuthMethod.objects.get(user=user, provider=AuthMethod.EMAIL)
    token = VerificationToken.objects.get(user=user)

    assert token.type == verification_type.EMAIL_TYPE
    assert token.auth_method_id == email_method.id
    assert token.used_at is None
    assert token.revoked_at is None
    assert token.expires_at > token.created_at


def test_register_sends_verification_email(mailoutbox):
    register_user(**_valid_payload(email="verify-me@example.com"))

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["verify-me@example.com"]
    assert "verify-email" in mailoutbox[0].body


def test_register_duplicate_email_raises_integrity_error(mailoutbox):
    register_user(**_valid_payload(email="dupe@example.com", phone_number="+919876500001"))

    with pytest.raises(IntegrityError):
        register_user(
            **_valid_payload(email="dupe@example.com", phone_number="+919876500002")
        )


def test_register_duplicate_phone_raises_integrity_error(mailoutbox):
    register_user(**_valid_payload(email="a@example.com", phone_number="+919876500003"))

    with pytest.raises(IntegrityError):
        register_user(
            **_valid_payload(email="b@example.com", phone_number="+919876500003")
        )