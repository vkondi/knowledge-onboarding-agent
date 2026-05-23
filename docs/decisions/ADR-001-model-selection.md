# ADR-001 — Model Selection for Embeddings and LLM

**Date**: 2026-05-18
**Status**: Draft
**Deciders**: Project architect
**Supersedes**: N/A

---

## Context

Knowledge Onboarding Agent requires two types of models:

1. **An embedding model** — converts text chunks to vector representations for semantic search. Called frequently (every new or changed document). Must be fast and memory-efficient.
2. **An LLM** — synthesizes retrieved chunks into a natural language answer. Called once per query. Quality matters more than speed, within the memory budget.

Both must run locally via Ollama on a 16GB RAM laptop with no GPU. This ADR documents the selection process.

---

## Decision Drivers

- Total RAM usage (LLM + embedding model + ChromaDB + OS) must stay under ~10 GB
- Embedding model must produce high-quality semantic vectors for English technical content
- LLM must produce coherent, grounded answers from retrieved context (no hallucination past context)
- Both models must be available in the Ollama model library
- Embedding model should support batched inference (multiple chunks at once)
- LLM response latency target: < 10 seconds on CPU for a 512-token context

---

## Options Considered

### Embedding Model Options

#### Option A: `nomic-embed-text` (Nomic AI)

Model size: ~274 MB. Dimension: 768. Context: 8192 tokens.

Pros:
- Extremely memory-efficient
- Strong performance on MTEB benchmark for its size
- Natively supported by Ollama
- 8192 token context handles large chunks

Cons:
- Slightly lower quality than larger models at very long contexts

#### Option B: `mxbai-embed-large` (MixedBread AI)

Model size: ~670 MB. Dimension: 1024. Context: 512 tokens.

Pros:
- Higher quality embeddings, especially for retrieval tasks
- Strong MTEB ranking

Cons:
- 512 token context limit requires smaller chunks
- Larger memory footprint

#### Option C: `all-minilm` (sentence-transformers)

Model size: ~45 MB. Dimension: 384. Context: 256 tokens.

Pros:
- Minimal memory usage
- Fast inference

Cons:
- Lower quality embeddings
- Very short context window (256 tokens)

---

### LLM Options

#### Option A: `llama3.2:3b` (Meta, Q4 quantized)

Model size: ~2.0 GB. Parameters: 3 billion.

Pros:
- Fits comfortably in memory alongside the embedding model
- Capable of instruction following and summarization
- Fast on CPU

Cons:
- Less capable than larger models on complex reasoning

#### Option B: `mistral:7b` (Mistral AI, Q4 quantized)

Model size: ~4.1 GB. Parameters: 7 billion.

Pros:
- Significantly better reasoning and synthesis quality
- Strong context following (important for RAG)

Cons:
- Larger memory footprint — leaves less headroom

#### Option C: `phi3:mini` (Microsoft, Q4 quantized)

Model size: ~2.2 GB. Parameters: 3.8 billion.

Pros:
- Strong performance per parameter (especially for reasoning)
- Good instruction following

Cons:
- Less community testing with LlamaIndex RAG patterns

---

## Preliminary Recommendation

> **This section requires benchmarking before the decision is finalized.**

**Embedding**: `nomic-embed-text`
- Rationale: Best balance of quality, context window, and memory for technical English content. 8192 token context means generous chunk sizes. 274 MB leaves ample headroom.

**LLM**: `mistral:7b` (with fallback to `llama3.2:3b` if memory pressure observed)
- Rationale: RAG synthesis quality benefits significantly from a stronger model. At Q4, 4.1 GB is feasible on 16 GB with `nomic-embed-text`. Total model memory: ~4.4 GB, well within budget.

---

## Decision

**Status: DRAFT — requires validation**

Finalize after:
1. Running `ollama pull nomic-embed-text` and `ollama pull mistral` on target hardware
2. Measuring actual RAM usage during a 50-document ingestion and a sample query
3. Validating query latency meets the < 10 second target on CPU

If `mistral:7b` exceeds memory budget, fall back to `llama3.2:3b` and update this ADR to Accepted.

---

## Consequences

### Positive
- `nomic-embed-text` leaves substantial memory headroom for ChromaDB and the application
- 8192 token context allows larger, more semantically complete chunks
- Both models are widely used with LlamaIndex — good documentation

### Negative / Tradeoffs
- `mistral:7b` on CPU will be slower than GPU inference (expected ~5–15 tokens/sec)
- If the user runs other memory-heavy applications simultaneously, headroom shrinks

### Risks
- Ollama model availability: both models are in the public library, risk is low
- Quality regression if forced to fall back to `llama3.2:3b`

---

## Implementation Notes

- Model names are never hardcoded. They are read from `config/settings.yaml`:
  ```yaml
  embeddings:
    model: nomic-embed-text
  llm:
    model: mistral
  ```
- The `EmbeddingProvider` and `QueryEngine` must accept model name from config, not hardcode it.

---

## Review Triggers

- If a new embedding model achieves significantly better MTEB scores at similar memory footprint
- If `mistral:7b` consistently exceeds the memory budget on target hardware
- If Ollama introduces a more efficient inference backend that changes the memory profile
- At Phase 2 milestone, before embedding pipeline is finalized
