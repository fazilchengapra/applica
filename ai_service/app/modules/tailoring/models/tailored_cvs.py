import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class TailoredCV(Base):
    __tablename__ = "tailored_cvs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    tailoring_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tailoring_runs.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    cv_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cv_templates.id"),
        nullable=False,
    )
    cv_structure: Mapped[dict] = mapped_column(JSONB, nullable=False)
    critic_score: Mapped[Decimal | None] = mapped_column(Numeric)
    critic_verdict: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )