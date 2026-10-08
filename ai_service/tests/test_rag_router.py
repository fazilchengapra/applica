"""Endpoint tests for POST /api/ai/v1/rag/load (the document upload workflow).

Real FastAPI app so gateway middleware and the X-User-Id dependency are
covered. Parsing runs against the real loaders; embedding and DB persistence
are stubbed at their module boundaries so no network or database is touched.
"""

import io
import uuid
import zipfile
from datetime import datetime
from types import SimpleNamespace

import fitz
import httpx
import pytest
from httpx import ASGITransport

from app.api.v1 import rag
from app.core.config import settings
from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.main import app
from app.modules.rag.exceptions import DocumentTypeNotFoundError
from app.modules.rag.utils.hashing import calculate_hash

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


def _pdf_with_text(text: str) -> bytes:
    document = fitz.open()
    document.new_page().insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def _blank_pdf() -> bytes:
    document = fitz.open()
    document.new_page()
    data = document.tobytes()
    document.close()
    return data


def _docx(paragraphs: list[str]) -> bytes:
    body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


HTML_BYTES = b"""<!DOCTYPE html>
<html><head><title>Page Title</title><script>var x = 1;</script></head>
<body><h1>Heading One</h1><p>First paragraph.</p><p>Second paragraph.</p></body></html>"""


