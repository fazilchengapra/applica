from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Form
import uuid
from app.core.dependencies import get_current_user_id
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

# service
from app.modules.master_cv.services.cv_service import (
    process_cv_upload,
    process_cv_update,
    get_all_cv,
    get_parsed_cv,
    get_cv_skills,
)
from app.modules.master_cv.services.master_cv_service import if_master_cv_exist
from app.modules.master_cv.services.cv_stats_service import get_cv_stats
from app.modules.master_cv.services.s3_service import delete_pdf_from_s3

# schema
from ...modules.master_cv.schemas import (
    CVUploadResponse,
    CVStatsResponse,
    CVSkillResponse,
    GetCVSResponse,
    StructuredCV,
)

# exceptions
from ...modules.master_cv.exceptions import (
    InvalidPDFError,
    S3UploadError,
    FileTooLargeError,
    S3ObjectNotFoundError,
    CVNotfoundError,
    CVNotReadyError,
    CVInvalidParsedDataError,
    MultipleMasterCVError,
)

router = APIRouter(prefix="/master-cv", tags=["master-cv"])


@router.post("/", response_model=CVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_master_cv(
    target_role: str = Form(...),
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    content = await file.read()
    try:
        await if_master_cv_exist(current_user_id, session)
        version_id = await process_cv_upload(
            file.filename,
            content,
            current_user_id,
            session=session,
            target_role=target_role,
        )
    except (InvalidPDFError, FileTooLargeError, MultipleMasterCVError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except S3UploadError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return CVUploadResponse(
        details="success", filename=file.filename, version_id=str(version_id)
    )


@router.put(
    "/{cv_id:uuid}",
    response_model=CVUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def update_master_cv(
    cv_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    content = await file.read()

    try:
        version_id = await process_cv_update(
            file.filename, content, cv_id, current_user_id, session
        )
    except (InvalidPDFError, FileTooLargeError, CVNotfoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except S3UploadError as e:
        raise HTTPException(status_code=502, detail=str(e))

    except S3ObjectNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CVUploadResponse(
        details="success", filename=file.filename, version_id=str(version_id)
    )


@router.get("/stats", response_model=CVStatsResponse, status_code=status.HTTP_200_OK)
async def get_master_cv_stats(
    current_user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    stats = await get_cv_stats(current_user_id, session)
    return CVStatsResponse(**stats)


@router.get("/", response_model=list[GetCVSResponse], status_code=status.HTTP_200_OK)
async def get_master_cv_versions(
    current_user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    return await get_all_cv(current_user_id, session)


@router.get(
    "/parsed",
    response_model=StructuredCV,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "No current CV version"},
        409: {"description": "Current CV version is not completed yet"},
    },
)
async def get_parsed_master_cv(
    current_user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    try:
        return await get_parsed_cv(current_user_id, session)
    except CVNotfoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CVNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except CVInvalidParsedDataError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/skills",
    response_model=list[CVSkillResponse],
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "No current CV version"},
        409: {"description": "Current CV version is not completed yet"},
    },
)
async def get_master_cv_skills(
    current_user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    try:
        return await get_cv_skills(current_user_id, session)
    except CVNotfoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CVNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# @router.delete("/{object_key:path}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_master_cv(object_key: str):

#     try:
#         delete_pdf_from_s3(object_key)
#     except S3ObjectNotFoundError as e:
#         raise HTTPException(status_code=404, detail=str(e))
