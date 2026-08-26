from fastapi import APIRouter, status, Depends
from app.db.session import get_db
from app.modules.cv_template.schemas import (
    CreateCVTemplateRequest,
    CreateCVTemplateResponse,
)
from app.modules.cv_template.repository import create
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cv_template.tasks import process_cv_template_task

router = APIRouter(prefix="/admin/cv-templates", tags=["CV Templates"])


@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=CreateCVTemplateResponse
)
async def create_cv_template(
    payload: CreateCVTemplateRequest, db: AsyncSession = Depends(get_db)
):
    template_record = await create(
        title=payload.title, description=payload.description, tex=payload.tex, db=db
    )
    process_cv_template_task.delay(str(template_record.id))
    return CreateCVTemplateResponse(
        message="CV template created successfully",
        id=template_record.id,
        title=template_record.title,
    )
