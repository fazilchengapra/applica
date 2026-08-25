from pydantic import BaseModel, Field
from uuid import UUID


class CreateCVTemplateRequest(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

    tex: str = Field(
        min_length=1,
    )


class CreateCVTemplateResponse(BaseModel):
    message: str
    id: UUID
    title: str
