# Knowledge Onboarding Agent — Master Project Context

> **Load this file at the start of every AI session.**
> It is the authoritative summary of what this project is, where it stands, and what conventions govern it.

---

## Project Identity

**Name**: Knowledge Onboarding Agent
**Type**: Local-first AI knowledge system
**Language**: Python 3.11+
**Status**: Implementation complete (v1 — all phases shipped)
**Last Updated**: 2026-05-23

---

## Core Purpose

Knowledge Onboarding Agent ingests markdown files, notes, articles, and documentation into a local vector store, then uses a local LLM (via Ollama) to:

- Answer questions synthesized across all documents
- Detect conflicting claims between sources
- Generate learning paths
- Surface contextually related content
- Maintain a growing personal knowledge base

**Everything runs locally. No cloud APIs. No telemetry.**

---

## Technical Stack (Decided)

| Concern | Choice | Status |
|---|---|---|
| LLM runtime | Ollama | Confirmed |
| Embedding model | `nomic-embed-text` via Ollama | Confirmed |
| LLM model | `mistral` via Ollama | Confirmed |
| Framework | LlamaIndex | Confirmed |
| Vector store | ChromaDB (primary), FAISS (fallback) | Confirmed |
| File watching | Watchdog | Confirmed |
| Markdown parsing | `mistune` | Confirmed |
| Testing | pytest | Confirmed |

---

## Architecture Summary

The system is a pipeline with five stages:

```
[Watched Folders]
       ↓
  [Ingestion]      ← parse, chunk, tag
       ↓
  [Embeddings]     ← local Ollama embedding model
       ↓
  [Storage]        ← ChromaDB / FAISS
       ↓
  [Retrieval]      ← semantic search + reranking
       ↓
  [Orchestration]  ← LlamaIndex agent + Ollama LLM → response
```

Each stage is a separate Python module with no direct cross-imports. They communicate through well-defined interfaces.

---

## Key Constraints (Non-Negotiable)

1. **No cloud AI APIs** — Ollama only
2. **16GB RAM ceiling** — models must fit in memory with headroom for the OS
3. **Incremental ingestion** — do not re-embed unchanged documents
4. **Modular** — every component must be replaceable without cascading changes
5. **Architecture before code** — always update docs before writing implementation

---

## Active Architecture Decisions

| ADR | Decision | Status |
|---|---|---|
| [ADR-001](../docs/decisions/ADR-001-model-selection.md) | Model selection for embeddings and LLM | Draft |

---

## Current Development Phase

All phases complete. The system is fully operational.

- [x] Phase 0 — Architecture and Scaffolding
- [x] Phase 1 — Ingestion Pipeline (`FileWatcher`, `MarkdownParser`, `SentenceWindowChunker`)
- [x] Phase 2 — Embedding Pipeline (`OllamaEmbedder`, `ChunkEmbedder` with deduplication)
- [x] Phase 3 — Storage Layer (`ChromaDBStore` primary, `FAISSStore` optional)
- [x] Phase 4 — Retrieval (`SemanticSearch`)
- [x] Phase 5 — Orchestration and CLI (`QueryEngine`; `koa ingest`, `reingest`, `ask`, `conflicts`, `path`, `watch`)

**Next focus**: ADR-001 finalization, optional reranking/hybrid search (Phase 4 deferred items)

See [`../docs/roadmap/roadmap.md`](../docs/roadmap/roadmap.md) for full roadmap.

---

## Conventions

### Code
- All modules live under `src/knowledge_onboarding_agent/`
- Each module has a `__init__.py` and a matching `tests/test_<module>.py`
- Interfaces are defined as Python Protocols (not ABCs)
- No circular imports — component graph is a DAG
- Config is loaded from `config/settings.yaml` (never hardcoded)

### Commits
- Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- ADRs must be committed before implementation code that enacts the decision

### AI Sessions
- Always load `context/CONTEXT.md` + `context/implementation-tracker.md` first
- Update `context/session-log.md` with a brief summary at end of session
- Update `implementation-tracker.md` after completing any meaningful unit of work

---

## Do Not Do

- Do not hardcode model names — use config
- Do not import across pipeline stages directly
- Do not re-embed documents that have not changed
- Do not begin implementation without a relevant ADR if a significant architectural choice is involved
- Do not add dependencies without noting them in `docs/decisions/`

---

## Related Context Files

| File | When to read |
|---|---|
| [`implementation-tracker.md`](implementation-tracker.md) | Every session — shows current progress |
| [`session-log.md`](session-log.md) | When picking up from a previous session |
| [`../docs/architecture/system-design.md`](../docs/architecture/system-design.md) | When working on any component |
| [`../docs/decisions/`](../docs/decisions/) | Before making any architectural choice |
