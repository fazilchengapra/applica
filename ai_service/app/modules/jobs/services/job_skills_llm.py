# app/modules/jobs/services/job_skills_llm.py

from app.core.llm_client import get_structured_llm
from app.modules.jobs.schemas import ExtractedSkills

SKILLS_PROMPT = """Extract technical skills, tools, frameworks, and technologies mentioned in this job description.

Classify each skill as:
- "required": explicitly stated as required, must-have, mandatory, or a core responsibility
- "preferred": mentioned as nice-to-have, bonus, a plus, or preferred but not mandatory

Rules:
- Use canonical, commonly recognized names (e.g. "Node.js" not "nodejs", "PostgreSQL" not "postgres", "AWS" not "amazon web services")
- Only extract skills that are actually mentioned in the text below — do not infer or invent skills
- Do not extract soft skills (e.g. "communication", "teamwork") — only technical skills, tools, languages, frameworks, and platforms
- If a skill is mentioned multiple times, include it only once

Job description:
{description}"""


def get_skills_llm():
    return get_structured_llm(ExtractedSkills)


async def extract_skills(llm, description: str) -> ExtractedSkills:
    """
    Runs the skill-extraction chain against a job's structured description.
    The actual async boundary is here (.ainvoke), not at chain construction.
    """
    prompt = SKILLS_PROMPT.format(description=description)
    result: ExtractedSkills = await llm.ainvoke(prompt)
    return result