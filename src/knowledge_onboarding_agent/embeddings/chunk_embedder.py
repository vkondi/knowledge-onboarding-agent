"""ChunkEmbedder: drives the EmbeddingProvider over a list of Chunk objects.

Responsibilities:
- Skip chunks whose ``(content_hash, source_path)`` pair is already indexed
  (enables incremental indexing — unchanged content from the same source is
  never re-embedded across sessions or within a watch session).
- Reuse cached vectors when the same content appears in a different source
  file so that Ollama is not called again for identical text.
- Deduplicate within the incoming batch: identical content is embedded once
  and the vector is reused for all matching chunks.
- Delegate actual embedding work to an ``EmbeddingProvider``.
- Return ``EmbeddedChunk`` objects ready for the storage layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from knowledge_onboarding_agent.embeddings.ollama_embedder import OllamaEmbedder
from knowledge_onboarding_agent.models import Chunk, EmbeddedChunk

if TYPE_CHECKING:
    from knowledge_onboarding_agent.config import Settings
    from knowledge_onboarding_agent.interfaces import EmbeddingProvider


class ChunkEmbedder:
    """Embeds ``Chunk`` objects using an ``EmbeddingProvider``.

    Deduplication is keyed by ``(content_hash, source_path)`` so that the
    same content can be independently indexed from different source files.
    A ``_vector_cache`` keyed by ``content_hash`` avoids redundant Ollama
    calls when the same text appears in more than one source file.
    """

    #: Sentinel source used by the legacy ``known_hashes`` constructor path.
    _WILDCARD = "*"

    def __init__(
        self,
        embedder: EmbeddingProvider,
        known_hashes: set[str] | None = None,
        known_pairs: set[tuple[str, str]] | None = None,
    ) -> None:
        self._embedder = embedder
        # Internal dedup table: {(content_hash, source_path_str), ...}
        # Entries with source_path == _WILDCARD match any source (backward compat).
        self._indexed_keys: set[tuple[str, str]] = set()
        if known_pairs is not None:
            self._indexed_keys.update(known_pairs)
        if known_hashes is not None:
            self._indexed_keys.update((h, self._WILDCARD) for h in known_hashes)
        # Per-session vector cache — reused across sources for identical content.
        self._vector_cache: dict[str, list[float]] = {}

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        known_hashes: set[str] | None = None,
        known_pairs: set[tuple[str, str]] | None = None,
    ) -> ChunkEmbedder:
        """Construct a ``ChunkEmbedder`` backed by ``OllamaEmbedder``."""
        embedder = OllamaEmbedder.from_settings(settings)
        return cls(embedder=embedder, known_hashes=known_hashes, known_pairs=known_pairs)

    @property
    def known_hashes(self) -> frozenset[str]:
        """Read-only set of all content hashes currently tracked as indexed."""
        return frozenset(h for h, _ in self._indexed_keys)

    def _is_indexed(self, content_hash: str, source_path: str) -> bool:
        """Return True if this ``(content_hash, source_path)`` pair is indexed."""
        return (
            (content_hash, source_path) in self._indexed_keys
            or (content_hash, self._WILDCARD) in self._indexed_keys
        )

    def forget_source(self, source_path: str | Path) -> None:
        """Remove all indexed keys for *source_path*.

        Call this before re-ingesting a source so that its chunks are
        re-embedded regardless of whether the same content exists elsewhere.
        """
        sp = str(source_path)
        self._indexed_keys = {(h, s) for h, s in self._indexed_keys if s != sp}

    def forget_hashes(self, hashes: set[str]) -> None:
        """Remove all indexed keys whose content hash is in *hashes*.

        Kept for compatibility.  Prefer ``forget_source`` when possible,
        as this removes entries across ALL sources for the given hashes.
        """
        self._indexed_keys = {(h, s) for h, s in self._indexed_keys if h not in hashes}

    def embed_chunks(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """Embed *chunks*, returning ``EmbeddedChunk`` objects for new entries.

        Deduplication is keyed by ``(content_hash, source_path)`` so the
        same content stored under different source files is indexed separately.
        When a hash has already been seen in this session (from another source),
        its cached vector is reused — Ollama is not called again.

        Args:
            chunks: Chunks to embed.  May be empty.

        Returns:
            One ``EmbeddedChunk`` per new ``(content_hash, source_path)``
            pair (order: cached reuses first, then newly embedded).
            Returns ``[]`` if all pairs are already indexed.
        """
        if not chunks:
            return []

        cached: list[EmbeddedChunk] = []    # same content, different source
        to_embed: list[Chunk] = []          # content never seen — call Ollama

        for chunk in chunks:
            sp = str(chunk.source_path)
            if self._is_indexed(chunk.content_hash, sp):
                continue
            if chunk.content_hash in self._vector_cache:
                # Same content seen earlier this session — reuse vector.
                cached.append(EmbeddedChunk(chunk=chunk, vector=self._vector_cache[chunk.content_hash]))
                self._indexed_keys.add((chunk.content_hash, sp))
            else:
                to_embed.append(chunk)

        if not to_embed and not cached:
            return []

        embedded_new: list[EmbeddedChunk] = []
        if to_embed:
            # Deduplicate within batch: each unique text is sent to Ollama once.
            hash_to_vector: dict[str, list[float]] = {}
            unique: list[Chunk] = []
            for chunk in to_embed:
                if chunk.content_hash not in hash_to_vector:
                    hash_to_vector[chunk.content_hash] = []
                    unique.append(chunk)

            vectors = self._embedder.embed([c.content for c in unique])
            for chunk, vector in zip(unique, vectors):
                hash_to_vector[chunk.content_hash] = vector
                self._vector_cache[chunk.content_hash] = vector  # cache for reuse

            for chunk in to_embed:
                sp = str(chunk.source_path)
                embedded_new.append(EmbeddedChunk(chunk=chunk, vector=hash_to_vector[chunk.content_hash]))
                self._indexed_keys.add((chunk.content_hash, sp))

        return cached + embedded_new
