# app/modules/companies/models.py
import uuid
import enum
from sqlalchemy import String, Enum as SAEnum, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime


class CompanyStatus(str, enum.Enum):
    PENDING = "pending"
    AUTO_VERIFIED = "approved"
    ADMIN_VERIFIED = "admin_verified"
    PENDING_REVIEW = "pending_review"
    REJECTED = "rejected"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    normalized_name: Mapped[str] = mapped_column(String, unique=True, index=True)

    display_name: Mapped[str] = mapped_column(String)

    status: Mapped[CompanyStatus] = mapped_column(
        SAEnum(
            CompanyStatus,
            values_callable=lambda enum: [e.value for e in enum],
        ),
        default=CompanyStatus.PENDING.value,
        nullable=False,
    )

    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    verified_website_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    verified_linkedin_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    verification_reasoning: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    verification_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
