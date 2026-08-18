import hashlib


def compute_dedup_hash(title: str, company: str, location: str | None) -> str:

    key = f"{title.strip().lower()}|{company.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()
