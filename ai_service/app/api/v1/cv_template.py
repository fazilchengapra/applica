import hashlib
from uuid import UUID
from fastapi import APIRouter, status, Depends, HTTPException
from app.db.session import get_db
from app.modules.cv_template.models import CVTemplate
from app.modules.cv_template.schemas import (
    CreateCVTemplateRequest,
    CreateCVTemplateResponse,
    CVTemplateAdminOut,
    DeleteCVTemplateResponse,
)
from app.dependencies.admin import require_admin
from app.modules.cv_template.repository import create, get_all, get_by_id, soft_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.cv_template.tasks import process_cv_template_task

router = APIRouter(prefix="/admin/cv-templates", tags=["CV Templates"])


def _hash_tex(tex: str) -> str:
    normalized = "\n".join(line.rstrip() for line in tex.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=CreateCVTemplateResponse
)
async def create_cv_template(
    payload: CreateCVTemplateRequest,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    tex_hash = _hash_tex(payload.tex)
    existing = await db.scalar(
        select(CVTemplate).where(CVTemplate.tex_hash == tex_hash)
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An identical template already exists (id: {existing.id}, title: '{existing.title}')",
        )
    template_record = await create(
        title=payload.title,
        description=payload.description,
        tex=payload.tex,
        tex_hash=tex_hash,
        db=db,
    )
    hash_tex = _hash_tex(payload.tex)
    print("hash_tex is : ", hash_tex)
    process_cv_template_task.delay(str(template_record.id))
    return CreateCVTemplateResponse(
        message="CV template created successfully",
        id=template_record.id,
        title=template_record.title,
    )


@router.get("/", response_model=list[CVTemplateAdminOut])
async def list_cv_templates_admin(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    return await get_all(db, include_inactive=True, include_deleted=True)


@router.get("/{template_id}", response_model=CVTemplateAdminOut)
async def get_cv_template_admin(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    template = await get_by_id(
        db, template_id, include_inactive=True, include_deleted=True
    )
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return template


@router.delete("/{template_id}", response_model=DeleteCVTemplateResponse)
async def delete_cv_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    template = await soft_delete(db, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or already deleted",
        )
    return DeleteCVTemplateResponse(
        message="Template deleted successfully", id=template.id
    )
