"""Tests for knowledge_onboarding_agent.ingestion.watcher."""

import queue
import time
from pathlib import Path

import pytest

from knowledge_onboarding_agent.ingestion.watcher import FileWatcher
from knowledge_onboarding_agent.models import FileEvent


class TestFileWatcherSeedFromExisting:
    def test_seeds_existing_md_files(self, tmp_path):
        (tmp_path / "a.md").write_text("# A", encoding="utf-8")
        (tmp_path / "b.md").write_text("# B", encoding="utf-8")
        watcher = FileWatcher(watch_paths=[tmp_path])
        count = watcher.seed_from_existing()
        assert count == 2

    def test_ignores_non_markdown_files(self, tmp_path):
        (tmp_path / "readme.txt").write_text("text", encoding="utf-8")
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        (tmp_path / "note.md").write_text("# Note", encoding="utf-8")
        watcher = FileWatcher(watch_paths=[tmp_path])
        count = watcher.seed_from_existing()
        assert count == 1

    def test_seed_enqueues_created_events(self, tmp_path):
        (tmp_path / "c.md").write_text("# C", encoding="utf-8")
        q: queue.Queue[FileEvent] = queue.Queue()
        watcher = FileWatcher(watch_paths=[tmp_path], event_queue=q)
        watcher.seed_from_existing()
        event = q.get_nowait()
        assert event.event_type == "created"
        assert event.path.suffix == ".md"

    def test_seed_returns_zero_for_empty_directory(self, tmp_path):
        watcher = FileWatcher(watch_paths=[tmp_path])
        assert watcher.seed_from_existing() == 0

    def test_markdown_extension_accepted(self, tmp_path):
        (tmp_path / "note.markdown").write_text("content", encoding="utf-8")
        watcher = FileWatcher(watch_paths=[tmp_path])
        count = watcher.seed_from_existing()
        assert count == 1


class TestFileWatcherContextManager:
    def test_start_stop_does_not_raise(self, tmp_path):
        watcher = FileWatcher(watch_paths=[tmp_path])
        watcher.start()
        watcher.stop()

    def test_context_manager_lifecycle(self, tmp_path):
        with FileWatcher(watch_paths=[tmp_path]) as watcher:
            assert watcher.event_queue is not None


class TestFileWatcherFromSettings:
    def test_constructs_from_settings_with_paths(self, tmp_path):
        from knowledge_onboarding_agent.config import Settings, IngestionConfig

        settings = Settings(
            ingestion=IngestionConfig(watch_paths=[str(tmp_path)])
        )
        watcher = FileWatcher.from_settings(settings)
        assert watcher._watch_paths == [tmp_path.expanduser().resolve()]

    def test_constructs_from_settings_empty_paths(self):
        from knowledge_onboarding_agent.config import Settings, IngestionConfig

        settings = Settings(ingestion=IngestionConfig(watch_paths=[]))
        watcher = FileWatcher.from_settings(settings)
        assert watcher._watch_paths == []

    def test_constructs_from_settings_multiple_paths(self, tmp_path):
        from knowledge_onboarding_agent.config import Settings, IngestionConfig

        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        settings = Settings(
            ingestion=IngestionConfig(watch_paths=[str(dir_a), str(dir_b)])
        )
        watcher = FileWatcher.from_settings(settings)
        assert len(watcher._watch_paths) == 2


@pytest.mark.integration
class TestFileWatcherLiveEvents:
    """Live filesystem event tests — require real OS file events."""

    def test_created_event_on_new_file(self, tmp_path):
        q: queue.Queue[FileEvent] = queue.Queue()
        watcher = FileWatcher(watch_paths=[tmp_path], event_queue=q)
        with watcher:
            time.sleep(0.1)
            (tmp_path / "new_note.md").write_text("# New", encoding="utf-8")
            event = q.get(timeout=3)
        assert event.event_type == "created"
        assert event.path.name == "new_note.md"

    def test_non_markdown_not_enqueued(self, tmp_path):
        q: queue.Queue[FileEvent] = queue.Queue()
        watcher = FileWatcher(watch_paths=[tmp_path], event_queue=q)
        with watcher:
            time.sleep(0.1)
            (tmp_path / "data.json").write_text('{"key": "value"}', encoding="utf-8")
            time.sleep(0.5)
        assert q.empty()
