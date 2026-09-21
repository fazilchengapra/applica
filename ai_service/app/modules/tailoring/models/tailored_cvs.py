import uuid
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, func, Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class TailoredCVStatus(str, enum.Enum):
    approved = "approved"
    failed = "failed"

class CVRenderStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"

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
    cv_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cv_templates.id"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(TailoredCVStatus, name="tailored_cv_status"), nullable=False
    )
    cv_structure: Mapped[dict] = mapped_column(JSONB, nullable=False)
    critic_score: Mapped[Decimal | None] = mapped_column(Numeric)
    critic_verdict: Mapped[dict | None] = mapped_column(JSONB)

    render_status: Mapped[str] = mapped_column(
    Enum(CVRenderStatus, name="cv_render_status"), nullable=False, default=CVRenderStatus.pending
)
    file_s3_key: Mapped[str | None] = mapped_column(String(500))
    render_error_message: Mapped[str | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
