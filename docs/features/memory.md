# Memory

> Layer 1 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Memory is everything YARNNN knows *about the user* — their name, role, how they like to work, facts and standing instructions they've stated. **Memory is stable, explicit, and user-owned.**

Memory formation is **implicit** — TP doesn't announce when it's remembering something. Extraction happens through conversation analysis (nightly cron). Users can also write memories directly via the Memory page.

**Analogy**: Memory is YARNNN's equivalent of Claude Code's auto-memory. The system learns from interaction and stores what's useful. Users can review and edit anytime.

**Strategic principle**: For new users (0-30 days), Memory carries the heaviest reasoning load alongside Context. For mature users (90+ days), Memory accumulates behavioral intelligence that informs Work generation quality.

---

## What it is not

- Not platform content (emails, Slack messages, Notion pages) — that is Context
- Not a log of what YARNNN has done — that is Activity
- Not generated output — that is Work
- Not visible during conversation — memory writes happen in the background
- Not agent-specific knowledge — that lives in `agent_instructions` (user-authored) and `agent_memory` (agent observations). See ADR-087.

---

## Table: `user_memory`

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

**Source values**: `user_stated` (user wrote directly), `tp_extracted` (extracted from conversation by nightly cron).

**Confidence**: `user_stated = 1.0`. All others below 1.0.

**Unique constraint**: `(user_id, key)` — one value per key per user.

---

## How Memory is written

ADR-064, ADR-087 Phase 2: Memory is written by the **User Memory Service** (`api/services/memory.py`), explicitly scoped to global (cross-agent) user knowledge.

### Write sources

| Source | Trigger | What's extracted | Confidence |
|---|---|---|---|
| **User directly** | Context page save | Profile, styles, manual entries | 1.0 (user_stated) |
| **TP conversation** | Nightly cron (midnight UTC, processes yesterday's sessions) | Preferences, facts, instructions stated in chat | 0.8 (tp_extracted) |

### How it works

**Conversation extraction** (`process_conversation()`): The nightly cron (`unified_scheduler.py`, midnight UTC) processes all TP sessions from the previous day. The User Memory Service reviews each conversation via LLM and extracts stable personal facts worth remembering. This is **not** triggered at real-time session end — it's a batch job. A preference stated in a conversation today will be in working memory by the next morning.

**What was removed** (ADR-087 Phase 2):
- `process_feedback()` — edit-diff heuristics from agent approvals. Superseded by the conversational iteration model: users refine output through TP chat and `agent_instructions`, not through approval-gate review.
- `process_patterns()` — activity log pattern detection ("runs agents on Mondays"). Marginal value, speculative inference not worth the complexity.

**Never written by**: Real-time tool calls during conversation. The explicit `create_memory` tool was removed in ADR-064.

---

## How Memory is read

At the start of every TP session, `working_memory.py → build_working_memory()` reads all `user_memory` rows and formats them into the system prompt:

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
| Can TP write Memory during conversation? | No — Memory is extracted by nightly cron, not in real-time |
| Does the user see memory writes? | No — writes are invisible. User reviews in Context page |
| Can Memory contain platform content? | No — platform content lives in `platform_content` (Context layer) |
| Does Memory grow automatically? | Yes — through implicit extraction from conversation |
| What happens when a key conflicts? | Upsert on `(user_id, key)` — last write wins, with source priority (user_stated > tp_extracted) |
| Is Memory persistent across sessions? | Yes — it's the only layer that is explicitly persistent and stable |
| What about agent-specific learning? | Agent-specific context lives in `agent_instructions` (user-authored) and `agent_memory` JSONB (observations, goal). See ADR-087. |

---

## User control

Users have full control over Memory via the **Memory page**:

- **View**: See all memories
- **Edit**: Modify any value
- **Delete**: Remove any memory
- **Add**: Create new entries manually

The system learns implicitly, but the user owns the data.

### API behavior (user-facing)

- `PATCH /api/memory/profile`: partial upsert. Omitted fields are untouched. Explicit `null` or empty string clears that field.
- `GET /api/memory/styles`: list configured platform styles.
- `GET /api/memory/styles/{platform}`: fetch one platform style state.
- `PATCH /api/memory/styles/{platform}`: partial upsert. Omitted fields are untouched. Explicit `null` or empty string clears tone/verbosity for that platform.
- `DELETE /api/memory/styles/{platform}`: clear tone + verbosity for that platform.

---

## TP behavior

TP doesn't have memory tools. It simply converses naturally:

```
User: "I prefer bullet points over prose"
TP: "Got it, I'll use bullet points going forward."
```

At session end, the backend extracts "prefers bullet points" and writes it to `user_memory`. Next session, TP knows about this preference from the working memory prompt.

If the user asks "what do you know about me?", TP can describe the working memory block injected at session start.

---

## Frontend: Memory page

The Memory page is the primary user interface for Memory. It surfaces:
- **Profile** — name, role, company, timezone, summary
- **Styles** — tone and verbosity per platform
- **Entries** — facts, instructions, preferences

Users can add, edit, and delete Memory entries directly. Changes are immediate.

---

## Related

- [ADR-064](../adr/ADR-064-unified-memory-service.md) — Unified Memory Service (original three-source design)
- [ADR-087](../adr/ADR-087-workspace-scoping-architecture.md) — Agent Scoped Context (Phase 2: simplified to conversation extraction only)
- [ADR-059](../adr/ADR-059-simplified-context-model.md) — Memory table design (user_memory)
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- `api/services/memory.py` — User Memory Service (process_conversation, get_for_prompt)
- `api/services/session_continuity.py` — Session summary generation (chat-layer, separate from memory)
- `api/services/working_memory.py` — Formats memory for prompt injection
