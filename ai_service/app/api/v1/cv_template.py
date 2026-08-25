from fastapi import APIRouter, status
from app.modules.cv_template.schemas import (
    CreateCVTemplateRequest,
    CreateCVTemplateResponse,
)

router = APIRouter(prefix="/admin/cv-templates", tags=["CV Templates"])


@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=CreateCVTemplateResponse
)
async def create_cv_template(payload: CreateCVTemplateRequest):
    return CreateCVTemplateResponse(
        message="CV template created successfully",
        id="f198c16b-2299-4c4a-bd58-d8e5b291bdcc",
        title="noting",
    )
