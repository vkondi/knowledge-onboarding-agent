# Indexing Documents

Before querying, documents must be indexed. The ingestion pipeline reads your markdown files, splits them into overlapping chunks, generates embeddings via Ollama, and stores them in ChromaDB.

The vector database is persisted to `.knowledge-onboarding-agent/db/` (configurable in `settings.yaml`) and survives process restarts.

## Index a folder or file

```bash
# Index an entire folder (recursive — finds all .md and .markdown files)
koa ingest sample-knowledge/

# Index a single file
koa ingest sample-knowledge/git-guide.md

# Index multiple locations at once
koa ingest sample-knowledge/ ~/work/docs
```

Running `koa ingest sample-knowledge/` for the first time produces output like:

```
  ai-agents.md: 56 chunks (56 new)
  deep-learning.md: 13 chunks (13 new)
  docker-guide.md: 31 chunks (31 new)
  git-guide.md: 14 chunks (14 new)
  git-workflows.md: 11 chunks (11 new)
  machine-learning-intro.md: 8 chunks (8 new)
  ml-evaluation.md: 14 chunks (14 new)
  python-advanced.md: 20 chunks (20 new)
  python-basics.md: 11 chunks (11 new)
  rest-api-design.md: 12 chunks (12 new)
  sql-guide.md: 10 chunks (10 new)

Done. 200 new chunk(s) added to the knowledge base.
```

**Re-running is safe.** Unchanged files are detected by content hash and skipped automatically — only new or modified content is re-embedded. Running the same command again shows:

```
  ai-agents.md: 56 chunks (0 new)
  deep-learning.md: 13 chunks (0 new)
  ...

Done. 0 new chunk(s) added to the knowledge base.
```

Files with identical content but different source paths are each indexed independently.

## Watch folders for live updates

```bash
# Watch paths configured in config/settings.yaml
koa watch

# Or pass a path directly
koa watch sample-knowledge/
```

The watcher seeds the index from existing files on startup, then monitors in the foreground. File creations, modifications, and deletions are all handled automatically. Press **Ctrl+C** to stop.

## Wipe and re-index from scratch

```bash
# Uses ingestion.watch_paths from settings.yaml
koa reingest

# Or pass paths directly
koa reingest sample-knowledge/
```

This clears the entire vector store before re-embedding. Use it after changing chunking settings, swapping embedding models, or when the database gets into a bad state. Example output:

```
Wiping vector store (200 chunk(s) currently stored)...
Re-indexing 11 file(s)...

  ai-agents.md: 56 chunks (56 new)
  deep-learning.md: 13 chunks (13 new)
  ...

Done. 200 chunk(s) indexed from scratch.
```

---

Next: [Querying the Knowledge Base](querying.md)
