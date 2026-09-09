from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.modules.master_cv.models import MasterCV


class AdminMasterCVResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class AdminMasterCVVersionResponse(BaseModel):
    id: UUID
    version: int
    target_role: str | None
    status: str
    is_current: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminMasterCVDetailsResponse(BaseModel):
    master_cv: AdminMasterCVResponse
    versions: list[AdminMasterCVVersionResponse]


router = APIRouter(prefix="/admin/users", tags=["Admin Master CV"])


@router.get(
    "/{user_id}/master-cv",
    response_model=AdminMasterCVDetailsResponse,
    status_code=status.HTTP_200_OK,
)
async def get_user_master_cv_for_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    master_cv = await db.scalar(
        select(MasterCV)
        .options(selectinload(MasterCV.versions))
        .where(MasterCV.user_id == user_id)
    )
    if master_cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master CV not found",
        )

    master_cv_data = AdminMasterCVResponse(
        id=master_cv.id,
        status="deleted" if master_cv.deleted_at is not None else "active",
        created_at=master_cv.created_at,
        updated_at=master_cv.updated_at,
        deleted_at=master_cv.deleted_at,
    )
    versions = [
        AdminMasterCVVersionResponse.model_validate(version)
        for version in sorted(master_cv.versions, key=lambda item: item.version)
    ]

    return AdminMasterCVDetailsResponse(master_cv=master_cv_data, versions=versions)
