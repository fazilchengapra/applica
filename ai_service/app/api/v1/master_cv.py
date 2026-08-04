from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.modules.master_cv.services.cv_service import process_cv_upload

# schema
from ...modules.master_cv.schemas import CVUploadResponse

# exceptions
from ...modules.master_cv.exceptions import (
    InvalidPDFError,
    S3UploadError,
    FileTooLargeError,
)

router = APIRouter(prefix="/master-cv", tags=["master-cv"])


@router.post("/", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    content = await file.read()

    try:
        object_key = await process_cv_upload(file.filename, content)
    except (InvalidPDFError, FileTooLargeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except S3UploadError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return CVUploadResponse(
        details="success", filename=file.filename, object_key=object_key
    )
