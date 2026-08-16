from pydantic import BaseModel, Field
from .constants import SourceType


class FetchJobsRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, description="Search term, e.g. 'backend engineer'"
    )
    location: str | None = Field(
        None, description="Optional location filter, e.g. 'remote', 'New York'"
    )
    max_pages: int = Field(
        3, ge=1, le=10, description="Max pages to fetch from the source"
    )


# app/modules/jobs/schemas.py
class RawJobInput(BaseModel):
    source_type: SourceType
    source_name: str
    external_id: str | None = None
    source_url: str
    title: str | None = None
    company_name: str | None = None
    description_raw: str | None = None
    location_raw: str | None = None
    salary_raw: str | None = None
    posted_at_raw: str | None = None
