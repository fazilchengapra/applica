import uuid
import enum
from datetime import datetime

from sqlalchemy import Integer
from sqlalchemy import ForeignKey, UniqueConstraint, Index, Float, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class MatchStatus(str, enum.Enum):
    NEW = "new"
    VIEWED = "viewed"
    SAVED = "saved"
    DISMISSED = "dismissed"
    APPLIED = "applied"


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )

    # Stage-level scores (kept separate for debugging/tuning, not just the final blend)
    vector_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    lexical_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rrf_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # LLM relevance_score, drives sort order

    # LLM reranking output
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_matches: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    key_gaps: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus, name="match_status"),
        default=MatchStatus.NEW.value,
        nullable=False,
    )

    matched_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    job = relationship("Job", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_job_match_user_job"),
        Index(
            "ix_job_matches_user_score", "user_id", "final_score"
        ),  # for sorted "top matches" queries
    )
