import pytest

from app.apps.profiles.models import Profile
from app.apps.users.services.me_service import get_current_user
from app.apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_get_current_user_returns_correct_user():
    user = UserFactory()
    Profile.objects.create(user=user, first_name="Fazil", last_name="C")

    result = get_current_user(user.id)

    assert result.id == user.id
    assert result.email == user.email


def test_get_current_user_prefetches_profile_in_one_query(django_assert_num_queries):
    user = UserFactory()
    Profile.objects.create(user=user, first_name="Fazil", last_name="C")

    with django_assert_num_queries(1):
        result = get_current_user(user.id)
        # accessing .profile here must NOT trigger a second query,
        # because select_related already joined it
        _ = result.profile.first_name