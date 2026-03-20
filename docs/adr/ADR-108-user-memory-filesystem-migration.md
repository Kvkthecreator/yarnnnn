# ADR-108: User Memory Filesystem Migration

**Status:** Superseded — user_memory replaced by workspace `/memory/` filesystem (ADR-106 Phase 2). Extraction pipeline writes to workspace; nightly cron in memory.py unchanged.
**Date:** 2026-03-11
**Supersedes:** ADR-059 (Simplified Context Model — `user_memory` table replaced by `/memory/` filesystem)
**Related:**
- [ADR-106: Agent Workspace Architecture](ADR-106-agent-workspace-architecture.md) — workspace-files-over-Postgres model
- [ADR-107: Knowledge Filesystem Architecture](ADR-107-knowledge-filesystem-architecture.md) — `/knowledge/` shared filesystem
- [ADR-064: Unified Memory Service](ADR-064-unified-memory-service.md) — nightly extraction pipeline (write path changes)
- [ADR-063: Activity Log](ADR-063-activity-log-four-layer-model.md) — Layer 2, unchanged
- [Workspace Conventions](../architecture/workspace-conventions.md) — path tree extension

---

## Context

ADR-106 migrated agent-scoped intelligence from DB columns to workspace files (`/agents/{slug}/`). ADR-107 migrated agent-produced outputs from `platform_content` to `/knowledge/`. The filesystem-over-Postgres model is now proven across two domains.

One domain remains on a legacy table: **global user memory** (`user_memory`).

### What `user_memory` is today

A flat key-value table (ADR-059). ~30 rows per user. Three writers:
1. **User directly** (Memory page) — `source: "user_stated"`, confidence 1.0
2. **Nightly cron** (LLM extraction from conversations) — `source: "tp_extracted"`, confidence 0.6-0.95
3. **Bulk text import** — same extraction pipeline

One primary consumer:
- `build_working_memory()` in `working_memory.py` — reads all rows, parses key prefixes, formats into TP system prompt (~2K tokens)

### Problems

1. **Duplication without deduplication.** The extraction cron writes new key-value rows without reading existing state. Real production data shows 4 entries for "keep deliverables brief" (`instruction:brief_deliverables`, `instruction:deliverables`, `instruction:deliverables_brief`, `instruction:keep_brief`) and 6+ entries about preferring concise content. The key-value model has no structural defense against this.

2. **Ad-hoc key schema.** Key naming (`fact:`, `preference:`, `instruction:`, `tone_`, `verbosity_`) is convention, not enforced. LLM extraction invents verbose keys like `fact:generates_weekly_founder_brief`. Profile fields (`name`, `role`) coexist with extracted duplicates (`fact:name`, `fact:role`). The same information lives at two confidence levels.

3. **No document-level coherence.** Working memory is assembled by parsing key prefixes — a row-by-row reconstruction that produces incoherent output when duplicates exist. There's no concept of "this is the user's profile" as a coherent document.

4. **Inconsistent with established model.** Agent intelligence uses workspace files. Agent outputs use workspace files. User memory uses a separate SQL table with a different abstraction. Three storage mechanisms for conceptually similar data.

5. **Write-only extraction.** The nightly cron appends new rows but never reconciles with existing state. Over time, memory grows noisier. There's no compaction, no merge, no "rewrite this section."

## Decision

### Migrate `user_memory` to `/memory/` in `workspace_files`

User memory moves from a key-value table to a small set of markdown files in the workspace filesystem. Same backing store (`workspace_files`), same access patterns (read/write via file path), same full-text search (via `search_workspace` RPC).

### File Structure

```
/memory/
├── MEMORY.md              # Entry point — profile + summary (like CLAUDE.md's MEMORY.md)
│                          # Contains: name, role, company, timezone, bio
│                          # Canonical identity — user-writable, system-readable
│
├── preferences.md         # Communication and content preferences
│                          # Tone, verbosity, format preferences (per-platform or general)
│                          # Deduplicated — one section per concern, not one row per extraction
│
└── notes.md               # Standing instructions, facts, observations
                           # Things the user has stated or the system has observed
                           # Accumulated but periodically compacted
```

