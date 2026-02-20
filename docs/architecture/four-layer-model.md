# Four-Layer Model

> ADR-063 — Architectural overview of YARNNN's data and state model

---

## The model

YARNNN organises all persistent state into four layers. Each layer has a distinct purpose, lifecycle, and access rules. **The layers form both a generation pipeline (unidirectional) and a learning system (bidirectional feedback).**

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Memory                                   │
│  What the user has explicitly stated and what      │
│  YARNNN has learned about their preferences         │
│  Table: user_context                                │
│  Stable · Explicit + Implicit · Cross-session      │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 2 — Activity                                 │
│  Behavioral provenance: what YARNNN has done and   │
│  when, enabling pattern detection and recency       │
│  Table: activity_log                                │
│  Append-only · System-written · Pattern source     │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 3 — Context                                  │
│  Live platform state: the user's current work      │
│  environment and information landscape              │
│  Tables: filesystem_items (cache) + live APIs       │
│  Ephemeral · Large · Platform-authoritative        │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 4 — Work                                     │
│  Synthesized output: what YARNNN produces and      │
│  learns from through content quality assessment     │
│  Tables: deliverables, deliverable_versions         │
│  Versioned · Delivered · Learning signal source    │
└─────────────────────────────────────────────────────┘
```

### Strategic principle: Weighting shift over time

**New users** (first 30 days): Rely heavily on **L1 (Memory) + L3 (Context)** because they have little Layer 4 history. The system uses stated preferences and live platform data.

**Mature users** (90+ days): Rely increasingly on **L4 (Work)** as the system learns what quality looks like from prior deliverable versions. Layer 4 content becomes the strongest signal for what the user values.

This weighting shift is implicit in signal reasoning (ADR-069) and pattern detection (ADR-064/070).

---

## Reference models

The four-layer structure maps cleanly onto analogies from adjacent tools:

| Layer | YARNNN | Claude Code | Git |
|---|---|---|---|
| Memory | `user_context` | `CLAUDE.md` | — |
| Activity | `activity_log` | — | commit log |
| Context | `filesystem_items` + live APIs | source files on disk | working tree |
| Work | `deliverable_versions` | build output | tagged release |

**Claude Code analogy**: Memory is the `CLAUDE.md` Claude reads at startup. Context is the filesystem — files exist on disk, but only the relevant ones are opened when needed. Work is the build artifact the pipeline produces.

**Git analogy**: Activity is the commit log — it records what happened and when, without being the output itself.

---

## Layer 1 — Memory

**What it is**: Everything YARNNN knows *about the user* — name, role, preferences, stated facts, standing instructions.

**Table**: `user_context` — single flat key-value store. One row per fact.

**How it is written** — ADR-064 implicit extraction:
1. User edits directly on the Context page (Profile / Styles / Entries tabs)
2. Backend extracts from conversation at session end (implicit, no tool call)
3. Backend extracts from deliverable feedback (when user edits and approves)
4. Background job detects patterns from activity_log (daily)

**How it is read**: `working_memory.py → build_working_memory()` reads all rows at session start and injects them into the TP system prompt as the "About you / Your preferences / What you've told me" block.

**Key property**: Memory grows through implicit extraction at pipeline boundaries (ADR-064). The explicit memory tools were removed. The old inference pipeline (ADR-059) was replaced with boundary-triggered extraction.

**Lifecycle**: Persistent. Memory from six months ago is still in the prompt today unless the user or TP explicitly removes it.

---

## Layer 2 — Activity

**What it is**: The system provenance log — a record of what YARNNN has done. Answers "what happened recently?" not "what do I know?" (Memory) or "what's on the platforms?" (Context).

**Table**: `activity_log` — append-only. Four event types:

| event_type | Written by | When |
|---|---|---|
| `deliverable_run` | `deliverable_execution.py` | After version created |
| `memory_written` | `memory.py` | After `user_context` upsert (implicit extraction) |
| `platform_synced` | `platform_worker.py` | After sync batch completes |
| `chat_session` | `chat.py` | After each chat turn |

**How it is written**: Single `write_activity()` call at each write point. All calls wrapped in `try/except pass` — a log failure is never allowed to block the primary operation.

**How it is read**: `working_memory.py → _get_recent_activity()` fetches the last 10 events in the last 7 days and renders them as a "### Recent activity" block in the TP system prompt (~300 tokens of the 2,000 token working memory budget).

**Key property**: Service-role writes only. Users can SELECT their own rows via RLS, but cannot INSERT, UPDATE, or DELETE.

**Lifecycle**: Append-only, no TTL. Rows accumulate indefinitely. Typical volume: 20–40 rows/day per active user.

---

## Layer 3 — Context

**What it is**: The current working material — emails, Slack messages, Notion pages, calendar events. It is ephemeral, large, and lives on the platforms themselves. YARNNN accesses it two ways.

### Access path A — Conversational search (cache)

`filesystem_items` is a local cache of recent platform content, populated by `platform_worker.py` on a schedule. When TP calls `Search(scope="platform_content")`, it runs an ILIKE query against this table.

The cache exists because live multi-platform search during a streaming conversation would be too slow and composable cross-platform queries would be impossible.

### Access path B — Live platform APIs

Two sub-paths use live API calls:

1. **Deliverable execution** — `deliverable_pipeline.py → fetch_integration_source_data()` decrypts credentials from `platform_connections` and calls platform APIs directly at the moment of generation. No cache consulted.

2. **TP platform tools** — `platform_gmail_search`, `platform_notion_search`, `platform_calendar_list_events`, `platform_slack_list_channels`, and action tools. Targeted live calls, not cross-platform content search.

**Key property**: These two paths are completely independent. The cache and live APIs serve different purposes and cannot replace each other.

| | Cache (`filesystem_items`) | Live APIs |
|---|---|---|
| Used for | `Search(scope="platform_content")` | Deliverable execution, TP platform tools |
| Freshness | Tier-dependent (2–24h stale) | Always current |
| Authority | No — convenience index | Yes — direct from platform |

**Lifecycle**: TTL-based. Slack items expire after 72 hours; Gmail/Notion/Calendar after 168 hours. Refreshed on each sync run.

---

## Layer 4 — Work

**What it is**: What YARNNN produces. Scheduled digests, meeting briefs, weekly summaries, drafted emails. Every generation run creates a versioned, immutable output record. **Layer 4 is both the output of the system and a learning signal for future work quality.**

**Tables**:
- `deliverables` — Standing configuration for a recurring output (what to read, how to format, where to send, when to run)
- `deliverable_versions` — Immutable record of each generated output (content, source_snapshots, status progression, edit history)

**How it is produced**: Headless execution triggered by `unified_scheduler.py`. Credentials decrypted from `platform_connections`. Platform data fetched live. LLM call (Claude API). Version created. Activity event written.

**Three origins** (ADR-068):
- `user_configured` — Explicitly created by user in UI or via TP
- `analyst_suggested` — Detected from TP conversation patterns (ADR-060)
- `signal_emergent` — Created by signal processing from behavioral signals (ADR-068)

**Status progression**: `generating` → `delivered` (ADR-066 simplified flow)

**Key properties**:
1. **Live platform reads**: Deliverable execution never reads `filesystem_items`. Platform data is always fetched live to ensure output reflects actual platform state at generation time.

2. **Content as learning signal** (ADR-069): Recent deliverable version content (400-char preview) is included in signal reasoning prompts. This enables the LLM to assess whether existing deliverables are stale or still current, improving `trigger_existing` vs `create_signal_emergent` decisions.

3. **Feedback extraction** (ADR-064): When users approve edited versions, the system extracts learning patterns (length preferences, format preferences) to Memory layer.

**Lifecycle**: Versions are immutable after generation (content does not change; `status` may progress). Versions are retained even if the parent deliverable is deleted. Deliverables can be promoted from one-time (`signal_emergent`) to recurring (`user_configured`).

---

## Cross-layer interaction

The layers interact in a defined, unidirectional way. Data flows in one direction; no layer writes upward into a "higher" layer.

```
                    TP session start
                          │
                          ▼
        ┌─────── build_working_memory() ────────┐
        │                                       │
        │  reads Memory (user_context)          │
        │  reads Activity (last 10 events)      │
        │                                       │
        └──────────────►  TP system prompt ◄────┘

                    During conversation
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
           Search tool        Platform tools
      (filesystem_items       (live Gmail /
        ILIKE cache)           Notion / etc.)
              │
              │ reads Context

                    Deliverable execution
                          │
              decrypts platform_connections
                          │
              fetches live platform APIs  ──► reads Context (live)
                          │
                    LLM call
                          │
              creates deliverable_version ──► writes Work
                          │
              write_activity()            ──► writes Activity
