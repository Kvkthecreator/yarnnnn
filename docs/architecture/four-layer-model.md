# Four-Layer Model

> ADR-063 — Architectural overview of YARNNN's data and state model
> **Updated**: 2026-02-26 — ADR-080 unified agent modes, corrected execution model, TTL values

---

## The model

YARNNN organises all persistent state into four layers. Each layer has a distinct purpose, lifecycle, and access rules. **The layers form both a generation pipeline (unidirectional) and a learning system (bidirectional feedback).**

> **ADR-092 update (2026-03-04):** L3 is now genuinely dumb — platform sync writes, downstream consumers mark content retained. Signal processing as a separate L3-level reasoning subsystem is dissolved. Agent intelligence (proactive, reactive, coordinator modes) lives entirely in L4. See [ADR-092](../adr/ADR-092-agent-intelligence-mode-taxonomy.md).

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Memory                                   │
│  What the user has explicitly stated and what      │
│  YARNNN has learned about their preferences         │
│  Table: user_memory (with source_ref provenance)   │
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
│  Tables: agents, agent_runs         │
│  Versioned · Delivered · Learning signal source    │
└─────────────────────────────────────────────────────┘
```

### Strategic principle: Weighting shift over time

**New users** (first 30 days): Rely heavily on **L1 (Memory) + L3 (Context)** because they have little Layer 4 history. The system uses stated preferences and live platform data.

**Mature users** (90+ days): Rely increasingly on **L4 (Work)** as the system learns what quality looks like from prior agent versions. Layer 4 content becomes the strongest signal for what the user values.

This weighting shift is implicit in signal reasoning (ADR-069) and pattern detection (ADR-064/070).

---

## Reference models

The four-layer structure maps cleanly onto analogies from adjacent tools:

| Layer | YARNNN | Claude Code | Git |
|---|---|---|---|
| Memory | `user_memory` | `CLAUDE.md` | — |
| Activity | `activity_log` | — | commit log |
| Context | `platform_content` (unified layer) | source files on disk | working tree |
| Work | `agent_runs` | build output | tagged release |

**Claude Code analogy**: Memory is the `CLAUDE.md` Claude reads at startup. Context is the filesystem — files exist on disk, but only the relevant ones are opened when needed. Work is the build artifact the pipeline produces.

**Git analogy**: Activity is the commit log — it records what happened and when, without being the output itself.

---

## Layer 1 — Memory

**What it is**: Everything YARNNN knows *about the user* — name, role, preferences, stated facts, standing instructions.

**Table**: `user_memory` — single flat key-value store. One row per fact.

**How it is written** — ADR-064 implicit extraction:
1. User edits directly on the Context page (Profile / Styles / Entries tabs)
2. Backend extracts from conversation at session end (implicit, no tool call)
3. Backend extracts from agent feedback (when user edits and approves)
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
| `agent_run` | `agent_execution.py` | After version created |
| `memory_written` | `memory.py` | After `user_memory` upsert (implicit extraction) |
| `platform_synced` | `platform_worker.py` | After sync batch completes |
| `chat_session` | `chat.py` | After each chat turn |

**How it is written**: Single `write_activity()` call at each write point. All calls wrapped in `try/except pass` — a log failure is never allowed to block the primary operation.

**How it is read**: `working_memory.py → _get_recent_activity()` fetches the last 10 events in the last 7 days and renders them as a "### Recent activity" block in the TP system prompt (~300 tokens of the 2,000 token working memory budget).

**Key property**: Service-role writes only. Users can SELECT their own rows via RLS, but cannot INSERT, UPDATE, or DELETE.

**Lifecycle**: Append-only, no TTL. Rows accumulate indefinitely. Typical volume: 20–40 rows/day per active user.

---

## Layer 3 — Context

> **ADR-072 UPDATE**: Layer 3 is now the **unified content layer** (`platform_content`), replacing the previous `filesystem_items` cache. Content is retention-policy-driven rather than TTL-only.

**What it is**: Platform content — emails, Slack messages, Notion pages, calendar events — with **retention-based accumulation**. Content that proves significant (referenced by agents, signal processing, or TP sessions) is retained indefinitely. Unreferenced content expires after TTL.

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
│  • Most content starts here │     agent exec, or TP   │
│  • Never referenced         │   • Accumulates over time     │
│                             │   • The compounding moat      │
└─────────────────────────────────────────────────────────────┘
```

