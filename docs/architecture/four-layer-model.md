# Four-Layer Model

> ADR-063 — Architectural overview of YARNNN's data and state model
> **Updated**: 2026-02-26 — ADR-080 unified agent modes, corrected execution model, TTL values

---

## The model

YARNNN organises all persistent state into four layers. Each layer has a distinct purpose, lifecycle, and access rules. **The layers form both a generation pipeline (unidirectional) and a learning system (bidirectional feedback).**

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Memory                                   │
│  What the user has explicitly stated and what      │
│  YARNNN has learned about their preferences         │
│  Table: user_context (with source_ref provenance)   │
│  Stable · Explicit + Implicit · Auditable          │
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
│  Platform content with retention-based accumulation │
│  Table: platform_content (ADR-072)                  │
│  Versioned · Retention-policy-driven · Semantic    │
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
| Context | `platform_content` (unified layer) | source files on disk | working tree |
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

> **ADR-072 UPDATE**: Layer 3 is now the **unified content layer** (`platform_content`), replacing the previous `filesystem_items` cache. Content is retention-policy-driven rather than TTL-only.

**What it is**: Platform content — emails, Slack messages, Notion pages, calendar events — with **retention-based accumulation**. Content that proves significant (referenced by deliverables, signal processing, or TP sessions) is retained indefinitely. Unreferenced content expires after TTL.

**Table**: `platform_content` — versioned, semantically indexed, retention-policy-driven.

### The Unified Content Model (ADR-072)

```
┌─────────────────────────────────────────────────────────────┐
│                    platform_content                          │
│                                                              │
│  Ephemeral content          │   Retained content            │
│  (retained=false)           │   (retained=true)             │
│  ───────────────────────    │   ─────────────────────────   │
│  • Expires after TTL        │   • Never expires             │
│  • Synced by platform_worker│   • Marked by signal proc,    │
│  • Most content starts here │     deliverable exec, or TP   │
│  • Never referenced         │   • Accumulates over time     │
│                             │   • The compounding moat      │
└─────────────────────────────────────────────────────────────┘
```

### Two writers to `platform_content`

**Platform Sync** (`platform_worker.py`):
- Runs continuously on tier-appropriate frequency
- Fetches content from external platforms
- Writes with `retained=false`, `expires_at=NOW()+TTL`
- Knows nothing about significance — just syncs

**Signal Processing** (`signal_extraction.py`):
- Reads live platform APIs for time-sensitive signals
- When it identifies significant content, writes directly with `retained=true`
- Sets `retained_reason='signal_processing'`, `retained_ref=signal_action_id`

Additionally, **Deliverable Execution** and **TP Sessions** mark existing records as retained after use.

### Retention policy

| Condition | `retained` | `expires_at` | Outcome |
|---|---|---|---|
| Content never referenced | `false` | `NOW() + TTL` | Expires after TTL |
| Referenced by deliverable_version | `true` | `NULL` | Retained indefinitely |
| Referenced by signal_processing | `true` | `NULL` | Retained indefinitely |
| Accessed during TP session | `true` | `NULL` | Retained indefinitely |

**TTL by platform** (for unreferenced content, ADR-077):
- Slack: 14 days
- Gmail: 30 days
- Notion: 90 days
- Calendar: 2 days

### How content is accessed

**Two access paths exist:**

**TP sessions** use primitives for on-demand content retrieval:
- `Search(scope="platform_content")` — semantic search via pgvector embeddings
- `FetchPlatformContent` — targeted retrieval by resource
- `CrossPlatformQuery` — multi-platform search

**Deliverable execution** uses the orchestration pipeline (ADR-045) for context gathering: `get_content_summary_for_generation()` fetches content chronologically from `platform_content`, formatted with signal markers. The agent in headless mode (ADR-080) then generates content with access to curated read-only primitives for supplementary investigation.

**Signal processing** reads from `platform_content` (ADR-073) for behavioral signal extraction, then can create or trigger deliverables based on what it observes.

### The accumulation moat

Over time, `platform_content` accumulates retained records that represent the user's **significant work history**:
- Slack threads that informed weekly digests
- Email exchanges that became client briefs
- Calendar events that triggered meeting prep

This is the content that proved its value through downstream consumption. It compounds intelligence. It is the moat.

**Key insight**: Don't accumulate everything. Don't expire everything. **Accumulate what proved significant.**

---

## Layer 4 — Work

**What it is**: What YARNNN produces. Scheduled digests, meeting briefs, weekly summaries, drafted emails. Every generation run creates a versioned, immutable output record. **Layer 4 is both the output of the system and a learning signal for future work quality.**

**Tables**:
- `deliverables` — Standing configuration for a recurring output (what to read, how to format, where to send, when to run)
- `deliverable_versions` — Immutable record of each generated output (content, source_snapshots with `platform_content_ids`, status progression)

### Unified Agent in Headless Mode (ADR-080)

Deliverable execution uses the **unified agent in headless mode** — the same agent that powers TP chat, with a curated subset of read-only primitives and a structured output prompt. The orchestration pipeline (strategy selection, delivery, retention) wraps the agent invocation.

