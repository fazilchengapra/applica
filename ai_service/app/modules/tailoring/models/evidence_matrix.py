from typing import TYPE_CHECKING
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .tailoring_run import TailoringRun
    from .evidence_item import EvidenceItem


class EvidenceMatrix(Base):
    __tablename__ = "evidence_matrices"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tailoring_run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tailoring_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    run: Mapped["TailoringRun"] = relationship(back_populates="evidence_matrix")
    items: Mapped[list["EvidenceItem"]] = relationship(
        back_populates="matrix", cascade="all, delete-orphan"
    )
