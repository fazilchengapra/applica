"""Split document text into overlapping chunks.

Chunking is token-aware and separator-aware: the splitter first breaks
the text on natural separators (paragraphs, lines, words) and then
merges pieces back into ~``CHUNK_SIZE``-token chunks. Consecutive
chunks share ``CHUNK_OVERLAP`` tokens so semantic context is not lost
at boundaries.
"""

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.modules.rag.constants import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHUNK_TOKEN_ENCODING,
)
from app.modules.rag.schemas import DocumentChunk
from app.modules.rag.utils.hashing import calculate_hash

_SEPARATORS = ["\n\n", "\n", " ", ""]

_encoder = tiktoken.get_encoding(CHUNK_TOKEN_ENCODING)


def _count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def split_text(text: str) -> list[DocumentChunk]:
    """Split document text into token-bounded chunks with overlap."""
    if not text:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=_count_tokens,
        separators=_SEPARATORS,
    )

    pieces = splitter.split_text(text)

    return [
        DocumentChunk(
            index=index,
            text=piece,
            characters=len(piece),
            tokens=_count_tokens(piece),
            content_hash=calculate_hash(piece),
        )
        for index, piece in enumerate(pieces)
    ]