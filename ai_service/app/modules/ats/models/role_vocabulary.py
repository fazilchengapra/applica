"""Cached expected-vocabulary for a target role.

``target_role`` is a short string shared by every user targeting that role, so
expanding it once per role rather than once per request turns the most expensive
step of keyword scoring into a single write per distinct role.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RoleVocabulary(Base):
    __tablename__ = "role_vocabularies"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_role: Mapped[str] = mapped_column(String(255), nullable=False)
    terms: Mapped[list] = mapped_column(JSONB, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("normalized_role", name="uq_role_vocab_role"),)
