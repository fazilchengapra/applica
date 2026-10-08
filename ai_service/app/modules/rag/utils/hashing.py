"""Content hashing utilities.

Hashes let change detection decide whether content has changed without
re-embedding it: identical content produces the identical hash, so hashes
are compared instead of the text itself. Hashing runs at document, section
and chunk granularity.
"""

import hashlib

from app.modules.rag.constants import HASH_ALGORITHM


def calculate_hash(content: str) -> str:
    """Return the hex digest of content under the configured algorithm."""
    digest = hashlib.new(HASH_ALGORITHM)
    digest.update(content.encode("utf-8"))
    return digest.hexdigest()