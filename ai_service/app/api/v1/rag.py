from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.rag.constants import AccessLevel
from app.modules.rag.exceptions import (
    DocumentTypeNameTakenError,
    DocumentTypeNotFoundError,
)
from app.modules.rag.repositories.chunk import save_document_with_chunks
from app.modules.rag.repositories.document_type import (
    create_document_type,
    get_document_type,
    list_document_types,
    update_document_type,
)
from app.modules.rag.schemas import (
    DocumentTypeCreate,
    DocumentTypeOut,
    DocumentTypeUpdate,
    IngestResponse,
)
from app.modules.rag.services.embedding import embed_chunks
from app.modules.rag.services.ingestion import process_upload
from app.modules.rag.utils.hashing import calculate_hash

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.get(
    "/document-types",
    response_model=list[DocumentTypeOut],
    summary="List all document types",
)
async def document_types(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """The full doc-type catalog, so upload forms can populate their dropdown."""
    return await list_document_types(db)


@router.post(
    "/document-types",
    response_model=DocumentTypeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a document type",
    responses={
        409: {"description": "A type with that name already exists"},
    },
)
async def create_type(
    payload: DocumentTypeCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_document_type(db, payload.name, payload.description)
    except DocumentTypeNameTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.put(
    "/document-types/{document_type_id}",
    response_model=DocumentTypeOut,
    summary="Update a document type",
    responses={
        404: {"description": "Document type not found"},
        409: {"description": "Another type already uses the requested name"},
    },
)
async def update_type(
    document_type_id: UUID,
    payload: DocumentTypeUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await update_document_type(
            db, document_type_id, payload.name, payload.description
        )
    except DocumentTypeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DocumentTypeNameTakenError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/load",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document: load, chunk, embed and persist it",
    responses={
        400: {"description": "Unsupported file type or unparseable content"},
        404: {"description": "Document type not found"},
        422: {"description": "Invalid access level"},
        502: {"description": "Embedding service failed"},
    },
)
async def load_document(
    file: UploadFile = File(...),
    document_type_id: UUID = Form(...),
    access_level: str = Form(...),
    title: str | None = Form(None),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read()

    try:
        loaded = process_upload(file.filename, file.content_type, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {error}",
        ) from error

    try:
        access_level_value = AccessLevel(access_level)
    except ValueError:
        valid = [level.value for level in AccessLevel]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"access_level must be one of {valid}",
        ) from None

    try:
        embeddings = await embed_chunks([chunk.text for chunk in loaded.chunks])
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding failed: {error}",
        ) from error

    if len(embeddings) != loaded.chunk_count:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding count mismatch: got {len(embeddings)}, "
            f"expected {loaded.chunk_count}",
        )

    try:
        document = await save_document_with_chunks(
            db,
            document_type_id=document_type_id,
            title=title or file.filename or "untitled",
            access_level=access_level_value,
            content_hash=calculate_hash(loaded.text),
            chunks=loaded.chunks,
            embeddings=embeddings,
        )
    except DocumentTypeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    document_type = await get_document_type(db, document_type_id)
    return IngestResponse(
        id=document.id,
        document_type_id=document.document_type_id,
        doc_type=document_type.name,
        title=document.title,
        version=document.version,
        access_level=document.access_level.value,
        status=document.status.value,
        content_hash=document.content_hash,
        chunk_count=loaded.chunk_count,
        created_at=document.created_at,
    )