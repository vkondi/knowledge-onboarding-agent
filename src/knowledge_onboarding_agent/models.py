"""Shared data models for all Knowledge Onboarding Agent pipeline stages.

These dataclasses are the *only* contracts between pipeline stages.
Stage modules import from here; they never import from sibling stage modules.

Pipeline data flow:
    FileEvent  → [Ingestion]     → Chunk
    Chunk      → [Embeddings]    → EmbeddedChunk
    EmbeddedChunk → [Storage]
    query str  → [Retrieval]     → RetrievedChunk
    RetrievedChunk → [Orchestration] → Response
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class FileEvent:
    """A filesystem event emitted by the FileWatcher."""

    path: Path
    event_type: str  # "created" | "modified" | "deleted"
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Section:
    """A section within a parsed document, delimited by a heading."""

    heading: str    # heading text; empty string for preamble or headingless content
    level: int      # 1–6 for H1–H6; 0 for content with no heading
    content: str    # plain text content of this section (markdown stripped)


@dataclass
class ParsedDocument:
    """A markdown document after parsing, before chunking.

    Produced by MarkdownParser; consumed by ChunkingStrategy.
    """

    source_path: Path
    title: str
    content: str            # full plain-text body (all sections joined)
    sections: list[Section]
    front_matter: dict      # YAML front matter key-value pairs (may be empty)
    modified_at: datetime
    word_count: int


@dataclass
class Chunk:
    """A text chunk ready to be embedded.

    Produced by ChunkingStrategy; consumed by EmbeddingProvider and VectorStore.
    """

    id: str             # stable identifier: "<source_stem>:<chunk_index>"
    source_path: Path
    content: str
    chunk_index: int    # 0-based position within the source document
    metadata: dict      # heading context, word count, source file path, etc.
    content_hash: str   # SHA-256 hex digest of content — used for change detection


@dataclass
class EmbeddedChunk:
    """A Chunk paired with its vector embedding.

    Produced by EmbeddingProvider; consumed by VectorStore.
    """

    chunk: Chunk
    vector: list[float]


@dataclass
class RetrievedChunk:
    """A Chunk returned from a similarity query, with a relevance score.

    Produced by SemanticSearch; consumed by the Orchestration stage.
    """

    chunk: Chunk
    score: float    # similarity score; higher = more relevant (cosine: 0.0–1.0)


@dataclass
class Response:
    """The final answer produced by the Orchestration stage.

    Produced by QueryEngine; the terminal output of the pipeline.
    """

    answer: str                     # LLM-generated answer text
    sources: list[RetrievedChunk]   # chunks used as context for the answer
    query: str                      # the original question
