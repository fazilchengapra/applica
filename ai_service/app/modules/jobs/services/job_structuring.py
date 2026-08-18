from app.modules.jobs.schemas import StructuredJob
from app.modules.jobs.models import RawJob

STRUCTURING_PROMPT = """You are structuring a raw job posting into normalized fields.

Title: {title}
Employment type (raw): {employment_type_raw}
Salary (raw): {salary_raw}
Posted date (raw): {posted_at_raw}
Location (raw): {location_raw}
Description:
{description_raw}

Extract normalized_title, cleaned description, location city/country, remote_type,
employment_type, salary fields, and posted_at as ISO date. Use null for anything
that cannot be confidently determined from the text above. Do not guess."""


async def structure_raw_job(llm, raw_job: RawJob) -> StructuredJob:
    prompt = STRUCTURING_PROMPT.format(
        title=raw_job.title or "",
        employment_type_raw=raw_job.employment_type_raw or "",
        salary_raw=raw_job.salary_raw or "",
        posted_at_raw=raw_job.posted_at_raw or "",
        location_raw=raw_job.location_raw or "",
        description_raw=raw_job.description_raw or "",
    )
    result: StructuredJob = await llm.ainvoke(prompt)
    return result
