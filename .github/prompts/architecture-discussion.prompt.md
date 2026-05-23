---
mode: ask
description: Start an architecture discussion for Knowledge Onboarding Agent. Loads project context and frames the decision correctly.
---

# Architecture Discussion - Knowledge Onboarding Agent

## Context

I am working on **Knowledge Onboarding Agent**, a local-first AI knowledge system.

Before we discuss, please acknowledge these constraints (from `docs/constraints/runtime-constraints.md`):
- Entirely local - no cloud AI APIs
- 16GB RAM laptop, CPU-only inference
- Ollama for all LLM and embedding inference
- Python 3.11+, LlamaIndex, ChromaDB

And these architecture rules (from `.github/copilot-instructions.md`):
- Pipeline stages are isolated (no cross-stage imports)
- Interfaces are Protocols, not ABCs
- No hardcoded values - everything from `config/settings.yaml`

---

## Decision to Discuss

<!-- Replace this section with the actual decision you need to make -->

**Decision**: [What needs to be decided?]

**Context**: [Why does this decision need to be made now? What triggered it?]

**Constraints that apply**:
- [List any specific constraints from the runtime-constraints doc or project conventions]

---

## Request

Please:
1. Identify 2–3 options for this decision
2. For each option, list pros and cons relative to our constraints
3. Recommend an option with reasoning
4. Identify any information I would need to gather before finalizing the decision (e.g., benchmarks, library docs)
5. Draft the outline of an ADR for this decision

Do not generate implementation code yet.
