# Development Workflow — Knowledge Onboarding Agent

> **Purpose**: Define the repeatable workflow for AI-assisted development on this project.
> Following this workflow minimizes context drift, hallucinated assumptions, and inconsistent code generation.

---

## The Core Problem This Solves

LLM-assisted development breaks down in long projects because:
- Each new conversation starts with zero context
- The AI makes different assumptions each time
- Architectural decisions get repeated or contradicted
- It's unclear what is already built vs. what needs to be done

This workflow makes AI sessions **stateful** by loading context at the start of every session.

---

## Session Start Protocol

At the beginning of every AI session (Copilot, ChatGPT, etc.), paste this as your first message:

```
Please load and acknowledge the following project context files before we begin:

1. context/CONTEXT.md — project identity, stack, conventions
2. context/implementation-tracker.md — what is built, in progress, and next

After loading, summarize:
- Current project phase
- What was last completed
- What is next

Then wait for my instruction.
```

This single habit eliminates most context drift.

---

## Workflow Types

### A. Architecture Discussion

Use when: making a significant design decision, choosing a library, defining an interface.

**Steps**:
1. Start session with context load (above)
2. State the decision that needs to be made
3. Ask the AI to enumerate options with tradeoffs
4. Discuss constraints (reference `docs/constraints/runtime-constraints.md`)
5. Record the decision in a new ADR (`docs/decisions/ADR-NNN-*.md`)
6. Update `context/CONTEXT.md` under "Active Architecture Decisions"
7. Commit the ADR before writing any code that enacts the decision

**Copilot prompt template**: `.github/prompts/architecture-discussion.md`

---

### B. Implementation Task

Use when: writing a specific module, function, or test.

**Steps**:
1. Start session with context load
2. Reference the relevant ADR(s) and system design section
3. State exactly what needs to be built (reference `implementation-tracker.md`)
4. Ask the AI to propose the interface first (data models, function signatures)
5. Review the interface — reject anything that violates conventions or constraints
6. Ask for implementation with tests
7. Review for: circular imports, hardcoded values, missing Protocol usage
8. Update `implementation-tracker.md` with completed task
9. Append brief note to `session-log.md`

**Copilot prompt template**: `.github/prompts/implementation-task.md`

---

### C. Refactoring

Use when: improving existing code without changing behavior.

**Steps**:
1. Start session with context load
2. State the specific refactoring goal (not "make it better")
3. Ask the AI to identify the minimal change needed
4. Confirm that tests pass before and after
5. If the refactoring changes an interface, create an ADR first

**Rule**: Never refactor and add features in the same session.

---

### D. ADR Creation

Use when: a non-trivial architectural decision must be made.

**Steps**:
1. Copy `docs/decisions/ADR-template.md` to `ADR-NNN-short-title.md`
2. Fill in Context, Decision Drivers, and Options Considered sections
3. Bring the draft ADR into the AI session
4. Ask the AI to critique the options or suggest missing alternatives
5. Fill in the Decision section
6. Commit the ADR
7. Update `context/CONTEXT.md` "Active Architecture Decisions" table

**Copilot prompt template**: `.github/prompts/adr-creation.md`

---

### E. Context Summarization

Use when: a session has been long and context window pressure is building.

**Steps**:
1. Ask the AI: "Summarize what we have decided and built in this session as a session log entry."
2. Paste the summary into `context/session-log.md`
3. Update `context/implementation-tracker.md`
4. Commit both files
5. Start a new session using the Session Start Protocol

**Copilot prompt template**: `.github/prompts/context-summary.md`

---

### F. Feature Onboarding

Use when: starting a new phase or major feature from the roadmap.

**Steps**:
1. Read the relevant phase definition in `docs/roadmap/roadmap.md`
2. Check `implementation-tracker.md` for prerequisites
3. If significant choices are needed, create an ADR first
4. Break the feature into the smallest independently testable tasks
5. Add tasks to `implementation-tracker.md` under the new phase
6. Begin with the data model (interfaces before implementations)

---

## Code Review Checklist

Before committing implementation code, verify:

- [ ] No hardcoded model names, file paths, or magic numbers (use `config/settings.yaml`)
- [ ] No cross-stage imports (ingestion does not import embeddings, etc.)
- [ ] All new interfaces defined as Protocols in `src/knowledge_onboarding_agent/interfaces.py`
- [ ] Corresponding test file exists under `tests/`
- [ ] ADR exists for any architectural decision made in this code
- [ ] `implementation-tracker.md` updated
- [ ] Commit message follows Conventional Commits format

---

## Commit Message Format

```
<type>(<scope>): <short description>

[optional body]
[optional footer: references ADR, closes issue, etc.]
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`

Scopes: `ingestion`, `embeddings`, `storage`, `retrieval`, `orchestration`, `config`, `docs`, `context`

Examples:
```
feat(ingestion): implement MarkdownParser with front matter support
docs(decisions): add ADR-001 model selection draft
test(storage): add ChromaDBStore persistence tests
chore(config): add settings.yaml with default values
```

---

## What to Do When the AI Hallucinates Architecture

If Copilot or any AI suggests something that contradicts the established architecture:

1. Stop and reference the relevant ADR or `system-design.md`
2. Paste the relevant section into the chat: "This contradicts our architecture: [paste]"
3. Ask the AI to revise its suggestion to align with the established design
4. If the AI's suggestion is actually better, create an ADR to formally evaluate it — don't silently deviate

---

## Measuring Workflow Health

Good signs:
- `session-log.md` has entries from every session
- `implementation-tracker.md` tasks are moving from `[ ]` to `[x]`
- ADRs exist before the code that implements their decisions
- No module imports another module that is two stages away in the pipeline

Warning signs:
- Sessions begin without loading context
- Architecture is being discovered by reading code rather than docs
- ADRs are being written after the fact to rationalize code already written
- `context/CONTEXT.md` is out of date
