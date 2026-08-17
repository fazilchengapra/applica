# app/modules/companies/models.py
import uuid
import enum
from sqlalchemy import String, Enum as SAEnum, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CompanyStatus(str, enum.Enum):
    PENDING = "pending"
    AUTO_VERIFIED = "auto_verified"
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
        SAEnum(CompanyStatus), default=CompanyStatus.PENDING
    )
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verification_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)