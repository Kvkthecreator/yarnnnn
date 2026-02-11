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

### Concrete Changes (Phase 1 - Implemented)

1. **Reduce primitives from 9 to 7** — Remove Respond (redundant with model output) and Todo (no multi-step workflows yet)
2. **Introduce context injection** — Preload user profile, active deliverables, platform summaries, and recent session summaries at session start (analogous to Claude Code reading CLAUDE.md)
3. **Demote domain entity** — Deferred; not essential for TP operations

### Deferred Changes (Phase 2 - Pending Infrastructure)

4. **Demote memory from first-class entity to background cache** — Keep `memory` scope in Search for now; deprecate when `platform_content` scope is ready
5. **Narrow Search scopes** — Replace `memory` scope with `platform_content` (requires `sync_summary` column and platform content indexing)
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

---

## Where the Analogy Breaks: Temporal Dimension

**Critical difference:** Claude Code's filesystem is static — files only change when the user edits them. YARNNN's "filesystem" has a temporal axis:

| Claude Code | YARNNN |
|-------------|--------|
| Files are static until edited | Platforms update continuously |
| User triggers all changes | System triggers on schedule |
| No anticipation needed | Must anticipate when to act |
| `Read(file)` = current state | `Read(platform:slack)` = cached state |

### Scheduling as First-Class

Deliverables are not just "build outputs" — they are **scheduled recurring commitments**:

```python
# Load-bearing fields on deliverables table:
schedule: JSONB        # {frequency, day, time, timezone}
next_run_at: TIMESTAMP # When to next execute
last_run_at: TIMESTAMP # When last executed
```

The `_process_deliverable` function in `write.py` calculates `next_run_at` based on schedule — this is core infrastructure, not metadata.

### Data Freshness

TP should be aware of staleness. Context injection includes `last_synced_at` for platforms. If a platform was synced 2 weeks ago, TP should communicate this to users when referencing that data.

### Bidirectional Sync

When TP does `Execute(action="platform.publish", target="platform:slack")`, it writes to an external filesystem the user doesn't fully control. Platform ACLs don't map cleanly to file ownership.

---

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

## Implementation Status

| Step | Action | Status |
|------|--------|--------|
| 1 | Remove Todo from primitive registry | ✅ Done |
| 2 | Remove Respond from primitive registry | ✅ Done |
| 3 | Add "Explore Before Asking" to TP prompt | ✅ Done |
| 4 | Implement `build_session_context()` | ✅ Done |
| 5 | Wire context injection into TP | ✅ Done |
| 6 | Update tp-prompt-guide.md to v5 | ✅ Done |
| 7 | Add `sync_summary` to platform schema | ⏸️ Phase 2 |
| 8 | Add `platform_content` scope to Search | ⏸️ Phase 2 |
| 9 | Remove `memory` scope from Search | ⏸️ Phase 2 |
| 10 | Move `memory.extract` to background job | ⏸️ Phase 2 |

---

## References

- Claude Code system prompt analysis (internal)
- Anthropic Agent SDK documentation
- [Primitives Architecture](../architecture/primitives.md)
- [TP Prompt Guide](../architecture/tp-prompt-guide.md)
