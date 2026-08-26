from pydantic import BaseModel, Field, field_validator
from uuid import UUID


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
