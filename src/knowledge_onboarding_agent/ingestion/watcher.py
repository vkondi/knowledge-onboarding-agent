"""FileWatcher: monitors directories for markdown file changes.

Uses Watchdog to observe filesystem events and puts them on a Queue.
Only .md and .markdown files are reported. Non-markdown files are silently ignored.
"""

from __future__ import annotations

import queue
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from knowledge_onboarding_agent.models import FileEvent

if TYPE_CHECKING:
    from knowledge_onboarding_agent.config import Settings

_WATCHED_EXTENSIONS = frozenset({".md", ".markdown"})


class _MarkdownEventHandler(FileSystemEventHandler):
    def __init__(self, event_queue: queue.Queue[FileEvent]) -> None:
        self._queue = event_queue

    def _is_markdown(self, path: str) -> bool:
        return Path(path).suffix.lower() in _WATCHED_EXTENSIONS

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory and self._is_markdown(event.src_path):
            self._queue.put(FileEvent(path=Path(event.src_path), event_type="created"))

    def on_modified(self, event: FileModifiedEvent) -> None:
        if not event.is_directory and self._is_markdown(event.src_path):
            self._queue.put(FileEvent(path=Path(event.src_path), event_type="modified"))

    def on_deleted(self, event: FileDeletedEvent) -> None:
        if not event.is_directory and self._is_markdown(event.src_path):
            self._queue.put(FileEvent(path=Path(event.src_path), event_type="deleted"))

    def on_moved(self, event: FileMovedEvent) -> None:
        if not event.is_directory:
            # Treat a rename/move as: delete the source, create the destination.
            if self._is_markdown(event.src_path):
                self._queue.put(FileEvent(path=Path(event.src_path), event_type="deleted"))
            if self._is_markdown(event.dest_path):
                self._queue.put(FileEvent(path=Path(event.dest_path), event_type="created"))


class FileWatcher:
    """Monitors one or more directories for markdown file changes.

    Events are placed on a Queue[FileEvent] for downstream processing.
    The Watchdog observer runs in a daemon background thread.

    Usage::

        watcher = FileWatcher(watch_paths=[Path("~/notes")])
        watcher.start()
        event = watcher.event_queue.get()   # blocks until an event arrives
        watcher.stop()

    As a context manager::

        with FileWatcher(watch_paths=[Path("~/notes")]) as watcher:
            event = watcher.event_queue.get()
    """

    def __init__(
        self,
        watch_paths: list[Path],
        event_queue: queue.Queue[FileEvent] | None = None,
    ) -> None:
        self._watch_paths = [Path(p).expanduser().resolve() for p in watch_paths]
        self._event_queue: queue.Queue[FileEvent] = event_queue or queue.Queue()
        self._observer = Observer()
        self._handler = _MarkdownEventHandler(self._event_queue)

    @classmethod
    def from_settings(cls, settings: Settings) -> FileWatcher:
        """Construct a FileWatcher from a Settings object.

        Uses ``settings.ingestion.watch_paths`` as the list of directories to
        monitor.  Returns a watcher with no paths configured if the list is
        empty (caller should check before starting).
        """
        return cls(watch_paths=[Path(p) for p in settings.ingestion.watch_paths])

    @property
    def event_queue(self) -> queue.Queue[FileEvent]:
        return self._event_queue

    def start(self) -> None:
        """Start the background observer thread."""
        for path in self._watch_paths:
            self._observer.schedule(self._handler, str(path), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        """Stop the background observer thread and wait for it to exit."""
        self._observer.stop()
        self._observer.join()

    def seed_from_existing(self) -> int:
        """Enqueue FileEvents for all existing markdown files in watched paths.

        Call this before ``start()`` on the first run when the watched
        directories already contain files that have not yet been indexed.

        Returns:
            The number of files enqueued.
        """
        count = 0
        for path in self._watch_paths:
            for ext in _WATCHED_EXTENSIONS:
                for file_path in sorted(path.rglob(f"*{ext}")):
                    self._event_queue.put(FileEvent(path=file_path, event_type="created"))
                    count += 1
        return count

    def __enter__(self) -> FileWatcher:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.stop()
