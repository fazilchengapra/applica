# app/modules/companies/utils/normalize.py
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass

LEGAL_SUFFIXES = [
    r"\bincorporated\b",
    r"\binc\b",
    r"\bcorporation\b",
    r"\bcorp\b",
    r"\bllc\b",
    r"\bllp\b",
    r"\bltd\b",
    r"\blimited\b",
    r"\bco\b",
    r"\bcompany\b",
    r"\bgmbh\b",
    r"\bplc\b",
    r"\bpvt\b",
    r"\bpte\b",
    r"\bpty\b",
    r"\bs\.a\.\b",
    r"\bab\b",
]


def normalize_company_name(raw: str) -> str:
    if not raw:
        return ""
    name = raw.strip().lower()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[.,\-']", "", name)
    for suffix in LEGAL_SUFFIXES:
        name = re.sub(suffix, "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


@dataclass
class CompanyGroup:
    normalized_name: str
    display_name: str
    raw_job_ids: list[str]
    source_types: set[str]


def group_raw_jobs_by_company(raw_jobs: list[dict]) -> dict[str, CompanyGroup]:

    groups: dict[str, CompanyGroup] = {}

    for job in raw_jobs:
        norm = normalize_company_name(job["company_name"])
        if not norm:
            continue  # skip junk rows with empty/garbage company_name

        if norm not in groups:
            groups[norm] = CompanyGroup(
                normalized_name=norm,
                display_name=job["company_name"].strip(),
                raw_job_ids=[],
                source_types=set(),
            )

        groups[norm].raw_job_ids.append(job["id"])
        groups[norm].source_types.add(job["source_type"])

    return groups
