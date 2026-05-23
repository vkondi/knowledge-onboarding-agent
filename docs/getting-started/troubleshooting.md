# Troubleshooting

## `connection refused` / `Failed to connect to Ollama`

Ollama is not running. Start it:

```bash
ollama serve
```

On macOS, you can also open the Ollama app from your Applications folder.

---

## `model "mistral" not found` or `model "nomic-embed-text" not found`

The model has not been pulled yet:

```bash
ollama pull mistral
ollama pull nomic-embed-text
```

---

## `koa: command not found`

Either the virtual environment is not active or the package was not installed:

```bash
# Activate the venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # macOS / Linux

# Reinstall
pip install -e ".[dev]"
```

---

## Answer is "I don't have enough information to answer that."

No documents have been indexed, or the indexed content does not cover the question. Run `koa ingest <path>` (see [Indexing Documents](indexing.md)), then try again.

---

## Out-of-memory / Ollama is very slow

- Reduce `embeddings.batch_size` in `settings.yaml` to `8` or `16`
- Close other memory-intensive applications while Ollama is running
- Run the pre-flight check to verify available RAM:

  ```bash
  python scripts/validate_environment.py
  ```

---

## `pytest` errors after pulling a new branch

Dependencies may have changed. Re-install:

```bash
pip install -e ".[dev]"
```
