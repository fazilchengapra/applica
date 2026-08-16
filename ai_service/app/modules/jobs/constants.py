from enum import Enum


class SourceType(str, Enum):
    API = "api"
    ATS_DIRECT = "ats_direct"
    SCRAPE = "scrape"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"