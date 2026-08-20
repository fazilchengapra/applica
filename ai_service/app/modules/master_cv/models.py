from app.db.base import Base
import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Index,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector


class CVStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MasterCV(Base):
    __tablename__ = "master_cvs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        BigInteger, nullable=False, index=True
    )  # plain reference, NOT a FK

    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    versions = relationship(
        "MasterCVVersion",
        back_populates="master_cv",
        cascade="all, delete-orphan",
    )


class MasterCVVersion(Base):
    __tablename__ = "master_cv_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    master_cv_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("master_cvs.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    embedding = Column(Vector(1024), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    s3_key: Mapped[str] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    parsed_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(
            CVStatus,
            name="cv_status",
            values_callable=lambda enum_class: [e.value for e in enum_class],
        ),
        nullable=False,
        default=CVStatus.PENDING,
    )

    created_at: Mapped["datetime"] = mapped_column(server_default=func.now())
    updated_at: Mapped["datetime"] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    master_cv = relationship("MasterCV", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("master_cv_id", "version", name="uq_master_cv_version"),
        Index(
            "one_current_version_per_cv",
            "master_cv_id",
            unique=True,
            postgresql_where=(is_current == True),  # noqa: E712
        ),
    )
