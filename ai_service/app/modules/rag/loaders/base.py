from abc import ABC, abstractmethod
from typing import ClassVar


class BaseLoader(ABC):

    extensions: ClassVar[tuple[str, ...]] = ()
    content_types: ClassVar[tuple[str, ...]] = ()

    @abstractmethod
    def load(self, data: bytes) -> str:
        """Parse file content and return it as plain text."""
