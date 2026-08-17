import asyncio
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.modules.companies.schemas import EvidenceBundle
from app.modules.companies.exceptions import EvidenceGatheringError


async def _serpapi_search(query: str, num: int = 10) -> dict:
    params = {
        "engine": "google",
        "q": query,
        "api_key": settings.SERPAPI_KEY,
        "num": num,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get("https://serpapi.com/search", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        raise EvidenceGatheringError(f"SerpApi request failed: {e}") from e


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "")


def _is_linkedin(url: str) -> bool:
    return "linkedin.com/company" in url


def _is_reputation_source(url: str) -> bool:
    domain = _domain(url)
    return any(d in domain for d in ["reddit.com", "glassdoor.com", "indeed.com"])


def _is_likely_official_site(url: str) -> bool:
    excluded = [
        "linkedin.com", "reddit.com", "glassdoor.com", "indeed.com",
        "facebook.com", "twitter.com", "x.com", "crunchbase.com", "wikipedia.org",
    ]
    domain = _domain(url)
    return not any(d in domain for d in excluded)


def parse_evidence(
    company_name: str, website_res: dict, linkedin_res: dict, reddit_res: dict
) -> EvidenceBundle:
    website_candidates = [
        r["link"] for r in website_res.get("organic_results", [])
        if _is_likely_official_site(r["link"])
    ][:3]

    linkedin_candidates = [
        r["link"] for r in linkedin_res.get("organic_results", [])
        if _is_linkedin(r["link"])
    ][:2]

    reputation_snippets = [
        r.get("snippet", "") for r in reddit_res.get("organic_results", [])
        if _is_reputation_source(r["link"]) and r.get("snippet")
    ][:5]

    return EvidenceBundle(
        company_name=company_name,
        website_candidates=website_candidates,
        linkedin_candidates=linkedin_candidates,
        reputation_snippets=reputation_snippets,
        raw_results={"website": website_res, "linkedin": linkedin_res, "reddit": reddit_res},
    )


async def fetch_search_results(normalized_company_name: str) -> tuple[dict, dict, dict]:
    website_query = f'"{normalized_company_name}" official website'
    linkedin_query = f'"{normalized_company_name}" site:linkedin.com/company'
    reddit_query = f'"{normalized_company_name}" site:reddit.com OR site:glassdoor.com'

    return await asyncio.gather(
        _serpapi_search(website_query),
        _serpapi_search(linkedin_query),
        _serpapi_search(reddit_query),
    )