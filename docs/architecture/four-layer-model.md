# Four-Layer Model

> ADR-063 — Architectural overview of YARNNN's data and state model

---

## The model

YARNNN organises all persistent state into four layers. Each layer has a distinct purpose, a distinct lifecycle, and distinct access rules.

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Memory                                   │
│  What YARNNN knows about the user                   │
│  Table: user_context                                │
│  Stable · Explicit · Persistent across sessions    │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 2 — Activity                                 │
│  What YARNNN has done                               │
│  Table: activity_log                                │
│  Append-only · System-written · Non-fatal           │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 3 — Context                                  │
│  What is on the user's platforms right now          │
│  Tables: filesystem_items (cache) + live APIs       │
│  Ephemeral · Large · Platform-resident             │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│  Layer 4 — Work                                     │
│  What YARNNN produces                               │
│  Tables: deliverables, deliverable_versions         │
│  Generated · Versioned · Delivered                 │
└─────────────────────────────────────────────────────┘
```

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

**What it is**: What YARNNN produces. Scheduled digests, meeting briefs, weekly summaries, drafted emails. Every generation run creates a versioned, immutable output record.

**Tables**:
- `deliverables` — Standing configuration for a recurring output (what to read, how to format, where to send, when to run)
- `deliverable_versions` — Immutable record of each generated output (content, source_snapshots, status progression)

**How it is produced**: Headless execution triggered by `unified_scheduler.py`. Credentials decrypted from `platform_connections`. Platform data fetched live. LLM call (Claude API). Version created. Activity event written.

**Status progression**: `draft` → `staged` → `approved` → `published`

**Governance modes**:
- `manual` (default): Version is staged, user reviews and approves in the UI
- `full_auto`: Version is automatically approved and delivered without user review

**Key property**: Deliverable execution never reads `filesystem_items`. Platform data is always fetched live to ensure the output reflects actual platform state at generation time.

**Lifecycle**: Versions are immutable after generation (content does not change; `status` progresses). Versions are retained even if the parent deliverable is deleted.

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

## Boundary reference

| Question | Answer |
|---|---|
| Why does `filesystem_items` exist if deliverables use live APIs? | Cache is for conversational search (ILIKE, cross-platform, low latency). Live APIs are for authoritative point-in-time reads. Neither can replace the other. |
| Why does `activity_log` exist if `deliverable_versions` records runs? | `deliverable_versions` holds full generated content. `activity_log` holds lightweight event summaries for prompt injection. Neither replaces the other. |
| Can platform content become Memory automatically? | No. Automatic promotion was removed in ADR-059. "Promote document to Memory" is a deferred feature (ADR-062). |
| Does TP get platform content in its system prompt? | No. Context is fetched on demand via Search or tools, never pre-loaded. |
| Is Memory updated during a session? | Memory is read at session start and does not update mid-session. Memory extraction happens at session end (ADR-064), taking effect in the *next* session's working memory. |
| What happens if `write_activity()` fails? | The calling operation continues. All log writes are non-fatal by design. |
| Can a user write to `activity_log`? | No. Service-role writes only. Users can SELECT their own rows. |
| Is a `deliverable_version` mutable after generation? | The `content` field is immutable. The `status` field progresses (staged → approved → published). |

---

## Design principles

**Explicit over implicit.** Every write to Memory, Activity, and Work is an explicit operation at a known call site. No background inference, no automatic promotion, no side effects.

**Non-fatal logging.** Activity writes are wrapped in `try/except pass` everywhere. The provenance log is valuable but never mission-critical. A log failure is a missing entry in a log, not a broken pipeline.

**Separation of freshness and authority.** The cache (`filesystem_items`) is fresh enough for conversation. Live APIs are authoritative for generation. Using the cache for deliverables would introduce silent staleness risk. Using live APIs for every conversational search would be prohibitively slow.

**Immutability where it matters.** Work versions are immutable records. Activity rows are immutable. Only Memory and the deliverable `status` field are mutable — and Memory mutability is user-controlled.

**Headless execution.** Work is produced by a scheduler that runs without a user session. It depends only on credentials stored in `platform_connections`. The user does not need to be online.

---

## Related

- [ADR-059](../adr/ADR-059-simplified-context-model.md) — Memory table design, removal of inference pipeline
- [ADR-062](../adr/ADR-062-platform-context-architecture.md) — `filesystem_items` role and mandate
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Activity layer and four-layer model formalisation
- [memory.md](../features/memory.md) — Memory layer detail
- [activity.md](../features/activity.md) — Activity layer detail
- [context.md](../features/context.md) — Context layer detail
- [work.md](../features/work.md) — Work layer detail
- [context-pipeline.md](context-pipeline.md) — Technical pipeline detail for Context
- `api/services/working_memory.py` — Working memory build and format
- `api/services/activity_log.py` — `write_activity()`, `get_recent_activity()`
