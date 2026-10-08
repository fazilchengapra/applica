"""Unit tests for the RAG content-hashing utilities."""

import hashlib

from app.modules.rag.constants import HASH_ALGORITHM
from app.modules.rag.utils.hashing import calculate_hash


class TestCalculateHash:
    def test_is_deterministic(self):
        assert calculate_hash("same content") == calculate_hash("same content")

    def test_matches_the_configured_algorithm(self):
        expected = hashlib.new(HASH_ALGORITHM, b"content here").hexdigest()

        assert calculate_hash("content here") == expected

    def test_different_content_hashes_differently(self):
        assert calculate_hash("old content") != calculate_hash("new content")

    def test_a_single_character_change_changes_the_hash(self):
        assert calculate_hash("Intro text.") != calculate_hash("Intro texy.")

    def test_empty_content_hashes_to_the_empty_digest(self):
        assert calculate_hash("") == hashlib.new(HASH_ALGORITHM, b"").hexdigest()