from app.core.llm_client import get_structured_llm
from app.modules.master_cv.schemas import StructuredCV

def get_structuring_llm():
    return get_structured_llm(StructuredCV)