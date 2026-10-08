"""Background ingestion pipeline for uploaded RAG documents.

The API hands this task raw file bytes (base64, because the broker is
JSON-serialized). The task runs load -> chunk -> embed -> persist and moves
the document from ``processing`` to ``completed`` (or ``failed``).
"""

import asyncio
import base64
import logging

from celery import shared_task

from app.db.celery_db import get_celery_db_session
from app.modules.rag.constants import DocumentStatus
from app.modules.rag.repositories.chunk import save_chunks
from app.modules.rag.repositories.document import get_document
from app.modules.rag.repositories.document_type import get_document_type
from app.modules.rag.services.embedding import embed_chunks
from app.modules.rag.services.ingestion import process_upload
from app.modules.rag.utils.hashing import calculate_hash

logger = logging.getLogger(__name__)


async def _process_document(
    document_id: str,
    file_b64: str,
    filename: str | None,
    content_type: str | None,
) -> None:
    file_bytes = base64.b64decode(file_b64.encode("ascii"))

    async with get_celery_db_session() as session:
        document = await get_document(session, document_id)
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        try:
            loaded = process_upload(filename, content_type, file_bytes)
            embeddings = await embed_chunks([chunk.text for chunk in loaded.chunks])
            if len(embeddings) != loaded.chunk_count:
                raise ValueError(
                    f"Embedding count mismatch: got {len(embeddings)}, "
                    f"expected {loaded.chunk_count}"
                )

            document_type = await get_document_type(session, document.document_type_id)
            if document_type is None:
                raise ValueError("Document type not found")

            await save_chunks(
                session,
                document_id=document.id,
                doc_type=document_type.name,
                access_level=document.access_level.value,
                chunks=loaded.chunks,
                embeddings=embeddings,
            )

            document.content_hash = calculate_hash(loaded.text)
            document.status = DocumentStatus.COMPLETED
            await session.commit()
            logger.info(
                "Persisted document %s with %d chunks", document.id, loaded.chunk_count
            )
        except Exception:
            logger.exception("RAG ingestion failed for document %s", document.id)
            await session.rollback()
            document.status = DocumentStatus.FAILED
            await session.commit()
            raise


@shared_task(name="rag.process_document", bind=True)
def process_document_task(
    self,
    document_id: str,
    file_b64: str,
    filename: str | None,
    content_type: str | None,
) -> None:
    try:
        asyncio.run(_process_document(document_id, file_b64, filename, content_type))
    except Exception:
        logger.exception("RAG processing failed for document %s", document_id)
        raise