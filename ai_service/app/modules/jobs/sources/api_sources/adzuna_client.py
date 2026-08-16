import httpx
from app.core.config import settings

class AdzunaClient:
    def __init__(self):
        self._base_url = settings.ADZUNA_BASE_URL
        self._country = settings.ADZUNA_COUNTRY
        self._app_id = settings.ADZUNA_APP_ID
        self._app_key = settings.ADZUNA_APP_KEY

    async def search(self, query: str, page: int = 1, results_per_page: int = 50) -> dict:
        url = f"{self._base_url}/jobs/{self._country}/search/{page}"
        params = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query,
            "results_per_page": results_per_page,
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()