# Memory

> Layer 1 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Memory is everything YARNNN knows *about the user* — their name, role, how they like to work, facts and standing instructions they've stated, and things TP has noted during conversations.

It is stable, explicit, and user-owned. Memory formation is **implicit** — TP doesn't announce when it's remembering something. Extraction happens via the nightly cron (midnight UTC), not during or at the end of a conversation.

**Analogy**: Memory is YARNNN's equivalent of Claude Code's auto-memory. The system learns from interaction and stores what's useful. Users can review and edit anytime.

---

## What it is not

- Not platform content (emails, Slack messages, Notion pages) — that is Context
- Not a log of what YARNNN has done — that is Activity
- Not generated output — that is Work
- Not visible during conversation — memory writes happen in the background

---

## Table: `user_context`

Single flat key-value store. One row per fact. Defined in ADR-059.

| Key pattern | Meaning | Example value |
|---|---|---|
| `name` | User's name | `"Kevin"` |
| `role` | Job title | `"Head of Growth"` |
| `company` | Company | `"YARNNN"` |
| `timezone` | IANA timezone | `"Asia/Singapore"` |
| `summary` | Brief bio | `"Solo founder building..."` |
| `tone_{platform}` | Communication style per platform | `"casual"` |
| `verbosity_{platform}` | Response length preference | `"detailed"` |
| `fact:...` | A noted fact | `"prefers bullet points"` |
| `instruction:...` | A standing instruction | `"always include TL;DR"` |
| `preference:...` | A stated preference | `"no jargon in reports"` |

**Source values**: `user_stated` (user wrote directly), `conversation` (TP extracted from chat), `feedback` (learned from deliverable edits), `pattern` (detected from activity).

**Confidence**: `user_stated = 1.0`. All others below 1.0.

**Unique constraint**: `(user_id, key)` — one value per key per user.

---

## How Memory is written

ADR-064: Memory is written by the **Memory Service** (`api/services/memory.py`), a backend component that extracts learnable facts from multiple sources.

### Write sources

| Source | Trigger | What's extracted |
|---|---|---|
| **User directly** | Context page save | Profile, styles, manual entries |
| **TP conversation** | Nightly cron (midnight UTC, processes yesterday's sessions) | Preferences, facts, instructions stated in chat |
| **Deliverable feedback** | User approves edited version | Patterns from consistent edits |
| **Activity patterns** | Daily background job | Behavioral patterns (e.g., runs digest every Monday) |

### How it works

1. **Conversation extraction**: The nightly cron (`unified_scheduler.py`, midnight UTC) processes all TP sessions from the previous day. The Memory Service reviews each conversation and extracts facts worth remembering. This is **not** triggered at real-time session end — it's a batch job. A preference stated in a conversation today will be in working memory by the next morning.

2. **Feedback extraction**: When a user edits and approves a deliverable, the service analyzes what changed. Consistent patterns (e.g., always shortens intro) become memories.

3. **Pattern detection**: A daily job analyzes `activity_log` for behavioral patterns (e.g., if user always runs a deliverable at the same time).

**Never written by**: Real-time tool calls during conversation. The explicit `create_memory` tool was removed in ADR-064.

---

## How Memory is read

At the start of every TP session, `working_memory.py → build_working_memory()` reads all `user_context` rows and formats them into the system prompt:

```
### About you
Kevin (Head of Growth) at YARNNN
Timezone: Asia/Singapore

### Your preferences
- slack: tone: casual, verbosity: brief
- gmail: verbosity: detailed

### What you've told me
- Note: always include TL;DR
- Prefers: bullet points in reports
```

This block is injected as part of the TP system prompt (~2,000 token budget total). TP reads it once, at session start. Memory does not update mid-session.

---

## Boundaries

| Question | Answer |
|---|---|
| Can TP write Memory during conversation? | No — Memory is extracted at session end by the backend |
| Does the user see memory writes? | No — writes are invisible. User reviews in Context page |
| Can Memory contain platform content? | No — platform content lives in `filesystem_items` (Context layer) |
| Does Memory grow automatically? | Yes — through implicit extraction from conversation and behavior |
| What happens when a key conflicts? | Upsert on `(user_id, key)` — last write wins |
| Is Memory persistent across sessions? | Yes — it's the only layer that is explicitly persistent and stable |

---

## User control

Users have full control over Memory via the **Context page**:

- **View**: See all memories, grouped by type
- **Edit**: Modify any value
- **Delete**: Remove any memory
- **Add**: Create new entries manually

The system learns implicitly, but the user owns the data.

---

## TP behavior

TP doesn't have memory tools. It simply converses naturally:

```
User: "I prefer bullet points over prose"
TP: "Got it, I'll use bullet points going forward."
```

At session end, the backend extracts "prefers bullet points" and writes it to `user_context`. Next session, TP knows about this preference from the working memory prompt.

If the user asks "what do you know about me?", TP can describe the working memory block injected at session start.

---

## Frontend: Context page

The Context page is the primary user interface for Memory. It surfaces:
- **Profile** — name, role, company, timezone, summary
- **Styles** — tone and verbosity per platform
- **Entries** — facts, instructions, preferences

Users can add, edit, and delete Memory entries directly. Changes are immediate.

---

## Related

- [ADR-064](../adr/ADR-064-unified-memory-service.md) — Unified Memory Service (implicit extraction)
- [ADR-059](../adr/ADR-059-simplified-context-model.md) — Memory table design (user_context)
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- `api/services/memory.py` — Memory extraction service
- `api/services/working_memory.py` — Formats memory for prompt injection
