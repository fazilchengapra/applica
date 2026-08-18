import enum
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import (
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RemoteType(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"


class SourceType(str, enum.Enum):
    API = "api"
    ATS_DIRECT = "ats_direct"
    SCRAPE = "scrape"
    FEED = "feed"


class JobStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    FILLED = "filled"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    # No foreign key constraint
    raw_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    normalized_title: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    location: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    remote_type: Mapped[RemoteType | None] = mapped_column(
        nullable=True,
    )

    employment_type: Mapped[EmploymentType | None] = mapped_column(
        nullable=True,
    )

    salary_min: Mapped[Decimal | None] = mapped_column(
        Numeric,
        nullable=True,
    )

    salary_max: Mapped[Decimal | None] = mapped_column(
        Numeric,
        nullable=True,
    )

    salary_currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    salary_period: Mapped[str | None] = mapped_column(String, nullable=True)

    source_type: Mapped[SourceType] = mapped_column(
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(String, nullable=False)

    source_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    external_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    external_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    dedup_hash: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    status: Mapped[JobStatus] = mapped_column(
        default=JobStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    company = relationship(
        "Company",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_name",
            "external_id",
            name="uq_job_source",
        ),
        Index("ix_jobs_company_id", "company_id"),
        Index("ix_jobs_status", "status"),
    )
