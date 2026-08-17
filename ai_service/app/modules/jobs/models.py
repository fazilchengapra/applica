# app/modules/jobs/models.py
import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    DateTime,
    UniqueConstraint,
    Index,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.jobs.constants import SourceType, ProcessingStatus

source_type_enum = ENUM(
    SourceType,
    name="source_type",
    create_type=False,
)


class RawJob(Base):
    __tablename__ = "raw_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )

    source_type: Mapped[SourceType] = mapped_column(source_type_enum, nullable=False)
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # company_id: Mapped[uuid.UUID | None] = mapped_column(
    #     UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True
    # )
    location_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    salary_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at_raw: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    dedup_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=ProcessingStatus.PENDING.value
    )

    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_name",
            "external_id",
            name="uq_raw_jobs_source",
        ),
        Index("idx_raw_jobs_dedup_hash", "dedup_hash"),
        Index(
            "idx_raw_jobs_unprocessed",
            "processing_status",
            postgresql_where=(processing_status == ProcessingStatus.PENDING.value),
        ),
    )

    def __repr__(self) -> str:
        return f"<RawJob {self.source_name}:{self.external_id or self.dedup_hash}>"
