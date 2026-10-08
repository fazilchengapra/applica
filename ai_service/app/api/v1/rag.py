from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.rag.exceptions import (
    DocumentTypeNameTakenError,
    DocumentTypeNotFoundError,
)
from app.modules.rag.repositories.document_type import (
    create_document_type,
    list_document_types,
    update_document_type,
)
from app.modules.rag.schemas import (
    DocumentTypeCreate,
    DocumentTypeOut,
    DocumentTypeUpdate,
    LoadedDocument,
)
from app.modules.rag.services.ingestion import process_upload

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
    response_model=LoadedDocument,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Unsupported file type or unparseable content"},
    },
)
async def load_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    data = await file.read()

    try:
        return process_upload(file.filename, file.content_type, data)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {error}",
        ) from error