### Writers to `platform_content`

**Platform Sync** (`platform_worker.py`):
- Runs continuously on tier-appropriate frequency
- Fetches content from external platforms
- Writes with `retained=false`, `expires_at=NOW()+TTL`
- Knows nothing about significance — just syncs. L3 does not reason.

**Agent Execution** marks existing records as `retained=true` after consuming them, and writes agent outputs as new `platform_content` rows with `platform="yarnnn"`, `retained=true` (ADR-102). This closes the accumulation loop — L4 outputs flow back into L3 as searchable context.

**TP Sessions** mark existing records as `retained=true` after consuming them.

> **ADR-092:** Signal processing no longer writes to `platform_content`. It was an L3-level reasoning subsystem that violated the layer boundary. That capability moves into L4 coordinator agents.

### Retention policy

| Condition | `retained` | `expires_at` | Outcome |
|---|---|---|---|
| Content never referenced | `false` | `NOW() + TTL` | Expires after TTL |
| Referenced by agent_version | `true` | `NULL` | Retained indefinitely |
| Accessed during TP session | `true` | `NULL` | Retained indefinitely |

**TTL by platform** (for unreferenced content, ADR-077):
- Slack: 14 days
- Gmail: 30 days
- Notion: 90 days
- Calendar: 2 days
- yarnnn: Always retained (ADR-102 — agent outputs never expire)

### How content is accessed

**Two access paths exist:**

**TP sessions** use primitives for on-demand content retrieval:
- `Search(scope="platform_content")` — semantic search via pgvector embeddings
- `FetchPlatformContent` — targeted retrieval by resource
- `CrossPlatformQuery` — multi-platform search

**Agent execution** uses the orchestration pipeline (ADR-045) for context gathering: `get_content_summary_for_generation()` fetches content chronologically from `platform_content`, formatted with signal markers. The agent in headless mode (ADR-080) then generates content with access to curated read-only primitives for supplementary investigation.

**Coordinator agents** (ADR-092, `mode=coordinator`) read `platform_content` via headless mode primitives and can create or advance child agents based on what they find — but this is L4 intelligence, not L3 infrastructure.

### The accumulation moat

Over time, `platform_content` accumulates retained records that represent the user's **significant work history**:
- Slack threads that informed weekly digests
- Email exchanges that became client briefs
- Calendar events that triggered meeting prep
- Agent outputs that become context for future work (`platform="yarnnn"`, ADR-102)

This is the content that proved its value through downstream consumption — plus generated content that feeds back into the intelligence loop. It compounds. It is the moat.

**Key insight**: Don't accumulate everything. Don't expire everything. **Accumulate what proved significant** — and what YARNNN itself produces.

---

## Layer 4 — Work

**What it is**: What YARNNN produces. Scheduled digests, meeting briefs, weekly summaries, drafted emails. Every generation run creates a versioned, immutable output record. **Layer 4 is both the output of the system and a learning signal for future work quality.**

**Tables**:
- `agents` — Standing configuration for a recurring output (what to read, how to format, where to send, when to run)
- `agent_runs` — Immutable record of each generated output (content, source_snapshots with `platform_content_ids`, status progression)

### Unified Agent in Headless Mode (ADR-080)

Agent execution uses the **unified agent in headless mode** — the same agent that powers TP chat, with a curated subset of read-only primitives and a structured output prompt. The orchestration pipeline (strategy selection, delivery, retention) wraps the agent invocation.

