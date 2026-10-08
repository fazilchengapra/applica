"""HTTP request/response shapes for the RAG module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    """One piece of a document produced by the chunking service."""

    index: int = Field(..., description="Zero-based position within the document.")
    text: str = Field(..., description="Chunk content.")
    characters: int
    tokens: int = Field(..., description="Token count under the chunking encoding.")
    content_hash: str = Field(
        ...,
        description="Digest of the chunk text, used for change detection.",
    )


class LoadedDocument(BaseModel):
    """Common document format every loader normalises to, plus its chunks."""

    filename: str
    content_type: str | None = None
    loader: str = Field(..., description="Loader class that produced the text.")
    text: str = Field(..., description="Extracted plain text.")
    characters: int
    lines: int
    chunk_count: int = Field(..., description="Number of chunks split from the text.")
    chunks: list[DocumentChunk]


class DocumentTypeCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Business label for the document category, e.g. 'policy'.",
    )
    description: str | None = Field(default=None, max_length=255)


class DocumentTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)


class DocumentTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    created_at: datetime


class IngestResponse(BaseModel):
    id: UUID
    document_type_id: UUID
    doc_type: str = Field(..., description="Denormalized document type name.")
    title: str
    version: int
    access_level: str
    status: str
    content_hash: str
    chunk_count: int = Field(..., description="Number of chunks embedded and stored.")
    created_at: datetime