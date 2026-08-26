from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class CreateCVTemplateRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )
    description: str | None = None
    tex: str = Field(
        min_length=1,
    )

    @field_validator("tex")
    @classmethod
    def must_look_like_latex(cls, v: str) -> str:
        if "\\documentclass" not in v:
            raise ValueError("tex source must contain a \\documentclass declaration")
        return v


class CreateCVTemplateResponse(BaseModel):
    message: str
    id: UUID
    title: str


class CVTemplateAdminOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    is_active: bool
    file_s3_key: str | None
    image_s3_key: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeleteCVTemplateResponse(BaseModel):
    message: str
    id: UUID


class DeleteCVTemplateResponse(BaseModel):
    message: str
    id: UUID