| Aspect | Chat Mode (TP) | Headless Mode (Agents) |
|---|---|---|
| **Content access** | On-demand via full primitive set | Strategy-gathered baseline + curated primitives for investigation |
| **Reasoning** | Iterative tool-use loop (up to 15 rounds) | Bounded investigation (up to 3 rounds) |
| **User context** | Full working memory in system prompt | Memories appended to generation context |
| **Primitives** | Full set (read + write + action) | Read-only subset (Search, FetchPlatformContent, CrossPlatformQuery) |

**How it is produced**: Triggered by `unified_scheduler.py` → `execute_agent_generation()`. Strategy gathers context from `platform_content`. `build_type_prompt()` assembles type-specific prompt. Agent (headless mode) generates via `chat_completion_with_tools()` — can supplement gathered context with primitive calls (max 3 tool rounds). Version created with `platform_content_ids` in source_snapshots. Source content marked `retained=true`. Delivered immediately (ADR-066). Activity event written.

**Three origins** (ADR-068):
- `user_configured` — Explicitly created by user in UI or via TP
- `analyst_suggested` — Detected from TP conversation patterns (ADR-060)
- `signal_emergent` — Created by signal processing from behavioral signals (ADR-068)

**Status progression**: `generating` → `delivered` (ADR-066 simplified flow)

**Agent intelligence model (ADR-101)**: Each agent carries four layers of knowledge — Skills (type-specific format), Directives (user instructions + audience), Memory (observations, goals, review log), and Feedback (edit patterns from user corrections). These compose into the headless agent's system prompt. See [ADR-101](../adr/ADR-101-agent-intelligence-model.md).

**Key properties**:
1. **Provenance closure**: `source_snapshots` now includes `platform_content_ids[]` — specific record IDs that were synthesized. This answers "what content informed this agent?"

2. **Content as learning signal** (ADR-069): Recent agent version content (400-char preview) is included in signal reasoning prompts. This enables the LLM to assess whether existing agents are stale or still current.

3. **Feedback loop** (ADR-101): When users edit delivered versions, `feedback_engine.py` computes edit metrics (distance score, categories). `get_past_versions_context()` aggregates these into "learned preferences" injected into the headless system prompt. The status filter includes both `approved` and `delivered` versions.

4. **Retention marking**: After generation, source `platform_content` records are marked `retained=true`, `retained_reason='agent_execution'`, `retained_ref=version_id`. This is how significant content accumulates.

**Lifecycle**: Versions are immutable after generation (content does not change; `status` may progress). Versions are retained even if the parent agent is deleted. Agents can be promoted from one-time (`signal_emergent`) to recurring (`user_configured`).

---

## Cross-layer interaction

The layers interact in defined ways. Data flows downward for generation; learning flows upward through feedback loops.

```
                    TP session start
                          │
                          ▼
        ┌─────── build_working_memory() ────────┐
        │                                       │
        │  reads Memory (user_memory)          │
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

                    Agent execution (ADR-045 + ADR-080)
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
              creates agent_version ──► writes Work (L4)
                          │
         marks source records retained=true ──► updates Context (L3)
                          │
         source_snapshots includes platform_content_ids
                          │
              write_activity()            ──► writes Activity (L2)

                    Coordinator/Proactive agent (ADR-092)
                          │
              Scheduler: proactive_next_review_at
                          │
              Agent (headless mode) — review pass
               reads platform_content via primitives
                          │
         observe / generate / create_child / advance_schedule
                          │
         creates child agents       ──► writes Work (L4)
                          │
         marks consumed content retained  ──► updates Context (L3)
```

**What never happens**:
- Memory is written by backend extraction at session end (ADR-064), not by TP tool calls
- Activity is never written by user-facing clients
- Context (platform content) is never pre-loaded into the TP system prompt

