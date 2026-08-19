import hashlib
import unicodedata
import re


def normalize_text(text: str | None) -> str:
    """Lowercase, strip accents, collapse whitespace, strip punctuation noise."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def compute_dedup_hash(title: str, company: str, location: str | None) -> str:

    key = f"{title.strip().lower()}|{company.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()
