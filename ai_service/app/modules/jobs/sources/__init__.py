# app/modules/jobs/sources/__init__.py
from .api_sources.adzuna import AdzunaSource
from .base import BaseJobSource

SOURCE_REGISTRY: dict[str, type[BaseJobSource]] = {
    "adzuna": AdzunaSource,
}
