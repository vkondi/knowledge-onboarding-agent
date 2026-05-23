"""SentenceWindowChunker: splits a ParsedDocument into overlapping Chunk objects.

Chunking strategy:
- Each section is chunked independently (no cross-section merging).
- Text is first split into units (paragraphs, then sentences for long paragraphs).
- Units are grouped into chunks targeting *chunk_size* words.
- Consecutive chunks share *chunk_overlap* words to preserve cross-chunk context.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from knowledge_onboarding_agent.models import Chunk, ParsedDocument, Section


def _word_count(text: str) -> int:
    return len(text.split())


def _split_into_units(text: str) -> list[str]:
    """Split *text* into the smallest meaningful units suitable for chunking.

    Strategy:
    1. Split on paragraph breaks (2+ newlines).
    2. Paragraphs longer than 80 words are further split at sentence boundaries.
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    units: list[str] = []
    for para in paragraphs:
        if _word_count(para) <= 80:
            units.append(para)
        else:
            sentences = [
                s.strip()
                for s in re.split(r"(?<=[.!?])\s+", para)
                if s.strip()
            ]
            units.extend(sentences)
    return units


class SentenceWindowChunker:
    """Chunks a ParsedDocument into overlapping Chunk objects.

    Respects section boundaries — content from different sections is never
    merged into a single chunk, preserving heading context in metadata.

    Conforms to the ``ChunkingStrategy`` Protocol defined in ``interfaces.py``.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be less than "
                f"chunk_size ({chunk_size})"
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Split *document* into a list of overlapping Chunk objects."""
        all_chunks: list[Chunk] = []

        for section in document.sections:
            if not section.content.strip():
                continue
            section_chunks = self._chunk_section(
                section=section,
                source_path=document.source_path,
                start_index=len(all_chunks),
            )
            all_chunks.extend(section_chunks)

        # Fallback: document has content but no parseable sections
        if not all_chunks and document.content.strip():
            all_chunks = self._chunk_text(
                text=document.content,
                source_path=document.source_path,
                heading_context="",
                start_index=0,
            )

        return all_chunks

    def _chunk_section(
        self,
        section: Section,
        source_path: Path,
        start_index: int,
    ) -> list[Chunk]:
        return self._chunk_text(
            text=section.content,
            source_path=source_path,
            heading_context=section.heading,
            start_index=start_index,
        )

    def _chunk_text(
        self,
        text: str,
        source_path: Path,
        heading_context: str,
        start_index: int,
    ) -> list[Chunk]:
        units = _split_into_units(text)
        if not units:
            return []

        chunks: list[Chunk] = []
        buffer: list[str] = []
        buffer_words = 0
        local_index = 0

        for unit in units:
            unit_words = _word_count(unit)

            # Flush buffer when adding this unit would exceed chunk_size
            if buffer_words + unit_words > self._chunk_size and buffer:
                chunks.append(
                    self._make_chunk(
                        buffer, source_path, start_index + local_index, heading_context
                    )
                )
                local_index += 1
                # Trim buffer from the front until remaining words ≤ chunk_overlap
                while buffer and buffer_words - _word_count(buffer[0]) >= self._chunk_overlap:
                    buffer_words -= _word_count(buffer.pop(0))

            buffer.append(unit)
            buffer_words += unit_words

        # Flush any remaining units
        if buffer:
            chunks.append(
                self._make_chunk(
                    buffer, source_path, start_index + local_index, heading_context
                )
            )

        return chunks

    @staticmethod
    def _make_chunk(
        units: list[str],
        source_path: Path,
        index: int,
        heading_context: str,
    ) -> Chunk:
        content = " ".join(units)
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return Chunk(
            id=f"{source_path.stem}:{index}",
            source_path=source_path,
            content=content,
            chunk_index=index,
            metadata={
                "heading": heading_context,
                "word_count": _word_count(content),
                "source_file": str(source_path),
            },
            content_hash=content_hash,
        )
