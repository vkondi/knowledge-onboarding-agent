"""Tests for knowledge_onboarding_agent.embeddings.chunk_embedder.

Uses a fake EmbeddingProvider (duck-typed) so no Ollama daemon is required.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from knowledge_onboarding_agent.embeddings.chunk_embedder import ChunkEmbedder
from knowledge_onboarding_agent.models import Chunk, EmbeddedChunk

_DIM = 4  # small vectors for unit tests


def _make_chunk(content: str, index: int = 0, path: Path | None = None) -> Chunk:
    p = path or Path("doc.md")
    return Chunk(
        id=f"{p.stem}:{index}",
        source_path=p,
        content=content,
        chunk_index=index,
        metadata={"heading": "", "word_count": len(content.split()), "source_file": str(p)},
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )


class FakeEmbedder:
    """Deterministic fake that produces a fixed-length vector per text."""

    def __init__(self, dim: int = _DIM) -> None:
        self._dim = dim
        self.call_count = 0
        self.received_texts: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        self.received_texts.append(list(texts))
        # Use hash of the text as a deterministic seed for the vector.
        result = []
        for text in texts:
            seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
            result.append([(seed >> (i * 8) & 0xFF) / 255.0 for i in range(self._dim)])
        return result


class TestChunkEmbedderEmbedChunks:
    @pytest.fixture
    def embedder_pair(self):
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake)
        return ce, fake

    def test_empty_input_returns_empty_list(self, embedder_pair):
        ce, _ = embedder_pair
        assert ce.embed_chunks([]) == []

    def test_single_chunk_returns_one_embedded_chunk(self, embedder_pair):
        ce, _ = embedder_pair
        chunk = _make_chunk("Hello world.")
        result = ce.embed_chunks([chunk])
        assert len(result) == 1
        assert isinstance(result[0], EmbeddedChunk)

    def test_embedded_chunk_wraps_original_chunk(self, embedder_pair):
        ce, _ = embedder_pair
        chunk = _make_chunk("Test content.")
        result = ce.embed_chunks([chunk])
        assert result[0].chunk is chunk

    def test_vector_length_matches_embedder_dimension(self, embedder_pair):
        ce, _ = embedder_pair
        chunk = _make_chunk("Some text here.")
        result = ce.embed_chunks([chunk])
        assert len(result[0].vector) == _DIM

    def test_multiple_chunks_all_returned(self, embedder_pair):
        ce, _ = embedder_pair
        chunks = [_make_chunk(f"Chunk {i}", index=i) for i in range(5)]
        result = ce.embed_chunks(chunks)
        assert len(result) == 5

    def test_order_preserved(self, embedder_pair):
        ce, _ = embedder_pair
        chunks = [_make_chunk(f"Text {i}", index=i) for i in range(3)]
        result = ce.embed_chunks(chunks)
        for i, ec in enumerate(result):
            assert ec.chunk.chunk_index == i


class TestChunkEmbedderDeduplication:
    def test_known_hash_skipped_on_first_call(self):
        chunk = _make_chunk("Existing content.")
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake, known_hashes={chunk.content_hash})
        result = ce.embed_chunks([chunk])
        assert result == []
        assert fake.call_count == 0

    def test_known_hashes_accumulate_after_call(self):
        chunks = [_make_chunk(f"Content {i}", index=i) for i in range(3)]
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake)
        ce.embed_chunks(chunks)
        # All three hashes should now be known.
        for chunk in chunks:
            assert chunk.content_hash in ce.known_hashes

    def test_second_call_with_same_chunks_returns_empty(self):
        chunks = [_make_chunk("Repeated content.", index=0)]
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake)
        ce.embed_chunks(chunks)  # first call — embeds
        result = ce.embed_chunks(chunks)  # second call — already known
        assert result == []
        assert fake.call_count == 1  # embed called only once

    def test_within_batch_duplicate_embedded_once(self):
        """Two chunks with identical content should cause only one embed call entry."""
        content = "Duplicate content."
        chunk_a = _make_chunk(content, index=0)
        chunk_b = _make_chunk(content, index=1)
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake)
        result = ce.embed_chunks([chunk_a, chunk_b])
        # Both chunks appear in result.
        assert len(result) == 2
        # But the fake was called with only 1 unique text.
        assert len(fake.received_texts[0]) == 1

    def test_within_batch_duplicates_share_same_vector(self):
        content = "Shared content."
        chunk_a = _make_chunk(content, index=0)
        chunk_b = _make_chunk(content, index=1)
        ce = ChunkEmbedder(embedder=FakeEmbedder())
        result = ce.embed_chunks([chunk_a, chunk_b])
        # Both must carry identical vectors (same object or equal values).
        assert result[0].vector == result[1].vector

    def test_mixed_new_and_known_only_new_embedded(self):
        chunk_known = _make_chunk("Already embedded.")
        chunk_new = _make_chunk("Brand new text.")
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake, known_hashes={chunk_known.content_hash})
        result = ce.embed_chunks([chunk_known, chunk_new])
        assert len(result) == 1
        assert result[0].chunk is chunk_new
        # The embedder should only have received the new text.
        assert fake.received_texts[0] == [chunk_new.content]


class TestChunkEmbedderKnownHashes:
    def test_known_hashes_initially_empty(self):
        ce = ChunkEmbedder(embedder=FakeEmbedder())
        assert ce.known_hashes == frozenset()

    def test_known_hashes_returns_frozenset(self):
        ce = ChunkEmbedder(embedder=FakeEmbedder())
        assert isinstance(ce.known_hashes, frozenset)

    def test_pre_seeded_hashes_respected(self):
        hashes = {"abc123", "def456"}
        ce = ChunkEmbedder(embedder=FakeEmbedder(), known_hashes=hashes)
        assert "abc123" in ce.known_hashes
        assert "def456" in ce.known_hashes

    def test_known_hashes_immutable_from_outside(self):
        """Mutating the returned frozenset does not affect internal state."""
        ce = ChunkEmbedder(embedder=FakeEmbedder())
        snapshot = ce.known_hashes
        # frozenset has no add/remove — this is enforced by type, but verify
        assert not hasattr(snapshot, "add")

    def test_forget_hashes_removes_specified_hashes(self):
        ce = ChunkEmbedder(embedder=FakeEmbedder(), known_hashes={"h1", "h2", "h3"})
        ce.forget_hashes({"h1", "h3"})
        assert "h1" not in ce.known_hashes
        assert "h3" not in ce.known_hashes
        assert "h2" in ce.known_hashes

    def test_forget_hashes_allows_re_embedding(self):
        """After forget_hashes, a previously-known chunk is re-embedded."""
        chunk = _make_chunk("content", 0, Path("doc.md"))
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake, known_hashes={chunk.content_hash})
        # With the hash known, embed_chunks skips it.
        assert ce.embed_chunks([chunk]) == []
        # After forgetting, it is re-embedded.
        ce.forget_hashes({chunk.content_hash})
        result = ce.embed_chunks([chunk])
        assert len(result) == 1

    def test_forget_hashes_unknown_hash_is_safe(self):
        ce = ChunkEmbedder(embedder=FakeEmbedder(), known_hashes={"h1"})
        ce.forget_hashes({"not_there"})  # should not raise
        assert "h1" in ce.known_hashes


class TestChunkEmbedderFromSettings:
    def test_from_settings_constructs_instance(self):
        from knowledge_onboarding_agent.config import load_settings

        settings_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        settings = load_settings(settings_path)
        ce = ChunkEmbedder.from_settings(settings)
        assert isinstance(ce, ChunkEmbedder)


class TestChunkEmbedderKnownPairs:
    def test_known_pairs_skips_exact_hash_source(self):
        """A chunk whose (hash, source) pair is pre-seeded is skipped."""
        chunk = _make_chunk("Pre-indexed content.", 0, Path("page.md"))
        ce = ChunkEmbedder(
            embedder=FakeEmbedder(),
            known_pairs={(chunk.content_hash, str(chunk.source_path))},
        )
        assert ce.embed_chunks([chunk]) == []

    def test_known_pairs_allows_same_hash_different_source(self):
        """Same content from a different source is NOT skipped."""
        content = "Shared content."
        chunk_a = _make_chunk(content, 0, Path("file-a.md"))
        chunk_b = _make_chunk(content, 0, Path("file-b.md"))
        fake = FakeEmbedder()
        # Only file-a is pre-indexed.
        ce = ChunkEmbedder(
            embedder=fake,
            known_pairs={(chunk_a.content_hash, str(chunk_a.source_path))},
        )
        result = ce.embed_chunks([chunk_b])
        assert len(result) == 1
        assert result[0].chunk is chunk_b


class TestChunkEmbedderForgetSource:
    def test_forget_source_removes_entries_for_that_source(self):
        chunk = _make_chunk("Some text.", 0, Path("notes.md"))
        ce = ChunkEmbedder(
            embedder=FakeEmbedder(),
            known_pairs={(chunk.content_hash, str(chunk.source_path))},
        )
        ce.forget_source("notes.md")
        # After forgetting, the chunk should be re-embedded.
        result = ce.embed_chunks([chunk])
        assert len(result) == 1

    def test_forget_source_leaves_other_sources_intact(self):
        chunk_a = _make_chunk("Text A.", 0, Path("a.md"))
        chunk_b = _make_chunk("Text B.", 0, Path("b.md"))
        fake = FakeEmbedder()
        ce = ChunkEmbedder(
            embedder=fake,
            known_pairs={
                (chunk_a.content_hash, "a.md"),
                (chunk_b.content_hash, "b.md"),
            },
        )
        ce.forget_source("a.md")
        # chunk_a is no longer known → embedded.
        result_a = ce.embed_chunks([chunk_a])
        assert len(result_a) == 1
        # chunk_b is still known → skipped.
        result_b = ce.embed_chunks([chunk_b])
        assert result_b == []

    def test_forget_source_accepts_path_object(self):
        chunk = _make_chunk("Path obj test.", 0, Path("readme.md"))
        ce = ChunkEmbedder(
            embedder=FakeEmbedder(),
            known_pairs={(chunk.content_hash, "readme.md")},
        )
        ce.forget_source(Path("readme.md"))
        assert ce.embed_chunks([chunk]) != []

    def test_forget_source_unknown_source_is_safe(self):
        ce = ChunkEmbedder(embedder=FakeEmbedder())
        ce.forget_source("nonexistent.md")  # should not raise


class TestChunkEmbedderSameContentDifferentSources:
    def test_same_content_two_sources_both_indexed(self):
        """Two files with identical content are indexed independently."""
        content = "Identical content across files."
        chunk_a = _make_chunk(content, 0, Path("file-a.md"))
        chunk_b = _make_chunk(content, 0, Path("file-b.md"))
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake)

        result_a = ce.embed_chunks([chunk_a])
        result_b = ce.embed_chunks([chunk_b])

        assert len(result_a) == 1
        assert len(result_b) == 1
        assert result_a[0].chunk is chunk_a
        assert result_b[0].chunk is chunk_b

    def test_second_source_reuses_vector_without_extra_embed_call(self):
        """After the first source is embedded, the second reuses the vector."""
        content = "Vector cache test content."
        chunk_a = _make_chunk(content, 0, Path("src-a.md"))
        chunk_b = _make_chunk(content, 0, Path("src-b.md"))
        fake = FakeEmbedder()
        ce = ChunkEmbedder(embedder=fake)

        ce.embed_chunks([chunk_a])   # first source — calls Ollama
        ce.embed_chunks([chunk_b])   # second source — reuses cache

        # The embedder should have been called exactly once (for chunk_a).
        assert fake.call_count == 1

    def test_second_source_vector_equals_first_source_vector(self):
        content = "Same vector expected."
        chunk_a = _make_chunk(content, 0, Path("src-a.md"))
        chunk_b = _make_chunk(content, 0, Path("src-b.md"))
        ce = ChunkEmbedder(embedder=FakeEmbedder())

        result_a = ce.embed_chunks([chunk_a])
        result_b = ce.embed_chunks([chunk_b])

        assert result_a[0].vector == result_b[0].vector
