"""Orchestration stage: coordinates retrieval and LLM to produce responses."""

from __future__ import annotations

import argparse
import sys
import textwrap
import time

from knowledge_onboarding_agent.orchestration.query_engine import QueryEngine

__all__ = ["QueryEngine", "cli_entry"]


def cli_entry() -> None:
    """Entry point for the ``koa`` CLI command.

    Sub-commands
    ------------
    ingest <path> [path ...]
        Index markdown files from one or more files or directories.
    reingest [path ...]
        Wipe the vector store and rebuild it from scratch.
    ask <question>
        Answer a natural-language question over the indexed knowledge base.
    conflicts <topic>
        Detect contradictions between sources on a topic.
    path <topic>
        Print a suggested learning path for a topic (ordered source chunks).
    watch
        Start a background file watcher that re-indexes documents on change.
    """
    parser = argparse.ArgumentParser(
        prog="koa",
        description="Local-first AI knowledge assistant — query your markdown knowledge base.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Index markdown files from files or directories.")
    ingest_p.add_argument("paths", nargs="+", metavar="PATH", help="Files or directories to index.")

    reingest_p = sub.add_parser(
        "reingest",
        help="Wipe the vector store and re-index from scratch.",
    )
    reingest_p.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="Files or directories to index. Defaults to ingestion.watch_paths in settings.yaml.",
    )

    ask_p = sub.add_parser("ask", help="Answer a question using the knowledge base.")
    ask_p.add_argument("question", help="The question to ask.")

    conf_p = sub.add_parser("conflicts", help="Detect conflicting claims on a topic.")
    conf_p.add_argument("topic", help="The topic to check for contradictions.")

    path_p = sub.add_parser("path", help="Generate a suggested learning path for a topic.")
    path_p.add_argument("topic", help="The topic to build a learning path for.")

    watch_p = sub.add_parser("watch", help="Watch paths and re-index documents on change.")
    watch_p.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="Directories or files to watch. Overrides ingestion.watch_paths in settings.yaml.",
    )

    args = parser.parse_args()

    if args.command == "ingest":
        _cmd_ingest(args)
        return

    if args.command == "reingest":
        _cmd_reingest(args.paths or [])
        return

    if args.command == "watch":
        _cmd_watch(args.paths or [])
        return

    # Remaining commands require the query engine.
    try:
        engine = _build_engine()
    except Exception as exc:  # noqa: BLE001
        print(f"Error initialising Knowledge Onboarding Agent: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.command == "ask":
        response = engine.ask(args.question)
        print(response.answer)
        if response.sources:
            print("\nSources:")
            seen: set[str] = set()
            for r in response.sources:
                label = str(r.chunk.source_path)
                if label not in seen:
                    print(f"  • {label}")
                    seen.add(label)

    elif args.command == "conflicts":
        result = engine.detect_conflicts(args.topic)
        print(result)

    elif args.command == "path":
        path = engine.generate_learning_path(args.topic)
        if not path:
            print("No relevant content found for that topic.")
        else:
            print(f"Suggested reading order for '{args.topic}':\n")
            current_source = None
            for r in path:
                source = str(r.chunk.source_path)
                if source != current_source:
                    print(f"\n{source}")
                    current_source = source
                preview = textwrap.shorten(r.chunk.content, width=80, placeholder="…")
                print(f"  [{r.chunk.chunk_index}] {preview}")


def _cmd_ingest(args: argparse.Namespace) -> None:
    """Handle the ``ingest`` sub-command."""
    from pathlib import Path

    _MARKDOWN_EXTS = frozenset({".md", ".markdown"})

    target_paths = [Path(p) for p in args.paths]
    files: list[Path] = []
    for tp in target_paths:
        if tp.is_file():
            if tp.suffix.lower() in _MARKDOWN_EXTS:
                files.append(tp)
            else:
                print(f"Warning: {tp} is not a markdown file — skipped.", file=sys.stderr)
        elif tp.is_dir():
            for ext in sorted(_MARKDOWN_EXTS):
                files.extend(sorted(tp.rglob(f"*{ext}")))
        else:
            print(f"Warning: {tp} does not exist — skipped.", file=sys.stderr)

    if not files:
        print("No markdown files found to index.")
        return

    try:
        pipeline, chunk_embedder, store = _build_ingester()
    except Exception as exc:  # noqa: BLE001
        print(f"Error initialising ingestion pipeline: {exc}", file=sys.stderr)
        sys.exit(1)

    total_new = 0
    for fp in files:
        chunks = pipeline.ingest_file(fp)
        embedded = chunk_embedder.embed_chunks(chunks)
        if embedded:
            store.upsert_embedded_chunks(embedded)
        total_new += len(embedded)
        print(f"  {fp.name}: {len(chunks)} chunks ({len(embedded)} new)")

    print(f"\nDone. {total_new} new chunk(s) added to the knowledge base.")


def _cmd_reingest(cli_paths: list[str]) -> None:
    """Handle the ``reingest`` sub-command.

    Wipes all stored vectors then re-indexes every markdown file found under
    the supplied paths (or ``ingestion.watch_paths`` from settings.yaml when
    no paths are given on the CLI).
    """
    from pathlib import Path

    from knowledge_onboarding_agent.config import load_settings
    from knowledge_onboarding_agent.embeddings.chunk_embedder import ChunkEmbedder
    from knowledge_onboarding_agent.ingestion.pipeline import IngestionPipeline
    from knowledge_onboarding_agent.storage.chroma_store import ChromaDBStore

    _MARKDOWN_EXTS = frozenset({".md", ".markdown"})

    settings = load_settings()

    target_dirs: list[Path] = (
        [Path(p) for p in cli_paths]
        if cli_paths
        else [Path(p) for p in settings.ingestion.watch_paths]
    )

    if not target_dirs:
        print(
            "Error: no paths to index.\n"
            "Either pass a path: koa reingest <path>\n"
            "Or set ingestion.watch_paths in config/settings.yaml.",
            file=sys.stderr,
        )
        sys.exit(1)

    files: list[Path] = []
    for tp in target_dirs:
        if tp.is_file():
            if tp.suffix.lower() in _MARKDOWN_EXTS:
                files.append(tp)
            else:
                print(f"Warning: {tp} is not a markdown file — skipped.", file=sys.stderr)
        elif tp.is_dir():
            for ext in sorted(_MARKDOWN_EXTS):
                files.extend(sorted(tp.rglob(f"*{ext}")))
        else:
            print(f"Warning: {tp} does not exist — skipped.", file=sys.stderr)

    if not files:
        print("No markdown files found to index.")
        return

    try:
        store = ChromaDBStore.from_settings(settings)
    except Exception as exc:  # noqa: BLE001
        print(f"Error initialising store: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Wiping vector store ({store.count()} chunk(s) currently stored)...")
    store.reset()

    # Fresh embedder — no known pairs after wipe.
    pipeline = IngestionPipeline.from_settings(settings)
    chunk_embedder = ChunkEmbedder.from_settings(settings)

    print(f"Re-indexing {len(files)} file(s)...\n")
    total_new = 0
    for fp in files:
        chunks = pipeline.ingest_file(fp)
        embedded = chunk_embedder.embed_chunks(chunks)
        if embedded:
            store.upsert_embedded_chunks(embedded)
        total_new += len(embedded)
        print(f"  {fp.name}: {len(chunks)} chunks ({len(embedded)} new)")

    print(f"\nDone. {total_new} chunk(s) indexed from scratch.")


def _cmd_watch(cli_paths: list[str]) -> None:
    """Handle the ``watch`` sub-command.

    Path resolution order:
    1. Paths passed on the CLI (``koa watch <path> ...``)
    2. ``ingestion.watch_paths`` in ``config/settings.yaml``
    """
    from pathlib import Path

    from knowledge_onboarding_agent.config import load_settings
    from knowledge_onboarding_agent.ingestion.watcher import FileWatcher

    settings = load_settings()

    effective_paths = [Path(p) for p in cli_paths] if cli_paths else [
        Path(p) for p in settings.ingestion.watch_paths
    ]

    if not effective_paths:
        print(
            "Error: no paths to watch.\n"
            "Either pass a path: koa watch <path>\n"
            "Or set ingestion.watch_paths in config/settings.yaml.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Inject CLI paths back into settings so FileWatcher.from_settings picks them up.
    if cli_paths:
        settings.ingestion.watch_paths = effective_paths

    try:
        pipeline, chunk_embedder, store = _build_ingester()
    except Exception as exc:  # noqa: BLE001
        print(f"Error initialising ingestion pipeline: {exc}", file=sys.stderr)
        sys.exit(1)

    watcher = FileWatcher.from_settings(settings)

    seed_count = watcher.seed_from_existing()
    if seed_count:
        print(f"Seeding {seed_count} existing file(s) from watched paths...")

    print(
        f"Watching {len(settings.ingestion.watch_paths)} path(s). Press Ctrl+C to stop.\n"
    )

    with watcher:
        try:
            while True:
                try:
                    event = watcher.event_queue.get(timeout=1.0)
                except __import__("queue").Empty:
                    continue  # no event — loop back and check for KeyboardInterrupt
                if event.event_type == "deleted":
                    chunk_embedder.forget_source(str(event.path))
                    store.delete_by_source(str(event.path))
                    print(f"  Removed: {event.path.name}")
                else:
                    # Brief pause so editors that do atomic writes (delete +
                    # create, or rename) finish flushing before we read.
                    time.sleep(0.2)
                    # Forget the source so its chunks are eligible for
                    # re-embedding even if the content hasn't changed.
                    chunk_embedder.forget_source(str(event.path))
                    store.delete_by_source(str(event.path))
                    chunks = pipeline.process_event(event)
                    embedded = chunk_embedder.embed_chunks(chunks)
                    if embedded:
                        store.upsert_embedded_chunks(embedded)
                    print(
                        f"  Indexed: {event.path.name} — "
                        f"{len(chunks)} chunks ({len(embedded)} new)"
                    )
        except KeyboardInterrupt:
            print("\nStopping watcher.")


def _build_ingester() -> tuple:
    """Construct ingestion pipeline, chunk embedder, and store from project settings."""
    from knowledge_onboarding_agent.config import load_settings
    from knowledge_onboarding_agent.embeddings.chunk_embedder import ChunkEmbedder
    from knowledge_onboarding_agent.ingestion.pipeline import IngestionPipeline
    from knowledge_onboarding_agent.storage.chroma_store import ChromaDBStore

    settings = load_settings()
    store = ChromaDBStore.from_settings(settings)
    known_pairs = store.get_stored_hash_source_pairs()
    chunk_embedder = ChunkEmbedder.from_settings(settings, known_pairs=known_pairs)
    pipeline = IngestionPipeline.from_settings(settings)
    return pipeline, chunk_embedder, store


def _build_engine() -> QueryEngine:
    """Construct a ``QueryEngine`` wired to the project settings."""
    from knowledge_onboarding_agent.config import load_settings
    from knowledge_onboarding_agent.embeddings.ollama_embedder import OllamaEmbedder
    from knowledge_onboarding_agent.retrieval.semantic_search import SemanticSearch
    from knowledge_onboarding_agent.storage.chroma_store import ChromaDBStore

    settings = load_settings()
    store = ChromaDBStore.from_settings(settings)
    embedder = OllamaEmbedder.from_settings(settings)
    retriever = SemanticSearch.from_settings(settings, embedder, store)
    return QueryEngine.from_settings(settings, retriever)