```

**What never happens**:
- Memory is written by backend extraction at session end (ADR-064), not by TP tool calls
- Activity is never written by user-facing clients
- Deliverable execution never reads `filesystem_items`
- Context (platform content) is never pre-loaded into the TP system prompt

---

## Bidirectional learning loops

While data flows **unidirectionally downward** for generation (Memory → Activity → Context → Work), **learning flows upward** through feedback loops that improve future quality:

```
┌──────────────────────────────────────────────────────────────┐
│                    GENERATION (Downward)                      │
│                                                               │
│   Memory (L1) ───────┐                                       │
│                      │                                       │
│   Activity (L2) ─────┤                                       │
│                      ├──► Signal Processing ──► Work (L4)   │
│   Context (L3) ──────┘     (ADR-068/069)                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    LEARNING (Upward)                          │
│                                                               │
│   Work (L4) ─────► Deliverable Feedback ──► Memory (L1)     │
│                    (ADR-064: process_feedback)                │
│                                                               │
│   Work (L4) ─────► Content Quality Signal ──► Signal (L4)   │
│                    (ADR-069: recent_content in reasoning)     │
│                                                               │
│   Activity (L2) ──► Pattern Detection ────► Memory (L1)     │
│                    (ADR-064/070: process_patterns)            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Three feedback mechanisms (ADR-064 completion)

