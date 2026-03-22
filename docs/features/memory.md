# Memory

> Layer 1 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Memory is everything YARNNN knows *about the user* — their name, role, how they like to work, facts and standing instructions they've stated. **Memory is stable, explicit, and user-owned.**

**Storage**: Memory lives in `/memory/` files within `workspace_files` (ADR-108). Three files back the Memory page:

| File | Purpose | Example content |
|------|---------|-----------------|
| `/memory/MEMORY.md` | Profile (identity) | name, role, company, timezone, summary |
| `/memory/preferences.md` | Per-platform tone/verbosity | slack: casual/brief, notion: detailed |
| `/memory/notes.md` | Accumulated facts, instructions, preferences | "Prefers bullet points", "Always include TL;DR" |

**Analogy**: Memory is YARNNN's equivalent of Claude Code's auto-memory. The system learns from interaction and stores what's useful. Users can review and edit anytime.

**Strategic principle**: For new users (0-30 days), Memory carries the heaviest reasoning load alongside Context. For mature users (90+ days), Memory accumulates behavioral intelligence that informs Work generation quality.

---

## What it is not

- Not platform content (emails, Slack messages, Notion pages) — that is Context
- Not a log of what YARNNN has done — that is Activity
- Not generated output — that is Work
- Not agent-specific knowledge — that lives in agent workspace files (`/agents/{slug}/`). See ADR-087, ADR-106.
- Not agent cognitive state — self-assessments, directives, and project assessments live in agent/project workspace `memory/` files (ADR-128). See below.

---

## How Memory is written

Memory has three write paths:

