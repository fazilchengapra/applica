from app.core.llm_client import get_structured_llm
from app.modules.jobs.schemas import ExtractedSkills

from ..prompts.skill_extraction_prompt import SKILLS_PROMPT


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
