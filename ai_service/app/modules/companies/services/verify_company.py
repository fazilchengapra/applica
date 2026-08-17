from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.modules.companies.models import Company
from app.modules.companies.schemas import EvidenceBundle, VerificationResult
from app.modules.companies.utils.serpapi import fetch_search_results, parse_evidence
from app.modules.companies.exceptions import (
    CompanyNotFoundError,
    VerificationDecisionError,
)

from app.modules.companies.llm_client import get_structured_llm


# ---- helper service: fetch the company row ----
async def get_company_or_raise(session: AsyncSession, company_id: UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise CompanyNotFoundError(f"Company {company_id} not found")
    return company


# ---- helper service: gather evidence (cache-aware) ----
async def gather_evidence(company: Company) -> EvidenceBundle:
    # if company.verification_evidence is not None:
    #     print("Using cached evidence for company:", company.normalized_name)
    #     return EvidenceBundle.model_validate(company.verification_evidence)
    
    website_res, linkedin_res, reddit_res = await fetch_search_results(
        company.normalized_name
    )
    return parse_evidence(
        company.normalized_name, website_res, linkedin_res, reddit_res
    )


# ---- helper service: LLM decision ----
async def decide_verification(company_name: str, evidence: EvidenceBundle) -> VerificationResult:
    llm = get_structured_llm(output_schema=VerificationResult)

    prompt = (
        f"Company name: {company_name}\n"
        f"Website candidates: {evidence.website_candidates}\n"
        f"LinkedIn candidates: {evidence.linkedin_candidates}\n"
        f"Reputation snippets: {evidence.reputation_snippets}\n\n"
        "Decide whether this is a legitimate, currently operating company. "
        "Return verdict, confidence (0-1), best website_url, best linkedin_url, "
        "and brief reasoning."
    )

    try:
        return await llm.ainvoke(prompt)
    except Exception as e:
        raise VerificationDecisionError(f"LLM decision failed: {e}") from e


# ---- helper service: apply verdict + persist ----
async def apply_verdict(
    session: AsyncSession,
    company: Company,
    evidence: EvidenceBundle,
    result: VerificationResult,
) -> Company:
    if (
        result.confidence >= float(settings.VERIFICATION_APPROVE_THRESHOLD)
        and result.verdict in ("approved", "rejected")
    ):
        final_status = result.verdict
    else:
        final_status = "pending_review"

    company.status = final_status
    company.confidence_score = result.confidence
    company.verified_website_url = result.website_url
    company.verified_linkedin_url = result.linkedin_url
    company.verification_reasoning = result.reasoning
    company.verification_evidence = evidence.model_dump()
    company.verified_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(company)
    return company


# ---- orchestrator: coordinates the full flow ----
async def verify_company(session: AsyncSession, company_id: UUID) -> Company:
    company = await get_company_or_raise(session, company_id)
    evidence = await gather_evidence(company)
    result = await decide_verification(company.normalized_name, evidence)
    print('result is : ', result)
    return await apply_verdict(session, company, evidence, result)
