from io import BytesIO

import fitz


def extract_pdf(file_bytes: bytes) -> str:
    document = fitz.open(stream=file_bytes, filetype="pdf")

    text = []

    for page in document:
        text.append(page.get_text())

    document.close()

    return "\n".join(text).strip()
