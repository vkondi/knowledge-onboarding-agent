# Knowledge Onboarding Agent

> A local-first AI-powered knowledge assistant that ingests your markdown notes, indexes them with local embeddings, and answers questions by reasoning across your entire knowledge base - entirely on your own hardware, with no cloud APIs.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Validate Your Environment](#validate-your-environment)
4. [Next Steps](#next-steps)

---

## Prerequisites

### 1. Python 3.11 or later

```bash
python --version   # must print 3.11.x or higher
```

Download from [python.org](https://www.python.org/downloads/) if needed.

### 2. Ollama

Ollama runs the local LLM and embedding models.

- **Install**: [https://ollama.com/download](https://ollama.com/download)
- **Start the daemon** (runs in the background on port `11434`):

  ```bash
  ollama serve
  ```

  On macOS, Ollama starts automatically after installation. On Windows/Linux, run the command above in a separate terminal or configure it as a service.

### 3. Pull the required models

```bash
# Embedding model (~274 MB)
ollama pull nomic-embed-text

# LLM for answer synthesis (~4 GB for Q4 quantisation)
ollama pull mistral
```

Verify: `ollama list` should list both models.

### 4. Hardware

- **RAM**: 16 GB recommended (8 GB minimum - model loading may be slow)
- **Disk**: ~5 GB free for models + vector database
- **CPU-only inference** is supported; a GPU is not required

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/vkondi/knowledge-onboarding-agent.git
cd koa
```

### 2. Create a virtual environment

```powershell
# Windows - PowerShell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```

```cmd
:: Windows - Command Prompt
python -m venv .venv
.venv\Scripts\activate.bat
```

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

> **Note (Windows PowerShell):** `Set-ExecutionPolicy` is required once per session - Windows blocks unsigned `.ps1` scripts by default. This does not change any permanent system setting.

### 3. Install the package and its dependencies

```bash
pip install -e ".[dev]"
```

This installs the `koa` CLI and all required dependencies.

### 4. (Optional) Install FAISS support

```bash
pip install -e ".[faiss]"
```

---

## Validate Your Environment

Run the bundled validation script to confirm Ollama is reachable and the required models are present:

```bash
python scripts/validate_environment.py
```

Expected output when everything is ready:

```
Checking Python version...
  [ OK ] Python 3.13
Checking Ollama daemon...
  [ OK ] Ollama reachable at http://localhost:11434
Checking required models...
  [ OK ] nomic-embed-text
  [ OK ] mistral
Checking available RAM...
  [ OK ] 14.2 GB free
All checks passed.
```

If any check shows `[FAIL]`, resolve it before continuing.

---

## Next Steps

### Step 1 - Configure your paths

Open `config/settings.yaml` and set `ingestion.watch_paths` to the folders containing your markdown files. Review the full settings reference to tune chunking, retrieval, and model options.

→ [Configuration guide](docs/getting-started/configuration.md)

### Step 2 - Index your documents

Parse, chunk, embed, and store your documents. Unchanged files are detected by content hash and skipped automatically.

```bash
koa ingest sample-knowledge/
```

→ [Indexing guide](docs/getting-started/indexing.md)

### Step 3 - Query your knowledge base

Ask questions, detect conflicting claims across sources, or generate a progressive reading path for a topic.

```bash
koa ask "What are decorators in Python and how do you use them?"
koa conflicts "git workflow"
koa path "machine learning"
```

→ [Querying guide](docs/getting-started/querying.md)

### Step 4 - Keep documents up to date _(optional)_

Monitor your notes folders continuously - files are re-indexed automatically on any change.

```bash
koa watch sample-knowledge/
```

→ [Indexing guide - watch mode](docs/getting-started/indexing.md#watch-folders-for-live-updates)

---

### Reference

| Topic | Guide |
|---|---|
| All settings and their defaults | [configuration.md](docs/getting-started/configuration.md) |
| Running tests, project layout, pipeline overview | [development.md](docs/getting-started/development.md) |
| Common errors and fixes | [troubleshooting.md](docs/getting-started/troubleshooting.md) |

---

## 📄 License

This project is open source and available under the [MIT License](./LICENSE).

## 📞 Contact

- **LinkedIn**: [Vishwajeet Kondi](https://www.linkedin.com/in/vishwajeetkondi/)
- **GitHub**: [@vkondi](https://github.com/vkondi)

---

_Vibe coded with local models, markdown, and the quiet satisfaction of zero cloud API calls_ 🧠📝🔒
