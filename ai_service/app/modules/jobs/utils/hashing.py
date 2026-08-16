# app/modules/jobs/utils/hashing.py
import hashlib


def compute_dedup_hash(title: str, company: str, location: str | None) -> str:
    """
    Deterministic hash used to detect the same job posted across
    multiple sources (LinkedIn, Greenhouse, Adzuna, etc.)
    """
    key = f"{title.strip().lower()}|{company.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()