"""Persisted ATS readiness report, one row per (content, ruleset) evaluation."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ATSReport(Base):
    __tablename__ = "ats_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    cv_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("master_cv_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    checks: Mapped[list] = mapped_column(JSONB, nullable=False)
    summary: Mapped[list] = mapped_column(JSONB, nullable=False)
    semantic_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ruleset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "cv_version_id",
            "content_hash",
            "ruleset_version",
            name="uq_ats_report_cv_content_ruleset",
        ),
    )