| Source | Trigger | What's written | Where |
|--------|---------|---------------|-------|
| **User directly** | Memory page save | Profile, styles, manual entries | MEMORY.md, preferences.md, notes.md |
| **TP conversation** | User says "remember this" → `SaveMemory` primitive | Facts, preferences, instructions stated in chat | notes.md |
| **Nightly extraction** | Cron (midnight UTC, processes yesterday's sessions) | Stable facts extracted from conversations | notes.md |

### SaveMemory primitive (ADR-108)

TP has the `SaveMemory` primitive (chat-mode only). When a user explicitly asks to remember something, TP calls SaveMemory to persist it immediately to `/memory/notes.md`.

- **Add-only**: SaveMemory appends. No update/delete from chat.
- **Deduplication**: Checks existing notes before adding (case-insensitive content match).
- **Activity logged**: Each save creates a `memory_written` activity entry.
- **Three entry types**: `fact` (about the user), `preference` (how they like things), `instruction` (standing directive).

Users manage existing entries (edit, delete) via the Memory page UI.

### Nightly extraction (`process_conversation()`)

The nightly cron (`unified_scheduler.py`, midnight UTC) processes all TP sessions from the previous day. The User Memory Service (`api/services/memory.py`) reviews each conversation via LLM and extracts stable personal facts worth remembering. This is a batch job — a preference stated in conversation today will be in working memory by the next morning (or immediately if the user asks TP to remember it via SaveMemory).

### Read-merge-write pattern

All mutations to `/memory/` files use read-merge-write:
1. Read current file content from `workspace_files`
2. Parse markdown into structured data
3. Merge changes (deduplicate on content)
4. Render back to markdown
5. Upsert to `workspace_files`

This prevents duplication and maintains document-level coherence.

---

## How Memory is read

At the start of every TP session, `working_memory.py → build_working_memory()` reads `/memory/` files and formats them into the system prompt:

```
### About you
Kevin (Head of Growth) at YARNNN
Timezone: Asia/Singapore

### Your preferences
- slack: tone: casual, verbosity: brief

### What you've told me
- Note: always include TL;DR
- Prefers: bullet points in reports
```

This block is injected as part of the TP system prompt (~2,000 token budget total). TP reads it once, at session start. Memory does not update mid-session.

---

## Boundaries

| Question | Answer |
|---|---|
| Can TP write Memory during conversation? | Yes — via the `SaveMemory` primitive when user explicitly asks |
| Does implicit extraction happen in real time? | No — nightly cron extracts from yesterday's sessions |
| Does the user see memory writes? | SaveMemory confirms inline. Nightly extraction is invisible. User reviews all in Memory page |
| Can Memory contain platform content? | No — platform content lives in `platform_content` (Context layer) |
| Does Memory grow automatically? | Yes — through SaveMemory (explicit) and nightly extraction (implicit) |
| Is Memory persistent across sessions? | Yes — it's the only layer that is explicitly persistent and stable |
| What about agent-specific learning? | Agent context lives in workspace files (`/agents/{slug}/`). See ADR-106 |

---

## User control

Users have full control over Memory via the **Memory page**:

- **View**: See all memories
- **Edit**: Modify any value
- **Delete**: Remove any memory
- **Add**: Create new entries manually

The system learns implicitly, but the user owns the data.

### API behavior (user-facing)

- `PATCH /api/memory/profile`: partial upsert to MEMORY.md. Omitted fields are untouched. Explicit `null` or empty string clears that field.
- `GET /api/memory/styles`: list configured platform styles from preferences.md.
- `GET /api/memory/styles/{platform}`: fetch one platform style state.
- `PATCH /api/memory/styles/{platform}`: partial upsert to preferences.md. Omitted fields are untouched. Explicit `null` or empty string clears tone/verbosity.
- `DELETE /api/memory/styles/{platform}`: clear tone + verbosity for that platform.
- `GET /api/memory/user/memories`: list notes from notes.md (content-hash IDs).
- `POST /api/memory/user/memories`: add a note to notes.md.
- `DELETE /api/memory/memories/{id}`: delete a note by content hash.

---

## TP behavior

TP has the `SaveMemory` primitive for persisting user-stated facts:

```
User: "Remember that I prefer bullet points over prose"
TP: [calls SaveMemory(content="Prefers bullet points over prose", entry_type="preference")]
TP: "Got it, I'll remember that you prefer bullet points."
```

If the user asks "what do you know about me?", TP can describe the working memory block injected at session start.

---

## Frontend: Memory page

The Memory page is the primary user interface for Memory. It surfaces:
- **Profile** — name, role, company, timezone, summary
- **Styles** — tone and verbosity per platform
- **Entries** — facts, instructions, preferences (from notes.md)

Users can add, edit, and delete Memory entries directly. Changes are immediate.

---

## Key files

| File | Purpose |
|------|---------|
| `api/services/memory.py` | Extraction service (nightly cron) |
| `api/services/primitives/save_memory.py` | SaveMemory primitive (real-time, chat-mode) |
| `api/services/workspace.py` | `UserMemory` class — reads/writes `/memory/` files |
| `api/services/working_memory.py` | Formats memory for prompt injection |
| `api/routes/memory.py` | Memory page API endpoints |
| `api/services/session_continuity.py` | Session summary generation (chat-layer, separate from memory) |

---

## Agent Cognitive Files (ADR-128)

Separate from user Memory, agents maintain their own cognitive state in workspace `memory/` files. These are **not** part of the Memory page UI — they are coordination infrastructure between agents.

| File | Scope | Written by | Semantics |
|------|-------|-----------|-----------|
| `/agents/{slug}/memory/self_assessment.md` | Per-agent | Agent after each run | Rolling history (5 recent): mandate, fitness, currency, confidence |
| `/agents/{slug}/memory/directives.md` | Per-agent | Agent-via-chat | Accumulated user directives from meeting room |
| `/projects/{slug}/memory/project_assessment.md` | Per-project | PM after each pulse | Overwrite: 5-layer prerequisite evaluation |
| `/projects/{slug}/memory/decisions.md` | Per-project | PM-via-chat | Accumulated project-level decisions from meeting room |

**Key distinction**: User memory (`/memory/`) is user-owned, user-visible, and user-editable. Agent cognitive files (`/agents/{slug}/memory/`, `/projects/{slug}/memory/`) are system-managed coordination infrastructure. They are never shown on the Memory page.

See [workspace-conventions.md](../architecture/workspace-conventions.md) for full file semantics. See [agent-framework.md](../architecture/agent-framework.md) for the cognitive architecture.

---

## Related

- [ADR-108](../adr/ADR-108-user-memory-filesystem-migration.md) — User memory filesystem migration
- [ADR-064](../adr/ADR-064-unified-memory-service.md) — Unified Memory Service (original three-source design)
- [ADR-087](../adr/ADR-087-workspace-scoping-architecture.md) — Agent Scoped Context
- [ADR-106](../adr/ADR-106-agent-workspace-architecture.md) — Agent Workspace Architecture
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
