"""Protocol definitions for all inter-stage contracts in Knowledge Onboarding Agent.

All concrete implementations must conform to these Protocols.
Stages must only import from this module — never from a sibling stage's module.
The module graph is a strict DAG: no circular imports are permitted.

Pipeline order (data flows top-to-bottom):
    Ingestion → Embeddings → Storage → Retrieval → Orchestration
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from knowledge_onboarding_agent.models import Chunk, ParsedDocument, RetrievedChunk


class EmbeddingProvider(Protocol):
    """Converts text into vector embeddings using a local model."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns one float vector per input text."""
        ...


class VectorStore(Protocol):
    """Persists and retrieves embeddings with associated metadata."""

    def upsert(
        self,
        ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """Insert or update records. Identified by id."""
        ...

    def query(self, vector: list[float], top_k: int) -> list[dict]:
        """Return the top_k most similar records to the given vector."""
        ...

    def delete(self, ids: list[str]) -> None:
        """Remove records by id."""
        ...

    def count(self) -> int:
        """Return the total number of stored records."""
        ...


class ChunkingStrategy(Protocol):
    """Splits a ParsedDocument into a list of Chunk objects."""

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Split *document* into chunks. Returns List[Chunk]."""
        ...


class Retriever(Protocol):
    """Searches stored embeddings for chunks relevant to a query string."""

    def search(self, query: str) -> list[RetrievedChunk]:
        """Return the most relevant chunks for *query*, ordered by descending score."""
        ...
