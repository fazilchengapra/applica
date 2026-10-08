"""Unit tests for the RAG embedding service (client is stubbed)."""

import pytest

from app.modules.rag.services import embedding


class _FakeEmbeddings:
    def __init__(self, vectors=None, exc=None):
        self._vectors = vectors or []
        self._exc = exc
        self.calls = []

    async def aembed_documents(self, texts):
        self.calls.append(list(texts))
        if self._exc is not None:
            raise self._exc
        return self._vectors


@pytest.fixture
def _patch_client(monkeypatch):
    def _install(vectors=None, exc=None):
        fake = _FakeEmbeddings(vectors=vectors, exc=exc)
        monkeypatch.setattr(embedding, "embeddings", fake)
        return fake

    return _install


async def test_empty_input_yields_no_embeddings(_patch_client):
    fake = _patch_client()
    assert await embedding.embed_chunks([]) == []
    assert fake.calls == []


async def test_embeds_every_chunk_text_and_passes_them_through(_patch_client):
    fake = _patch_client(vectors=[[0.1, 0.2], [0.3, 0.4]])
    vectors = await embedding.embed_chunks(["a", "b"])

    assert vectors == [[0.1, 0.2], [0.3, 0.4]]
    assert fake.calls == [["a", "b"]]


async def test_embedding_failures_propagate(_patch_client):
    fake = _patch_client(exc=RuntimeError("upstream refused"))
    with pytest.raises(RuntimeError, match="upstream refused"):
        await embedding.embed_chunks(["a"])