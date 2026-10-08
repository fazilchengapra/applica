"""Persisted RAG document, the unit change detection and embedding act on."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import ENUM, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.rag.constants import AccessLevel, DocType, DocumentStatus


def _enum_values(enum_class) -> list[str]:
    return [member.value for member in enum_class]


doc_type_enum = ENUM(
    DocType, name="document_doc_type", create_type=False, values_callable=_enum_values
)
access_level_enum = ENUM(
    AccessLevel,
    name="document_access_level",
    create_type=False,
    values_callable=_enum_values,
)
status_enum = ENUM(
    DocumentStatus,
    name="document_status",
    create_type=False,
    values_callable=_enum_values,
)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    doc_type: Mapped[DocType] = mapped_column(doc_type_enum, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    access_level: Mapped[AccessLevel] = mapped_column(
        access_level_enum, nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        status_enum, nullable=False, server_default=DocumentStatus.PENDING.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Document {self.title!r} v{self.version} ({self.doc_type.value})>"