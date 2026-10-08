import fitz

from .base import BaseLoader


class PdfLoader(BaseLoader):
    """Extracts text from PDF files, page by page.

    Pages are joined with a blank line so page boundaries survive as
    paragraph breaks for the chunking service.
    """

    extensions: tuple[str, ...] = (".pdf",)
    content_types: tuple[str, ...] = ("application/pdf",)

    def load(self, data: bytes) -> str:
        with fitz.open(stream=data, filetype="pdf") as document:
            text = "\n\n".join(page.get_text() for page in document)

        return text.strip()
