import io
import xml.etree.ElementTree as ET
import zipfile

from app.modules.rag.constants import WORD_NS

from .base import BaseLoader


class DocxLoader(BaseLoader):

    extensions: tuple[str, ...] = (".docx",)
    content_types: tuple[str, ...] = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    def load(self, data: bytes) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                with archive.open("word/document.xml") as file:
                    root = ET.fromstring(file.read())
        except KeyError as error:
            raise ValueError("Not a valid DOCX file") from error

        return self._extract_paragraphs(root).strip()

    def _extract_paragraphs(self, root: ET.Element) -> str:
        paragraphs = []

        for paragraph in root.iter(f"{WORD_NS}p"):
            parts = []

            for node in paragraph.iter():
                if node.tag == f"{WORD_NS}t":
                    parts.append(node.text or "")
                elif node.tag == f"{WORD_NS}tab":
                    parts.append("\t")
                elif node.tag == f"{WORD_NS}br":
                    parts.append("\n")

            paragraphs.append("".join(parts))

        return "\n".join(paragraphs)
