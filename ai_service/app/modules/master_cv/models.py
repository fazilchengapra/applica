from app.db.base import Base
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime


class MasterCV(Base):
    __tablename__ = "master_cvs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), nullable=False, index=True
    )  # plain reference, NOT a FK

    raw_text = Column(Text, nullable=False)
    s3_key = Column(String, nullable=True)  # original uploaded file
    embedding = Column(
        Vector(1536), nullable=True
    )  # pgvector, if you're embedding the whole CV
    parsed_data = Column(
        JSON, nullable=True
    )  # structured extraction (education, experience, etc.)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)