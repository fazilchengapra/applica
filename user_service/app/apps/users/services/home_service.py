"""Assembles the account half of the home aggregate.

This service owns the four account onboarding steps it can actually evaluate
(``verify_email``, ``verify_phone``, ``add_photo``, ``complete_profile``) plus
the notification unread count, because the ``Notification`` table lives in this
service.

The ``upload_cv`` step is deliberately *not* computed here: the master CV lives
in ai_service's database. The BFF owns that step and the overall percent.
"""

from app.apps.authentication.models import AuthMethod
from app.apps.notifications.models import Notification
from app.apps.users.models import User
from app.apps.users.services.roles_service import get_user_roles

# Fields that must all be filled for a profile to count as complete. Kept as a
# tuple so the rule is asserted in one place and easy to widen or tighten.
COMPLETE_PROFILE_FIELDS = ("display_name", "bio", "country", "city")


class UserNotFoundError(Exception):
    """Raised when the requested user does not exist."""


def _count_unread_notifications(user) -> int:
    """Number of the user's notifications that have not been read.

    Unread is ``read_at IS NULL``. The composite index
    ``idx_user_read_created (user, read_at, -created_at)`` covers this filter.
    """
    return Notification.objects.filter(user=user, read_at__isnull=True).count()


def _is_profile_complete(profile) -> bool:
    if profile is None:
        return False

    return all(
        bool(getattr(profile, field_name, "").strip())
        for field_name in COMPLETE_PROFILE_FIELDS
    )


def _build_linked_accounts(user) -> list[dict]:
    """One entry per authentication method linked to the user.

    Ordered by provider so the payload is stable between calls.
    """
    return [
        {
            "provider": auth_method.provider,
            "is_verified": auth_method.is_verified,
            "is_active": auth_method.is_active,
            "linked_at": auth_method.linked_at,
        }
        for auth_method in AuthMethod.objects.filter(user=user).order_by("provider")
    ]


def _build_account_steps(user, profile) -> dict[str, bool]:
    """The four onboarding steps this service can evaluate."""
    return {
        "verify_email": bool(user.is_email_verified),
        "verify_phone": bool(user.is_phone_verified),
        "add_photo": bool(profile is not None and profile.avatar_url.strip()),
        "complete_profile": _is_profile_complete(profile),
    }


def _build_profile(profile) -> dict:
    """Serialize the profile, tolerating a user that has no Profile row yet.

    ``Profile`` is a OneToOne created on registration, but rows can be absent
    (e.g. accounts created before the profile was introduced), so every field
    falls back to an empty value rather than raising.
    """
    if profile is None:
        return {
            "display_name": "",
            "avatar_url": "",
            "bio": "",
            "country": "",
            "city": "",
            "timezone": "",
            "locale": "",
        }

    return {
        "display_name": profile.display_name,
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "country": profile.country,
        "city": profile.city,
        "timezone": profile.timezone,
        "locale": profile.locale,
    }


def build_home_account(user_id: int) -> dict:
    """Everything the home aggregate needs that lives in this service.

    Two queries total: the user joined to its profile, then the auth methods
    and unread count (which is a single aggregate query rather than fetching
    notification rows).
    """
    try:
        user = User.objects.select_related("profile").get(id=user_id)
    except User.DoesNotExist as e:
        raise UserNotFoundError(f"User {user_id} does not exist") from e

    profile = getattr(user, "profile", None)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            # PhoneNumber renders as an object; force E.164-ish string form.
            "phone_number": str(user.phone_number) if user.phone_number else None,
            "is_email_verified": user.is_email_verified,
            "is_phone_verified": user.is_phone_verified,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
            "is_staff": user.is_staff,
            "roles": get_user_roles(user),
        },
        "profile": _build_profile(profile),
        "account_steps": _build_account_steps(user, profile),
        "notifications": {"unread": _count_unread_notifications(user)},
        "linked_accounts": _build_linked_accounts(user),
    }
