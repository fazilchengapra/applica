"""Embed document chunk texts for vector retrieval.

Reuses the shared VoyageAI client already used by the jobs and master_cv
modules (``voyage-3.5``, 1024 dims), so the service has a single embedder.
"""

import logging

from app.core.embedding_client import embeddings

logger = logging.getLogger(__name__)


async def embed_chunks(chunk_texts: list[str]) -> list[list[float]]:
    """Return one 1024-dim Voyage AI embedding per chunk text."""
    if not chunk_texts:
        return []
    return await embeddings.aembed_documents(chunk_texts)