# Configuration

All runtime settings live in `config/settings.yaml`. Edit this file to change behaviour. Never hardcode values in source files.

## Minimum setup before first use

Set the paths to your markdown folders:

```yaml
ingestion:
  watch_paths:
    - /path/to/your/notes
    - /path/to/another/folder
```

Paths may be absolute or relative to the project root. Any folder listed here is used by default when you run `koa watch` or `koa reingest` without explicit path arguments.

## Full settings reference

| Setting | Default | Description |
|---|---|---|
| `ingestion.watch_paths` | `[]` | Folders containing markdown files to index |
| `ingestion.chunking.strategy` | `sentence_window` | Chunking algorithm (`sentence_window`, `fixed_size`, `recursive`) |
| `ingestion.chunking.chunk_size` | `512` | Target chunk size in words |
| `ingestion.chunking.chunk_overlap` | `64` | Overlap in words between consecutive chunks |
| `embeddings.model` | `nomic-embed-text` | Ollama embedding model name |
| `embeddings.batch_size` | `32` | Chunks embedded per Ollama API call (reduce if memory pressure occurs) |
| `embeddings.ollama_base_url` | `http://localhost:11434` | Ollama daemon URL for embeddings |
| `storage.backend` | `chromadb` | Vector store backend (`chromadb` or `faiss`) |
| `storage.path` | `./.knowledge-onboarding-agent/db` | Local folder for the vector database |
| `storage.collection_name` | `knowledge_base` | ChromaDB collection name |
| `retrieval.top_k` | `10` | Maximum number of chunks retrieved per query |
| `retrieval.top_k_scale_factor` | `0.5` | Dynamic scaling factor — grows effective k with KB size; set to `0.0` to use `top_k` directly |
| `retrieval.reranking_enabled` | `false` | Enable cross-encoder reranking (improves precision, adds latency) |
| `llm.model` | `mistral` | Ollama LLM model name for answer synthesis |
| `llm.ollama_base_url` | `http://localhost:11434` | Ollama daemon URL for LLM inference |
| `llm.temperature` | `0.1` | Sampling temperature (0 = fully deterministic) |
| `llm.context_window` | `8192` | Maximum token context passed to the LLM per query |

---

Next: [Indexing Documents](indexing.md)
