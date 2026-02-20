# Memory

> Layer 1 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Memory is everything YARNNN knows *about the user* — their name, role, how they like to work, facts and standing instructions they've stated, and patterns YARNNN has learned from their behavior. **Memory is both input for generation and output from learning feedback loops.**

It is stable, explicit, and user-owned. Memory formation is **implicit** — TP doesn't announce when it's remembering something. Extraction happens through three sources: conversation (nightly cron), deliverable feedback (on approval), and activity patterns (daily detection).

**Analogy**: Memory is YARNNN's equivalent of Claude Code's auto-memory. The system learns from interaction and stores what's useful. Users can review and edit anytime.

**Strategic principle**: For new users (0-30 days), Memory carries the heaviest reasoning load alongside Context. For mature users (90+ days), Memory accumulates behavioral intelligence that informs Work generation quality.

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

ADR-064: Memory is written by the **Memory Service** (`api/services/memory.py`), a backend component that extracts learnable facts from three distinct sources, implementing a **learning feedback loop** from Work (Layer 4) and Activity (Layer 2) back to Memory (Layer 1).

### Write sources (ADR-064, ADR-070)

| Source | Trigger | What's extracted | Confidence |
|---|---|---|---|
| **User directly** | Context page save | Profile, styles, manual entries | 1.0 (user_stated) |
| **TP conversation** | Nightly cron (midnight UTC, processes yesterday's sessions) | Preferences, facts, instructions stated in chat | 0.7 (conversation) |
| **Deliverable feedback** | User approves edited version | Length preferences, format preferences from edit diffs | 0.7 (feedback) |
| **Activity patterns** | Daily background job (midnight UTC) | 5 behavioral patterns from `activity_log` | 0.6 (pattern) |

### How it works

1. **Conversation extraction** (`process_conversation()`): The nightly cron (`unified_scheduler.py`, midnight UTC) processes all TP sessions from the previous day. The Memory Service reviews each conversation and extracts facts worth remembering. This is **not** triggered at real-time session end — it's a batch job. A preference stated in a conversation today will be in working memory by the next morning.

2. **Feedback extraction** (`process_feedback()`): When a user edits and approves a deliverable, `routes/deliverables.py` triggers async memory extraction. The service analyzes diffs between draft and final content. Consistent patterns (e.g., always shortens intro, always adds bullet points) become Memory entries with `source=feedback`.

3. **Pattern detection** (`process_patterns()`): A daily job (midnight UTC) analyzes `activity_log` rows from the last 90 days. Detects 5 pattern types (ADR-070):
   - **Day-of-week**: "Typically runs deliverables on Mondays"
   - **Time-of-day**: "Typically runs deliverables in the afternoon (12pm-6pm)"
   - **Deliverable type preference**: "Frequently uses meeting_prep deliverables"
   - **Edit location patterns**: "Tends to edit intro sections when revising"
   - **Formatting length**: "Prefers concise output; typically shortens generated content"

**Never written by**: Real-time tool calls during conversation. The explicit `create_memory` tool was removed in ADR-064.

**Learning loop**: Memory extraction from deliverable feedback and activity patterns creates a **quality flywheel**: better deliverables → more usage → more pattern detection → richer Memory → better future deliverables.

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
| Can TP write Memory during conversation? | No — Memory is extracted at session end by backend jobs |
| Does the user see memory writes? | No — writes are invisible. User reviews in Context page |
| Can Memory contain platform content? | No — platform content lives in `platform_content` (Context layer) |
| Does Memory grow automatically? | Yes — through implicit extraction from conversation, deliverable feedback, and activity patterns |
| What happens when a key conflicts? | Upsert on `(user_id, key)` — last write wins |
| Is Memory persistent across sessions? | Yes — it's the only layer that is explicitly persistent and stable |
| What are the three extraction sources? | 1) Conversation (nightly batch), 2) Deliverable feedback (on approval), 3) Activity patterns (daily detection). See ADR-064. |
| Is extraction real-time? | No. Conversation/pattern extraction are batch jobs. Feedback extraction is async. All writes take effect in *next* session. |

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

- [ADR-064](../adr/ADR-064-unified-memory-service.md) — Unified Memory Service (three extraction sources)
- [ADR-070](../adr/ADR-070-enhanced-activity-pattern-detection.md) — Enhanced pattern detection (5 pattern types)
- [ADR-059](../adr/ADR-059-simplified-context-model.md) — Memory table design (user_context)
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview (bidirectional learning)
- `api/services/memory.py` — Memory extraction service (process_conversation, process_feedback, process_patterns)
- `api/services/working_memory.py` — Formats memory for prompt injection
- `api/routes/deliverables.py` — Triggers feedback extraction on approval
