# Memory

> Layer 1 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Memory is everything YARNNN knows *about the user* — their name, role, how they like to work, facts and standing instructions they've stated, and preferences TP has noted during conversation.

It is stable, explicit, and user-owned. Nothing enters Memory by inference or background job. If TP learns something, it writes it during the conversation, in context, with the user present.

**Analogy**: Memory is YARNNN's equivalent of Claude Code's `CLAUDE.md`. Exactly what's written there gets read at the start of every session. No more, no less.

---

## What it is not

- Not platform content (emails, Slack messages, Notion pages) — that is Context
- Not a log of what YARNNN has done — that is Activity
- Not generated output — that is Work
- Not inferred by background analysis — the inference pipeline was removed in ADR-059

---

## Table: `user_context`

Single flat key-value store. One row per fact. Replaced four prior tables (`knowledge_profile`, `knowledge_styles`, `knowledge_domains`, `knowledge_entries`) in ADR-059.

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

**Source values**: `user_stated` (user wrote it directly), `tp_extracted` (TP noted it during conversation), `document` (reserved for future document-to-memory promotion).

**Confidence**: `user_stated = 1.0`. All others below 1.0.

**Unique constraint**: `(user_id, key)` — one value per key per user.

---

## How Memory is written

**Two write paths, no others:**

1. **User directly** — via the Context page (Profile tab, Styles tab, Entries tab). The user types or edits a value. Saves immediately to `user_context`.

2. **TP during conversation** — via the `create_memory` and `update_memory` tools in `api/services/project_tools.py`. TP calls these when the user states something worth remembering ("I prefer weekly summaries over daily ones"). The user is always present and in context when this happens. An `activity_log` event is written (`memory_written`) for each write.

**Never written by**: background inference jobs, extraction pipelines, document parsing. These were explicitly removed in ADR-059 because implicit memory writes were unreliable and invisible to the user.

---

## How Memory is read

At the start of every TP session, `working_memory.py → build_working_memory()` reads all `user_context` rows for the user and formats them into the system prompt block:

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
| Can TP write Memory without telling the user? | No — `create_memory` / `update_memory` are called during conversation, with the user present |
| Can Memory contain platform content? | No — platform content lives in `filesystem_items` (Context layer) |
| Does Memory grow automatically? | No — only grows when the user or TP explicitly writes a key |
| What happens when a key conflicts? | Upsert on `(user_id, key)` — last write wins |
| Is Memory persistent across sessions? | Yes — it's the only layer that is explicitly persistent and stable |

---

## Frontend: Context page

The Context page is the primary user interface for Memory. It surfaces:
- **Profile** — name, role, company, timezone, summary
- **Styles** — tone and verbosity per platform
- **Entries** — facts, instructions, preferences

Users can add, edit, and delete Memory entries directly. Changes are immediate.

---

## Related

- [ADR-059](../adr/ADR-059-simplified-context-model.md) — Memory table design and migration from knowledge_* tables
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- `api/services/working_memory.py` — builds and formats Memory for prompt injection
- `api/services/project_tools.py` — `handle_create_memory()`, `handle_update_memory()`
