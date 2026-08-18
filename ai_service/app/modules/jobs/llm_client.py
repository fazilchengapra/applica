from app.core.llm_client import get_structured_llm
from app.modules.jobs.schemas import StructuredJob


def get_structuring_llm():
    return get_structured_llm(StructuredJob)
