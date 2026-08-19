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

from pydantic import BaseModel, Field
from enum import Enum


class RemoteType(str, Enum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"


class SalaryPeriod(str, Enum):
    yearly = "yearly"
    monthly = "monthly"
    hourly = "hourly"


class StructuredJob(BaseModel):
    normalized_title: str = Field(..., description="Cleaned, canonical job title")
    description: str = Field(..., description="Cleaned description, HTML/noise removed")

    location_city: str | None = None
    location_country: str | None = None
    remote_type: RemoteType | None = None

    employment_type: EmploymentType | None = None

    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = Field(None, description="ISO 4217, e.g. USD")
    salary_period: SalaryPeriod | None = None

    posted_at: str | None = Field(None, description="ISO 8601 date string, null if unparseable")


from pydantic import BaseModel
from enum import Enum


class SkillType(str, Enum):
    required = "required"
    preferred = "preferred"


class ExtractedSkill(BaseModel):
    skill_name: str
    skill_type: SkillType


class ExtractedSkills(BaseModel):
    skills: list[ExtractedSkill]