**What now happens** (ADR-072, ADR-080, ADR-092):
- TP sessions (chat mode) mark accessed `platform_content` records as retained
- Agent execution uses strategy pipeline (ADR-045) for context gathering, then agent in headless mode (ADR-080) generates with curated primitives
- Coordinator and proactive agents (ADR-092) review their domain via headless primitives; create or advance child agents when warranted; mark consumed content retained
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
│                      ├──► Agent Execution ──► Work (L4)│
│   Context (L3) ──────┘     (ADR-045/080/092)                 │
│                                                               │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    LEARNING (Upward)                          │
│                                                               │
│   Chat (TP) ─────► Conversation Extraction ──► Memory (L1)  │
│                    (ADR-064: nightly cron)                    │
│                                                               │
│   Chat (TP) ─────► Conversational Iteration ──► Instructions │
│                    (ADR-087: agent_instructions)        │
│                                                               │
│   Work (L4) ─────► Content Quality Signal ──► Signal (L4)   │
│                    (ADR-069: recent_content in reasoning)     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Feedback mechanisms

1. **Conversation extraction** (Chat → Memory)
   - When: Nightly cron (midnight UTC) processes prior day's sessions
   - What: `process_conversation()` extracts stable personal facts via LLM
   - Writes: Preferences, facts, instructions to `user_memory`
   - Source: `tp_extracted` (confidence: 0.8)

2. **Conversational iteration** (Chat → Instructions)
   - When: User chats with TP about a agent, refining how it should work
   - What: User updates `agent_instructions` based on conversation
   - Writes: Behavioral directives directly to `agents.agent_instructions`
   - ADR-087: Replaces the old approval-gate feedback model

3. **Content quality signal** (Work → Work)
   - When: Coordinator/proactive agent review pass runs
   - What: Recent agent content included in review prompt context
   - Effect: Agent assesses whether existing agents are current or if new work is warranted
   - Enables: Smart `advance_schedule` vs `create_child` vs `observe` decisions (ADR-092)

**Removed** (ADR-087 Phase 2): `process_feedback()` (edit-diff heuristics) and `process_patterns()` (activity log pattern detection). Superseded by the conversational iteration model.

### Key insight: Layer 4 is both output and input

Layer 4 serves dual purpose:
- **Output**: Versioned work products delivered to users
- **Input**: Training signal for what quality looks like (recency, edits, staleness)

The more agents a user runs, the more the system learns what they value. This creates a **quality flywheel**: better agents → more usage → more learning → better agents.

---

## Boundary reference

| Question | Answer |
|---|---|
| What is `platform_content`? | The unified content layer (ADR-072). Replaces `filesystem_items`. Versioned, retention-policy-driven, semantically indexed. |
| How does retention work? | Content starts with `retained=false` and TTL expiry. When referenced (by agent, signal processing, or TP session), marked `retained=true` and never expires. |
| Why does `activity_log` exist if `agent_runs` records runs? | `agent_runs` holds full generated content. `activity_log` holds lightweight event summaries for prompt injection and pattern detection. Neither replaces the other. |
| Does TP get platform content in its system prompt? | No. Context is fetched on demand via primitives, never pre-loaded. |
| Is Memory updated during a session? | Memory is read at session start and does not update mid-session. Memory extraction happens at session end or via background jobs (ADR-064), taking effect in the *next* session's working memory. |
| What is `source_ref` on `user_memory`? | Provenance tracking (ADR-072). Every memory entry links to its origin (session_message, agent_version, platform_content, activity_log). |
| How does agent execution work? | Orchestration pipeline (ADR-045): strategy gathers content from `platform_content`, `build_type_prompt()` assembles prompt, agent (headless mode, ADR-080) generates draft with curated primitives, delivered immediately (ADR-066). |
| What happens if `write_activity()` fails? | The calling operation continues. All log writes are non-fatal by design. |
| Can a user write to `activity_log`? | No. Service-role writes only. Users can SELECT their own rows. |
| Is a `agent_version` mutable after generation? | The `final_content` field is immutable. The `status` field progresses (generating → delivered). |
| How does Layer 4 content influence future work? | Recent agent version content (400-char preview) is included in signal reasoning prompts (ADR-069). This enables quality-aware orchestration decisions. |
| What are the three memory extraction sources? | 1) Conversation (nightly batch), 2) Agent feedback (on approval), 3) Activity patterns (daily detection). See ADR-064. |
| Is signal processing real-time? | No. Signals are extracted on cron schedule (hourly). Near-real-time via webhooks is future work. |
| Does anything write to `platform_content` beyond platform sync? | Yes — agent execution writes outputs as `platform="yarnnn"` rows after successful delivery (ADR-102). Platform sync writes external content; agent execution also marks consumed records `retained=true`. L3 does not reason. (ADR-092) |
| Can coordinator-created agents become recurring? | Yes. Agents with `origin=coordinator_created` can be promoted to recurring (add schedule). Origin field preserves provenance. |
| What is the "accumulation moat"? | Retained `platform_content` accumulates over time — both external content that proved significant through downstream consumption, and agent outputs written back as `platform="yarnnn"` (ADR-102). This creates a compounding intelligence loop: outputs become inputs for future work. |

