"""CRUD helpers for RAG documents."""

import uuid
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.constants import AccessLevel, DocumentStatus
from app.modules.rag.exceptions import DocumentTypeNotFoundError
from app.modules.rag.models.document import Document
from app.modules.rag.models.document_type import DocumentType


async def create_document(
    db: AsyncSession,
    *,
    document_type_id: UUID,
    title: str,
    access_level: AccessLevel,
    status: DocumentStatus = DocumentStatus.PROCESSING,
) -> Document:
    """Insert a document row and return it with its id populated.

    The row starts in ``PROCESSING``; the background task later flips it to
    ``COMPLETED`` or ``FAILED`` and fills in ``content_hash``. Raises
    :class:`DocumentTypeNotFoundError` when ``document_type_id`` is unknown.
    """
    if await db.get(DocumentType, document_type_id) is None:
        raise DocumentTypeNotFoundError("Document type not found")

    document = Document(
        id=uuid.uuid4(),
        document_type_id=document_type_id,
        title=title,
        version=1,
        content_hash="",
        access_level=access_level,
        status=status,
    )
    db.add(document)
    await db.commit()
    return document


def _coerce_uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


async def get_document(db: AsyncSession, document_id: UUID | str) -> Document | None:
    """Fetch a document by id, or ``None`` when it does not exist."""
    return await db.get(Document, _coerce_uuid(document_id))