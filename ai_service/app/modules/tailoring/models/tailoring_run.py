import enum
import uuid
from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .evidence_matrix import EvidenceMatrix

from .strategy_brief import StrategyBrief


class TailoringStage(str, enum.Enum):
    evidence_match = "evidence_match"
    strategy = "strategy"
    write = "write"
    critic = "critic"


class TailoringRunStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# Order the pipeline moves through; used by advance_stage to find "next".
STAGE_SEQUENCE = [
    TailoringStage.evidence_match,
    TailoringStage.strategy,
    TailoringStage.write,
    TailoringStage.critic,
]


class TailoringRun(Base):
    __tablename__ = "tailoring_runs"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "job_id", "cv_version_id", name="uq_tailoring_runs_user_job_cv"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int] = mapped_column(nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )
    cv_version_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )

    stage: Mapped[TailoringStage] = mapped_column(
        SAEnum(TailoringStage, name="tailoring_stage"),
        nullable=False,
        default=TailoringStage.evidence_match,
    )
    status: Mapped[TailoringRunStatus] = mapped_column(
        SAEnum(TailoringRunStatus, name="tailoring_run_status"),
        nullable=False,
        default=TailoringRunStatus.pending,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    critic_retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    critic_verdict: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    evidence_matrix: Mapped["EvidenceMatrix | None"] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )
    strategy_brief: Mapped["StrategyBrief | None"] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )
