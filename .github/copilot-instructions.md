# GitHub Copilot Instructions - Knowledge Onboarding Agent

<!-- 
  This file governs how Copilot behaves in this repository.
  It is automatically loaded by GitHub Copilot Chat when working in this workspace.
  Keep this file updated as the project evolves.
-->

## Project Identity

You are helping develop **Knowledge Onboarding Agent** - a local-first AI-powered knowledge system that ingests markdown files, generates local embeddings, and synthesizes answers using a local Ollama LLM. No cloud AI APIs are used.

Before writing any code, you should understand the project's current state. Ask me to load context if it hasn't been established:
- `.github/context/CONTEXT.md` - project identity, stack, conventions
- `.github/context/implementation-tracker.md` - current progress

---

## Technical Stack

| Concern | Technology |
|---|---|
| Language | Python 3.11+ |
| LLM runtime | Ollama (local only) |
| Embedding model | `nomic-embed-text` via Ollama |
| LLM model | `mistral` via Ollama |
| Framework | LlamaIndex |
| Vector store | ChromaDB (primary), FAISS (secondary) |
| File watching | Watchdog |
| Config | PyYAML (`config/settings.yaml`) |
| Testing | pytest |

---

## Architecture Rules (Always Enforce)

1. **Pipeline stages are isolated.** Do not import `embeddings` from `ingestion`, do not import `storage` from `retrieval`. Stages communicate via shared data models only.

2. **Interfaces are Protocols.** All inter-stage contracts use `typing.Protocol`, not ABCs or concrete base classes. Define new interfaces in `src/knowledge_onboarding_agent/interfaces.py`.

3. **No hardcoded values.** Model names, file paths, batch sizes, and thresholds come from `config/settings.yaml`. Never hardcode them in source files.

4. **No cloud APIs.** Do not suggest OpenAI, Anthropic, Cohere, Hugging Face Inference API, or any external LLM/embedding service. Ollama only.

5. **Memory budget awareness.** The target machine has 16GB RAM. Flag anything that could create unbounded memory growth. Prefer streaming or batched operations.

6. **ADR before architecture changes.** If a suggestion would change the established architecture (adding a new stage, changing an interface, swapping a dependency), say so and ask whether to create an ADR first.

---

## Code Conventions

### Module Structure
```
src/knowledge_onboarding_agent/
├── interfaces.py           # All Protocols live here
├── ingestion/
│   ├── __init__.py
│   ├── watcher.py
│   ├── parser.py
│   └── chunker.py
├── embeddings/
│   ├── __init__.py
│   └── ollama_embedder.py
├── storage/
│   ├── __init__.py
│   └── chroma_store.py
├── retrieval/
│   ├── __init__.py
│   └── semantic_search.py
└── orchestration/
    ├── __init__.py
    └── query_engine.py
```

### Style
- Type hints on all function signatures
- Dataclasses or Pydantic models for data objects (no plain dicts as function return types)
- `pathlib.Path` for file paths (not `os.path` string manipulation)
- Explicit error messages (not bare `except:` or silent failures)
- Each public function has a single responsibility

### Testing
- Test files live in `tests/` and mirror the `src/` structure
- Test file name: `tests/test_<module_name>.py`
- Use `pytest` fixtures for shared state
- Integration tests that require Ollama should be marked `@pytest.mark.integration` and skipped in CI unless explicitly requested

---

## What To Do When Starting a New Task

1. Confirm which phase and task is being worked on (reference `implementation-tracker.md`)
2. Check whether a relevant ADR exists before proposing an architectural approach
3. Propose the **interface / data model first** - get confirmation before implementing
4. Implement with tests
5. Do not add features beyond the stated task

---

## What NOT To Do

- Do not use `os.system()` or `subprocess` for tasks that Python libraries handle
- Do not add optional features that weren't requested ("I've also added X which might be useful")
- Do not suggest cloud-based alternatives as "better" options - local-first is a constraint, not a preference
- Do not write implementation code before the interface is agreed upon
- Do not suggest `asyncio` unless we are explicitly in an async implementation phase
- Do not import from a stage that is downstream in the pipeline

---

## When You're Unsure

If a task could be implemented multiple ways that make different architectural tradeoffs, present the options with their tradeoffs - don't silently pick one. Reference the constraints document if relevant: `docs/constraints/runtime-constraints.md`.

---

## Key Reference Documents

| What | Where |
|---|---|
| Project overview and goals | `docs/project-overview.md` |
| System architecture | `docs/architecture/system-design.md` |
| Hardware and software constraints | `docs/constraints/runtime-constraints.md` |
| Development roadmap | `docs/roadmap/roadmap.md` |
| Architecture decisions | `docs/decisions/` |
| Current implementation state | `.github/context/implementation-tracker.md` |
| Session history | `.github/context/session-log.md` |
