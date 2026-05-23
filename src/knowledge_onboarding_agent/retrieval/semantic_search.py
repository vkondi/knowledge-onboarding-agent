"""SemanticSearch: embed a query and retrieve the most relevant chunks.

Conforms to the ``Retriever`` Protocol defined in ``interfaces.py``.

Data flow:
    query str
      → EmbeddingProvider.embed([query])[0]   (single vector)
      → VectorStore.query(vector, top_k)       (list[dict])
      → reconstruct Chunk from stored metadata
      → list[RetrievedChunk]  (ordered by descending score)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from knowledge_onboarding_agent.models import Chunk, RetrievedChunk

if TYPE_CHECKING:
    from knowledge_onboarding_agent.config import Settings
    from knowledge_onboarding_agent.interfaces import EmbeddingProvider, VectorStore

# Keys injected by ChromaDBStore.upsert_embedded_chunks that are NOT part of
# the original Chunk.metadata dict.
_RESERVED_METADATA_KEYS = frozenset(
    {"content_hash", "content", "source_path", "chunk_index"}
)


class SemanticSearch:
    """Embeds a query and retrieves the top-k most similar stored chunks.

    Parameters
    ----------
    embedder:
        Any ``EmbeddingProvider`` implementation.  Used to embed the query.
    store:
        Any ``VectorStore`` implementation.  Used to perform the similarity search.
    top_k:
        Maximum number of results to return.  Sourced from
        ``settings.retrieval.top_k``; defaults to 10.
    """

    def __init__(
        self,
        embedder: EmbeddingProvider,
        store: VectorStore,
        top_k: int = 10,
        top_k_scale_factor: float = 0.0,
    ) -> None:
        if top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        if top_k_scale_factor < 0.0:
            raise ValueError(f"top_k_scale_factor must be >= 0.0, got {top_k_scale_factor}")
        self._embedder = embedder
        self._store = store
        self._top_k = top_k
        self._top_k_scale_factor = top_k_scale_factor

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        embedder: EmbeddingProvider,
        store: VectorStore,
    ) -> SemanticSearch:
        """Construct a ``SemanticSearch`` from a ``Settings`` object."""
        return cls(
            embedder=embedder,
            store=store,
            top_k=settings.retrieval.top_k,
            top_k_scale_factor=settings.retrieval.top_k_scale_factor,
        )

    # ------------------------------------------------------------------
    # Retriever Protocol
    # ------------------------------------------------------------------

    def search(self, query: str) -> list[RetrievedChunk]:
        """Return the top-k chunks most relevant to *query*.

        Returns an empty list when the store is empty or *query* is blank.
        Results are ordered by descending similarity score.
        """
        if not query.strip():
            return []

        # Embed the query — embed() returns a list; take the first (and only) vector.
        query_vector: list[float] = self._embedder.embed([query])[0]

        raw_results: list[dict] = self._store.query(query_vector, self._effective_top_k())

        return [self._to_retrieved_chunk(hit) for hit in raw_results]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _effective_top_k(self) -> int:
        """Return the number of chunks to retrieve for the current query.

        When ``top_k_scale_factor > 0``, the value grows sub-linearly with
        knowledge base size using a square-root formula::

            effective_k = max(3, min(top_k, round(sqrt(total_chunks) * scale_factor))

        This keeps retrieval focused (3–6 results for small–medium bases)
        while allowing modest growth for very large bases, capped at ``top_k``.
        Falls back to the static ``top_k`` when scale_factor is 0 or the
        store is empty.
        """
        import math

        if self._top_k_scale_factor <= 0.0:
            return self._top_k
        total = self._store.count()
        if total == 0:
            return self._top_k
        dynamic = max(3, round(math.sqrt(total) * self._top_k_scale_factor))
        return min(dynamic, self._top_k)

    @staticmethod
    def _to_retrieved_chunk(hit: dict) -> RetrievedChunk:
        """Convert a raw VectorStore query result dict to a ``RetrievedChunk``."""
        meta: dict = hit["metadata"]

        # Strip the 4 fields injected by upsert_embedded_chunks; the rest
        # belongs to the original Chunk.metadata (e.g. heading, word_count).
        chunk_metadata = {
            k: v for k, v in meta.items() if k not in _RESERVED_METADATA_KEYS
        }

        chunk = Chunk(
            id=hit["id"],
            source_path=Path(meta["source_path"]),
            content=meta["content"],
            chunk_index=int(meta["chunk_index"]),
            metadata=chunk_metadata,
            content_hash=meta["content_hash"],
        )
        return RetrievedChunk(chunk=chunk, score=float(hit["score"]))
