"""Tests for SemanticSearch.

Uses duck-typed fakes for EmbeddingProvider and VectorStore so no live
Ollama or ChromaDB instance is required.  Integration tests that require
Ollama are marked ``@pytest.mark.integration`` and excluded from the
default CI run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from knowledge_onboarding_agent.models import Chunk, EmbeddedChunk, RetrievedChunk
from knowledge_onboarding_agent.retrieval.semantic_search import SemanticSearch


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------

def _make_vector(seed: float, dim: int = 8) -> list[float]:
    """Deterministic vector for testing."""
    return [seed * (i + 1) * 0.1 for i in range(dim)]


class FakeEmbedder:
    """EmbeddingProvider duck-type that records calls and returns deterministic vectors."""

    def __init__(self, vector_seed: float = 1.0) -> None:
        self._seed = vector_seed
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [_make_vector(self._seed + i * 0.1) for i in range(len(texts))]


class FakeStore:
    """VectorStore duck-type backed by an in-memory list of pre-canned results."""

    def __init__(self, results: list[dict] | None = None) -> None:
        self._results = results or []
        self.queries: list[tuple[list[float], int]] = []

    def upsert(self, ids, vectors, metadatas) -> None:  # noqa: ANN001
        pass

    def query(self, vector: list[float], top_k: int) -> list[dict]:
        self.queries.append((vector, top_k))
        return self._results[:top_k]

    def delete(self, ids) -> None:  # noqa: ANN001
        pass

    def count(self) -> int:
        return len(self._results)


def _make_store_result(
    chunk_id: str = "doc:0",
    content: str = "Sample content.",
    source_path: str = "notes.md",
    chunk_index: int = 0,
    content_hash: str = "abc123",
    score: float = 0.95,
    extra_meta: dict | None = None,
) -> dict:
    """Build a result dict in the format returned by VectorStore.query."""
    metadata: dict = {
        "content_hash": content_hash,
        "content": content,
        "source_path": source_path,
        "chunk_index": chunk_index,
    }
    if extra_meta:
        metadata.update(extra_meta)
    return {"id": chunk_id, "score": score, "metadata": metadata}


# ---------------------------------------------------------------------------
# Constructor and from_settings
# ---------------------------------------------------------------------------

class TestSemanticSearchInit:
    def test_requires_top_k_at_least_one(self):
        with pytest.raises(ValueError, match="top_k"):
            SemanticSearch(FakeEmbedder(), FakeStore(), top_k=0)

    def test_negative_top_k_raises(self):
        with pytest.raises(ValueError, match="top_k"):
            SemanticSearch(FakeEmbedder(), FakeStore(), top_k=-5)

    def test_valid_construction(self):
        ss = SemanticSearch(FakeEmbedder(), FakeStore(), top_k=5)
        assert ss._top_k == 5

    def test_from_settings_uses_top_k(self):
        from knowledge_onboarding_agent.config import load_settings
        settings = load_settings()
        ss = SemanticSearch.from_settings(settings, FakeEmbedder(), FakeStore())
        assert ss._top_k == settings.retrieval.top_k

    def test_from_settings_uses_top_k_scale_factor(self):
        from knowledge_onboarding_agent.config import load_settings
        settings = load_settings()
        ss = SemanticSearch.from_settings(settings, FakeEmbedder(), FakeStore())
        assert ss._top_k_scale_factor == settings.retrieval.top_k_scale_factor

    def test_top_k_scale_factor_negative_raises(self):
        with pytest.raises(ValueError, match="top_k_scale_factor"):
            SemanticSearch(FakeEmbedder(), FakeStore(), top_k=10, top_k_scale_factor=-0.1)


# ---------------------------------------------------------------------------
# Dynamic top_k (_effective_top_k)
# ---------------------------------------------------------------------------

class TestEffectiveTopK:
    def test_static_mode_when_factor_is_zero(self):
        ss = SemanticSearch(FakeEmbedder(), FakeStore(), top_k=7, top_k_scale_factor=0.0)
        assert ss._effective_top_k() == 7

    def test_dynamic_scales_with_store_count(self):
        # sqrt(100) * 0.5 = 5.0 → rounds to 5
        results = [_make_store_result(chunk_id=f"doc:{i}") for i in range(100)]
        store = FakeStore(results=results)
        ss = SemanticSearch(FakeEmbedder(), store, top_k=10, top_k_scale_factor=0.5)
        assert ss._effective_top_k() == 5

    def test_dynamic_respects_hard_cap(self):
        # sqrt(900) * 0.5 = 15 → capped at top_k=10
        results = [_make_store_result(chunk_id=f"doc:{i}") for i in range(900)]
        store = FakeStore(results=results)
        ss = SemanticSearch(FakeEmbedder(), store, top_k=10, top_k_scale_factor=0.5)
        assert ss._effective_top_k() == 10

    def test_dynamic_minimum_is_3(self):
        # sqrt(4) * 0.5 = 1.0 → floored to 3
        results = [_make_store_result(chunk_id=f"doc:{i}") for i in range(4)]
        store = FakeStore(results=results)
        ss = SemanticSearch(FakeEmbedder(), store, top_k=10, top_k_scale_factor=0.5)
        assert ss._effective_top_k() == 3

    def test_dynamic_falls_back_to_cap_on_empty_store(self):
        ss = SemanticSearch(FakeEmbedder(), FakeStore(), top_k=10, top_k_scale_factor=0.5)
        assert ss._effective_top_k() == 10

    def test_dynamic_top_k_used_in_search(self):
        # sqrt(100) * 0.5 = 5.0 → store queried with 5
        results = [_make_store_result(chunk_id=f"doc:{i}") for i in range(100)]
        store = FakeStore(results=results)
        ss = SemanticSearch(FakeEmbedder(), store, top_k=10, top_k_scale_factor=0.5)
        ss.search("anything")
        _, queried_k = store.queries[0]
        assert queried_k == 5

    def test_scale_factor_above_one_is_valid(self):
        # factor > 1.0 is allowed — top_k cap is the safety net
        results = [_make_store_result(chunk_id=f"doc:{i}") for i in range(9)]
        store = FakeStore(results=results)
        ss = SemanticSearch(FakeEmbedder(), store, top_k=10, top_k_scale_factor=2.0)
        # sqrt(9) * 2.0 = 6.0 → 6
        assert ss._effective_top_k() == 6


# ---------------------------------------------------------------------------
# Delegation: embed → query
# ---------------------------------------------------------------------------

class TestSemanticSearchDelegation:
    def test_embed_called_with_query(self):
        embedder = FakeEmbedder()
        store = FakeStore()
        ss = SemanticSearch(embedder, store)
        ss.search("What is onboarding?")
        assert embedder.calls == [["What is onboarding?"]]

    def test_store_queried_with_embedded_vector(self):
        embedder = FakeEmbedder(vector_seed=1.0)
        store = FakeStore()
        ss = SemanticSearch(embedder, store, top_k=7)
        ss.search("test query")
        assert len(store.queries) == 1
        queried_vector, queried_k = store.queries[0]
        assert queried_vector == embedder.embed(["test query"])[0]
        assert queried_k == 7

    def test_top_k_passed_to_store(self):
        store = FakeStore()
        ss = SemanticSearch(FakeEmbedder(), store, top_k=3)
        ss.search("query")
        assert store.queries[0][1] == 3


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------

class TestSemanticSearchEdgeCases:
    def test_empty_query_returns_empty(self):
        ss = SemanticSearch(FakeEmbedder(), FakeStore([_make_store_result()]))
        assert ss.search("") == []

    def test_whitespace_only_query_returns_empty(self):
        ss = SemanticSearch(FakeEmbedder(), FakeStore([_make_store_result()]))
        assert ss.search("   ") == []

    def test_empty_query_does_not_call_embedder(self):
        embedder = FakeEmbedder()
        ss = SemanticSearch(embedder, FakeStore())
        ss.search("")
        assert embedder.calls == []

    def test_empty_store_returns_empty_list(self):
        ss = SemanticSearch(FakeEmbedder(), FakeStore(results=[]))
        results = ss.search("hello")
        assert results == []

    def test_returns_list_type(self):
        ss = SemanticSearch(FakeEmbedder(), FakeStore())
        result = ss.search("query")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Return type and field reconstruction
# ---------------------------------------------------------------------------

class TestSemanticSearchResults:
    def test_returns_retrieved_chunk_instances(self):
        store = FakeStore([_make_store_result()])
        ss = SemanticSearch(FakeEmbedder(), store)
        results = ss.search("query")
        assert all(isinstance(r, RetrievedChunk) for r in results)

    def test_result_count_matches_store_output(self):
        store = FakeStore([_make_store_result(f"doc:{i}") for i in range(3)])
        ss = SemanticSearch(FakeEmbedder(), store, top_k=10)
        assert len(ss.search("q")) == 3

    def test_chunk_id_preserved(self):
        store = FakeStore([_make_store_result(chunk_id="article:5")])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert result.chunk.id == "article:5"

    def test_chunk_content_preserved(self):
        store = FakeStore([_make_store_result(content="The quick brown fox.")])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert result.chunk.content == "The quick brown fox."

    def test_chunk_source_path_is_path_object(self):
        store = FakeStore([_make_store_result(source_path="docs/guide.md")])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert isinstance(result.chunk.source_path, Path)
        assert result.chunk.source_path == Path("docs/guide.md")

    def test_chunk_index_preserved(self):
        store = FakeStore([_make_store_result(chunk_index=3)])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert result.chunk.chunk_index == 3

    def test_chunk_content_hash_preserved(self):
        store = FakeStore([_make_store_result(content_hash="deadbeef")])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert result.chunk.content_hash == "deadbeef"

    def test_score_preserved(self):
        store = FakeStore([_make_store_result(score=0.87)])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert result.score == pytest.approx(0.87)

    def test_score_is_float(self):
        store = FakeStore([_make_store_result(score=1)])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert isinstance(result.score, float)

    def test_extra_metadata_preserved_in_chunk_metadata(self):
        store = FakeStore([
            _make_store_result(extra_meta={"heading": "Intro", "word_count": 42})
        ])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        assert result.chunk.metadata["heading"] == "Intro"
        assert result.chunk.metadata["word_count"] == 42

    def test_reserved_keys_not_in_chunk_metadata(self):
        """content_hash, content, source_path, chunk_index should not appear
        in Chunk.metadata — they are stored as dedicated Chunk fields."""
        store = FakeStore([_make_store_result()])
        ss = SemanticSearch(FakeEmbedder(), store)
        result = ss.search("q")[0]
        for key in ("content_hash", "content", "source_path", "chunk_index"):
            assert key not in result.chunk.metadata

    def test_results_ordered_by_store_output(self):
        """SemanticSearch preserves the ordering returned by the VectorStore."""
        results_data = [
            _make_store_result(chunk_id=f"doc:{i}", score=1.0 - i * 0.1)
            for i in range(5)
        ]
        store = FakeStore(results_data)
        ss = SemanticSearch(FakeEmbedder(), store, top_k=5)
        results = ss.search("q")
        ids = [r.chunk.id for r in results]
        assert ids == ["doc:0", "doc:1", "doc:2", "doc:3", "doc:4"]

    def test_top_k_limits_results(self):
        results_data = [_make_store_result(chunk_id=f"doc:{i}") for i in range(10)]
        store = FakeStore(results_data)
        ss = SemanticSearch(FakeEmbedder(), store, top_k=3)
        results = ss.search("q")
        assert len(results) <= 3


# ---------------------------------------------------------------------------
# Integration test (requires Ollama + ChromaDB)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestSemanticSearchIntegration:
    def test_search_returns_relevant_chunks(self):
        """End-to-end: embed a real query, upsert chunks, retrieve top result."""
        import chromadb

        from knowledge_onboarding_agent.config import load_settings
        from knowledge_onboarding_agent.embeddings.ollama_embedder import OllamaEmbedder
        from knowledge_onboarding_agent.storage.chroma_store import ChromaDBStore
        from knowledge_onboarding_agent.models import Chunk, EmbeddedChunk
        import hashlib, uuid

        settings = load_settings()
        embedder = OllamaEmbedder.from_settings(settings)
        store = ChromaDBStore(
            path=settings.storage.path,
            collection_name=f"test_integration_{uuid.uuid4().hex}",
            _client=chromadb.EphemeralClient(),
        )

        def _make_chunk(text: str, idx: int) -> Chunk:
            return Chunk(
                id=f"test:{idx}",
                source_path=Path("test.md"),
                content=text,
                chunk_index=idx,
                metadata={"heading": "Test"},
                content_hash=hashlib.sha256(text.encode()).hexdigest(),
            )

        chunks = [
            _make_chunk("Onboarding helps new employees get started.", 0),
            _make_chunk("The cafeteria serves lunch from 12 to 2 pm.", 1),
            _make_chunk("New hires should complete orientation on day one.", 2),
        ]
        vectors = embedder.embed([c.content for c in chunks])
        embedded = [EmbeddedChunk(chunk=c, vector=v) for c, v in zip(chunks, vectors)]
        store.upsert_embedded_chunks(embedded)

        ss = SemanticSearch.from_settings(settings, embedder, store)
        results = ss.search("onboarding new employees")

        assert len(results) > 0
        # The two onboarding-related chunks should rank above the cafeteria chunk.
        top_ids = {r.chunk.id for r in results[:2]}
        assert "test:0" in top_ids or "test:2" in top_ids
