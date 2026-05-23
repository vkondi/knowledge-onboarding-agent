# Runtime Constraints - Knowledge Onboarding Agent

> **Purpose**: Document the hard constraints that every architectural and implementation decision must respect.
> These are non-negotiable. Add to this list; never remove without a new ADR.

---

## Hardware Constraints

### Target Machine

| Resource | Limit | Notes |
|---|---|---|
| RAM | 16 GB total | OS + background apps consume ~4–6 GB; headroom ~8–10 GB for the application |
| GPU | None (CPU-only) | Ollama will use CPU inference |
| Storage | No hard limit | SSD preferred for ChromaDB performance |
| Network | Offline-capable | No runtime network calls; Ollama and all models installed locally |

### Memory Budget

| Component | Estimated RAM | Notes |
|---|---|---|
| OS + background | ~4–6 GB | Baseline |
| Ollama LLM (mistral 7B Q4) | ~4.5 GB | Conservative estimate |
| Ollama embedding model (nomic-embed-text) | ~0.5 GB | |
| ChromaDB in-process | ~0.5–1 GB | Depends on corpus size |
| Python process (app) | ~0.3–0.5 GB | |
| **Total estimated** | **~10–12 GB** | Leaves ~4–6 GB headroom |

**Rule**: The application must never cause the OS to swap to disk under normal load. If a component approaches its memory budget, it must page data or reduce batch size before allocating more.

---

## Software Constraints

### AI / Model Runtime

| Constraint | Detail |
|---|---|
| No cloud AI APIs | No calls to OpenAI, Anthropic, Cohere, Hugging Face Inference API, or any external LLM service |
| Ollama required | All LLM and embedding inference goes through the local Ollama daemon |
| Model must be pre-pulled | Models must be available locally before the app starts; no auto-download at runtime |

### Python Environment

| Constraint | Detail |
|---|---|
| Python version | 3.11 or later |
| Package manager | pip with `pyproject.toml`; optionally `uv` |
| No private PyPI | All dependencies must be available on public PyPI |
| Dependency pinning | Version lower bounds declared in `pyproject.toml`; use `pip freeze > requirements.txt` for fully reproducible installs |

---

## Operational Constraints

| Constraint | Detail |
|---|---|
| Incremental indexing | Never re-embed a document that has not changed. Use content hashes. |
| Graceful degradation | If Ollama is not running, the watcher still collects file events via `queue.Queue`. However, the embedding call will fail and the watch loop will exit; events are not currently retried automatically. |
| No data egress | No document content, embeddings, or metadata leaves the machine |
| Persistence | Vector store must persist to disk; data must survive process restart |

---

## Performance Targets

| Operation | Target | Acceptable Maximum |
|---|---|---|
| Ingest and embed a single new markdown file (~1000 words) | < 5 seconds | 15 seconds |
| Query response (top-k retrieval + LLM synthesis) | < 10 seconds | 30 seconds |
| Full initial ingestion of 500 files | < 10 minutes | 30 minutes |
| Memory usage at steady state | < 8 GB | 10 GB |

These are not hard failures but design targets. Performance regressions against these targets should be documented in ADRs.

---

## Dependency Constraints

### Allowed (Preferred)

| Package | Role |
|---|---|
| `chromadb` | Primary vector store |
| `faiss-cpu` | Alternative vector store |
| `watchdog` | File system monitoring |
| `ollama` (Python client) | Ollama API client |
| `pydantic` | Data validation and config |
| `pytest` | Testing |
| `pyyaml` | Config loading and front matter parsing |

### Avoid

| Category | Examples | Reason |
|---|---|---|
| Cloud SDK | `boto3`, `google-cloud-*`, `azure-*` | Cloud-free constraint |
| Heavy ML frameworks | `torch` as primary dep | Memory; Ollama handles inference |
| GUI frameworks | `tkinter`, `PyQt` | CLI-first for v1 |
| Paid APIs | Any | Cost and privacy |

---

## Future Constraint Relaxations (Require New ADR)

The following constraints may be relaxed in future versions with an explicit ADR:

- GPU support (if hardware upgrades)
- Optional cloud sync / backup (user-controlled, opt-in)
- PDF ingestion (separate process, bounded memory)
- Web UI (separate process)
