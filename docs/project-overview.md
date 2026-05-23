# Project Overview — Knowledge Onboarding Agent

> **Purpose of this document**: Authoritative description of what Knowledge Onboarding Agent is, what it is trying to achieve, and what it explicitly is not.
> Update this document when the project scope changes.

---

## Problem Statement

Knowledge workers accumulate large amounts of markdown notes, technical articles, blog posts, and documentation. This material is:

- **Scattered** — across folders, tools, and formats
- **Unsearchable** — keyword search misses semantic relationships
- **Unsynthesized** — insights across documents remain siloed
- **Ephemeral** — context is lost when a browser tab closes

Existing solutions (Notion, Obsidian, Roam) provide organization but do not reason across content. Cloud AI tools (ChatGPT, Perplexity) require sending private notes to third-party servers.

**Knowledge Onboarding Agent solves this by bringing AI reasoning to local files, running entirely on-device.**

---

## Vision

A personal AI librarian that:
- Knows everything you have written or read
- Can answer questions by reasoning across your entire knowledge base
- Flags when two sources contradict each other
- Suggests what to read next based on what you already know
- Runs on your laptop, offline, with no subscription

---

## Goals

| # | Goal | Priority |
|---|---|---|
| G1 | Ingest markdown files automatically on change | Must |
| G2 | Generate local embeddings without cloud APIs | Must |
| G3 | Answer natural language questions over ingested content | Must |
| G4 | Surface conflicting claims between documents | Should |
| G5 | Generate learning paths from ingested content | Should |
| G6 | Support incremental re-indexing (no full re-embed on change) | Must |
| G7 | Run on 16GB RAM without swapping | Must |
| G8 | Provide a CLI interface | Should |
| G9 | (Future) Web UI | Could |
| G10 | (Future) Multi-agent knowledge workers | Could |

---

## Non-Goals

| # | Non-Goal | Reason |
|---|---|---|
| NG1 | Cloud LLM integration | Local-first constraint |
| NG2 | Real-time collaboration | Out of scope for v1 |
| NG3 | Mobile support | Out of scope for v1 |
| NG4 | PDF / DOCX ingestion | Phase 2+ extension |
| NG5 | Web scraping | Phase 2+ extension |
| NG6 | Fine-tuning local models | Resource constraints |

---

## Success Criteria

The system is considered successful at v1 when:

1. A folder of 500 markdown files is fully ingested in under 10 minutes on target hardware
2. A natural language question returns a relevant, sourced answer in under 10 seconds
3. Adding a new document triggers re-indexing of only that document
4. The system runs continuously without exceeding 8GB RAM under normal load
5. All components have >80% unit test coverage

---

## User Personas

### Primary: The Technical Note-Taker
- Accumulates markdown notes from reading, research, and development
- Wants to query across notes without manually searching
- Comfortable with CLI tools

### Secondary: The Developer Learner
- Takes notes while learning new technologies
- Wants learning paths and concept synthesis
- Wants to know when two tutorials contradict each other

---

## Scope Boundaries

| In Scope (v1) | Out of Scope (v1) |
|---|---|
| Markdown files | PDFs, Word docs |
| Local Ollama LLMs | OpenAI / Anthropic APIs |
| ChromaDB / FAISS | Pinecone / Weaviate |
| CLI interface | Web UI |
| Single-user | Multi-user |
| English content | Multi-language |

---

## Related Documents

- [Architecture: System Design](architecture/system-design.md)
- [Constraints: Runtime Constraints](constraints/runtime-constraints.md)
- [Roadmap](roadmap/roadmap.md)
- [ADR-001: Model Selection](decisions/ADR-001-model-selection.md)
