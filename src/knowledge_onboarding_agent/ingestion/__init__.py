"""Ingestion stage: file watching, markdown parsing, and chunking."""

from knowledge_onboarding_agent.ingestion.chunker import SentenceWindowChunker
from knowledge_onboarding_agent.ingestion.parser import MarkdownParser
from knowledge_onboarding_agent.ingestion.pipeline import IngestionPipeline
from knowledge_onboarding_agent.ingestion.watcher import FileWatcher

__all__ = ["FileWatcher", "MarkdownParser", "SentenceWindowChunker", "IngestionPipeline"]