---

## Design principles

**Unidirectional generation, bidirectional learning.** Data flows downward (L1→L2→L3→L4) for generation. Learning flows upward (L4→L1, L2→L1) through feedback loops. This separation enables predictable generation while allowing quality improvement over time.

**Explicit writes at boundaries.** Every write to Memory, Activity, and Work happens at a known boundary: session end, agent approval, pattern detection cron. No scattered inference, no automatic promotion mid-operation.

**Non-fatal logging.** Activity writes are wrapped in `try/except pass` everywhere. The provenance log is valuable but never mission-critical. A log failure is a missing entry, not a broken pipeline.

**Retention-based accumulation.** (ADR-072) Content that proves significant is retained indefinitely. Significance is determined by downstream consumption: if a agent used it, a signal identified it, or a TP session accessed it, the content is retained. Unreferenced content expires. This is how the accumulation moat compounds without infinite storage growth.

**Immutability where it matters.** Work versions are immutable records. Activity rows are immutable. Retained `platform_content` records are immutable (their `retained` flag can be set to true, never back to false). Only Memory and agent metadata are mutable — and Memory mutability is boundary-controlled.

**Unified agent, separate orchestration.** (ADR-080) One agent with two modes: chat (TP, streaming, full primitives) and headless (background, non-streaming, curated read-only primitives). Primitive updates improve both modes. Orchestration (scheduling, delivery, retention) remains separate from the agent.

**Quality flywheel through Layer 4.** The more agents a user runs, the more the system learns what they value. Layer 4 content becomes training signal for future work. This creates a feedback loop: better agents → more usage → more learning → better agents.

**Provenance everywhere.** (ADR-072) Every agent version links to specific `platform_content_ids`. Every memory entry has a `source_ref`. The system can answer "what informed this output?" at every layer.

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
- [ADR-068](../adr/ADR-068-signal-emergent-agents.md) — Signal-emergent agents (Superseded by ADR-092)
- [ADR-092](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — Agent Intelligence & Mode Taxonomy (dissolves signal processing, defines coordinator/proactive/reactive modes)
- [ADR-071](../adr/ADR-071-strategic-architecture-principles.md) — Strategic architecture principles

**Architecture docs**:
- [agents.md](agents.md) — Agents architecture
- [context-pipeline.md](context-pipeline.md) — Technical pipeline detail for Context

**Implementation**:
- `api/services/working_memory.py` — Working memory build and format
- `api/services/activity_log.py` — `write_activity()`, `get_recent_activity()`
- `api/services/platform_content.py` — (ADR-072) Unified content layer (replaces `filesystem.py`)
