from app.db.base import Base
import uuid
from sqlalchemy import Column, String, DateTime, Text, BigInteger, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector


class CVStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MasterCV(Base):
    __tablename__ = "master_cvs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        BigInteger, nullable=False, index=True
    )  # plain reference, NOT a FK

    raw_text = Column(Text, nullable=True)
    s3_key = Column(String, nullable=True)  # original uploaded file
    embedding = Column(
        Vector(1024), nullable=True
    )  # pgvector, if you're embedding the whole CV
    parsed_data = Column(
        JSONB, nullable=True
    )  # structured extraction (education, experience, etc.)

    status = Column(
        String(20),
        nullable=False,
        default=CVStatus.PENDING,
    )

    is_deleted = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
