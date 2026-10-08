"""Endpoint tests for POST /api/ai/v1/rag/load (the async document upload).

Real FastAPI app so gateway middleware and the X-User-Id dependency are
covered. The loader check runs for real (cheap extension/content-type match,
no parsing); document creation and the Celery enqueue are stubbed so no
database, broker or network is touched.
"""

import base64
import uuid
from types import SimpleNamespace

import httpx
import pytest
from httpx import ASGITransport

from app.api.v1 import rag
from app.core.config import settings
from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.modules.rag.constants import AccessLevel
from app.modules.rag.exceptions import DocumentTypeNotFoundError

GATEWAY_HEADERS = {
    "X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET,
    "X-User-Id": "7",
}

DOCUMENT_TYPE_ID = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000001")
DOCUMENT_ID = uuid.UUID("aaaaaaaa-0000-4000-8000-000000000002")


def _form_args():
    return {
        "document_type_id": str(DOCUMENT_TYPE_ID),
        "access_level": "internal",
    }


class FakeTask:
    def __init__(self):
        self.calls = []
        self.fail = False

    def delay(self, *args):
        if self.fail:
            raise RuntimeError("broker down")
        self.calls.append(args)


class FakeDB:
    def __init__(self):
        self.deleted = []
        self.commits = 0

    async def delete(self, row):
        self.deleted.append(row)

    async def commit(self):
        self.commits += 1


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


def _override_db(fake_db=None):
    async def _db():
        yield fake_db or object()

    app.dependency_overrides[get_db] = _db


def _stub_flow(monkeypatch, task=None):
    """Stub document creation + task enqueue; return their captures."""
    calls = {"task_calls": [], "create": None}

    async def _create(db, **kwargs):
        calls["create"] = kwargs
        return SimpleNamespace(
            id=DOCUMENT_ID, status=SimpleNamespace(value="processing")
        )

    fake_task = task or FakeTask()
    document = SimpleNamespace(id=DOCUMENT_ID, status=SimpleNamespace(value="processing"))
    monkeypatch.setattr(rag, "create_document", _create)
    monkeypatch.setattr(rag, "process_document_task", fake_task)
    calls["task"] = fake_task
    calls["document"] = document
    return calls


async def _run(client, files=None, data=None):
    return await client.post(
        "/api/ai/v1/rag/load",
        files=files or {"file": ("notes.txt", b"line one\nline two", "text/plain")},
        data=_form_args() if data is None else data,
        headers=GATEWAY_HEADERS,
    )


