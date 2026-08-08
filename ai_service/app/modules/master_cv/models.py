from app.db.base import Base
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
from enum import Enum as PyEnum


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
        Vector(1536), nullable=True
    )  # pgvector, if you're embedding the whole CV
    parsed_data = Column(
        JSON, nullable=True
    )  # structured extraction (education, experience, etc.)

    status = Column(
        String(20),
        nullable=False,
        default=CVStatus.PENDING,
    )

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
