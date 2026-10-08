"""Unit tests for the RAG chunking service."""

import tiktoken

from app.modules.rag.constants import CHUNK_OVERLAP, CHUNK_SIZE, CHUNK_TOKEN_ENCODING
from app.modules.rag.services.chunking import split_text
from app.modules.rag.utils.hashing import calculate_hash

_encoder = tiktoken.get_encoding(CHUNK_TOKEN_ENCODING)


def _tokens(text: str) -> int:
    return len(_encoder.encode(text))


class TestSplitText:
    def test_short_text_is_a_single_chunk(self):
        chunks = split_text("Just a short note.")

        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].text == "Just a short note."
        assert chunks[0].characters == len("Just a short note.")
        assert chunks[0].tokens == _tokens("Just a short note.")
        assert chunks[0].content_hash == calculate_hash("Just a short note.")

    def test_long_text_keeps_every_chunk_within_size(self):
        text = ("word " * 5000).strip()

        chunks = split_text(text)

        assert len(chunks) > 1
        assert all(chunk.tokens <= CHUNK_SIZE for chunk in chunks)
        assert all(chunk.characters > 0 for chunk in chunks)

        indices = [chunk.index for chunk in chunks]
        assert indices == list(range(len(chunks)))

    def test_every_chunk_carries_a_stable_content_hash(self):
        text = " ".join(f"token{i}" for i in range(3000))

        chunks = split_text(text)

        assert all(chunk.content_hash == calculate_hash(chunk.text) for chunk in chunks)
        assert all(
            chunk.content_hash != other.content_hash
            for chunk in chunks
            for other in chunks
            if other is not chunk
        )

    def test_consecutive_chunks_overlap(self):
        text = ("word " * 5000).strip()

        chunks = split_text(text)

        for previous, current in zip(chunks, chunks[1:]):
            previous_words = set(previous.text.split())
            current_words = set(current.text.split())
            assert previous_words & current_words, "expected an overlap token window"

    def test_overlap_is_smaller_than_chunk_size(self):
        assert CHUNK_OVERLAP < CHUNK_SIZE, "overlap must stay under chunk_size"

    def test_empty_text_yields_no_chunks(self):
        assert split_text("") == []