class TestLoad:
    async def test_txt_upload_is_enqueued(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_flow(monkeypatch)

        response = await _run(
            client, files={"file": ("notes.txt", b"line one\nline two", "text/plain")}
        )

        assert response.status_code == 202
        body = response.json()
        assert body == {
            "document_id": str(DOCUMENT_ID),
            "status": "processing",
        }
        assert calls["task"].calls == [
            (
                str(DOCUMENT_ID),
                base64.b64encode(b"line one\nline two").decode("ascii"),
                "notes.txt",
                "text/plain",
            )
        ]
        assert calls["create"]["title"] == "notes.txt"
        assert calls["create"]["document_type_id"] == DOCUMENT_TYPE_ID
        assert calls["create"]["access_level"] == AccessLevel.INTERNAL

    async def test_explicit_title_is_used(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_flow(monkeypatch)

        response = await _run(
            client,
            files={"file": ("notes.txt", b"line one", "text/plain")},
            data={**_form_args(), "title": "Quarterly Policy Notes"},
        )

        assert response.status_code == 202
        assert calls["create"]["title"] == "Quarterly Policy Notes"

    async def test_content_type_fallback_when_filename_has_no_extension(
        self, client, monkeypatch
    ):
        _override_user()
        _override_db()
        calls = _stub_flow(monkeypatch)

        response = await _run(
            client, files={"file": ("blob", b"fallback text", "text/plain")}
        )

        assert response.status_code == 202
        assert len(calls["task"].calls) == 1

    async def test_invalid_access_level_is_a_422(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_flow(monkeypatch)

        response = await _run(
            client, data={**_form_args(), "access_level": "public-ish"}
        )

        assert response.status_code == 422
        assert "access_level" in response.json()["detail"]
        assert calls["task"].calls == []

    async def test_unknown_document_type_is_a_404(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _boom(db, **kwargs):
            raise DocumentTypeNotFoundError("Document type not found")

        monkeypatch.setattr(rag, "create_document", _boom)
        task = FakeTask()
        monkeypatch.setattr(rag, "process_document_task", task)

        response = await _run(client)

        assert response.status_code == 404
        assert response.json()["detail"] == "Document type not found"
        assert task.calls == []

    async def test_unsupported_type_is_a_400(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_flow(monkeypatch)

        response = await _run(
            client, files={"file": ("archive.tar.gz", b"\x00\x01", "application/gzip")}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Unsupported file type: archive.tar.gz"
        assert calls["task"].calls == []

    async def test_enqueue_failure_is_a_503(self, client, monkeypatch):
        _override_user()
        fake_db = FakeDB()
        _override_db(fake_db)
        calls = _stub_flow(monkeypatch)
        calls["task"].fail = True

        response = await _run(client)

        assert response.status_code == 503
        assert "Could not enqueue processing job" in response.json()["detail"]
        assert len(fake_db.deleted) == 1


class TestQuery:
    async def test_query_is_embedded_and_echoed(self, client, monkeypatch):
        _override_user()
        called = []

        async def _embed(texts):
            called.append(list(texts))
            return [[0.5] * 1024]

        monkeypatch.setattr(rag, "embed_chunks", _embed)

        response = await client.post(
            "/api/ai/v1/rag/query",
            json={"query": "how i can use this platform"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "how i can use this platform"
        assert body["embedding"] == [0.5] * 1024
        assert called == [["how i can use this platform"]]

    async def test_embedding_failure_is_a_502(self, client, monkeypatch):
        _override_user()

        async def _embed(texts):
            raise RuntimeError("upstream refused")

        monkeypatch.setattr(rag, "embed_chunks", _embed)

        response = await client.post(
            "/api/ai/v1/rag/query",
            json={"query": "how i can use this platform"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 502
        assert "Embedding failed" in response.json()["detail"]


class TestSearch:
    def _chunk(self, index=0, content="refund within 30 days"):
        return SimpleNamespace(
            document_id=DOCUMENT_ID,
            doc_type="policy",
            access_level="internal",
            chunk_index=index,
            content=content,
        )

    async def test_query_is_embedded_searched_and_context_built(self, client, monkeypatch):
        _override_user()
        _override_db()
        embed_calls = []

        async def _embed(texts):
            embed_calls.append(list(texts))
            return [[0.1] * 1024]

        async def _search(db, **kwargs):
            return [(self._chunk(0), 0.7921), (self._chunk(1, "damaged items are refunded"), 0.618)]

        monkeypatch.setattr(rag, "embed_chunks", _embed)
        monkeypatch.setattr(rag, "search_chunks", _search)

        response = await client.post(
            "/api/ai/v1/rag/search",
            json={"query": "how do i get my money back"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "how do i get my money back"
        assert embed_calls == [["how do i get my money back"]]
        assert len(body["chunks"]) == 2
        first = body["chunks"][0]
        assert first["document_id"] == str(DOCUMENT_ID)
        assert first["doc_type"] == "policy"
        assert first["chunk_index"] == 0
        assert first["score"] == 0.7921
        assert "[policy | access=internal | #0]" in body["context"]
        assert "refund within 30 days" in body["context"]
        assert "damaged items are refunded" in body["context"]

    async def test_embedding_failure_is_a_502(self, client, monkeypatch):
        _override_user()

        async def _embed(texts):
            raise RuntimeError("upstream refused")

        monkeypatch.setattr(rag, "embed_chunks", _embed)

        response = await client.post(
            "/api/ai/v1/rag/search",
            json={"query": "how do i get my money back"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 502
        assert "Embedding failed" in response.json()["detail"]

    async def test_search_failure_is_a_500(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _embed(texts):
            return [[0.1] * 1024]

        async def _boom(db, **kwargs):
            raise RuntimeError("vector index down")

        monkeypatch.setattr(rag, "embed_chunks", _embed)
        monkeypatch.setattr(rag, "search_chunks", _boom)

        response = await client.post(
            "/api/ai/v1/rag/search",
            json={"query": "how do i get my money back"},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]


class TestGatewayGuards:
    async def test_requires_the_gateway_secret(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("a.txt", b"x", "text/plain")},
            data=_form_args(),
            headers={"X-User-Id": "7"},
        )

        assert response.status_code == 403

    async def test_requires_the_user_header(self, client):
        _override_db()

        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("a.txt", b"x", "text/plain")},
            data=_form_args(),
            headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
        )

        assert response.status_code == 422

    async def test_requires_the_upload_metadata(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("a.txt", b"x", "text/plain")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 422