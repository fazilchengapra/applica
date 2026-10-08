"""Persist RAG documents together with their embedded chunks."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.constants import AccessLevel, DocumentStatus
from app.modules.rag.exceptions import DocumentTypeNotFoundError
from app.modules.rag.models.chunk import Chunk
from app.modules.rag.models.document import Document
from app.modules.rag.models.document_type import DocumentType
from app.modules.rag.schemas import DocumentChunk


async def save_document_with_chunks(
    db: AsyncSession,
    *,
    document_type_id: UUID,
    title: str,
    access_level: AccessLevel,
    content_hash: str,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
) -> Document:
    """Insert one document and its embedded chunks in a single transaction.

    ``doc_type`` and ``access_level`` are denormalized onto each chunk for
    row-level scoping without a join. Raises :class:`DocumentTypeNotFoundError`
    when ``document_type_id`` does not exist.
    """
    document_type = await db.scalar(
        select(DocumentType).where(DocumentType.id == document_type_id)
    )
    if document_type is None:
        raise DocumentTypeNotFoundError("Document type not found")

    document = Document(
        document_type_id=document_type_id,
        title=title,
        version=1,
        content_hash=content_hash,
        access_level=access_level,
        status=DocumentStatus.COMPLETED,
    )
    db.add(document)
    await db.flush()

    if chunks:
        rows = [
            {
                "document_id": document.id,
                "doc_type": document_type.name,
                "access_level": access_level.value,
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

    await db.commit()
    return document