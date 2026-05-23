"""Tests for the koa CLI entry point.

Covers the ``ingest`` and ``watch`` sub-commands.  All external dependencies
(IngestionPipeline, ChunkEmbedder, ChromaDBStore, FileWatcher) are replaced
with fakes so no Ollama instance or live database is required.
"""

from __future__ import annotations

import queue
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from knowledge_onboarding_agent.models import Chunk, EmbeddedChunk, FileEvent


# ---------------------------------------------------------------------------
# Shared fake helpers
# ---------------------------------------------------------------------------

def _make_chunk(path: Path, index: int = 0) -> Chunk:
    return Chunk(
        id=f"{path.stem}:{index}",
        source_path=path,
        content=f"Content {index}",
        chunk_index=index,
        metadata={},
        content_hash=f"hash-{path.stem}-{index}",
    )


def _make_embedded(chunk: Chunk) -> EmbeddedChunk:
    return EmbeddedChunk(chunk=chunk, vector=[0.1, 0.2])


class FakePipeline:
    def __init__(self, chunks_per_file: int = 2) -> None:
        self.chunks_per_file = chunks_per_file
        self.ingested: list[Path] = []

    def ingest_file(self, path: Path) -> list[Chunk]:
        self.ingested.append(path)
        return [_make_chunk(path, i) for i in range(self.chunks_per_file)]

    def process_event(self, event: FileEvent) -> list[Chunk]:
        if event.event_type == "deleted":
            return []
        self.ingested.append(event.path)
        return [_make_chunk(event.path, i) for i in range(self.chunks_per_file)]