| Aspect | Chat Mode (TP) | Headless Mode (Deliverables) |
|---|---|---|
| **Content access** | On-demand via full primitive set | Strategy-gathered baseline + curated primitives for investigation |
| **Reasoning** | Iterative tool-use loop (up to 15 rounds) | Bounded investigation (up to 3 rounds) |
| **User context** | Full working memory in system prompt | Memories appended to generation context |
| **Primitives** | Full set (read + write + action) | Read-only subset (Search, FetchPlatformContent, CrossPlatformQuery) |

**How it is produced**: Triggered by `unified_scheduler.py` → `execute_deliverable_generation()`. Strategy gathers context from `platform_content`. `build_type_prompt()` assembles type-specific prompt. Agent (headless mode) generates via `chat_completion_with_tools()` — can supplement gathered context with primitive calls (max 3 tool rounds). Version created with `platform_content_ids` in source_snapshots. Source content marked `retained=true`. Delivered immediately (ADR-066). Activity event written.

**Three origins** (ADR-068):
- `user_configured` — Explicitly created by user in UI or via TP
- `analyst_suggested` — Detected from TP conversation patterns (ADR-060)
- `signal_emergent` — Created by signal processing from behavioral signals (ADR-068)

**Status progression**: `generating` → `delivered` (ADR-066 simplified flow)

**Key properties**:
1. **Provenance closure**: `source_snapshots` now includes `platform_content_ids[]` — specific record IDs that were synthesized. This answers "what content informed this deliverable?"

2. **Content as learning signal** (ADR-069): Recent deliverable version content (400-char preview) is included in signal reasoning prompts. This enables the LLM to assess whether existing deliverables are stale or still current.

3. **Feedback extraction** (ADR-064): When users approve edited versions, the system extracts learning patterns (length preferences, format preferences) to Memory layer.

4. **Retention marking**: After generation, source `platform_content` records are marked `retained=true`, `retained_reason='deliverable_execution'`, `retained_ref=version_id`. This is how significant content accumulates.

**Lifecycle**: Versions are immutable after generation (content does not change; `status` may progress). Versions are retained even if the parent deliverable is deleted. Deliverables can be promoted from one-time (`signal_emergent`) to recurring (`user_configured`).

---

## Cross-layer interaction

The layers interact in defined ways. Data flows downward for generation; learning flows upward through feedback loops.

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
                          ▼
                    TP Primitives
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
      Search         FetchContent    CrossPlatformQuery
         │                │                │
         └────────────────┴────────────────┘
                          │
                          ▼
               reads platform_content (L3)
                          │
            marks accessed records retained=true

                    Deliverable execution (ADR-045 + ADR-080)
                          │
              Strategy gathers context
                          │
         get_content_summary_for_generation()
                          │
               reads platform_content (L3)
                          │
              Agent (headless mode) generates
               + can call Search, Fetch primitives
                          │
              creates deliverable_version ──► writes Work (L4)
                          │
         marks source records retained=true ──► updates Context (L3)
                          │
         source_snapshots includes platform_content_ids
                          │
              write_activity()            ──► writes Activity (L2)

                    Signal processing
                          │
              reads platform_content (L3)
                          │
         LLM reasoning (Haiku): what warrants action?
                          │
         creates/triggers deliverables    ──► writes Work (L4)
                          │
         marks significant content retained ──► updates Context (L3)
