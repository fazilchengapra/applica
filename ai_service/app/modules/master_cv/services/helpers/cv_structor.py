from app.modules.master_cv.schemas import StructuredCV
from app.modules.master_cv.exceptions import CVStructuringError
from app.modules.master_cv.llm_client import get_structuring_llm


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

    return result.model_dump(mode="json")
