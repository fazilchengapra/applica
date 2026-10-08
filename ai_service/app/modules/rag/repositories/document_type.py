"""CRUD helpers for the dynamic document-type catalog."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.exceptions import (
    DocumentTypeNameTakenError,
    DocumentTypeNotFoundError,
)
from app.modules.rag.models.document_type import DocumentType


def normalize_name(name: str) -> str:
    """Store names in a stable lowercase, slug-like form."""
    return " ".join(name.strip().split()).lower()


async def list_document_types(db: AsyncSession) -> list[DocumentType]:
    return list(
        (await db.execute(select(DocumentType).order_by(DocumentType.name))).scalars()
    )


async def get_document_type(
    db: AsyncSession, document_type_id: UUID
) -> DocumentType | None:
    return await db.scalar(
        select(DocumentType).where(DocumentType.id == document_type_id)
    )


async def get_document_type_by_name(
    db: AsyncSession, name: str
) -> DocumentType | None:
    return await db.scalar(
        select(DocumentType).where(DocumentType.name == normalize_name(name))
    )


async def create_document_type(
    db: AsyncSession, name: str, description: str | None = None
) -> DocumentType:
    normalized = normalize_name(name)
    if await get_document_type_by_name(db, normalized) is not None:
        raise DocumentTypeNameTakenError(f"A document type named '{normalized}' already exists")

    row = DocumentType(name=normalized, description=description)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DocumentTypeNameTakenError(
            f"A document type named '{normalized}' already exists"
        ) from exc
    await db.refresh(row)
    return row


async def update_document_type(
    db: AsyncSession,
    document_type_id: UUID,
    name: str | None = None,
    description: str | None = None,
) -> DocumentType:
    row = await get_document_type(db, document_type_id)
    if row is None:
        raise DocumentTypeNotFoundError("Document type not found")

    normalized = None
    if name is not None:
        normalized = normalize_name(name)
        if (
            normalized != row.name
            and await get_document_type_by_name(db, normalized) is not None
        ):
            raise DocumentTypeNameTakenError(
                f"A document type named '{normalized}' already exists"
            )
        row.name = normalized
    if description is not None:
        row.description = description

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise DocumentTypeNameTakenError(
            f"A document type named '{normalized}' already exists"
        ) from exc
    await db.refresh(row)
    return row