from app.core.llm_client import get_structured_llm
from app.modules.companies.schemas import VerificationResult


def get_verification_llm():
    return get_structured_llm(VerificationResult)