def _fake_document():
    return SimpleNamespace(
        id=DOCUMENT_ID,
        document_type_id=DOCUMENT_TYPE_ID,
        title="policy.txt",
        version=1,
        access_level=SimpleNamespace(value="internal"),
        status=SimpleNamespace(value="completed"),
        content_hash="c" * 64,
        created_at=datetime(2026, 10, 8),
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


def _stub_pipeline(monkeypatch, save_handler=None):
    """Stub embedding + persistence so the real loaders/chunking run."""
    calls = {}

    async def _embed(texts):
        calls["texts"] = list(texts)
        return [[0.1] for _ in texts]

    async def _save(db, **kwargs):
        calls.update(kwargs)
        if save_handler is not None:
            return await save_handler(db, **kwargs)
        return _fake_document()

    async def _get_type(db, document_type_id):
        return SimpleNamespace(name="policy")

    monkeypatch.setattr(rag, "embed_chunks", _embed)
    monkeypatch.setattr(rag, "save_document_with_chunks", _save)
    monkeypatch.setattr(rag, "get_document_type", _get_type)
    return calls


async def _run(client, files=None, data=None):
    return await client.post(
        "/api/ai/v1/rag/load",
        files=files or {"file": ("notes.txt", b"line one\nline two", "text/plain")},
        data=_form_args() if data is None else data,
        headers=GATEWAY_HEADERS,
    )


class TestLoad:
    async def test_txt_upload_is_chunked_embedded_and_persisted(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("notes.txt", b"line one\nline two", "text/plain")}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["id"] == str(DOCUMENT_ID)
        assert body["doc_type"] == "policy"
        assert body["access_level"] == "internal"
        assert body["status"] == "completed"
        assert body["chunk_count"] == 1
        assert calls["content_hash"] == calculate_hash("line one\nline two")

        saved_chunks = calls["chunks"]
        assert len(saved_chunks) == 1
        assert saved_chunks[0].text == "line one\nline two"
        assert calls["texts"] == ["line one\nline two"]
        assert saved_chunks[0].content_hash == calculate_hash("line one\nline two")
        assert calls["embeddings"] == [[0.1]]
        assert calls["title"] == "notes.txt"

    async def test_a_long_document_gets_multiple_chunks(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_pipeline(monkeypatch)

        text = ("word " * 3000).strip()
        response = await _run(
            client, files={"file": ("long.txt", text.encode(), "text/plain")}
        )

        assert response.status_code == 201
        saved_chunks = calls["chunks"]
        assert len(saved_chunks) > 1
        indices = [chunk.index for chunk in saved_chunks]
        assert indices == list(range(len(saved_chunks)))
        assert all(chunk.content_hash for chunk in saved_chunks)
        assert len(calls["embeddings"]) == len(saved_chunks)

    async def test_pdf(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("cv.pdf", _pdf_with_text("Hello PDF"), "application/pdf")}
        )

        assert response.status_code == 201
        content = " ".join(chunk.text for chunk in calls["chunks"])
        assert "Hello PDF" in content

    async def test_docx(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("policy.docx", _docx(["Intro.", "Refund rules"]), None)}
        )

        assert response.status_code == 201
        content = " ".join(chunk.text for chunk in calls["chunks"])
        assert content == "Intro.\nRefund rules"

    async def test_html(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("page.html", HTML_BYTES, "text/html")}
        )

        assert response.status_code == 201
        content = " ".join(chunk.text for chunk in calls["chunks"])
        assert "Heading One" in content
        assert "First paragraph." in content
        assert "var x" not in content

    async def test_content_type_fallback_when_filename_has_no_extension(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("blob", b"fallback text", "text/plain")}
        )

        assert response.status_code == 201
        assert calls["chunks"][0].text == "fallback text"

    async def test_explicit_title_is_used(self, client, monkeypatch):
        _override_user()
        _override_db()
        calls = _stub_pipeline(monkeypatch)

        response = await _run(
            client,
            files={"file": ("notes.txt", b"line one", "text/plain")},
            data={**_form_args(), "title": "Quarterly Policy Notes"},
        )

        assert response.status_code == 201
        assert calls["title"] == "Quarterly Policy Notes"

    async def test_invalid_access_level_is_a_422(self, client, monkeypatch):
        _override_user()
        _override_db()
        _stub_pipeline(monkeypatch)

        response = await _run(
            client, data={**_form_args(), "access_level": "public-ish"}
        )

        assert response.status_code == 422
        assert "access_level" in response.json()["detail"]

    async def test_unknown_document_type_is_a_404(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _boom(db, **kwargs):
            raise DocumentTypeNotFoundError("Document type not found")

        _stub_pipeline(monkeypatch, save_handler=_boom)

        response = await _run(client)

        assert response.status_code == 404
        assert response.json()["detail"] == "Document type not found"

    async def test_embedding_service_failure_is_a_502(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _embed(texts):
            raise RuntimeError("upstream refused")

        monkeypatch.setattr(rag, "embed_chunks", _embed)

        response = await _run(client)

        assert response.status_code == 502
        assert "Embedding failed" in response.json()["detail"]

    async def test_embedding_count_mismatch_is_a_502(self, client, monkeypatch):
        _override_user()
        _override_db()

        async def _embed(texts):
            return [[0.1]]  # fewer than the multiple chunks

        monkeypatch.setattr(rag, "embed_chunks", _embed)

        text = ("word " * 3000).strip()
        response = await _run(
            client, files={"file": ("long.txt", text.encode(), "text/plain")}
        )

        assert response.status_code == 502
        assert "count mismatch" in response.json()["detail"]

    async def test_unsupported_type_is_a_400(self, client, monkeypatch):
        _override_user()
        _override_db()
        _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("archive.tar.gz", b"\x00\x01", "application/gzip")}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Unsupported file type: archive.tar.gz"

    async def test_corrupt_pdf_is_a_400(self, client, monkeypatch):
        _override_user()
        _override_db()
        _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("broken.pdf", b"not a pdf", "application/pdf")}
        )

        assert response.status_code == 400
        assert response.json()["detail"].startswith("Failed to parse file:")

    async def test_a_file_with_no_extractable_text_is_a_400(self, client, monkeypatch):
        _override_user()
        _override_db()
        _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("empty.pdf", _blank_pdf(), "application/pdf")}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "No text could be extracted from the file"

    async def test_an_empty_txt_is_a_400(self, client, monkeypatch):
        _override_user()
        _override_db()
        _stub_pipeline(monkeypatch)

        response = await _run(
            client, files={"file": ("empty.txt", b"", "text/plain")}
        )

        assert response.status_code == 400


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