"""ChromaDBStore: persistent vector storage backed by a local ChromaDB database.

Conforms to the ``VectorStore`` Protocol defined in ``interfaces.py``.
Configuration is sourced from ``Settings``; no paths or names are hardcoded.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import chromadb

from knowledge_onboarding_agent.models import EmbeddedChunk

if TYPE_CHECKING:
    from knowledge_onboarding_agent.config import Settings


class ChromaDBStore:
    """Wraps a ChromaDB collection with the VectorStore Protocol interface.

    The collection is created with cosine similarity (``hnsw:space = cosine``).
    Upserting a record that already exists updates the vector and metadata
    in place, making the store safe to call on repeated ingestion runs.

    Convenience helpers beyond the Protocol:
    - ``upsert_embedded_chunks`` — upsert directly from ``EmbeddedChunk`` objects.
    - ``get_stored_hashes``      — return all ``content_hash`` values stored,
                                   used to seed ``ChunkEmbedder.known_hashes``
                                   on startup for incremental indexing.
    - ``delete_by_source``       — delete all chunks for a given source file,
                                   called when a deletion ``FileEvent`` is processed.
    """

    def __init__(
        self,
        path: str,
        collection_name: str,
        *,
        _client: chromadb.ClientAPI | None = None,
    ) -> None:
        # Accept an injected client for testing (EphemeralClient); otherwise
        # create a real PersistentClient.
        self._client = _client or chromadb.PersistentClient(path=path)
        self._collection_name = collection_name
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> ChromaDBStore:
        """Construct a ``ChromaDBStore`` from a ``Settings`` object."""
        return cls(
            path=settings.storage.path,
            collection_name=settings.storage.collection_name,
        )

    # ------------------------------------------------------------------
    # VectorStore Protocol
    # ------------------------------------------------------------------

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Insert or update records.  Existing ids are updated in place."""
        if not ids:
            return
        self._collection.upsert(ids=ids, embeddings=vectors, metadatas=metadatas)

    def query(self, vector: list[float], top_k: int) -> list[dict]:
        """Return the *top_k* most similar records to *vector*.

        Each result dict contains:
        - ``"id"``       — the record's string id
        - ``"score"``    — cosine similarity in [-1, 1] (higher = more similar)
        - ``"metadata"`` — stored metadata dict

        Returns ``[]`` when the collection is empty.
        """
        if self._collection.count() == 0:
            return []
        actual_k = min(top_k, self._collection.count())
        results = self._collection.query(
            query_embeddings=[vector],
            n_results=actual_k,
            include=["metadatas", "distances"],
        )
        hits: list[dict] = []
        for i, record_id in enumerate(results["ids"][0]):
            # ChromaDB cosine distance ∈ [0, 2]; similarity = 1 - distance
            distance = results["distances"][0][i]
            score = 1.0 - distance
            hits.append(
                {
                    "id": record_id,
                    "score": score,
                    "metadata": results["metadatas"][0][i],
                }
            )
        return hits

    def delete(self, ids: list[str]) -> None:
        """Remove records by id.  Silently ignores ids that do not exist."""
        if not ids:
            return
        self._collection.delete(ids=ids)

    def count(self) -> int:
        """Return the total number of stored records."""
        return self._collection.count()

    # ------------------------------------------------------------------
    # Convenience helpers (not on VectorStore Protocol)
    # ------------------------------------------------------------------

    def upsert_embedded_chunks(self, embedded_chunks: list[EmbeddedChunk]) -> None:
        """Upsert ``EmbeddedChunk`` objects directly, enriching metadata automatically.

        Stored metadata includes everything from ``Chunk.metadata`` plus:
        - ``content_hash`` — used for incremental indexing deduplication
        - ``content``      — raw chunk text, available during retrieval
        - ``source_path``  — string form of ``Chunk.source_path``
        - ``chunk_index``  — position within the source document
        """
        if not embedded_chunks:
            return
        ids = [ec.chunk.id for ec in embedded_chunks]
        vectors = [ec.vector for ec in embedded_chunks]
        metadatas = [
            {
                **ec.chunk.metadata,
                "content_hash": ec.chunk.content_hash,
                "content": ec.chunk.content,
                "source_path": str(ec.chunk.source_path),
                "chunk_index": ec.chunk.chunk_index,
            }
            for ec in embedded_chunks
        ]
        self.upsert(ids=ids, vectors=vectors, metadatas=metadatas)

    def get_stored_hashes(self) -> set[str]:
        """Return the ``content_hash`` of every record in the collection.

        Call this at startup to seed ``ChunkEmbedder.known_hashes`` so that
        unchanged chunks are never re-embedded across sessions.
        """
        if self._collection.count() == 0:
            return set()
        results = self._collection.get(include=["metadatas"])
        hashes: set[str] = set()
        for meta in results.get("metadatas") or []:
            if meta and "content_hash" in meta:
                hashes.add(meta["content_hash"])
        return hashes

    def get_hashes_for_source(self, source_path: str | Path) -> set[str]:
        """Return the ``content_hash`` of every chunk stored for *source_path*.

        Used before deleting a source so that its hashes can be removed from
        ``ChunkEmbedder._known_hashes``, allowing unchanged chunks to be
        re-embedded after the source is re-ingested.
        """
        if self._collection.count() == 0:
            return set()
        results = self._collection.get(
            where={"source_path": str(source_path)},
            include=["metadatas"],
        )
        hashes: set[str] = set()
        for meta in results.get("metadatas") or []:
            if meta and "content_hash" in meta:
                hashes.add(meta["content_hash"])
        return hashes

    def get_stored_hash_source_pairs(self) -> set[tuple[str, str]]:
        """Return ``(content_hash, source_path)`` for every record in the collection.

        Use this to seed ``ChunkEmbedder`` at startup so that deduplication is
        keyed by *both* content and source path.  Two files with the same
        content but different source paths are treated as independent entries.
        """
        if self._collection.count() == 0:
            return set()
        results = self._collection.get(include=["metadatas"])
        pairs: set[tuple[str, str]] = set()
        for meta in results.get("metadatas") or []:
            if meta and "content_hash" in meta and "source_path" in meta:
                pairs.add((meta["content_hash"], meta["source_path"]))
        return pairs

    def delete_by_source(self, source_path: str | Path) -> None:
        """Delete all chunks whose ``source_path`` metadata matches *source_path*.

        Called when a ``FileEvent(event_type='deleted')`` is processed so that
        stale chunks are removed from the vector store.
        """
        self._collection.delete(where={"source_path": source_path})

    def reset(self) -> None:
        """Delete and recreate the collection, wiping all stored chunks.

        Used by the ``reingest`` command to start indexing from scratch.
        """
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
