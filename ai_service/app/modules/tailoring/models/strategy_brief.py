from typing import TYPE_CHECKING
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .tailoring_run import TailoringRun


class StrategyBrief(Base):
    __tablename__ = "strategy_briefs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tailoring_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tailoring_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tone: Mapped[str | None] = mapped_column(String, nullable=True)
    section_order: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    lead_experiences: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    gaps_to_address: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    keywords_to_weave: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    run: Mapped["TailoringRun"] = relationship(back_populates="strategy_brief")
