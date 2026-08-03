import pytest
from django.utils import timezone
 
from app.apps.users.exception import InvalidPasswordError
from app.apps.users.services.acc_dlt_service import delete_account
from app.apps.users import tasks
from app.apps.users.tests.factories import UserFactory, DEFAULT_PASSWORD
 
pytestmark = pytest.mark.django_db
 
 
def test_raises_on_incorrect_password():
    """Wrong password must not touch the row or queue any task."""
    user = UserFactory()
 
    with pytest.raises(InvalidPasswordError):
        delete_account(user, password="wrong-password")
 
    user.refresh_from_db()
    assert user.is_active is True
    assert user.deactivated_at is None

def test_deactivates_user_on_correct_password():
    user = UserFactory()
    before = timezone.now()
 
    delete_account(user, password=DEFAULT_PASSWORD)
 
    user.refresh_from_db()
    assert user.is_active is False
    assert user.deactivated_at is not None
    assert user.deactivated_at >= before

def test_only_updates_expected_fields(mocker):
        
    user = UserFactory()
    save_spy = mocker.spy(user, "save")
 
    delete_account(user, password=DEFAULT_PASSWORD)
 
    save_spy.assert_called_once_with(update_fields=["is_active", "deactivated_at"])