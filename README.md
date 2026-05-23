# Knowledge Onboarding Agent

> A local-first AI-powered knowledge assistant that ingests your markdown notes, indexes them with local embeddings, and answers questions by reasoning across your entire knowledge base — entirely on your own hardware, with no cloud APIs.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Validate Your Environment](#validate-your-environment)

---

## Prerequisites

Before installing Knowledge Onboarding Agent, ensure the following are set up on your machine.

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

Knowledge Onboarding Agent needs two models. Pull them while Ollama is running:

```bash
# Embedding model (~274 MB)
ollama pull nomic-embed-text

# LLM for answer synthesis (~4 GB for Q4 quantisation)
ollama pull mistral
```

Verify both are present:

```bash
ollama list
```

You should see `nomic-embed-text` and `mistral` in the output.

### 4. Hardware

- **RAM**: 16 GB recommended (8 GB minimum — model loading may be slow)
- **Disk**: ~5 GB free for models + vector database
- **CPU-only inference** is supported; a GPU is not required

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-org/koa.git
cd koa
```

### 2. Create a virtual environment

```powershell
# Windows — PowerShell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate.ps1
```

```cmd
:: Windows — Command Prompt
python -m venv .venv
.venv\Scripts\activate.bat
```

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

> **Note (Windows PowerShell):** The `Set-ExecutionPolicy` line is required once per terminal session because Windows blocks running unsigned `.ps1` scripts by default. It does not change any permanent system setting.

### 3. Install the package and its dependencies

```bash
pip install -e ".[dev]"
```

This installs the `koa` CLI command and all required packages (ChromaDB, LlamaIndex, Watchdog, Ollama client, Pydantic, PyYAML).

### 4. (Optional) Install FAISS support

FAISS is a secondary vector store backend. Skip this if you plan to use ChromaDB (the default).

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

## Next steps

| Topic | Guide |
|---|---|
| Configure paths and model settings | [docs/getting-started/configuration.md](docs/getting-started/configuration.md) |
| Index your documents | [docs/getting-started/indexing.md](docs/getting-started/indexing.md) |
| Ask questions, detect conflicts, generate learning paths | [docs/getting-started/querying.md](docs/getting-started/querying.md) |
| Run tests and understand the project layout | [docs/getting-started/development.md](docs/getting-started/development.md) |
| Diagnose common errors | [docs/getting-started/troubleshooting.md](docs/getting-started/troubleshooting.md) |
