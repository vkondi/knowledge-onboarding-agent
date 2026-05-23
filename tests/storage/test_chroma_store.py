"""Tests for knowledge_onboarding_agent.storage.chroma_store.

Uses chromadb.EphemeralClient so tests are fast and leave no disk artifacts.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

import chromadb
import pytest

from knowledge_onboarding_agent.config import load_settings
from knowledge_onboarding_agent.models import Chunk, EmbeddedChunk
from knowledge_onboarding_agent.storage.chroma_store import ChromaDBStore

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

_DIM = 8  # small vectors for unit tests

# Single shared EphemeralClient for the test session — isolated by unique
# collection name per test so there is no cross-test state contamination.
_EPHEMERAL_CLIENT = chromadb.EphemeralClient()


def _ephemeral_store() -> ChromaDBStore:
    """Return a ChromaDBStore backed by the shared EphemeralClient.

    Each call creates a new, uniquely-named collection so tests are fully
    isolated even though the underlying client instance is shared.
    """
    return ChromaDBStore(
        path="/unused",
        collection_name=f"test_{uuid.uuid4().hex}",
        _client=_EPHEMERAL_CLIENT,
    )


def _make_vector(seed: int) -> list[float]:
    """Deterministic unit vector seeded by an integer."""
    import math
    angle = seed * 0.3
    # Build a simple unit vector (first two dims carry the direction).
    v = [math.cos(angle), math.sin(angle)] + [0.0] * (_DIM - 2)
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


def _make_embedded_chunk(
    content: str,
    index: int = 0,
    path: Path | None = None,
    vector_seed: int = 0,
) -> EmbeddedChunk:
    p = path or Path("doc.md")
    chunk = Chunk(
        id=f"{p.stem}:{index}",
        source_path=p,
        content=content,
        chunk_index=index,
        metadata={
            "heading": "Intro",
            "word_count": len(content.split()),
            "source_file": str(p),
        },
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    return EmbeddedChunk(chunk=chunk, vector=_make_vector(vector_seed))


# ---------------------------------------------------------------------------
# VectorStore Protocol surface
# ---------------------------------------------------------------------------

class TestChromaDBStoreUpsertAndCount:
    def test_count_starts_at_zero(self):
        store = _ephemeral_store()
        assert store.count() == 0

    def test_upsert_increases_count(self):
        store = _ephemeral_store()
        ec = _make_embedded_chunk("Hello world.", index=0, vector_seed=1)
        store.upsert_embedded_chunks([ec])
        assert store.count() == 1

    def test_upsert_multiple_increases_count(self):
        store = _ephemeral_store()
        ecs = [_make_embedded_chunk(f"Chunk {i}.", index=i, vector_seed=i) for i in range(5)]
        store.upsert_embedded_chunks(ecs)
        assert store.count() == 5

    def test_upsert_same_id_does_not_duplicate(self):
        store = _ephemeral_store()
        ec = _make_embedded_chunk("Original content.", index=0, vector_seed=0)
        updated = EmbeddedChunk(
            chunk=Chunk(
                id=ec.chunk.id,
                source_path=ec.chunk.source_path,
                content="Updated content.",
                chunk_index=0,
                metadata=ec.chunk.metadata,
                content_hash=hashlib.sha256(b"Updated content.").hexdigest(),
            ),
            vector=_make_vector(1),
        )
        store.upsert_embedded_chunks([ec])
        store.upsert_embedded_chunks([updated])
        assert store.count() == 1

    def test_upsert_empty_list_is_no_op(self):
        store = _ephemeral_store()
        store.upsert_embedded_chunks([])
        assert store.count() == 0

    def test_raw_upsert_protocol_method(self):
        store = _ephemeral_store()
        store.upsert(ids=["id1"], vectors=[_make_vector(0)], metadatas=[{"key": "val"}])
        assert store.count() == 1


class TestChromaDBStoreQuery:
    def test_query_empty_store_returns_empty(self):
        store = _ephemeral_store()
        result = store.query(_make_vector(0), top_k=5)
        assert result == []

    def test_query_returns_correct_count(self):
        store = _ephemeral_store()
        for i in range(4):
            store.upsert_embedded_chunks([_make_embedded_chunk(f"Doc {i}", index=i, vector_seed=i)])
        results = store.query(_make_vector(0), top_k=3)
        assert len(results) == 3

    def test_query_result_has_required_keys(self):
        store = _ephemeral_store()
        store.upsert_embedded_chunks([_make_embedded_chunk("Test doc.", vector_seed=0)])
        result = store.query(_make_vector(0), top_k=1)
        assert len(result) == 1
        assert "id" in result[0]
        assert "score" in result[0]
        assert "metadata" in result[0]

    def test_query_score_is_float(self):
        store = _ephemeral_store()
        store.upsert_embedded_chunks([_make_embedded_chunk("Content.", vector_seed=0)])
        result = store.query(_make_vector(0), top_k=1)
        assert isinstance(result[0]["score"], float)

    def test_query_identical_vector_has_highest_score(self):
        store = _ephemeral_store()
        v0 = _make_vector(0)
        v1 = _make_vector(5)
        store.upsert(ids=["a"], vectors=[v0], metadatas=[{"label": "a"}])
        store.upsert(ids=["b"], vectors=[v1], metadatas=[{"label": "b"}])
        results = store.query(v0, top_k=2)
        assert results[0]["id"] == "a"

    def test_query_top_k_capped_at_collection_size(self):
        store = _ephemeral_store()
        store.upsert_embedded_chunks([_make_embedded_chunk("Only one.", vector_seed=0)])
        results = store.query(_make_vector(0), top_k=100)
        assert len(results) == 1

    def test_query_metadata_preserved(self):
        store = _ephemeral_store()
        store.upsert(
            ids=["x"],
            vectors=[_make_vector(0)],
            metadatas=[{"source_file": "notes.md", "custom": "value"}],
        )
        results = store.query(_make_vector(0), top_k=1)
        assert results[0]["metadata"]["source_file"] == "notes.md"


class TestChromaDBStoreDelete:
    def test_delete_reduces_count(self):
        store = _ephemeral_store()
        store.upsert(ids=["a", "b"], vectors=[_make_vector(0), _make_vector(1)], metadatas=[{"k": "a"}, {"k": "b"}])
        store.delete(["a"])
        assert store.count() == 1

    def test_delete_removes_correct_record(self):
        store = _ephemeral_store()
        store.upsert(ids=["keep", "remove"], vectors=[_make_vector(0), _make_vector(1)], metadatas=[{"k": "keep"}, {"k": "remove"}])
        store.delete(["remove"])
        results = store.query(_make_vector(0), top_k=10)
        ids = [r["id"] for r in results]
        assert "keep" in ids
        assert "remove" not in ids

    def test_delete_empty_list_is_no_op(self):
        store = _ephemeral_store()
        store.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{"k": "a"}])
        store.delete([])
        assert store.count() == 1


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

class TestUpsertEmbeddedChunks:
    def test_metadata_enriched_with_content_hash(self):
        store = _ephemeral_store()
        ec = _make_embedded_chunk("Rich metadata test.", vector_seed=0)
        store.upsert_embedded_chunks([ec])
        results = store.query(_make_vector(0), top_k=1)
        assert results[0]["metadata"]["content_hash"] == ec.chunk.content_hash

    def test_metadata_enriched_with_content(self):
        store = _ephemeral_store()
        ec = _make_embedded_chunk("Stored content.", vector_seed=0)
        store.upsert_embedded_chunks([ec])
        results = store.query(_make_vector(0), top_k=1)
        assert results[0]["metadata"]["content"] == "Stored content."

    def test_metadata_enriched_with_source_path(self):
        store = _ephemeral_store()
        ec = _make_embedded_chunk("Path test.", path=Path("notes/topic.md"), vector_seed=0)
        store.upsert_embedded_chunks([ec])
        results = store.query(_make_vector(0), top_k=1)
        assert "topic.md" in results[0]["metadata"]["source_path"]


class TestGetStoredHashes:
    def test_empty_store_returns_empty_set(self):
        store = _ephemeral_store()
        assert store.get_stored_hashes() == set()

    def test_returns_hash_of_upserted_chunk(self):
        store = _ephemeral_store()
        ec = _make_embedded_chunk("Hash tracking test.", vector_seed=0)
        store.upsert_embedded_chunks([ec])
        hashes = store.get_stored_hashes()
        assert ec.chunk.content_hash in hashes

    def test_returns_all_hashes(self):
        store = _ephemeral_store()
        ecs = [_make_embedded_chunk(f"Doc {i}", index=i, vector_seed=i) for i in range(3)]
        store.upsert_embedded_chunks(ecs)
        hashes = store.get_stored_hashes()
        for ec in ecs:
            assert ec.chunk.content_hash in hashes

    def test_get_stored_hashes_seeds_chunk_embedder(self):
        """Demonstrates the incremental indexing workflow."""
        from knowledge_onboarding_agent.embeddings.chunk_embedder import ChunkEmbedder
        from tests.embeddings.test_chunk_embedder import FakeEmbedder

        store = _ephemeral_store()
        ec = _make_embedded_chunk("Seeded content.", vector_seed=0)
        store.upsert_embedded_chunks([ec])

        known = store.get_stored_hashes()
        ce = ChunkEmbedder(embedder=FakeEmbedder(), known_hashes=known)
        # Same chunk should be skipped.
        result = ce.embed_chunks([ec.chunk])
        assert result == []


class TestDeleteBySource:
    def test_deletes_all_chunks_for_source(self):
        store = _ephemeral_store()
        path = "notes/important.md"
        for i in range(3):
            store.upsert(
                ids=[f"important:{i}"],
                vectors=[_make_vector(i)],
                metadatas=[{"source_path": path}],
            )
        store.upsert(
            ids=["other:0"],
            vectors=[_make_vector(10)],
            metadatas=[{"source_path": "other.md"}],
        )
        store.delete_by_source(path)
        assert store.count() == 1

    def test_delete_nonexistent_source_is_safe(self):
        store = _ephemeral_store()
        store.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{"source_path": "x.md"}])
        store.delete_by_source("does_not_exist.md")
        assert store.count() == 1


class TestChromaDBStoreGetHashesForSource:
    def test_returns_hashes_for_matching_source(self):
        store = _ephemeral_store()
        store.upsert(
            ids=["a", "b"],
            vectors=[_make_vector(0), _make_vector(1)],
            metadatas=[
                {"source_path": "notes.md", "content_hash": "hash1"},
                {"source_path": "notes.md", "content_hash": "hash2"},
            ],
        )
        store.upsert(
            ids=["c"],
            vectors=[_make_vector(2)],
            metadatas=[{"source_path": "other.md", "content_hash": "hash3"}],
        )
        result = store.get_hashes_for_source("notes.md")
        assert result == {"hash1", "hash2"}

    def test_returns_empty_set_for_unknown_source(self):
        store = _ephemeral_store()
        store.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{"source_path": "x.md", "content_hash": "h1"}])
        assert store.get_hashes_for_source("missing.md") == set()

    def test_returns_empty_set_on_empty_store(self):
        store = _ephemeral_store()
        assert store.get_hashes_for_source("any.md") == set()

    def test_accepts_path_object(self):
        from pathlib import Path
        store = _ephemeral_store()
        store.upsert(
            ids=["a"],
            vectors=[_make_vector(0)],
            metadatas=[{"source_path": "notes.md", "content_hash": "hash1"}],
        )
        result = store.get_hashes_for_source(Path("notes.md"))
        assert "hash1" in result
    def test_from_settings_constructs_instance(self, tmp_path):
        settings = load_settings(CONFIG_PATH)
        # Override path to avoid writing to project directory during tests.
        settings.storage.path = str(tmp_path / "db")
        store = ChromaDBStore.from_settings(settings)
        assert isinstance(store, ChromaDBStore)


class TestChromaDBStoreGetHashSourcePairs:
    def test_empty_store_returns_empty_set(self):
        store = _ephemeral_store()
        assert store.get_stored_hash_source_pairs() == set()

    def test_returns_pairs_for_upserted_chunks(self):
        store = _ephemeral_store()
        store.upsert(
            ids=["a", "b"],
            vectors=[_make_vector(0), _make_vector(1)],
            metadatas=[
                {"content_hash": "hash1", "source_path": "doc.md"},
                {"content_hash": "hash2", "source_path": "doc.md"},
            ],
        )
        pairs = store.get_stored_hash_source_pairs()
        assert ("hash1", "doc.md") in pairs
        assert ("hash2", "doc.md") in pairs

    def test_same_hash_different_sources_returns_both_pairs(self):
        """Same content indexed from two sources yields two distinct pairs."""
        store = _ephemeral_store()
        store.upsert(
            ids=["a", "b"],
            vectors=[_make_vector(0), _make_vector(0)],
            metadatas=[
                {"content_hash": "shared-hash", "source_path": "file-a.md"},
                {"content_hash": "shared-hash", "source_path": "file-b.md"},
            ],
        )
        pairs = store.get_stored_hash_source_pairs()
        assert ("shared-hash", "file-a.md") in pairs
        assert ("shared-hash", "file-b.md") in pairs

    def test_records_without_hash_or_source_are_skipped(self):
        store = _ephemeral_store()
        store.upsert(
            ids=["a"],
            vectors=[_make_vector(0)],
            metadatas=[{"unrelated_key": "value"}],
        )
        assert store.get_stored_hash_source_pairs() == set()
