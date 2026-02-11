# ADR-038: Filesystem-as-Context Architecture

> **Status**: Accepted
> **Date**: 2026-02-11
> **Deciders**: Kevin (solo founder)
> **Supersedes**: Implicit memory-first architecture
> **Related**: ADR-036 (Two-Layer), ADR-037 (Chat-First Surface)

---

## Context

YARNNN's Thinking Partner (TP) needed a clear architectural model for how it interacts with user data. The v1 primitives spec included 9 tools, 8 entity types, and a first-class memory system with embedding search, importance scoring, and extraction pipelines.

Cross-analysis with Claude Code's architecture revealed that Claude Code operates on a simpler mental model: **the codebase is the filesystem, and all context comes from navigating it directly.** Claude Code doesn't maintain a separate "memory" of the code — it reads files on demand.

The question: does YARNNN need a separate memory layer, or can it treat platform content and documents as its "filesystem"?

## Decision

**Adopt the filesystem-as-context model.** Platform-synced content and uploaded documents are YARNNN's equivalent of a codebase. TP navigates and acts on this content directly rather than through an extracted memory layer.

### Concrete Changes

1. **Reduce primitives from 9 to 7** — Remove Respond (redundant with model output) and Todo (no multi-step workflows yet)
2. **Demote memory from first-class entity to background cache** — Memories still get written for audit/caching, but TP doesn't interact with them as tools
3. **Demote domain entity** — Deferred; not essential for TP operations
4. **Introduce context injection** — Preload user profile, active deliverables, platform summaries, and recent session summaries at session start (analogous to Claude Code reading CLAUDE.md)
5. **Narrow Search scopes** — Replace `memory` scope with `platform_content`; keep `document`, `deliverable`, `all`
6. **Move `memory.extract`** from Execute action catalog to background job triggered by `platform.sync`

### The Mapping

```
Claude Code                    YARNNN
──────────                    ──────
Source files                  Platform content + documents
Build output                  Deliverables
CLAUDE.md                     Context injection (user profile + summaries)
Shell history                 Session history
CI jobs                       Work tickets
Grep/Glob/Read                List/Search/Read
Write/Edit                    Write/Edit
Bash (execute)                Execute (sync/generate/publish)
```

## Consequences

### Positive

- **Simpler mental model** — Both for TP (fewer tools, clearer intent) and for developers (fewer abstractions to maintain)
- **Better model performance** — 7 tools instead of 9 means less decision surface; model makes fewer wrong tool choices
- **Reduced prompt size** — Fewer tools to describe, fewer entity types to list
- **Faster responses** — Context injection eliminates runtime memory searches for common queries
- **Principled entity design** — Clear framework for evaluating new entities: "Is this a source file or a build artifact?"

### Negative

- **Memory search at scale** — If/when YARNNN has users with hundreds of deliverables and months of platform history, context injection won't scale. Will need to re-introduce semantic retrieval, likely scoped to platform content rather than extracted memories.
- **Loss of memory importance scoring** — The memory system's ability to weight retrieval by importance is lost. Context injection is flat — everything gets equal weight. Acceptable at current scale.
- **Migration work** — Need to update TP prompt, primitives implementation, and remove dead code paths for Respond, Todo, memory-as-entity.

### Neutral

- **Memory table stays** — No data migration needed. The table remains; only the TP-facing interface changes.
- **Todo can return** — When `deliverable.generate` becomes a multi-step pipeline taking 30+ seconds, re-introduce Todo as a primitive.
- **Respond can return** — If streaming interleaved messages during long operations becomes necessary, re-introduce as a primitive or handle via websocket.

## Alternatives Considered

### Keep Memory as First-Class Entity
- Pros: More powerful retrieval, importance scoring, semantic search across all user knowledge
- Cons: Adds complexity without proportional value at current scale; duplicates source content; 9 tools instead of 7
- Rejected because: The current user base (1) doesn't benefit from embedding-based retrieval when context injection covers the same ground

### Remove Memory Table Entirely
- Pros: Simplest possible architecture
- Cons: Loses audit trail; makes future scaling harder
- Rejected because: The table has no maintenance cost when TP doesn't interact with it directly; it's a free option on future capability

### Keep 9 Primitives But Deprioritize Memory in Prompt
- Pros: No code changes needed
- Cons: Model still sees 9 tools and may choose memory-related operations; prompt is longer than necessary
- Rejected because: Tool count directly affects model decision quality; removing tools is more effective than deprioritizing them in prompt text

## Implementation Plan

| Step | Action | Files Affected |
|------|--------|----------------|
| 1 | Update TP system prompt to v5 (7 primitives) | `api/agents/thinking_partner.py` |
| 2 | Remove Respond from primitive registry | `api/services/primitives/registry.py` |
| 3 | Remove Todo from primitive registry + delete file | `api/services/primitives/registry.py`, `todo.py` |
| 4 | Remove `memory` scope from Search | `api/services/primitives/search.py` |
| 5 | Add `platform_content` scope to Search | `api/services/primitives/search.py` |
| 6 | Move `memory.extract` to background job on sync | `api/services/primitives/execute.py`, new background job |
| 7 | Add `sync_summary` to platform schema | DB migration |
| 8 | Implement `build_session_context()` | New file: `api/services/context.py` |
| 9 | Wire context injection into session start | `api/agents/thinking_partner.py` |
| 10 | Update primitives spec doc | `docs/primitives-v2.md` |
| 11 | Update TP prompt guide | `docs/tp-prompt-guide.md` |

Steps 1-6 can be done in one PR. Steps 7-9 in a second PR. Steps 10-11 are this ADR's companion docs.

---

## References

- Claude Code system prompt analysis (internal)
- Anthropic Agent SDK documentation
- [Primitives Architecture v2](../docs/primitives-v2.md)
- [TP Prompt Guide v5](../docs/tp-prompt-guide.md)
