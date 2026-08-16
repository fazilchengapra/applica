from abc import ABC, abstractmethod
from app.modules.jobs.schemas import RawJobInput
from app.modules.jobs.constants import SourceType

class BaseJobSource(ABC):
    source_type: SourceType
    source_name: str

    @abstractmethod
    async def fetch(self, **kwargs) -> list[RawJobInput]:
        ...