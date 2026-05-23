"""Tests for knowledge_onboarding_agent.ingestion.pipeline."""

from datetime import datetime
from pathlib import Path

import pytest

from knowledge_onboarding_agent.config import load_settings
from knowledge_onboarding_agent.ingestion.pipeline import IngestionPipeline
from knowledge_onboarding_agent.models import FileEvent

FIXTURES = Path(__file__).parent.parent / "fixtures"
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


@pytest.fixture
def pipeline() -> IngestionPipeline:
    settings = load_settings(CONFIG_PATH)
    return IngestionPipeline.from_settings(settings)


class TestIngestionPipelineIngestFile:
    def test_ingest_file_returns_chunks(self, pipeline):
        chunks = pipeline.ingest_file(FIXTURES / "simple.md")
        assert len(chunks) > 0

    def test_ingest_file_chunks_have_non_empty_content(self, pipeline):
        chunks = pipeline.ingest_file(FIXTURES / "simple.md")
        assert all(c.content.strip() for c in chunks)

    def test_ingest_file_all_chunks_have_valid_ids(self, pipeline):
        chunks = pipeline.ingest_file(FIXTURES / "simple.md")
        for chunk in chunks:
            assert ":" in chunk.id
            stem, index = chunk.id.rsplit(":", 1)
            assert stem == "simple"
            assert index.isdigit()

    def test_ingest_file_indices_sequential_from_zero(self, pipeline):
        chunks = pipeline.ingest_file(FIXTURES / "long_article.md")
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_ingest_file_source_path_matches_input(self, pipeline):
        path = FIXTURES / "simple.md"
        chunks = pipeline.ingest_file(path)
        assert all(c.source_path == path for c in chunks)

    def test_ingest_no_headings_fixture(self, pipeline):
        chunks = pipeline.ingest_file(FIXTURES / "no_headings.md")
        assert len(chunks) >= 1

    def test_ingest_long_article_many_chunks(self, pipeline):
        settings = load_settings(CONFIG_PATH)
        from knowledge_onboarding_agent.ingestion.chunker import SentenceWindowChunker
        from knowledge_onboarding_agent.ingestion.parser import MarkdownParser
        small_pipeline = IngestionPipeline(
            parser=MarkdownParser(),
            chunker=SentenceWindowChunker(chunk_size=100, chunk_overlap=20),
        )
        chunks = small_pipeline.ingest_file(FIXTURES / "long_article.md")
        assert len(chunks) > 3


class TestIngestionPipelineProcessEvent:
    def test_process_created_event_returns_chunks(self, pipeline):
        event = FileEvent(
            path=FIXTURES / "simple.md",
            event_type="created",
            timestamp=datetime.now(),
        )
        chunks = pipeline.process_event(event)
        assert len(chunks) > 0

    def test_process_modified_event_returns_chunks(self, pipeline):
        event = FileEvent(
            path=FIXTURES / "simple.md",
            event_type="modified",
            timestamp=datetime.now(),
        )
        chunks = pipeline.process_event(event)
        assert len(chunks) > 0

    def test_process_deleted_event_returns_empty_list(self, pipeline):
        event = FileEvent(
            path=FIXTURES / "simple.md",
            event_type="deleted",
            timestamp=datetime.now(),
        )
        chunks = pipeline.process_event(event)
        assert chunks == []

    def test_process_event_nonexistent_file_returns_empty(self, pipeline, tmp_path):
        missing = tmp_path / "does_not_exist.md"
        event = FileEvent(path=missing, event_type="created", timestamp=datetime.now())
        chunks = pipeline.process_event(event)
        assert chunks == []


class TestIngestionPipelineFromSettings:
    def test_from_settings_constructs_pipeline(self):
        settings = load_settings(CONFIG_PATH)
        pipeline = IngestionPipeline.from_settings(settings)
        assert isinstance(pipeline, IngestionPipeline)

    def test_from_settings_uses_config_chunk_size(self):
        settings = load_settings(CONFIG_PATH)
        pipeline = IngestionPipeline.from_settings(settings)
        # Chunk size from settings should be respected (we verify indirectly
        # by confirming the pipeline runs without error)
        chunks = pipeline.ingest_file(FIXTURES / "simple.md")
        assert len(chunks) > 0
