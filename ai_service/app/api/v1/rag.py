import base64
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
from app.modules.rag.loaders import get_loader
from app.modules.rag.repositories.document import create_document
from app.modules.rag.repositories.document_type import (
    create_document_type,
    list_document_types,
    update_document_type,
)
from app.modules.rag.schemas import (
    DocumentEnqueued,
    DocumentTypeCreate,
    DocumentTypeOut,
    DocumentTypeUpdate,
    QueryEmbeddingResponse,
    QueryRequest,
)
from app.modules.rag.services.embedding import embed_chunks
from app.modules.rag.tasks import process_document_task

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
    response_model=DocumentEnqueued,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document for asynchronous processing",
    responses={
        400: {"description": "Unsupported file type"},
        404: {"description": "Document type not found"},
        422: {"description": "Invalid access level"},
        503: {"description": "Could not enqueue the processing job"},
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
    """Accept the upload, queue it and return 202 immediately.

    Load, chunk, embed and persist all happen in the Celery task
    ``rag.process_document``. The returned ``document_id`` tracks the row's
    status as it moves ``processing`` -> ``completed``/``failed``.
    """
    data = await file.read()

    try:
        get_loader(file.filename, file.content_type)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    try:
        access_level_value = AccessLevel(access_level)
    except ValueError:
        valid = [level.value for level in AccessLevel]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"access_level must be one of {valid}",
        ) from None

    try:
        document = await create_document(
            db,
            document_type_id=document_type_id,
            title=title or file.filename or "untitled",
            access_level=access_level_value,
        )
    except DocumentTypeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    try:
        process_document_task.delay(
            str(document.id),
            base64.b64encode(data).decode("ascii"),
            file.filename or "",
            file.content_type,
        )
    except Exception as error:
        await db.delete(document)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not enqueue processing job: {error}",
        ) from error

    return DocumentEnqueued(document_id=document.id, status=document.status.value)


@router.post(
    "/query",
    response_model=QueryEmbeddingResponse,
    summary="Embed a user query",
    responses={
        502: {"description": "Embedding service failed"},
    },
)
async def embed_query(
    payload: QueryRequest,
    user_id: int = Depends(get_current_user_id),
):
    """Embed the query and return it with its vector."""
    try:
        vectors = await embed_chunks([payload.query])
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Embedding failed: {error}",
        ) from error

    return QueryEmbeddingResponse(query=payload.query, embedding=vectors[0])