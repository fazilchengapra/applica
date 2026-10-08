from lxml import html

from app.modules.rag.constants import HTML_BLOCK_ELEMENTS, HTML_SKIPPED_XPATH

from .base import BaseLoader


class HtmlLoader(BaseLoader):
    """Strips HTML down to readable plain text.

    Scripts, styles and the document head are removed, and block-level
    elements become line breaks so headings and paragraphs stay
    separated for the chunking service.
    """

    extensions: tuple[str, ...] = (".html", ".htm")
    content_types: tuple[str, ...] = ("text/html",)

    def load(self, data: bytes) -> str:
        document = html.fromstring(data)

        for node in document.xpath(HTML_SKIPPED_XPATH):
            node.drop_tree()

        parts: list[str] = []
        self._walk(document, parts)

        lines = (" ".join(line.split()) for line in "".join(parts).splitlines())

        return "\n".join(line for line in lines if line)

    def _walk(self, element: html.HtmlElement, parts: list[str]) -> None:
        if element.text:
            parts.append(element.text)

        for child in element:
            if isinstance(child.tag, str):
                if child.tag == "br":
                    parts.append("\n")
                elif child.tag in HTML_BLOCK_ELEMENTS:
                    self._walk(child, parts)
                    parts.append("\n")
                else:
                    self._walk(child, parts)

            if child.tail:
                parts.append(child.tail)
