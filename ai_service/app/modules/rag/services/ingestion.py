"""Document ingestion orchestration.

Currently this runs the load + chunk pipeline on an uploaded file:
the right loader turns bytes into plain text, then the chunking
service splits it. Change detection, embedding and vector storage
will join this flow later.
"""

from app.modules.rag.loaders import get_loader
from app.modules.rag.schemas import LoadedDocument
from app.modules.rag.services.chunking import split_text


def process_upload(
    filename: str | None, content_type: str | None, data: bytes
) -> LoadedDocument:
    loader = get_loader(filename, content_type)
    text = loader.load(data)

    if not text:
        raise ValueError("No text could be extracted from the file")

    chunks = split_text(text)

    return LoadedDocument(
        filename=filename or "",
        content_type=content_type,
        loader=type(loader).__name__,
        text=text,
        characters=len(text),
        lines=len(text.splitlines()),
        chunk_count=len(chunks),
        chunks=chunks,
    )