from pathlib import Path

from .base import BaseLoader
from .docx import DocxLoader
from .html import HtmlLoader
from .pdf import PdfLoader
from .txt import TxtLoader

_LOADER_CLASSES: tuple[type[BaseLoader], ...] = (
    PdfLoader,
    DocxLoader,
    HtmlLoader,
    TxtLoader,
)

_BY_EXTENSION = {
    extension: loader_class()
    for loader_class in _LOADER_CLASSES
    for extension in loader_class.extensions
}

_BY_CONTENT_TYPE = {
    content_type: loader_class()
    for loader_class in _LOADER_CLASSES
    for content_type in loader_class.content_types
}


def get_loader(file_name: str | None = None, content_type: str | None = None) -> BaseLoader:
    """Return the loader for a file, chosen by extension or MIME type.

    The extension wins because it is the most reliable signal; the
    content type is only a fallback for uploads that carry one.
    """
    extension = Path(file_name).suffix.lower() if file_name else ""

    if extension in _BY_EXTENSION:
        return _BY_EXTENSION[extension]

    if content_type:
        normalized = content_type.split(";")[0].strip().lower()

        if normalized in _BY_CONTENT_TYPE:
            return _BY_CONTENT_TYPE[normalized]

    raise ValueError(f"Unsupported file type: {file_name or content_type}")
