"""IngestionPipeline: end-to-end orchestration of FileEvent → List[Chunk]."""

from __future__ import annotations

from pathlib import Path

from knowledge_onboarding_agent.config import Settings
from knowledge_onboarding_agent.ingestion.chunker import SentenceWindowChunker
from knowledge_onboarding_agent.ingestion.parser import MarkdownParser
from knowledge_onboarding_agent.models import Chunk, FileEvent


class IngestionPipeline:
    """Processes a FileEvent (or a direct file path) into a list of Chunks.

    Wires together MarkdownParser → SentenceWindowChunker.

    Deletion events return an empty list; the caller is responsible for
    removing the corresponding chunks from storage by source path.
    """

    def __init__(self, parser: MarkdownParser, chunker: SentenceWindowChunker) -> None:
        self._parser = parser
        self._chunker = chunker

    @classmethod
    def from_settings(cls, settings: Settings) -> IngestionPipeline:
        """Construct an IngestionPipeline from a Settings object."""
        chunker = SentenceWindowChunker(
            chunk_size=settings.ingestion.chunking.chunk_size,
            chunk_overlap=settings.ingestion.chunking.chunk_overlap,
        )
        return cls(parser=MarkdownParser(), chunker=chunker)

    def process_event(self, event: FileEvent) -> list[Chunk]:
        """Process a FileEvent into chunks.

        Returns an empty list for deletion events and for files that no
        longer exist at event-processing time (race condition on delete).
        """
        if event.event_type == "deleted":
            return []
        path = event.path
        if not path.exists():
            return []
        return self._ingest(path)

    def ingest_file(self, path: Path) -> list[Chunk]:
        """Directly ingest a single file without wrapping it in a FileEvent."""
        return self._ingest(path)

    def _ingest(self, path: Path) -> list[Chunk]:
        document = self._parser.parse(path)
        return self._chunker.chunk(document)
