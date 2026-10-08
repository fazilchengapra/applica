"""Tests for the RAG background ingestion task (rag.process_document)."""

import base64
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from app.modules.rag import tasks
from app.modules.rag.constants import DocumentStatus
from app.modules.rag.utils.hashing import calculate_hash

DOCUMENT_ID = "aaaaaaaa-0000-4000-8000-000000000002"


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.save_kwargs = None

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class FakeDocument:
    id = DOCUMENT_ID
    document_type_id = "aaaaaaaa-0000-4000-8000-000000000001"
    access_level = SimpleNamespace(value="internal")
    status = DocumentStatus.PROCESSING
    content_hash = ""


def _loaded():
    return SimpleNamespace(
        text="hello world",
        chunk_count=2,
        chunks=[
            SimpleNamespace(text="line one"),
            SimpleNamespace(text="line two"),
        ],
    )


def _fake_session(fail_embed=False):
    document = FakeDocument()
    session = FakeSession()

    @asynccontextmanager
    async def _session():
        yield session

    async def _get_document(db, document_id):
        return document

    async def _get_document_type(db, document_type_id):
        return SimpleNamespace(name="policy")

    async def _embed(texts):
        if fail_embed:
            raise RuntimeError("upstream refused")
        return [[0.1], [0.2]]

    async def _save_chunks(db, **kwargs):
        session.save_kwargs = kwargs

    tasks.get_celery_db_session = _session
    tasks.get_document = _get_document
    tasks.get_document_type = _get_document_type
    tasks.process_upload = _loaded
    tasks.embed_chunks = _embed
    tasks.save_chunks = _save_chunks
    tasks.calculate_hash = calculate_hash
    return document, session


class TestProcessDocument:
    async def test_completes_the_document_after_persisting(self, monkeypatch):
        document, session = _fake_session()
        monkeypatch.setattr(tasks, "process_upload", lambda *a: _loaded())
        monkeypatch.setattr(tasks, "calculate_hash", calculate_hash)

        await tasks._process_document(DOCUMENT_ID, _b64(b"bytes"), "n.txt", "text/plain")

        assert document.status is DocumentStatus.COMPLETED
        assert document.content_hash == calculate_hash("hello world")
        assert session.save_kwargs == {
            "document_id": DOCUMENT_ID,
            "doc_type": "policy",
            "access_level": "internal",
            "chunks": _loaded().chunks,
            "embeddings": [[0.1], [0.2]],
        }
        assert session.commits == 1

    async def test_marks_the_document_failed_and_reraises(self, monkeypatch):
        document, session = _fake_session(fail_embed=True)
        monkeypatch.setattr(tasks, "process_upload", lambda *a: _loaded())
        monkeypatch.setattr(tasks, "calculate_hash", calculate_hash)

        with pytest.raises(RuntimeError, match="upstream refused"):
            await tasks._process_document(DOCUMENT_ID, _b64(b"bytes"), "n.txt", "text/plain")

        assert document.status is DocumentStatus.FAILED
        assert session.commits == 1
        assert session.rollbacks == 1

    async def test_missing_document_raises(self, monkeypatch):
        _fake_session()

        async def _none(db, document_id):
            return None

        monkeypatch.setattr(tasks, "get_document", _none)

        with pytest.raises(ValueError, match="not found"):
            await tasks._process_document(DOCUMENT_ID, _b64(b"bytes"), "n.txt", "text/plain")

    def test_task_wrapper_decodes_base64_and_runs(self, monkeypatch):
        document, session = _fake_session()
        monkeypatch.setattr(tasks, "process_upload", lambda *a: _loaded())
        monkeypatch.setattr(tasks, "calculate_hash", calculate_hash)

        tasks.process_document_task.run(
            DOCUMENT_ID,
            base64.b64encode(b"raw bytes").decode("ascii"),
            "n.txt",
            "text/plain",
        )

        assert document.status is DocumentStatus.COMPLETED
        assert session.commits == 1


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")