class FakeChunkEmbedder:
    def __init__(self, *, skip_all: bool = False) -> None:
        self.embedded: list[Chunk] = []
        self.skip_all = skip_all
        self.forgotten: list[set[str]] = []
        self.forgotten_sources: list[str] = []

    def embed_chunks(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        if self.skip_all:
            return []
        self.embedded.extend(chunks)
        return [_make_embedded(c) for c in chunks]

    def forget_hashes(self, hashes: set[str]) -> None:
        self.forgotten.append(hashes)

    def forget_source(self, source_path: str) -> None:
        self.forgotten_sources.append(source_path)


class FakeStore:
    def __init__(self) -> None:
        self.upserted: list[EmbeddedChunk] = []
        self.deleted: list[Path] = []

    def upsert_embedded_chunks(self, embedded: list[EmbeddedChunk]) -> None:
        self.upserted.extend(embedded)

    def get_stored_hashes(self) -> set[str]:
        return set()

    def get_stored_hash_source_pairs(self) -> set[tuple[str, str]]:
        return set()

    def get_hashes_for_source(self, source_path: str) -> set[str]:
        return set()

    def delete_by_source(self, path: str) -> None:
        self.deleted.append(path)


def _fake_ingester(pipeline=None, embedder=None, store=None):
    """Return a fake triple suitable for patching ``_build_ingester``."""
    return (
        pipeline or FakePipeline(),
        embedder or FakeChunkEmbedder(),
        store or FakeStore(),
    )


# ---------------------------------------------------------------------------
# CLI ingest command
# ---------------------------------------------------------------------------

class TestCLIIngest:
    def _run(self, args: list[str], pipeline=None, embedder=None, store=None):
        """Invoke cli_entry with patched _build_ingester."""
        fake_triple = _fake_ingester(pipeline=pipeline, embedder=embedder, store=store)
        with (
            patch("knowledge_onboarding_agent.orchestration._build_ingester", return_value=fake_triple),
            patch("sys.argv", ["koa", "ingest"] + args),
        ):
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()
        return fake_triple

    def test_ingest_single_file(self, tmp_path, capsys):
        md = tmp_path / "note.md"
        md.write_text("# Hello", encoding="utf-8")
        pipeline = FakePipeline(chunks_per_file=1)
        store = FakeStore()
        self._run([str(md)], pipeline=pipeline, store=store)
        assert md in pipeline.ingested
        assert len(store.upserted) == 1

    def test_ingest_directory_finds_md_files(self, tmp_path, capsys):
        (tmp_path / "a.md").write_text("# A", encoding="utf-8")
        (tmp_path / "b.md").write_text("# B", encoding="utf-8")
        (tmp_path / "ignore.txt").write_text("nope", encoding="utf-8")
        pipeline = FakePipeline(chunks_per_file=1)
        store = FakeStore()
        self._run([str(tmp_path)], pipeline=pipeline, store=store)
        assert len(pipeline.ingested) == 2
        assert len(store.upserted) == 2

    def test_ingest_multiple_paths(self, tmp_path, capsys):
        dir_a = tmp_path / "a"
        dir_a.mkdir()
        dir_b = tmp_path / "b"
        dir_b.mkdir()
        (dir_a / "x.md").write_text("X", encoding="utf-8")
        (dir_b / "y.md").write_text("Y", encoding="utf-8")
        pipeline = FakePipeline(chunks_per_file=1)
        self._run([str(dir_a), str(dir_b)], pipeline=pipeline)
        assert len(pipeline.ingested) == 2

    def test_ingest_prints_file_summary(self, tmp_path, capsys):
        md = tmp_path / "doc.md"
        md.write_text("# Doc", encoding="utf-8")
        self._run([str(md)])
        out = capsys.readouterr().out
        assert "doc.md" in out
        assert "Done" in out

    def test_ingest_non_existent_path_warns(self, tmp_path, capsys):
        missing = tmp_path / "missing.md"
        pipeline = FakePipeline()
        # No real files to ingest — should print warning and return gracefully.
        with (
            patch(
                "knowledge_onboarding_agent.orchestration._build_ingester",
                return_value=_fake_ingester(pipeline=pipeline),
            ),
            patch("sys.argv", ["koa", "ingest", str(missing)]),
        ):
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()
        err = capsys.readouterr().err
        assert "does not exist" in err or "skipped" in err

    def test_ingest_no_md_files_prints_message(self, tmp_path, capsys):
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        with (
            patch(
                "knowledge_onboarding_agent.orchestration._build_ingester",
                return_value=_fake_ingester(),
            ),
            patch("sys.argv", ["koa", "ingest", str(tmp_path)]),
        ):
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()
        out = capsys.readouterr().out
        assert "No markdown files" in out

    def test_ingest_skips_already_known_chunks(self, tmp_path, capsys):
        md = tmp_path / "old.md"
        md.write_text("# Old", encoding="utf-8")
        embedder = FakeChunkEmbedder(skip_all=True)
        store = FakeStore()
        self._run([str(md)], embedder=embedder, store=store)
        assert store.upserted == []
        out = capsys.readouterr().out
        assert "0 new" in out

    def test_ingest_non_markdown_file_warns(self, tmp_path, capsys):
        txt = tmp_path / "readme.txt"
        txt.write_text("text", encoding="utf-8")
        pipeline = FakePipeline()
        with (
            patch(
                "knowledge_onboarding_agent.orchestration._build_ingester",
                return_value=_fake_ingester(pipeline=pipeline),
            ),
            patch("sys.argv", ["koa", "ingest", str(txt)]),
        ):
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()
        err = capsys.readouterr().err
        assert "not a markdown file" in err or "skipped" in err


# ---------------------------------------------------------------------------
# CLI watch command
# ---------------------------------------------------------------------------

class TestCLIWatch:
    def _make_settings(self, watch_paths: list[str]):
        from knowledge_onboarding_agent.config import Settings, IngestionConfig
        return Settings(ingestion=IngestionConfig(watch_paths=watch_paths))

    def test_watch_exits_if_no_watch_paths_configured(self, tmp_path, capsys):
        settings = self._make_settings([])
        with (
            patch("knowledge_onboarding_agent.config.load_settings", return_value=settings),
            patch("sys.argv", ["koa", "watch"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "no paths to watch" in err

    def test_watch_cli_paths_override_settings(self, tmp_path):
        """Paths passed on the CLI take precedence over settings.yaml watch_paths."""
        # Settings has no watch_paths configured — CLI arg should be used instead.
        settings = self._make_settings([])
        md = tmp_path / "cli.md"
        md.write_text("# CLI", encoding="utf-8")

        pipeline = FakePipeline(chunks_per_file=1)
        store = FakeStore()
        fake_triple = _fake_ingester(pipeline=pipeline, store=store)

        event_q: queue.Queue[FileEvent] = queue.Queue()
        event_q.put(FileEvent(path=md, event_type="created"))

        fake_watcher = MagicMock()
        fake_watcher.event_queue = event_q
        fake_watcher.__enter__ = lambda s: s
        fake_watcher.__exit__ = MagicMock(return_value=False)
        fake_watcher.seed_from_existing.return_value = 0

        call_count = 0
        original_get = event_q.get

        def patched_get(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_get(block=False)
            raise KeyboardInterrupt

        fake_watcher.event_queue.get = patched_get

        with (
            patch("knowledge_onboarding_agent.config.load_settings", return_value=settings),
            patch("knowledge_onboarding_agent.orchestration._build_ingester", return_value=fake_triple),
            patch("knowledge_onboarding_agent.ingestion.watcher.FileWatcher") as mock_fw,
            patch("sys.argv", ["koa", "watch", str(tmp_path)]),
        ):
            mock_fw.from_settings.return_value = fake_watcher
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()

        assert md in pipeline.ingested

    def test_watch_processes_created_event(self, tmp_path):
        settings = self._make_settings([str(tmp_path)])
        md = tmp_path / "note.md"
        md.write_text("# Note", encoding="utf-8")

        pipeline = FakePipeline(chunks_per_file=1)
        store = FakeStore()
        fake_triple = _fake_ingester(pipeline=pipeline, store=store)

        # Populate a queue with one "created" event then raise KeyboardInterrupt.
        event_q: queue.Queue[FileEvent] = queue.Queue()
        event_q.put(FileEvent(path=md, event_type="created"))

        fake_watcher = MagicMock()
        fake_watcher.event_queue = event_q
        fake_watcher.__enter__ = lambda s: s
        fake_watcher.__exit__ = MagicMock(return_value=False)
        fake_watcher.seed_from_existing.return_value = 0

        call_count = 0
        original_get = event_q.get

        def patched_get(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_get(block=False)
            raise KeyboardInterrupt

        fake_watcher.event_queue.get = patched_get

        with (
            patch("knowledge_onboarding_agent.config.load_settings", return_value=settings),
            patch("knowledge_onboarding_agent.orchestration._build_ingester", return_value=fake_triple),
            patch("knowledge_onboarding_agent.ingestion.watcher.FileWatcher") as mock_fw,
            patch("sys.argv", ["koa", "watch"]),
        ):
            mock_fw.from_settings.return_value = fake_watcher
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()

        assert md in pipeline.ingested
        assert len(store.upserted) == 1

    def test_watch_processes_deleted_event(self, tmp_path):
        settings = self._make_settings([str(tmp_path)])
        md = tmp_path / "gone.md"

        store = FakeStore()
        embedder = FakeChunkEmbedder()
        fake_triple = _fake_ingester(embedder=embedder, store=store)

        event_q: queue.Queue[FileEvent] = queue.Queue()
        event_q.put(FileEvent(path=md, event_type="deleted"))

        fake_watcher = MagicMock()
        fake_watcher.event_queue = event_q
        fake_watcher.__enter__ = lambda s: s
        fake_watcher.__exit__ = MagicMock(return_value=False)
        fake_watcher.seed_from_existing.return_value = 0

        call_count = 0
        original_get = event_q.get

        def patched_get(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_get(block=False)
            raise KeyboardInterrupt

        fake_watcher.event_queue.get = patched_get

        with (
            patch("knowledge_onboarding_agent.config.load_settings", return_value=settings),
            patch("knowledge_onboarding_agent.orchestration._build_ingester", return_value=fake_triple),
            patch("knowledge_onboarding_agent.ingestion.watcher.FileWatcher") as mock_fw,
            patch("sys.argv", ["koa", "watch"]),
        ):
            mock_fw.from_settings.return_value = fake_watcher
            from knowledge_onboarding_agent.orchestration import cli_entry
            cli_entry()

        assert str(md) in store.deleted
        # Source must be forgotten so that a renamed file with the same
        # content can be re-embedded in a subsequent event.
        assert str(md) in embedder.forgotten_sources


# ---------------------------------------------------------------------------
# _build_ingester helper
# ---------------------------------------------------------------------------

class TestBuildIngester:
    def test_returns_three_tuple(self, tmp_path):
        """_build_ingester returns (pipeline, chunk_embedder, store)."""
        from knowledge_onboarding_agent.config import Settings, StorageConfig
        settings = Settings(
            storage=StorageConfig(
                path=str(tmp_path / "db"),
                collection_name="test_build_ingester",
            )
        )
        import chromadb

        fake_client = chromadb.EphemeralClient()

        with patch("knowledge_onboarding_agent.config.load_settings", return_value=settings):
            with patch(
                "knowledge_onboarding_agent.storage.chroma_store.chromadb.PersistentClient",
                return_value=fake_client,
            ):
                from knowledge_onboarding_agent.orchestration import _build_ingester
                from knowledge_onboarding_agent.embeddings.chunk_embedder import ChunkEmbedder
                from knowledge_onboarding_agent.ingestion.pipeline import IngestionPipeline
                from knowledge_onboarding_agent.storage.chroma_store import ChromaDBStore

                pipeline, embedder, store = _build_ingester()

        assert isinstance(pipeline, IngestionPipeline)
        assert isinstance(embedder, ChunkEmbedder)
        assert isinstance(store, ChromaDBStore)
