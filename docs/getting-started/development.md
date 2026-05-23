# Development

## Running tests

Ensure the virtual environment is active before running tests.

```bash
# Unit tests - no Ollama required
pytest tests/ -m "not integration"

# Integration tests - Ollama must be running
pytest tests/ -m "integration"

# Unit tests with a coverage report
pytest tests/ -m "not integration" --cov=src --cov-report=term-missing
```

Current status: **231 unit tests passing**, 1 skipped (FAISS - not installed by default), 8 deselected (integration).

## Project structure

```
koa/
├── config/
│   └── settings.yaml               # All runtime configuration - edit this file
├── src/knowledge_onboarding_agent/
│   ├── config.py                   # Pydantic settings loader
│   ├── interfaces.py               # Protocol contracts between pipeline stages
│   ├── models.py                   # Shared dataclasses (Chunk, EmbeddedChunk, Response …)
│   ├── ingestion/                  # FileWatcher → MarkdownParser → SentenceWindowChunker
│   ├── embeddings/                 # OllamaEmbedder, ChunkEmbedder (with deduplication)
│   ├── storage/                    # ChromaDBStore (primary), FAISSStore (optional)
│   ├── retrieval/                  # SemanticSearch
│   └── orchestration/              # QueryEngine, CLI entry point (cli_entry)
├── tests/                          # Mirror of src/ - unit + integration tests
├── scripts/
│   └── validate_environment.py     # Pre-flight check script
├── docs/                           # Architecture docs, constraints, ADRs, roadmap
└── pyproject.toml                  # Package definition and entry points
```

## Pipeline overview

```
Markdown files
  → Ingestion   (parse + chunk)
  → Embeddings  (Ollama nomic-embed-text)
  → Storage     (ChromaDB)
  → Retrieval   (semantic similarity search)
  → Orchestration (Ollama mistral + answer synthesis)
  → Answer
```

Each stage is isolated - stages never import from each other. All inter-stage contracts are `typing.Protocol` interfaces defined in `interfaces.py`.
