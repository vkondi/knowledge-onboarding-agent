"""Tests for knowledge_onboarding_agent.storage.faiss_store.

All tests are skipped if faiss-cpu is not installed.
Install with: pip install faiss-cpu
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

# Skip the entire module if faiss is not available.
faiss = pytest.importorskip("faiss", reason="faiss-cpu not installed; skipping FAISSStore tests")

from knowledge_onboarding_agent.storage.faiss_store import FAISSStore  # noqa: E402

_DIM = 8


def _make_vector(seed: int) -> list[float]:
    angle = seed * 0.3
    v = [math.cos(angle), math.sin(angle)] + [0.0] * (_DIM - 2)
    norm = math.sqrt(sum(x * x for x in v))
    return [x / norm for x in v]


@pytest.fixture
def store(tmp_path) -> FAISSStore:
    return FAISSStore(path=str(tmp_path / "faiss_db"), dimension=_DIM)


class TestFAISSStoreBasics:
    def test_count_starts_at_zero(self, store):
        assert store.count() == 0

    def test_upsert_increases_count(self, store):
        store.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{"label": "a"}])
        assert store.count() == 1

    def test_upsert_multiple(self, store):
        store.upsert(
            ids=["a", "b", "c"],
            vectors=[_make_vector(i) for i in range(3)],
            metadatas=[{"n": i} for i in range(3)],
        )
        assert store.count() == 3

    def test_upsert_empty_is_no_op(self, store):
        store.upsert(ids=[], vectors=[], metadatas=[])
        assert store.count() == 0

    def test_upsert_same_id_does_not_duplicate(self, store):
        store.upsert(ids=["x"], vectors=[_make_vector(0)], metadatas=[{"v": 1}])
        store.upsert(ids=["x"], vectors=[_make_vector(1)], metadatas=[{"v": 2}])
        assert store.count() == 1


class TestFAISSStoreQuery:
    def test_query_empty_returns_empty(self, store):
        assert store.query(_make_vector(0), top_k=5) == []

    def test_query_result_has_required_keys(self, store):
        store.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{"x": 1}])
        results = store.query(_make_vector(0), top_k=1)
        assert len(results) == 1
        assert "id" in results[0]
        assert "score" in results[0]
        assert "metadata" in results[0]

    def test_query_identical_vector_scores_highest(self, store):
        v0, v1 = _make_vector(0), _make_vector(5)
        store.upsert(ids=["near", "far"], vectors=[v0, v1], metadatas=[{}, {}])
        results = store.query(v0, top_k=2)
        assert results[0]["id"] == "near"

    def test_query_top_k_capped_at_store_size(self, store):
        store.upsert(ids=["only"], vectors=[_make_vector(0)], metadatas=[{}])
        results = store.query(_make_vector(0), top_k=100)
        assert len(results) == 1

    def test_query_metadata_preserved(self, store):
        store.upsert(ids=["m"], vectors=[_make_vector(0)], metadatas=[{"key": "value"}])
        results = store.query(_make_vector(0), top_k=1)
        assert results[0]["metadata"]["key"] == "value"


class TestFAISSStoreDelete:
    def test_delete_reduces_count(self, store):
        store.upsert(ids=["a", "b"], vectors=[_make_vector(0), _make_vector(1)], metadatas=[{}, {}])
        store.delete(["a"])
        assert store.count() == 1

    def test_delete_removes_correct_id(self, store):
        store.upsert(ids=["keep", "drop"], vectors=[_make_vector(0), _make_vector(1)], metadatas=[{}, {}])
        store.delete(["drop"])
        results = store.query(_make_vector(0), top_k=10)
        ids = [r["id"] for r in results]
        assert "keep" in ids
        assert "drop" not in ids

    def test_delete_empty_list_is_no_op(self, store):
        store.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{}])
        store.delete([])
        assert store.count() == 1

    def test_delete_missing_id_is_safe(self, store):
        store.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{}])
        store.delete(["nonexistent"])
        assert store.count() == 1


class TestFAISSStorePersistence:
    def test_reloaded_store_retains_records(self, tmp_path):
        path = str(tmp_path / "persist_db")
        store1 = FAISSStore(path=path, dimension=_DIM)
        store1.upsert(ids=["a"], vectors=[_make_vector(0)], metadatas=[{"val": 42}])
        # Re-open from the same path.
        store2 = FAISSStore(path=path, dimension=_DIM)
        assert store2.count() == 1
        results = store2.query(_make_vector(0), top_k=1)
        assert results[0]["id"] == "a"
        assert results[0]["metadata"]["val"] == 42

    def test_reloaded_store_next_id_continues(self, tmp_path):
        path = str(tmp_path / "persist_db2")
        store1 = FAISSStore(path=path, dimension=_DIM)
        store1.upsert(ids=["a", "b"], vectors=[_make_vector(0), _make_vector(1)], metadatas=[{}, {}])
        store2 = FAISSStore(path=path, dimension=_DIM)
        store2.upsert(ids=["c"], vectors=[_make_vector(2)], metadatas=[{}])
        assert store2.count() == 3


class TestFAISSStoreImportError:
    def test_raises_import_error_message(self, monkeypatch):
        """If faiss is not importable, FAISSStore raises ImportError with install hint."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "faiss":
                raise ImportError("No module named 'faiss'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="faiss-cpu"):
            FAISSStore(path="/tmp/test", dimension=_DIM)
