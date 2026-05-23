---
mode: ask
description: Summarize the current session into a context-continuity log entry for Knowledge Onboarding Agent.
---

# Context Summarization - Knowledge Onboarding Agent

## Purpose

This session is getting long. Please help me create a summary so we can maintain context continuity into future sessions.

---

## Request

Based on everything we have discussed and implemented in this session, please generate:

### 1. Session Log Entry

In this format (for `.github/context/session-log.md`):

```markdown
## YYYY-MM-DD - [Brief Title]

**Session goal**: 
**Completed**: 
**Decisions made**: 
**Deferred**: 
**Next session should start with**: 
```

### 2. Implementation Tracker Updates

List any tasks from `.github/context/implementation-tracker.md` that should be:
- Moved from `[ ]` to `[x]` (completed)
- Moved from `[ ]` to `[-]` (started but not done)
- Added as new tasks

### 3. CONTEXT.md Updates

List any changes that should be reflected in `.github/context/CONTEXT.md`:
- Stack decisions that were finalized
- Architecture changes
- Active ADRs to add or update
- Conventions that were established

---

## Output Format

Provide each section separately so I can paste them into the appropriate files.

Do not update any files yourself - give me the content and I will apply it.
