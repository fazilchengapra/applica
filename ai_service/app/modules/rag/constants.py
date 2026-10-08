"""Shared constant values for the RAG module.

Collecting the literals in one place keeps every loader focused on
parsing and gives a single file to adjust when a format detail changes.
"""

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
CHUNK_TOKEN_ENCODING = "o200k_base"

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

HTML_SKIPPED_XPATH = "//script|//style|//noscript|//head"

HTML_BLOCK_ELEMENTS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "dd",
        "div",
        "dl",
        "dt",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
)

TEXT_ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")
