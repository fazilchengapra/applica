"""HTTP API for the RAG load + chunk pipeline."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.dependencies import get_current_user_id
from app.modules.rag.schemas import LoadedDocument
from app.modules.rag.services.ingestion import process_upload

router = APIRouter(prefix="/rag", tags=["RAG"])


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