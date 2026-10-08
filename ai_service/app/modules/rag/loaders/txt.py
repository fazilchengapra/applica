from app.modules.rag.constants import TEXT_ENCODINGS

from .base import BaseLoader


class TxtLoader(BaseLoader):
    """Decodes plain-text files.

    Tries UTF-8 first (with BOM handling) and falls back to Windows-1252
    and Latin-1 so any byte sequence still produces ingestible text.
    """

    extensions: tuple[str, ...] = (".txt",)
    content_types: tuple[str, ...] = ("text/plain",)

    def load(self, data: bytes) -> str:
        for encoding in TEXT_ENCODINGS:
            try:
                return data.decode(encoding).strip()
            except UnicodeDecodeError:
                continue

        raise ValueError("Unable to decode text file")
