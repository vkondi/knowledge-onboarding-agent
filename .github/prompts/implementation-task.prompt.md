---
mode: agent
description: Implement a specific Knowledge Onboarding Agent task. Loads conventions and proposes interface before writing code.
---

# Implementation Task — Knowledge Onboarding Agent

## Context

I am working on **Knowledge Onboarding Agent**, a local-first AI knowledge system.

**Current phase**: [Phase N — name from roadmap]
**Task**: [Exact task from `implementation-tracker.md`]

## Relevant architecture

The system is a 5-stage pipeline:
```
Ingestion → Embeddings → Storage → Retrieval → Orchestration
```

Stages communicate through shared data models only. No cross-stage imports.

All interfaces are `typing.Protocol` objects defined in `src/knowledge_onboarding_agent/interfaces.py`.

All config values come from `config/settings.yaml`.

## Relevant ADRs

<!-- List ADRs that apply to this task, or write "None" -->

- [ADR-NNN: title]

## Request

For this task, please:

1. **Interface first**: Propose the data models (dataclasses or Pydantic) and Protocol definitions that this component needs. Do not write implementation yet.

2. Wait for my confirmation of the interface.

3. **Then implement**:
   - The module in `src/knowledge_onboarding_agent/<stage>/<file>.py`
   - The corresponding test in `tests/test_<module>.py`
   - Follow all conventions from `.github/copilot-instructions.md`

4. Do not add features beyond what is stated in the task.

5. After implementation, remind me to update `context/implementation-tracker.md`.

---

## Constraints Checklist (apply to all generated code)

- [ ] No hardcoded model names, paths, or magic numbers
- [ ] No cross-stage imports
- [ ] All new interfaces are Protocols in `interfaces.py`
- [ ] Type hints on all function signatures
- [ ] `pathlib.Path` for file paths
- [ ] Tests use pytest fixtures
- [ ] Integration tests needing Ollama are marked `@pytest.mark.integration`
