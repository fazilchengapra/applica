"""Tests for the notification purge task that account deletion depends on.

`notifications` lives in notification_service's own database, so there is no
foreign key to cascade and this task is the only thing that cleans those rows up
after an account is deactivated. That makes its failure behaviour worth pinning
down: it must ask for a retry on a transport failure rather than dropping the
purge on the floor, and it must not raise once retries are spent, because the
account is already deactivated by then and must stay that way.

Note that these call the task function directly. Celery treats that as
`request.called_directly` and re-raises the original exception from `retry()`
rather than a `Retry`, so the contract worth asserting is that `retry` was
requested, not which exception escapes.
"""

import pytest
import requests
from celery.exceptions import MaxRetriesExceededError, Retry

from app.apps.users import tasks

USER_ID = 4242


def _mock_delete(mocker, *, side_effect=None, status=200):
    """Patch requests.delete inside the task module and return the mock."""
    delete = mocker.patch(
        "app.apps.users.tasks.requests.delete",
        side_effect=side_effect,
    )
    if side_effect is None:
        delete.return_value.status_code = status
        delete.return_value.json.return_value = {"deleted": 3}
        if status >= 400:
            delete.return_value.raise_for_status.side_effect = requests.HTTPError(
                f"{status} Server Error"
            )
    return delete


def test_purges_via_the_internal_endpoint(mocker):
    delete = _mock_delete(mocker)

    tasks.purge_notifications_task(USER_ID)

    delete.assert_called_once()
    url = delete.call_args[0][0]
    headers = delete.call_args[1]["headers"]
    assert url.endswith(f"/api/v1/notifications/internal/users/{USER_ID}/notifications")
    assert headers["X-Internal-Service"] == "user-service"
    assert headers["X-Internal-Secret"]


def test_requests_a_retry_when_the_transport_fails(mocker):
    """A notification_service outage must not silently leave the rows behind."""
    retry = mocker.patch.object(
        tasks.purge_notifications_task, "retry", side_effect=Retry()
    )
    _mock_delete(mocker, side_effect=requests.ConnectionError("connection refused"))

    with pytest.raises(Retry):
        tasks.purge_notifications_task(USER_ID)

    retry.assert_called_once()


def test_requests_a_retry_on_an_error_status(mocker):
    retry = mocker.patch.object(
        tasks.purge_notifications_task, "retry", side_effect=Retry()
    )
    _mock_delete(mocker, status=500)

    with pytest.raises(Retry):
        tasks.purge_notifications_task(USER_ID)

    retry.assert_called_once()


def test_gives_up_quietly_once_retries_are_spent(mocker):
    """After the last retry the purge is dropped, not raised.

    The account is already deactivated; surfacing this would turn a cleanup
    problem into a deactivation the user cannot complete.
    """
    mocker.patch.object(
        tasks.purge_notifications_task,
        "retry",
        side_effect=MaxRetriesExceededError(),
    )
    _mock_delete(mocker, side_effect=requests.ConnectionError("connection refused"))

    tasks.purge_notifications_task(USER_ID)  # must not raise


def test_does_not_retry_on_success(mocker):
    retry = mocker.patch.object(
        tasks.purge_notifications_task, "retry", side_effect=Retry()
    )
    _mock_delete(mocker)

    tasks.purge_notifications_task(USER_ID)

    retry.assert_not_called()