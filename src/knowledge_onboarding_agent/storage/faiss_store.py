"""FAISSStore: experimental vector store backed by FAISS IndexIDMap(IndexFlatIP).

This backend is secondary to ChromaDBStore (see ADR-001 and system-design.md).
Use it when maximum ANN throughput matters more than ease of metadata management.

Requirements
------------
``faiss-cpu`` is **not** installed by default.  Install it manually::

    pip install faiss-cpu

Conforms to the ``VectorStore`` Protocol defined in ``interfaces.py``.

Persistence
-----------
Two files are written to *path*:

- ``faiss.index``    — FAISS binary index (IndexIDMap wrapping IndexFlatIP)
- ``metadata.json``  — JSON mapping FAISS int64 id → ``{"id": str, "metadata": dict}``

Cosine Similarity
-----------------
Vectors are L2-normalized before indexing so that inner-product search is
equivalent to cosine similarity.  Query vectors are normalized on the fly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from knowledge_onboarding_agent.config import Settings


def _require_faiss():
    """Import and return (faiss, numpy), raising ImportError if unavailable."""
    try:
        import faiss  # type: ignore[import]
        import numpy as np  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "FAISSStore requires 'faiss-cpu'.  "
            "Install it with:  pip install faiss-cpu"
        ) from exc
    return faiss, np


class FAISSStore:
    """Implements VectorStore using a FAISS IndexIDMap(IndexFlatIP) index.

    Records are identified by string ids.  Internally each string id is
    mapped to a unique int64 for FAISS, managed by a monotonically increasing
    counter persisted alongside the index.

    Raises:
        ImportError: on construction if ``faiss-cpu`` is not installed.
    """

    def __init__(self, path: str, dimension: int = 768) -> None:
        self._faiss, self._np = _require_faiss()
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._dim = dimension

        index_path = self._path / "faiss.index"
        meta_path = self._path / "metadata.json"

        if index_path.exists() and meta_path.exists():
            self._index = self._faiss.read_index(str(index_path))
            with meta_path.open(encoding="utf-8") as f:
                stored: dict = json.load(f)
            # records: {str(int_id): {"id": str_id, "metadata": dict}}
            self._records: dict[int, dict] = {
                int(k): v for k, v in stored["records"].items()
            }
            self._id_to_int: dict[str, int] = {
                v["id"]: int(k) for k, v in stored["records"].items()
            }
            self._next_id: int = stored["next_id"]
        else:
            inner = self._faiss.IndexFlatIP(dimension)
            self._index = self._faiss.IndexIDMap(inner)
            self._records = {}
            self._id_to_int = {}
            self._next_id = 0

    @classmethod
    def from_settings(cls, settings: Settings, dimension: int = 768) -> FAISSStore:
        """Construct a ``FAISSStore`` from a ``Settings`` object."""
        return cls(path=settings.storage.path, dimension=dimension)

    # ------------------------------------------------------------------
    # VectorStore Protocol
    # ------------------------------------------------------------------

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Insert or update records.  Existing ids are removed then re-added."""
        if not ids:
            return

        # Remove any existing entries so upsert behaves correctly.
        existing_int_ids = [
            self._id_to_int[sid] for sid in ids if sid in self._id_to_int
        ]
        if existing_int_ids:
            self._remove_by_int_ids(existing_int_ids)

        # Assign new int64 ids and register the records.
        int_ids: list[int] = []
        for sid, meta in zip(ids, metadatas):
            iid = self._next_id
            self._next_id += 1
            self._records[iid] = {"id": sid, "metadata": meta}
            self._id_to_int[sid] = iid
            int_ids.append(iid)

        normalized = self._normalize(vectors)
        int_ids_arr = self._np.array(int_ids, dtype="int64")
        self._index.add_with_ids(normalized, int_ids_arr)
        self._save()

    def query(self, vector: list[float], top_k: int) -> list[dict]:
        """Return the *top_k* most similar records (cosine similarity).

        Each result dict contains ``"id"``, ``"score"``, and ``"metadata"``.
        Returns ``[]`` when the index is empty.
        """
        if self._index.ntotal == 0:
            return []
        actual_k = min(top_k, self._index.ntotal)
        query_vec = self._normalize([vector])
        scores, int_ids = self._index.search(query_vec, actual_k)

        hits: list[dict] = []
        for score, iid in zip(scores[0], int_ids[0]):
            if iid == -1:  # FAISS sentinel for empty slots
                continue
            record = self._records.get(int(iid))
            if record is None:
                continue
            hits.append(
                {
                    "id": record["id"],
                    "score": float(score),
                    "metadata": record["metadata"],
                }
            )
        return hits

    def delete(self, ids: list[str]) -> None:
        """Remove records by string id.  Silently ignores missing ids."""
        if not ids:
            return
        int_ids = [self._id_to_int[sid] for sid in ids if sid in self._id_to_int]
        if not int_ids:
            return
        self._remove_by_int_ids(int_ids)
        self._save()

    def count(self) -> int:
        """Return the total number of stored records."""
        return self._index.ntotal

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize(self, vectors: list[list[float]]):
        """L2-normalize *vectors*; zero vectors are left unchanged."""
        arr = self._np.array(vectors, dtype="float32")
        norms = self._np.linalg.norm(arr, axis=1, keepdims=True)
        # Avoid division by zero for zero vectors.
        norms = self._np.where(norms == 0, 1.0, norms)
        return arr / norms

    def _remove_by_int_ids(self, int_ids: list[int]) -> None:
        """Remove *int_ids* from the FAISS index and internal mappings."""
        ids_arr = self._np.array(int_ids, dtype="int64")
        selector = self._faiss.IDSelectorBatch(ids_arr)
        self._index.remove_ids(selector)
        for iid in int_ids:
            sid = self._records[iid]["id"]
            del self._records[iid]
            del self._id_to_int[sid]

    def _save(self) -> None:
        """Persist the FAISS index and metadata mapping to disk."""
        self._faiss.write_index(self._index, str(self._path / "faiss.index"))
        stored = {
            "next_id": self._next_id,
            "records": {str(k): v for k, v in self._records.items()},
        }
        with (self._path / "metadata.json").open("w", encoding="utf-8") as f:
            json.dump(stored, f)
