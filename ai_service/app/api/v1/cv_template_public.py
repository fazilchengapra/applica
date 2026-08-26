from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

from app.shared.utils.s3 import get_public_url

from app.modules.cv_template.repository import get_all, get_by_id
from app.modules.cv_template.schemas import CVTemplatePublicOut

router = APIRouter(prefix="/cv-templates", tags=["CV Templates"])


def _to_public(template) -> CVTemplatePublicOut:
    image_url = None
    if template.image_s3_key:
        image_url = get_public_url(template.image_s3_key)
    out = CVTemplatePublicOut.model_validate(template)
    out.image_url = image_url
    return out


@router.get("/", response_model=list[CVTemplatePublicOut])
async def list_cv_templates(
    db: AsyncSession = Depends(get_db),
):
    templates = await get_all(db, include_inactive=False, include_deleted=False)
    return [_to_public(t) for t in templates]


@router.get("/{template_id}", response_model=CVTemplatePublicOut)
async def get_cv_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    template = await get_by_id(
        db, template_id, include_inactive=False, include_deleted=False
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return _to_public(template)