```

**What never happens**:
- Memory is written by backend extraction at session end (ADR-064), not by TP tool calls
- Activity is never written by user-facing clients
- Context (platform content) is never pre-loaded into the TP system prompt

**What now happens** (ADR-072, ADR-073, ADR-080):
- TP sessions (chat mode) mark accessed `platform_content` records as retained
- Deliverable execution uses strategy pipeline (ADR-045) for context gathering, then agent in headless mode (ADR-080) generates with curated primitives
- Signal processing reads `platform_content` (ADR-073), marks significant content as retained; signal reasoning forwarded to headless mode (ADR-080)
- `source_snapshots` includes specific `platform_content_ids` for provenance

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
| What is `platform_content`? | The unified content layer (ADR-072). Replaces `filesystem_items`. Versioned, retention-policy-driven, semantically indexed. |
| How does retention work? | Content starts with `retained=false` and TTL expiry. When referenced (by deliverable, signal processing, or TP session), marked `retained=true` and never expires. |
| Why does `activity_log` exist if `deliverable_versions` records runs? | `deliverable_versions` holds full generated content. `activity_log` holds lightweight event summaries for prompt injection and pattern detection. Neither replaces the other. |
| Does TP get platform content in its system prompt? | No. Context is fetched on demand via primitives, never pre-loaded. |
| Is Memory updated during a session? | Memory is read at session start and does not update mid-session. Memory extraction happens at session end or via background jobs (ADR-064), taking effect in the *next* session's working memory. |
| What is `source_ref` on `user_context`? | Provenance tracking (ADR-072). Every memory entry links to its origin (session_message, deliverable_version, platform_content, activity_log). |
| How does deliverable execution work? | Orchestration pipeline (ADR-045): strategy gathers content from `platform_content`, `build_type_prompt()` assembles prompt, agent (headless mode, ADR-080) generates draft with curated primitives, delivered immediately (ADR-066). |
| What happens if `write_activity()` fails? | The calling operation continues. All log writes are non-fatal by design. |
| Can a user write to `activity_log`? | No. Service-role writes only. Users can SELECT their own rows. |
| Is a `deliverable_version` mutable after generation? | The `final_content` field is immutable. The `status` field progresses (generating → delivered). |
| How does Layer 4 content influence future work? | Recent deliverable version content (400-char preview) is included in signal reasoning prompts (ADR-069). This enables quality-aware orchestration decisions. |
| What are the three memory extraction sources? | 1) Conversation (nightly batch), 2) Deliverable feedback (on approval), 3) Activity patterns (daily detection). See ADR-064. |
| Is signal processing real-time? | No. Signals are extracted on cron schedule (hourly). Near-real-time via webhooks is future work. |
| Does signal processing write to `platform_content`? | Signal processing reads from `platform_content` (ADR-073) and marks significant content as `retained=true`. It can also create or trigger deliverables based on observed patterns. |
| Can signal-emergent deliverables become recurring? | Yes. Deliverables can be promoted from one-time (`origin=signal_emergent`, no schedule) to recurring (add schedule). Origin field preserves provenance. |
| What is the "accumulation moat"? | Retained `platform_content` accumulates over time — the content that proved significant through downstream consumption. This is the compounding intelligence layer that makes YARNNN's outputs improve with tenure. |

---

## Design principles

**Unidirectional generation, bidirectional learning.** Data flows downward (L1→L2→L3→L4) for generation. Learning flows upward (L4→L1, L2→L1) through feedback loops. This separation enables predictable generation while allowing quality improvement over time.

**Explicit writes at boundaries.** Every write to Memory, Activity, and Work happens at a known boundary: session end, deliverable approval, pattern detection cron. No scattered inference, no automatic promotion mid-operation.

**Non-fatal logging.** Activity writes are wrapped in `try/except pass` everywhere. The provenance log is valuable but never mission-critical. A log failure is a missing entry, not a broken pipeline.

**Retention-based accumulation.** (ADR-072) Content that proves significant is retained indefinitely. Significance is determined by downstream consumption: if a deliverable used it, a signal identified it, or a TP session accessed it, the content is retained. Unreferenced content expires. This is how the accumulation moat compounds without infinite storage growth.

**Immutability where it matters.** Work versions are immutable records. Activity rows are immutable. Retained `platform_content` records are immutable (their `retained` flag can be set to true, never back to false). Only Memory and deliverable metadata are mutable — and Memory mutability is boundary-controlled.

**Unified agent, separate orchestration.** (ADR-080) One agent with two modes: chat (TP, streaming, full primitives) and headless (background, non-streaming, curated read-only primitives). Primitive updates improve both modes. Orchestration (scheduling, delivery, retention) remains separate from the agent.

**Quality flywheel through Layer 4.** The more deliverables a user runs, the more the system learns what they value. Layer 4 content becomes training signal for future work. This creates a feedback loop: better deliverables → more usage → more learning → better deliverables.

**Provenance everywhere.** (ADR-072) Every deliverable version links to specific `platform_content_ids`. Every memory entry has a `source_ref`. The system can answer "what informed this output?" at every layer.

---

## Related

**Core ADRs**:
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Activity layer and four-layer model formalisation
- [ADR-072](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — Unified content layer and TP execution pipeline (current governing ADR for Layer 3 and Layer 4 execution)
- [ADR-080](../adr/ADR-080-unified-agent-modes.md) — Unified agent with chat and headless modes

**Superseded ADRs** (historical context only):
- [ADR-049](../adr/ADR-049-context-freshness-model-SUPERSEDED.md) — Superseded by ADR-072 (retention-based accumulation replaces TTL-only)
- [ADR-062](../adr/ADR-062-platform-context-architecture-SUPERSEDED.md) — Superseded by ADR-072 (unified content layer replaces filesystem_items cache)

**Layer-specific ADRs**:
- [ADR-059](../adr/ADR-059-simplified-context-model.md) — Memory table design
- [ADR-064](../adr/ADR-064-unified-memory-service.md) — Implicit memory extraction
- [ADR-068](../adr/ADR-068-signal-emergent-deliverables.md) — Signal processing and deliverable origins
- [ADR-069](../adr/ADR-069-layer-4-content-in-signal-reasoning.md) — Layer 4 content in signal reasoning
- [ADR-071](../adr/ADR-071-strategic-architecture-principles.md) — Strategic architecture principles

**Architecture docs**:
- [deliverables.md](deliverables.md) — Deliverables architecture
- [context-pipeline.md](context-pipeline.md) — Technical pipeline detail for Context

**Implementation**:
- `api/services/working_memory.py` — Working memory build and format
- `api/services/activity_log.py` — `write_activity()`, `get_recent_activity()`
- `api/services/platform_content.py` — (ADR-072) Unified content layer (replaces `filesystem.py`)
