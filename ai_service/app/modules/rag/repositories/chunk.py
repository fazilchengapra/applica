"""Persist RAG chunks for documents already created by the ingest flow."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.models.chunk import Chunk
from app.modules.rag.schemas import DocumentChunk


async def save_chunks(
    db: AsyncSession,
    *,
    document_id: UUID,
    doc_type: str,
    access_level: str,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
) -> int:
    """Bulk-insert embedded chunks for an existing document.

    ``doc_type`` and ``access_level`` are denormalized onto each chunk for
    row-level scoping without a join. Returns the number of rows attempted.
    """
    if not chunks:
        return 0

    rows = [
        {
            "document_id": document_id,
            "doc_type": doc_type,
            "access_level": access_level,
            "chunk_index": chunk.index,
            "content": chunk.text,
            "content_hash": chunk.content_hash,
            "embedding": embedding,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    stmt = pg_insert(Chunk).values(rows).on_conflict_do_nothing(
        index_elements=["document_id", "chunk_index"]
    )
    await db.execute(stmt)
    return len(rows)