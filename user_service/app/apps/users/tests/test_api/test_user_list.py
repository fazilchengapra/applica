import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from app.apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def test_list_users_returns_paginated_minimal_fields(api_client):
    admin = User.objects.create_user(
        email="admin@example.com",
        password="StrongPass123!",
        is_staff=True,
        is_active=True,
    )

    User.objects.create_user(
        email="user1@example.com",
        password="StrongPass123!",
        is_active=True,
    )
    User.objects.create_user(
        email="user2@example.com",
        password="StrongPass123!",
        is_active=False,
    )

    api_client.force_authenticate(user=admin)
    response = api_client.get("/api/v1/users/?page=1")

    assert response.status_code == 200
    assert response.data["count"] == 3
    assert len(response.data["results"]) == 3

    first_item = response.data["results"][0]
    assert set(first_item.keys()) == {"id", "username", "email", "is_active"}
    assert first_item["username"] == "admin"
    assert first_item["email"] == "admin@example.com"
    assert first_item["is_active"] is True

    inactive = next(
        item
        for item in response.data["results"]
        if item["email"] == "user2@example.com"
    )
    assert inactive["is_active"] is False

    search_response = api_client.get("/api/v1/users/?search=admin")
    assert search_response.status_code == 200
    assert search_response.data["count"] == 1
    assert search_response.data["results"][0]["email"] == "admin@example.com"

    search_email_response = api_client.get("/api/v1/users/?search=user1")
    assert search_email_response.status_code == 200
    assert search_email_response.data["count"] == 1
    assert search_email_response.data["results"][0]["email"] == "user1@example.com"


def test_admin_can_toggle_user_active_status(api_client):
    admin = User.objects.create_user(
        email="admin@example.com",
        password="StrongPass123!",
        is_staff=True,
        is_active=True,
    )
    user = User.objects.create_user(
        email="target@example.com",
        password="StrongPass123!",
        is_active=True,
    )

    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        f"/api/v1/users/admin/{user.id}/toggle-active/",
        {"is_active": False},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active is False
    assert response.data["is_active"] is False

    second = api_client.patch(
        f"/api/v1/users/admin/{user.id}/toggle-active/",
        {"is_active": True},
        format="json",
    )

    assert second.status_code == 200
    user.refresh_from_db()
    assert user.is_active is True
    assert second.data["is_active"] is True


def test_admin_can_view_user_overview(api_client):
    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPass123!",
        phone_number="+919876543210",
        is_active=False,
        is_email_verified=True,
        is_phone_verified=False,
        deactivated_at=timezone.now(),
    )

    response = api_client.get(f"/api/v1/users/admin/{user.id}/overview/")

    assert response.status_code == 200
    assert response.data["id"] == user.id
    assert response.data["contact"] == {
        "email": "user@example.com",
        "phone_number": "+919876543210",
    }
    assert response.data["account"]["status"] == "deactivated"
    assert response.data["account"]["is_active"] is False
    assert response.data["account"]["is_deactivated"] is True
    assert response.data["account"]["deactivated_at"] is not None
    assert response.data["permissions"] == {
        "is_staff": False,
        "is_superuser": False,
    }
    assert response.data["verification"] == {
        "email_verified": True,
        "phone_verified": False,
    }
    assert set(response.data["timestamps"]) == {
        "joined_at",
        "last_login",
        "last_updated",
    }