Three files. Not 30 rows.

### Why these three files

| File | What it replaces | Who writes | Character |
|------|-----------------|-----------|-----------|
| `MEMORY.md` | `name`, `role`, `company`, `timezone`, `summary` keys | User (primary), system (bootstrap) | Stable identity — rarely changes |
| `preferences.md` | `tone_*`, `verbosity_*`, `preference:*` keys | System (extraction), user (overrides) | Evolves slowly — per-platform styles |
| `notes.md` | `fact:*`, `instruction:*` keys | System (extraction), user (additions) | Accumulates — needs periodic compaction |

### OS Analogy Extension

```
/agents/           = /home/          Per-process private state
/knowledge/        = /var/shared/    Shared knowledge filesystem
/memory/           = /etc/           System configuration (shapes all behavior)
platform_content   = /dev/           Hardware abstraction (external I/O)
```

`/etc/` is the right analogy: files that configure system behavior, readable by all processes, editable by the administrator. Every TP session reads `/memory/` the way every Linux process reads `/etc/`. It's global, persistent, and authoritative.

### Content Model

**MEMORY.md** — structured identity:
```markdown
# About You

**Kevin Kim** (entrepreneur) at KVK Labs
Timezone: Seoul

Founder building YARNNN, an autonomous agent platform for recurring knowledge work.
```

**preferences.md** — deduplicated preferences:
```markdown
# Preferences

## Communication Style
- Tone: brief, conversational
- Verbosity: concise — prefers shorter content over detailed explanations
- Format: bullet points over prose

## Per-Platform
- Slack: casual tone
- Email: professional but concise
```

**notes.md** — standing instructions and facts:
```markdown
# Notes

## Standing Instructions
- Always keep deliverables brief and to the point
- Always include a TL;DR

## Facts
- Creates strategic intelligence briefs for clients
- Has Slack, Gmail, Notion, and Calendar connected
- Works with KVK Labs and YARNNN projects
```

### Consumption: `build_working_memory()`

Today: queries `user_memory` table → parses key prefixes → assembles sections.

New: reads 3 files → concatenates into prompt block.

```python
# Before (ADR-059)
rows = client.table("user_memory").select("key, value").eq("user_id", user_id).execute()
profile = _extract_profile(rows)        # Parse name, role, company, timezone keys
preferences = _extract_preferences(rows) # Parse tone_*, verbosity_*, preference:* keys
known = _extract_known(rows)             # Parse fact:*, instruction:* keys

# After (ADR-108)
from services.workspace import UserMemory
um = UserMemory(client, user_id)
memory_md = await um.read("MEMORY.md")       # Already formatted, ready for prompt
preferences_md = await um.read("preferences.md")
notes_md = await um.read("notes.md")
```

No more key-prefix parsing. The files *are* the prompt sections. `format_for_prompt()` becomes `read and concatenate`.

### Extraction: Nightly Cron

Today: LLM extracts key-value pairs → blindly inserts rows.

New: LLM reads existing files → merges new observations → writes back clean files.

```
Cron reads /memory/notes.md (existing)
         + yesterday's conversations
         → LLM produces merged /memory/notes.md (deduplicated, compacted)
         → writes back via UserMemory.write("notes.md", merged_content)
```

The key insight: **read-before-write eliminates duplication.** The LLM sees what's already known before deciding what to add. This is the same pattern as a human editing a document — you read it first, then modify.

Extraction prompt changes from "extract facts as JSON key-value pairs" to "here's the user's current notes file and yesterday's conversations — produce an updated notes file that incorporates any new information without duplicating what's already there."

### User Editing

The Memory page shifts from row-per-fact CRUD to file editing:
- **MEMORY.md**: structured form (name, role, company, timezone, bio) that reads/writes the file
- **preferences.md**: markdown editor with preview
- **notes.md**: markdown editor with preview

Simpler UI. Users edit documents, not database rows.

### Priority and Authority

`user_stated` vs `tp_extracted` confidence is replaced by file-level authority:

| File | Primary author | Override model |
|------|---------------|----------------|
| `MEMORY.md` | User | User writes directly; system only bootstraps if empty |
| `preferences.md` | System (extraction) | User can edit any line; system respects existing content |
| `notes.md` | Both | System appends to "Facts" section; user can edit/delete anything |

User edits always win. The file itself is the source of truth — no separate confidence scoring needed.

## Implementation Plan

**Principle: Singular implementation.** No dual-write. Pre-launch — existing data migrated in-place.

### Phase 1: `/memory/` Files + Read Path

1. Add `UserMemory` class to `workspace.py` (scoped to `/memory/`, user-level, not agent-level)
2. One-time migration: read `user_memory` rows → generate 3 markdown files → write to `workspace_files`
3. Update `build_working_memory()` to read from `/memory/` files instead of `user_memory` table
4. Update `format_for_prompt()` — simplify to file concatenation (no key-prefix parsing)

### Phase 2: Write Path + Extraction

5. Update Memory page (frontend) to read/write `/memory/` files via new API endpoints
6. Update nightly cron extraction to read-merge-write pattern
7. Update bulk import to write to `/memory/notes.md` (append mode)
8. Delete `user_memory` table queries from all code paths

### Phase 3: Cleanup

9. Drop `user_memory` table (migration)
10. Mark ADR-059 as superseded by ADR-108
11. Update architecture docs (four-layer-model.md, workspace-conventions.md, naming-conventions.md)
12. Update feature docs (memory.md)
13. Update CLAUDE.md references

### Documentation Updates Required

| Document | Change |
|----------|--------|
| `docs/architecture/four-layer-model.md` | Layer 1 rewrite: table → filesystem |
| `docs/architecture/workspace-conventions.md` | Expand user-level section with `/memory/` paths |
| `docs/architecture/naming-conventions.md` | Update global user knowledge entry |
| `docs/architecture/context-pipeline.md` | Update memory layer diagram |
| `docs/features/memory.md` | Rewrite: API endpoints, UI model, data model |
| `docs/database/SCHEMA.md` | Remove `user_memory` table section |
| `CLAUDE.md` | Update ADR-059/064 summaries, add ADR-108 |

### Validation

**Post Phase 1:**
- [ ] `build_working_memory()` reads from `/memory/` files
- [ ] TP prompt contains same information as before (regression test)
- [ ] `/memory/` files exist for migrated user
- [ ] `search_workspace` RPC finds `/memory/` content

**Post Phase 2:**
- [ ] Memory page reads/writes files (not table)
- [ ] Nightly extraction produces clean, deduplicated notes
- [ ] User edits persist across extraction cycles
- [ ] No `user_memory` table queries in codebase

**Post Phase 3:**
- [ ] `user_memory` table dropped
- [ ] All docs updated

## What This Supersedes

- **ADR-059** (Simplified Context Model): `user_memory` table replaced by `/memory/` filesystem. The conceptual model (profile, preferences, facts) survives — the storage and extraction model changes.
- **ADR-064** (Unified Memory Service): Extraction pipeline changes from insert-rows to read-merge-write-files. The nightly cron timing and implicit-extraction philosophy are unchanged.

## What This Does NOT Change

- **Agent workspace** (ADR-106): `/agents/{slug}/` unchanged.
- **Knowledge filesystem** (ADR-107): `/knowledge/` unchanged.
- **Activity log** (ADR-063): Layer 2 unchanged.
- **Platform content** (ADR-072): External data unchanged.
- **Working memory injection timing**: Still assembled at session start, still injected into TP system prompt.
- **Extraction trigger**: Still nightly cron at midnight UTC. Not real-time.

## Full Filesystem Map

After ADR-108, the complete YARNNN filesystem:

```
/memory/                 = /etc/           User identity + preferences (global config)
/agents/{slug}/          = /home/          Per-agent private state
/knowledge/              = /var/shared/    Agent-produced knowledge artifacts
platform_content (table) = /dev/           External platform data (TTL-managed)
activity_log (table)     = /var/log/       System event log (append-only)
delivery layer           = /proc/          System services (actions, routing)
TP (orchestrator)        = shell           User interface
sync pipeline            = kernel drivers  Background I/O management
```