1. **Deliverable feedback loop** (Work → Memory)
   - When: User approves edited deliverable version
   - What: `process_feedback()` analyzes diff between draft and final
   - Writes: Length preferences, format preferences to `user_context`
   - Source: `feedback` (confidence: 0.7)

2. **Pattern detection loop** (Activity → Memory)
   - When: Daily at midnight UTC for all users
   - What: `process_patterns()` detects 5 behavioral patterns from activity_log
   - Writes: Day/time preferences, type preferences, edit/format patterns
   - Source: `pattern` (confidence: 0.6)

3. **Content quality signal** (Work → Work)
   - When: Signal processing runs (hourly/daily)
   - What: Recent deliverable content included in signal reasoning prompts
   - Effect: LLM assesses whether existing deliverables still address current signals
   - Enables: Smart `trigger_existing` vs `create_signal_emergent` decisions

### Key insight: Layer 4 is both output and input

Layer 4 serves dual purpose:
- **Output**: Versioned work products delivered to users
- **Input**: Training signal for what quality looks like (recency, edits, staleness)

The more deliverables a user runs, the more the system learns what they value. This creates a **quality flywheel**: better deliverables → more usage → more learning → better deliverables.

---

## Boundary reference

| Question | Answer |
|---|---|
| Why does `filesystem_items` exist if deliverables use live APIs? | Cache is for conversational search (ILIKE, cross-platform, low latency). Live APIs are for authoritative point-in-time reads. Neither can replace the other. |
| Why does `activity_log` exist if `deliverable_versions` records runs? | `deliverable_versions` holds full generated content. `activity_log` holds lightweight event summaries for prompt injection and pattern detection. Neither replaces the other. |
| Can platform content become Memory automatically? | No. Automatic promotion was removed in ADR-059. "Promote document to Memory" is a deferred feature (ADR-062). |
| Does TP get platform content in its system prompt? | No. Context is fetched on demand via Search or tools, never pre-loaded. |
| Is Memory updated during a session? | Memory is read at session start and does not update mid-session. Memory extraction happens at session end or via background jobs (ADR-064), taking effect in the *next* session's working memory. |
| What happens if `write_activity()` fails? | The calling operation continues. All log writes are non-fatal by design. |
| Can a user write to `activity_log`? | No. Service-role writes only. Users can SELECT their own rows. |
| Is a `deliverable_version` mutable after generation? | The `final_content` field is immutable. The `status` field progresses (generating → delivered). |
| How does Layer 4 content influence future work? | Recent deliverable version content (400-char preview) is included in signal reasoning prompts (ADR-069). This enables quality-aware orchestration decisions. |
| What are the three memory extraction sources? | 1) Conversation (nightly batch), 2) Deliverable feedback (on approval), 3) Activity patterns (daily detection). See ADR-064. |
| Is signal processing real-time? | No. Signals are extracted on cron schedule (hourly for calendar, daily for silence). Near-real-time via webhooks is future work. |
| Can signal-emergent deliverables become recurring? | Yes. Deliverables can be promoted from one-time (`origin=signal_emergent`, no schedule) to recurring (add schedule). Origin field preserves provenance. |

