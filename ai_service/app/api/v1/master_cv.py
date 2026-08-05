from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from app.core.dependencies import get_current_user_id

# service
from app.modules.master_cv.services.cv_service import (
    process_cv_upload,
    process_cv_update,
)
from app.modules.master_cv.services.s3_service import delete_pdf_from_s3

# schema
from ...modules.master_cv.schemas import CVUploadResponse

# exceptions
from ...modules.master_cv.exceptions import (
    InvalidPDFError,
    S3UploadError,
    FileTooLargeError,
    S3ObjectNotFoundError,
)

router = APIRouter(prefix="/master-cv", tags=["master-cv"])


@router.post("/", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_master_cv(
    file: UploadFile = File(...), current_user_id: str = Depends(get_current_user_id)
):
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


@router.put(
    "/{old_object_key:path}",
    response_model=CVUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def update_master_cv(old_object_key: str, file: UploadFile = File(...)):
    content = await file.read()

    try:
        object_key = await process_cv_update(old_object_key, file.filename, content)
    except (InvalidPDFError, FileTooLargeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except S3UploadError as e:
        raise HTTPException(status_code=502, detail=str(e))

    except S3ObjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CVUploadResponse(
        details="success", filename=file.filename, object_key=object_key
    )


@router.delete("/{object_key:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_master_cv(object_key: str):

    try:
        delete_pdf_from_s3(object_key)
    except S3ObjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
