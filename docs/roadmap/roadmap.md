# Roadmap — Knowledge Onboarding Agent

> **Purpose**: Track development milestones at a high level.
> Not a sprint board — think in phases, not tickets.
> Updated when phases are completed or reprioritized.

---

## Guiding Principle

Build the smallest complete vertical slice of functionality at each phase.

Each phase should produce:
- Working, tested code for its scope
- Updated `context/implementation-tracker.md`
- An ADR for any significant decision made during the phase

---

## Phase 0 — Architecture and Scaffolding

**Status**: In Progress
**Goal**: No implementation code. Establish the knowledge base, project memory, and development workflow.

Deliverables:
- [x] Repository structure designed and documented
- [x] AI context memory system created (`context/`)
- [x] All documentation templates created (`docs/`)
- [x] Copilot instructions and prompt templates created (`.github/`)
- [ ] `pyproject.toml` scaffolded
- [ ] `src/knowledge_onboarding_agent/` package stubs (empty `__init__.py` per module)
- [ ] `config/settings.yaml` with defaults
- [ ] `tests/` mirror structure
- [ ] Verify Ollama runs locally with target models

---

## Phase 1 — Ingestion Pipeline

**Status**: Not Started
**Depends on**: Phase 0 complete
**Goal**: Given a watched folder, detect new/changed markdown files, parse them, and produce a list of `Chunk` objects. No embeddings yet.

Deliverables:
- `FileEvent` and `Chunk` data models
- `FileWatcher` wrapping Watchdog
- `MarkdownParser` (headings, body, code blocks, front matter)
- `ChunkingStrategy` Protocol + `SentenceWindowChunker` implementation
- End-to-end ingestion pipeline test with fixture markdown files
- >80% unit test coverage for all ingestion components

**Success check**: Run the watcher on `tests/fixtures/`, drop in a markdown file, observe a populated `List[Chunk]` printed to stdout.

---

## Phase 2 — Embedding Pipeline

**Status**: Not Started
**Depends on**: Phase 1 complete, ADR-001 finalized
**Goal**: Take `Chunk` objects and produce embeddings. Persist content hashes. Skip re-embedding unchanged chunks.

Deliverables:
- `EmbeddingProvider` Protocol
- `OllamaEmbedder` implementation
- `BatchEmbedder` with deduplication by content hash
- Integration test against local Ollama (skipped in CI if Ollama not present)
- Memory benchmark: confirm embedding 500 chunks stays within memory budget

**Success check**: Embed a folder of 20 test files. Modify one file. Re-run. Confirm only the modified file is re-embedded.

---

## Phase 3 — Storage Layer

**Status**: Not Started
**Depends on**: Phase 2 complete
**Goal**: Persist `EmbeddedChunk` objects in ChromaDB. Support upsert, query by vector, delete by source path.

Deliverables:
- `VectorStore` Protocol
- `ChromaDBStore` implementation
- Persistence across process restarts (ChromaDB `PersistentClient`)
- Metadata stored: source path, content hash, ingestion timestamp, chunk index
- `FAISSStore` stub (not complete, just the interface)
- Tests including persistence across restart

**Success check**: Ingest 100 files, stop the process, restart it, query for a known chunk — it should be found without re-embedding.

---

## Phase 4 — Retrieval

**Status**: Not Started
**Depends on**: Phase 3 complete
**Goal**: Given a natural language query, return top-k relevant chunks.

Deliverables:
- `SemanticSearch` using the embedding model + ChromaDB similarity search
- `RetrievedChunk` model (chunk + similarity score + source metadata)
- Optional `Reranker` (disabled by default)
- Retrieval accuracy evaluation against a small golden dataset

**Success check**: Ask "what is sentence window chunking?" against an ingested set of notes on the topic — correct chunks returned in top 3.

---

## Phase 5 — Query Interface (MVP)

**Status**: Not Started
**Depends on**: Phase 4 complete
**Goal**: End-to-end: ask a natural language question, get a sourced answer synthesized from your documents.

Deliverables:
- LlamaIndex `VectorStoreIndex` wired to `ChromaDBStore`
- `QueryEngine` wrapper
- `ConflictDetector` (identify chunks with contradictory claims)
- CLI: `koa query "your question here"`
- Response format: answer + list of sources with file paths
- Demo: query across 100 personal notes

**Success check**: Full pipeline runs on 16GB laptop. Query in < 10 seconds. Sources cited correctly.

---

## Phase 6 — Learning Paths and Synthesis (v1 Feature Complete)

**Status**: Not Started
**Depends on**: Phase 5 complete
**Goal**: Generate a learning path and topic synthesis from ingested knowledge.

Deliverables:
- `LearningPathGenerator`: given a topic, returns an ordered sequence of documents to read
- `TopicSynthesizer`: summarizes what the knowledge base knows about a topic
- CLI commands: `koa learn "topic"`, `koa summarize "topic"`

---

## Future Considerations (Post-v1)

These are not on the current roadmap. They require new ADRs.

| Feature | Notes |
|---|---|
| PDF / DOCX ingestion | Bounded memory subprocess |
| Web UI | FastAPI + HTMX or simple Streamlit |
| Multi-agent knowledge workers | Requires new orchestration architecture |
| Incremental fine-tuning | Requires GPU or significant research |
| Cross-device sync | User-controlled, opt-in, E2E encrypted |

---

## Milestone Summary

| Phase | Scope | Status |
|---|---|---|
| 0 | Architecture + scaffolding | In Progress |
| 1 | Ingestion pipeline | Not Started |
| 2 | Embedding pipeline | Not Started |
| 3 | Storage layer | Not Started |
| 4 | Retrieval | Not Started |
| 5 | Query interface (MVP) | Not Started |
| 6 | Learning paths (v1 feature complete) | Not Started |
