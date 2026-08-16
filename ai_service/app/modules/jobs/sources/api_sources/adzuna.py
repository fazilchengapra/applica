# app/modules/jobs/sources/api_sources/adzuna.py
import logging
import httpx
from app.modules.jobs.sources.base import BaseJobSource
from app.modules.jobs.sources.api_sources.adzuna_client import AdzunaClient
from app.modules.jobs.schemas import RawJobInput
from app.modules.jobs.constants import SourceType
from app.modules.jobs.exceptions import JobSourceUnavailableError

logger = logging.getLogger(__name__)


class AdzunaSource(BaseJobSource):
    source_type = SourceType.API
    source_name = "adzuna"

    def __init__(self):
        self._client = AdzunaClient()

    async def fetch(self, query: str, max_pages: int = 3) -> list[RawJobInput]:
        jobs: list[RawJobInput] = []

        for page in range(1, max_pages + 1):
            try:
                data = await self._client.search(query=query, page=page)
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Adzuna fetch failed on page {page}: {e.response.status_code}"
                )
                raise JobSourceUnavailableError(
                    f"Adzuna API error: {e.response.status_code}"
                ) from e
            except httpx.TimeoutException as e:
                raise JobSourceUnavailableError("Adzuna API timeout") from e

            results = data.get("results", [])
            if not results:
                break  # no more pages

            jobs.extend(self._map(raw) for raw in results)

        return jobs

    def _map(self, raw: dict) -> RawJobInput:
        salary_raw = None
        if raw.get("salary_min") or raw.get("salary_max"):
            salary_raw = f"{raw.get('salary_min', '')}-{raw.get('salary_max', '')}"

        return RawJobInput(
            source_type=self.source_type,
            source_name=self.source_name,
            external_id=str(raw["id"]),
            source_url=raw["redirect_url"],
            title=raw.get("title"),
            company_name=raw.get("company", {}).get("display_name"),
            description_raw=raw.get("description"),
            location_raw=raw.get("location", {}).get("display_name"),
            salary_raw=salary_raw,
            posted_at_raw=raw.get("created"),
        )