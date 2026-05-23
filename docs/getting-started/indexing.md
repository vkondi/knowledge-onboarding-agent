# Indexing Documents

Before querying, documents must be indexed. The ingestion pipeline reads your markdown files, splits them into overlapping chunks, generates embeddings via Ollama, and stores them in ChromaDB.

The vector database is persisted to `.knowledge-onboarding-agent/db/` (configurable in `settings.yaml`) and survives process restarts.

## Index a folder or file

```bash
# Index an entire folder (recursive — finds all .md and .markdown files)
koa ingest /path/to/your/notes

# Index a single file
koa ingest /path/to/guide.md

# Index multiple locations at once
koa ingest ~/notes ~/work/docs
```

**Re-running is safe.** Unchanged files are detected by content hash and skipped automatically — only new or modified content is re-embedded. Files with identical content but different source paths are each indexed independently.

## Watch folders for live updates

```bash
# Watch paths configured in config/settings.yaml
koa watch

# Or pass a path directly
koa watch /path/to/your/notes
```

The watcher seeds the index from existing files on startup, then monitors in the foreground. File creations, modifications, and deletions are all handled automatically. Press **Ctrl+C** to stop.

## Wipe and re-index from scratch

```bash
# Uses ingestion.watch_paths from settings.yaml
koa reingest

# Or pass paths directly
koa reingest /path/to/your/notes
```

This clears the entire vector store before re-embedding. Use it after changing chunking settings, swapping embedding models, or when the database gets into a bad state.

---

Next: [Querying the Knowledge Base](querying.md)
