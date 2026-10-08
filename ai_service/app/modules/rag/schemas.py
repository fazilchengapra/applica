"""HTTP request/response shapes for the RAG module."""

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """One piece of a document produced by the chunking service."""

    index: int = Field(..., description="Zero-based position within the document.")
    text: str = Field(..., description="Chunk content.")
    characters: int
    tokens: int = Field(..., description="Token count under the chunking encoding.")


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