---

## Design principles

**Unidirectional generation, bidirectional learning.** Data flows downward (L1→L2→L3→L4) for generation. Learning flows upward (L4→L1, L2→L1) through feedback loops. This separation enables predictable generation while allowing quality improvement over time.

**Explicit writes at boundaries.** Every write to Memory, Activity, and Work happens at a known boundary: session end, deliverable approval, pattern detection cron. No scattered inference, no automatic promotion mid-operation.

**Non-fatal logging.** Activity writes are wrapped in `try/except pass` everywhere. The provenance log is valuable but never mission-critical. A log failure is a missing entry, not a broken pipeline.

**Separation of freshness and authority.** The cache (`filesystem_items`) is fresh enough for conversation. Live APIs are authoritative for generation. Using the cache for deliverables would introduce silent staleness risk. Using live APIs for every conversational search would be prohibitively slow.

**Immutability where it matters.** Work versions are immutable records. Activity rows are immutable. Only Memory and deliverable metadata are mutable — and Memory mutability is boundary-controlled (extraction happens at defined points, not arbitrarily).

**Headless execution.** Work is produced by a scheduler that runs without a user session. It depends only on credentials stored in `platform_connections`. The user does not need to be online.

**Quality flywheel through Layer 4.** The more deliverables a user runs, the more the system learns what they value. Layer 4 content becomes training signal for future work. This creates a feedback loop: better deliverables → more usage → more learning → better deliverables.

---

## Related

- [ADR-059](../adr/ADR-059-simplified-context-model.md) — Memory table design, removal of inference pipeline
- [ADR-062](../adr/ADR-062-platform-context-architecture.md) — `filesystem_items` role and mandate
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Activity layer and four-layer model formalisation
- [memory.md](../features/memory.md) — Memory layer detail
- [activity.md](../features/activity.md) — Activity layer detail
- [context.md](../features/context.md) — Context layer detail
- [deliverables.md](../features/deliverables.md) — Deliverables layer detail
- [context-pipeline.md](context-pipeline.md) — Technical pipeline detail for Context
- `api/services/working_memory.py` — Working memory build and format
- `api/services/activity_log.py` — `write_activity()`, `get_recent_activity()`
