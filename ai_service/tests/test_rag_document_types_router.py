"""Endpoint-level tests for the dynamic document-type catalog routes.

Real FastAPI app; the repository functions are stubbed at their module
boundary, so no database is touched.
"""

import uuid
from datetime import datetime

import httpx
import pytest
from httpx import ASGITransport

from app.api.v1 import rag
from app.core.config import settings
from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.modules.rag.exceptions import (
    DocumentTypeNameTakenError,
    DocumentTypeNotFoundError,
)
from app.modules.rag.schemas import DocumentTypeOut

GATEWAY_HEADERS = {
    "X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET,
    "X-User-Id": "7",
}

TYPE_ID = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")


def _type(name="policy", description="Company policies", type_id=TYPE_ID):
    return DocumentTypeOut(
        id=type_id,
        name=name,
        description=description,
        created_at=datetime(2026, 10, 7),
    )


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


class TestListDocumentTypes:
    async def test_lists_all_types(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _stub(db):
            return [_type("policy"), _type(name="investor", description=None)]

        monkeypatch.setattr(rag, "list_document_types", _stub)

        response = await client.get(
            "/api/ai/v1/rag/document-types", headers=GATEWAY_HEADERS
        )

        assert response.status_code == 200
        body = response.json()
        assert [row["name"] for row in body] == ["policy", "investor"]
        assert body[0]["description"] == "Company policies"

    async def test_requires_the_user_header(self, client):
        response = await client.get(
            "/api/ai/v1/rag/document-types",
            headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
        )
        assert response.status_code == 422


class TestCreateDocumentType:
    async def test_creates_a_type(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = {}

        async def _stub(db, name, description=None):
            calls.update(name=name, description=description)
            return _type(name=name, description=description)

        monkeypatch.setattr(rag, "create_document_type", _stub)

        response = await client.post(
            "/api/ai/v1/rag/document-types",
            json={"name": "shareholder-agreement", "description": "SA docs"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 201
        assert response.json()["name"] == "shareholder-agreement"
        assert calls == {
            "name": "shareholder-agreement",
            "description": "SA docs",
        }

    async def test_duplicate_name_is_a_409(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _stub(db, name, description=None):
            raise DocumentTypeNameTakenError("A document type named 'policy' already exists")

        monkeypatch.setattr(rag, "create_document_type", _stub)

        response = await client.post(
            "/api/ai/v1/rag/document-types",
            json={"name": "policy"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_invalid_body_is_a_422(self, client, monkeypatch):
        _override_user()
        _override_db()

        response = await client.post(
            "/api/ai/v1/rag/document-types",
            json={"name": ""},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 422


class TestUpdateDocumentType:
    async def test_updates_name_and_description(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = {}

        async def _stub(db, type_id, name=None, description=None):
            calls.update(type_id=type_id, name=name, description=description)
            return _type(name=name, description=description)

        monkeypatch.setattr(rag, "update_document_type", _stub)

        response = await client.put(
            f"/api/ai/v1/rag/document-types/{TYPE_ID}",
            json={"name": "policy", "description": "Updated"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["description"] == "Updated"
        assert calls == {
            "type_id": TYPE_ID,
            "name": "policy",
            "description": "Updated",
        }

    async def test_missing_type_is_a_404(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _stub(db, type_id, name=None, description=None):
            raise DocumentTypeNotFoundError("Document type not found")

        monkeypatch.setattr(rag, "update_document_type", _stub)

        response = await client.put(
            f"/api/ai/v1/rag/document-types/{TYPE_ID}",
            json={"name": "policy"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 404

    async def test_taken_name_is_a_409(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _stub(db, type_id, name=None, description=None):
            raise DocumentTypeNameTakenError("A document type named 'investor' already exists")

        monkeypatch.setattr(rag, "update_document_type", _stub)

        response = await client.put(
            f"/api/ai/v1/rag/document-types/{TYPE_ID}",
            json={"name": "investor"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 409