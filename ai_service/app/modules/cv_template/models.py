import uuid
from datetime import datetime
import enum

from sqlalchemy import Enum as SAEnum, Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CVTemplateStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    failed = "failed"


class CVTemplate(Base):
    __tablename__ = "cv_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tex_hash: Mapped[str] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

    tex: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    file_s3_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    image_s3_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    status: Mapped[CVTemplateStatus] = mapped_column(
        SAEnum(
            CVTemplateStatus, name="cv_template_status", native_enum=False, length=20
        ),
        nullable=False,
        default=CVTemplateStatus.pending,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
