from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.modules.master_cv.schemas import StructuredCV
from app.modules.master_cv.exceptions import CVStructuringError


def get_structuring_llm() -> ChatOpenAI:
    llm = ChatOpenAI(
        model=settings.OPENROUTER_MODEL,  # e.g. "openai/gpt-4o-mini" — keep configurable, not hardcoded
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        temperature=0,
    )
    return llm.with_structured_output(StructuredCV)


def structure_cv_text(raw_text: str) -> StructuredCV:
    structuring_llm = get_structuring_llm()

    prompt = f"""Extract structured information from this resume text.
                 Return only the fields defined in the schema. If a field is not present, omit it or use null.

                 Resume text:
                {raw_text}
"""

    try:
        result = structuring_llm.invoke(prompt)
    except Exception as e:
        raise CVStructuringError(f"Failed to structure CV text: {e}") from e

    return result.model_dump(mode='json')
