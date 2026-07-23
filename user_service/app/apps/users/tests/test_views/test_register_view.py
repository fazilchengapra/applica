import pytest
from rest_framework.test import APIClient

from app.apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def call():
    print('its fazil')


def _valid_payload(**overrides):
    payload = {
        "first_name": "Fazil",
        "last_name": "Chengapra",
        "email": "newuser@example.com",
        "phone_number": "+919876543210",
        "password": "StrongPass123!",
        "confirm_password": "StrongPass123!",
    }
    payload.update(overrides)
    return payload


def test_register_success_returns_201(client, call, mailoutbox):
    response = client.post(
        "/api/v1/users/",  # adjust to your real urls.py path
        _valid_payload(),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["data"]["email"] == "newuser@example.com"
    assert len(mailoutbox) == 1


def test_register_password_mismatch_returns_400(client):
    response = client.post(
        "/api/v1/users/",
        _valid_payload(confirm_password="different"),
        format="json",
    )

    assert response.status_code == 400
    assert "confirm_password" in response.data["errors"]


def test_register_duplicate_email_returns_400_at_serializer_level(client):
    existing = UserFactory(email="taken@example.com")

    response = client.post(
        "/api/v1/users/",
        _valid_payload(email="taken@example.com"),
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.data["errors"]