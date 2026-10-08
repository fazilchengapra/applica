"""Endpoint tests for POST /api/ai/v1/rag/load.

Real FastAPI app so gateway middleware and the X-User-Id dependency are
covered; parsing runs against the real loaders, so no database is used.
"""

import io
import zipfile

import fitz
import httpx
import pytest
from httpx import ASGITransport

from app.core.config import settings
from app.main import app

GATEWAY_HEADERS = {
    "X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET,
    "X-User-Id": "7",
}


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


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


class TestLoad:
    async def test_txt(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("notes.txt", b"line one\nline two\n", "text/plain")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["filename"] == "notes.txt"
        assert body["content_type"] == "text/plain"
        assert body["loader"] == "TxtLoader"
        assert body["text"] == "line one\nline two"
        assert body["characters"] == 17
        assert body["lines"] == 2
        assert body["chunk_count"] == 1
        assert body["chunks"] == [
            {
                "index": 0,
                "text": "line one\nline two",
                "characters": 17,
                "tokens": 5,
            }
        ]

    async def test_a_long_document_gets_multiple_chunks(self, client):
        text = ("word " * 3000).strip()
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("long.txt", text.encode(), "text/plain")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["chunk_count"] > 1
        assert len(body["chunks"]) == body["chunk_count"]
        indices = [chunk["index"] for chunk in body["chunks"]]
        assert indices == list(range(body["chunk_count"]))
        assert all(chunk["characters"] > 0 for chunk in body["chunks"])

    async def test_pdf(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("cv.pdf", _pdf_with_text("Hello PDF"), "application/pdf")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["loader"] == "PdfLoader"
        assert "Hello PDF" in body["text"]
        assert body["characters"] == len(body["text"])

    async def test_docx(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("policy.docx", _docx(["Intro.", "Refund rules"]), None)},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["loader"] == "DocxLoader"
        assert body["text"] == "Intro.\nRefund rules"
        assert body["lines"] == 2

    async def test_html(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("page.html", HTML_BYTES, "text/html")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["loader"] == "HtmlLoader"
        assert "Heading One" in body["text"]
        assert "First paragraph." in body["text"]
        assert "var x" not in body["text"]

    async def test_content_type_fallback_when_filename_has_no_extension(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("blob", b"fallback text", "text/plain")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 200
        assert response.json()["loader"] == "TxtLoader"

    async def test_unsupported_type_is_a_400(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("archive.tar.gz", b"\x00\x01", "application/gzip")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Unsupported file type: archive.tar.gz"

    async def test_corrupt_pdf_is_a_400(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("broken.pdf", b"not a pdf", "application/pdf")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 400
        assert response.json()["detail"].startswith("Failed to parse file:")

    async def test_a_file_with_no_extractable_text_is_a_400(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("empty.pdf", _blank_pdf(), "application/pdf")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "No text could be extracted from the file"

    async def test_an_empty_txt_is_a_400(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("empty.txt", b"", "text/plain")},
            headers=GATEWAY_HEADERS,
        )

        assert response.status_code == 400


class TestGatewayGuards:
    async def test_requires_the_gateway_secret(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("a.txt", b"x", "text/plain")},
            headers={"X-User-Id": "7"},
        )

        assert response.status_code == 403

    async def test_requires_the_user_header(self, client):
        response = await client.post(
            "/api/ai/v1/rag/load",
            files={"file": ("a.txt", b"x", "text/plain")},
            headers={"X-Gateway-Secret": settings.GATEWAY_INTERNAL_SECRET},
        )

        assert response.status_code == 422