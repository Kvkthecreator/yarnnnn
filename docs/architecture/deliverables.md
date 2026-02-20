# Architecture: Deliverables

**Status:** Canonical
**Date:** 2026-02-19
**Supersedes:** [docs/features/deliverables.md](../features/deliverables.md)
**Related:**
- [ADR-018: Recurring Deliverables](../adr/ADR-018-recurring-deliverables.md)
- [ADR-044: Deliverable Type Reconceptualization](../adr/ADR-044-deliverable-type-reconceptualization.md)
- [ADR-045: Deliverable Orchestration Redesign](../adr/ADR-045-deliverable-orchestration-redesign.md)
- [ADR-060: Background Conversation Analyst](../adr/ADR-060-background-conversation-analyst.md)
- [ADR-066: Delivery-First Redesign](../adr/ADR-066-deliverable-detail-redesign.md)
- [ADR-068: Signal-Emergent Deliverables](../adr/ADR-068-signal-emergent-deliverables.md)
- [Agent Execution Model](agent-execution-model.md)
- [Four-Layer Model](four-layer-model.md) — Deliverables are Layer 4 (Work)

---

## What Deliverables Are

A **deliverable** is a standing configuration for recurring (or one-time) AI-generated output. It defines:
- **What to read** — sources (Slack channels, Gmail labels, Notion pages, Calendar)
- **How to format** — deliverable type, template, tone, length
- **Where to send** — destination (Slack channel/DM, Gmail draft, Notion page, download)
- **When to run** — schedule (daily, weekly, manual) or event trigger

When a deliverable executes, it produces a **deliverable version** — an immutable record of the generated content, the sources used, and the delivery status.

**Conceptual analogy**: A deliverable is a standing order — "every Monday at 9am, read #engineering, summarize it, and send it to my Slack DM." The deliverable row is the configuration. The backend orchestrator (Path B) is the worker that executes it. The version is the build artifact.

---

## Schema

### `deliverables` Table — Standing Configurations

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `user_id` | uuid | Owner |
| `title` | text | Human-readable name ("Monday Slack Digest") |
| `description` | text | Optional user notes |
| `deliverable_type` | text | Type identifier (see Type System below) |
| `type_config` | jsonb | Type-specific settings |
| `type_classification` | jsonb | ADR-044: `{binding, primary_platform, temporal_pattern, freshness_requirement_hours}` |
| `origin` | text | ADR-068: `user_configured`, `analyst_suggested`, or `signal_emergent` |
| `trigger_type` | text | `schedule`, `event`, or `manual` |
| `schedule` | jsonb | Schedule config: `{frequency, day, time, timezone, cron}` |
| `trigger_config` | jsonb | ADR-031: Event trigger config (platform, event_types, cooldown) |
| `sources` | jsonb | `[{platform, resource_id, resource_name, scope_config}]` |
| `destination` | jsonb | `{platform, target, format, options}` |
| `destinations` | jsonb | ADR-031: Array of destination configs (multi-destination support) |
| `status` | text | `active`, `paused`, or `archived` |
| `next_run_at` | timestamptz | Calculated from schedule; NULL for manual trigger |
| `last_run_at` | timestamptz | Last successful execution timestamp |
| `last_triggered_at` | timestamptz | Last event trigger timestamp |
| `created_at` | timestamptz | Creation timestamp |
| `updated_at` | timestamptz | Last modification timestamp |

### `deliverable_versions` Table — Immutable Output Records

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `deliverable_id` | uuid | Foreign key to `deliverables` |
| `version_number` | int | Sequential version number (1, 2, 3...) |
| `status` | text | `delivered`, `failed`, or `suggested` (ADR-060) |
| `draft_content` | text | LLM-generated content (markdown) |
| `final_content` | text | User-edited content (if modified before delivery) |
| `source_snapshots` | jsonb | ADR-049: Platform state at generation time |
| `metadata` | jsonb | Execution metadata (strategy, tokens, timing) |
| `analyst_metadata` | jsonb | ADR-060: Confidence, detected pattern, source sessions |
| `delivery_metadata` | jsonb | Delivery details (message ID, URL, delivery timestamp) |
| `created_at` | timestamptz | Generation timestamp |
| `delivered_at` | timestamptz | Delivery timestamp (NULL if failed) |

---

## Deliverable Origins (ADR-068)

Every deliverable has an `origin` field recording how it came to exist:

| Origin | Created By | Signal Source | Lifecycle |
|---|---|---|---|
| `user_configured` | User (via UI) or TP (on explicit request) | User intent | Configured first, then scheduled |
| `analyst_suggested` | Conversation Analyst (ADR-060) | TP session content (`session_messages`) | Suggested, user enables or dismisses |
| `signal_emergent` | Signal Processing phase (ADR-068) | Live platform APIs (fresh external state) | One-time, user reviews and optionally promotes |

**`user_configured`** — Default. The user or TP explicitly created this deliverable. It runs on the configured schedule or manually.

**`analyst_suggested`** (ADR-060) — The Conversation Analyst detected a recurring pattern in TP sessions (e.g., user asks for weekly status updates every Monday). The system creates a suggested deliverable. The user reviews it in the UI and either enables it (becomes `active`), edits and enables, or dismisses it. Once enabled, it behaves identically to `user_configured`.

**`signal_emergent`** (ADR-068) — The Signal Processing phase observed the user's platform world (upcoming calendar event with external attendees, Gmail thread gone silent for 5+ days, Slack mention in a critical channel) and determined it warrants proactive work. The system creates a one-time deliverable (`trigger_type=manual`) and immediately executes it. The user reviews the output and can:
- Approve and deliver (one-time, done)
- Dismiss (archive)
- Promote to recurring (via `POST /deliverables/{id}/promote-to-recurring`) — `trigger_type` updates to `schedule`, `origin` stays `signal_emergent` as provenance

The `origin` field is **immutable provenance** — it records how the deliverable was born, not what it currently is. A signal-emergent deliverable promoted to recurring still has `origin=signal_emergent`.

---

## Type System (ADR-044)

### Deliverable Types

25 types across three tiers:

**Platform-Bound (Tier 1)** — Single-platform, recurring patterns
- `slack_channel_digest`, `slack_standup`
- `gmail_inbox_brief`
- `notion_page_summary`
- `meeting_prep`, `weekly_calendar_preview`

**User-Configured (Tier 2)** — Multi-platform, user-authored structure
- `status_report`, `stakeholder_update`, `one_on_one_prep`, `board_update`
- `research_brief`, `meeting_summary`, `client_proposal`
- `performance_self_assessment`, `newsletter`, `changelog`

**Synthesizers (Tier 3)** — Cross-platform, context-assembling
- `weekly_status`, `project_brief`, `cross_platform_digest`, `activity_summary`
- `inbox_summary`, `reply_draft`, `follow_up_tracker`, `thread_summary`

**Legacy / Deprecated**
- `custom` — generic fallback, being phased out in favor of specific types
- `digest` — deprecated in favor of `cross_platform_digest` or `slack_channel_digest`

### Type Classification (ADR-044)

Each deliverable type has a `type_classification` object that determines execution behavior:

```json
{
  "binding": "platform_bound" | "cross_platform" | "hybrid",
  "primary_platform": "slack" | "gmail" | "notion" | "google" | null,
  "temporal_pattern": "recurring" | "event_driven" | "ad_hoc",
  "freshness_requirement_hours": 1 | 4 | 24 | 168
}
```

**`binding`** — Determines execution strategy (see Execution Model below)
- `platform_bound` → `PlatformBoundStrategy` (single platform, API-native fetch)
- `cross_platform` → `CrossPlatformStrategy` (multi-platform, filesystem_items cache)
- `hybrid` → `HybridStrategy` (web research + platform fetch in parallel)

**`primary_platform`** — For platform-bound types, which platform to query

**`temporal_pattern`** — Scheduling hint
- `recurring`: Fixed schedule (daily, weekly)
- `event_driven`: Triggered by platform events (Slack mention, calendar event)
- `ad_hoc`: Manual trigger only

**`freshness_requirement_hours`** — How stale can source data be?
- 1h: Real-time critical (meeting prep)
- 4h: Same-day (inbox brief)
- 24h: Daily digest
- 168h: Weekly rollup

---

## Execution Model (ADR-045)

When a deliverable is due to run (scheduled, event-triggered, or manual), the `unified_scheduler.py` orchestrator:

1. Fetches the deliverable row
2. Selects an **execution strategy** based on `type_classification.binding`
3. Instantiates `DeliverableAgent` with the selected strategy
4. The strategy gathers context (live API calls or `filesystem_items` cache)
5. The agent generates content via LLM call (using the gathered context)
6. A `deliverable_version` row is created with `status=delivered`
7. The content is delivered to the configured destination(s)
8. An `activity_log` event is written (non-fatal)

### Execution Strategies

| Binding | Strategy | Context Source | Use Case |
|---|---|---|---|
| `platform_bound` | `PlatformBoundStrategy` | Live platform API (Gmail, Slack, Notion, Calendar) | Single-platform types — authoritative, fresh |
| `cross_platform` | `CrossPlatformStrategy` | `filesystem_items` cache | Cross-platform synthesizers — fast, cached |
| `hybrid` | `HybridStrategy` | Web research (Tavily) + platform fetch | Research briefs, external context needed |

**Why two context paths?**
- Live APIs are authoritative but slow. Good for deliverables (scheduled, latency-tolerant).
- The cache is fast but stale (2-24h depending on tier). Good for TP conversational search.
- Neither can replace the other — they serve different purposes (see [Four-Layer Model](four-layer-model.md)).

The agent is the same (`DeliverableAgent`) in all cases. The strategy determines what context it receives. This is **strategy pattern**, not agent proliferation.

---

## Lifecycle

### User-Configured Deliverable Lifecycle

```
User creates deliverable (UI or TP explicit request)
   ↓
deliverables row inserted (origin=user_configured, status=active, schedule set)
   ↓
unified_scheduler.py calculates next_run_at
   ↓
Scheduler reaches next_run_at → deliverable executes
   ↓
deliverable_version created (status=delivered)
   ↓
Content delivered to destination (Slack, Gmail, Notion, etc.)
   ↓
activity_log event written
   ↓
Scheduler calculates new next_run_at (for recurring deliverables)
```

### Analyst-Suggested Deliverable Lifecycle (ADR-060)

```
Conversation Analyst runs (daily cron, mines session_messages)
   ↓
Detects recurring pattern (confidence ≥ 0.60)
   ↓
deliverables row created (origin=analyst_suggested, status=paused)
deliverable_version created (status=suggested)
   ↓
User sees suggestion in UI (/deliverables page, "Suggested" section)
   ↓
User action:
  - Enable → status=active, next_run_at calculated
  - Edit + Enable → updated, then active
  - Dismiss → deliverable archived, version deleted
   ↓
If enabled: behaves identically to user_configured (scheduled execution)
```

### Signal-Emergent Deliverable Lifecycle (ADR-068)

**Hardened Two-Phase Model (2026-02-20):**

```
PHASE 1: ORCHESTRATION (Ephemeral)
──────────────────────────────────
Signal Processing phase runs (hourly for calendar, daily 7AM for silence)
   ↓
Queries LIVE platform APIs (Google Calendar, Gmail) for fresh external state
   ↓
Extracts behavioral signals (upcoming events, quiet threads, activity gaps)
   ↓
LLM reasoning pass (Haiku): "What does this user's world warrant?"
   ↓
Produces action recommendations (ephemeral SignalAction objects):
  - trigger_existing: Advance existing deliverable's next_run_at (pure orchestration)
  - create_signal_emergent: Create new deliverable for novel work (artifact creation)
  - no_action: Signal doesn't meet threshold or is redundant

PHASE 2: SELECTIVE ARTIFACT CREATION (Persistent)
──────────────────────────────────────────────────
For trigger_existing action:
   → Updates existing deliverable.next_run_at = now
   → No new deliverable row created (pure orchestration)
   → Existing recurring deliverable runs early

For create_signal_emergent action:
   → Checks signal_history for deduplication (per event_id/thread_id)
   → If not deduplicated (confidence ≥ 0.60):
      → deliverables row created (origin=signal_emergent, trigger_type=manual)
      → Records in signal_history (tracks which deliverable was created)
      → Immediately executes (doesn't wait for next cron cycle)
      → deliverable_version created (status=delivered)
      → Content delivered to user's inbox

User reviews delivered output:
  - Approves → deliverable stays in history (can view in UI)
  - Dismisses → deliverable archived
  - Promotes to recurring → POST /deliverables/{id}/promote-to-recurring
      → trigger_type=schedule, schedule set, next_run_at calculated
      → origin stays signal_emergent (immutable provenance)
      → behaves as recurring deliverable from this point forward
```

**Key Insight:** Signals are orchestration that creates artifacts. The system prefers `trigger_existing` (pure orchestration) when a recurring deliverable already handles the signal, but creates new `signal_emergent` deliverables (artifacts) when no suitable recurring deliverable exists.

---

## Governance Model (ADR-066)

**Current state (ADR-066)**: All deliverables deliver immediately. There is no staging or approval gate.

**The `governance` and `governance_ceiling` fields are DEPRECATED** (marked in Pydantic models with `deprecated=True`). They remain in the schema and API for backwards compatibility but are **ignored by all execution logic**.

When a deliverable executes:
- A version is created
- Content is generated
- Delivery is attempted
- Version `status` becomes `delivered` or `failed` (no `staged` state)

**Historical context**: The original governance model (ADR-028) had three levels:
- `manual` — staged for user review before delivery
- `semi_auto` — automated with notification
- `full_auto` — fully automated, no user interaction

ADR-066 removed this complexity. All deliverables are now effectively `full_auto` (delivery-first). Users can pause or archive deliverables, but there is no pre-delivery approval step.

**Deprecation path**: The `governance` field remains in the database schema and API responses for backwards compatibility. It is marked `deprecated=True` in Pydantic models (as of 2026-02-19). Plan: Remove entirely in Phase 3 cleanup (Option A per CLAUDE.md discipline: "Delete legacy code when replacing with new implementation").

**Rationale**: All deliverable outputs land in the user's own platforms (Slack DM, Gmail drafts, Notion pages). The user is the audience. Pre-approval adds friction without value — the user can always delete the delivered output if it's incorrect.

**Open question**: Signal-emergent deliverables may warrant a review-before-send gate (as originally stated in ADR-068), since they're proactive and unexpected. This is deferred to Phase 3. Current behavior: signal-emergent deliverables deliver immediately, same as all others.

---

## Trigger Types

| `trigger_type` | Behavior | `next_run_at` | Use Case |
|---|---|---|---|
| `schedule` | Runs on fixed schedule | Calculated from `schedule` config | Recurring deliverables (weekly status, daily digest) |
| `event` | Runs when platform event occurs | NULL (event-driven) | Slack mentions, calendar events (ADR-031 Phase 4) |
| `manual` | User or system triggers explicitly | NULL (no auto-run) | One-time deliverables, signal-emergent (before promotion) |

**Scheduled deliverables**: `unified_scheduler.py` queries `deliverables WHERE next_run_at <= NOW()` every 5 minutes. After execution, `next_run_at` is recalculated from `schedule.frequency`.

**Event-triggered deliverables**: (ADR-031, Phase 4 — not yet implemented) Platform webhook handler receives event, checks for deliverables with matching `trigger_config`, executes if cooldown passed.

**Manual deliverables**: Execute via `POST /api/deliverables/{id}/run` endpoint or when created by signal processing (immediate execution, no schedule).

---

## Deduplication & Cost Gates

### Signal Processing Cost Gate (ADR-068)

Signal processing only runs for users with active platform connections. This prevents unnecessary LLM calls for users who haven't connected any platforms.

```sql
SELECT DISTINCT user_id FROM platform_connections
WHERE status = 'active';
```

### Deduplication Rules (ADR-068)

Signal processing applies two deduplication checks:

1. **Confidence threshold**: Only create actions with `confidence ≥ 0.60`
2. **Type deduplication**: Don't create a signal-emergent deliverable if a user-configured deliverable of the same type is already scheduled to run within 24 hours
3. **Per-cycle limit**: Only one action per `deliverable_type` per signal processing cycle

Example: If a `meeting_prep` deliverable already exists and is scheduled to run today, signal processing will not create another `meeting_prep` deliverable for a different event. This prevents spam.

**Open question** (ADR-068): Per-signal deduplication windows — if a signal-emergent deliverable was created for a contact drift 2 days ago, how long before the same contact drift signal is eligible again? This is deferred to Phase 4.

---

## Source & Destination Model

### Sources

Each deliverable has a `sources` array:

```json
[
  {
    "platform": "slack",
    "resource_id": "C01234567",
    "resource_name": "#engineering",
    "scope_config": {
      "mode": "delta",
      "fallback_days": 7,
      "max_items": 200
    }
  }
]
```

**Source scope modes** (ADR-030):
- `delta` — Fetch since `last_run_at` (or `fallback_days` if first run). Efficient for recurring deliverables.
- `fixed_window` — Always fetch last N days. Predictable for weekly digests.

### Destinations

Destination config (ADR-028):

```json
{
  "platform": "slack",
  "target": "D01234567",  // DM ID or channel ID
  "format": "markdown",    // markdown | html | plain
  "options": {
    "thread_reply": false,
    "unfurl_links": true
  }
}
```

**Multi-destination support** (ADR-031 Phase 6): `destinations` array allows sending the same deliverable to multiple targets (e.g., Slack DM + Notion page). Not yet implemented in UI, but schema supports it.

---

## Quality Metrics (ADR-018)

Each deliverable tracks quality trend across versions:

| Metric | Calculation | Meaning |
|---|---|---|
| `quality_score` | Edit distance between `draft_content` and `final_content` (0.0–1.0) | 0.0 = no edits, 1.0 = full rewrite |
| `quality_trend` | "improving", "stable", or "declining" | Trend over last 5 versions |
| `avg_edit_distance` | Average quality_score over last 5 versions | Overall quality indicator |

If `quality_trend = "declining"` for 3+ consecutive versions, the system could surface a suggestion to update sources or template (deferred feature).

---

## Relationship to Other Systems

| System | Relationship |
|---|---|
| **TP (Thinking Partner)** | TP can create `user_configured` deliverables on explicit user request. TP does NOT generate deliverable content (ADR-061 Path A/B boundary). |
| **Backend Orchestrator** | `unified_scheduler.py` executes deliverables. Three phases: Signal Processing → Analysis → Execution. |
| **Memory (Layer 1)** | Memory informs deliverable generation (user preferences, tone, context) but is not sourced by deliverables. |
| **Activity (Layer 2)** | Each deliverable execution writes an `activity_log` event. Activity log is read for signal processing deduplication. |
| **Context (Layer 3)** | Deliverables read Context via live APIs (platform_bound) or `filesystem_items` cache (cross_platform). |
| **Conversation Analyst** | Creates `analyst_suggested` deliverables by mining TP sessions. Runs daily, produces suggestions. |
| **Signal Processing** | Creates `signal_emergent` deliverables by observing platform world. Runs hourly (testing) or daily (production). |

---

## Implementation Status

**ADR-068 Signal-Emergent Deliverables: Phase 3+4 Complete (2026-02-20)**

Phase 3 delivered:
- Migration 071: `signal_history` table for per-signal deduplication tracking
- Migration 072: Extended `user_notification_preferences` with signal type toggles (meeting_prep, silence_alert, contact_drift)
- Migration 073: Dropped `governance` and `governance_ceiling` columns (ADR-066 cleanup)
- Per-signal deduplication logic in `signal_processing.py` with configurable windows (24h/7d/14d)
- Pydantic model cleanup — removed all governance field references

Phase 4 delivered:
- Split signal processing cron: Calendar signals (hourly), other signals (daily 7 AM)
- Gmail silence signal extraction via live Gmail API (thread history analysis)
- `signals_filter` parameter in `extract_signal_summary()` for selective signal extraction

**Status (2026-02-20):** Signal-emergent deliverables fully operational with hardened two-phase model.

**What works:**
- ✅ Two-phase execution (orchestration → selective artifact creation)
- ✅ Hybrid action model (trigger_existing + create_signal_emergent)
- ✅ Meeting prep deliverables (hourly check, 48h lookahead, calendar signals)
- ✅ Gmail silence extraction (daily check, 5+ day threshold)
- ✅ Per-signal deduplication via signal_history table
- ✅ User preferences via user_notification_preferences
- ✅ Split cron frequency (hourly/daily based on signal urgency)

**What's pending:**
- ⚠️ `silence_alert` deliverable type needs prompt template (extraction works, generation doesn't)
- ⚠️ `contact_drift` signal extraction not yet implemented
- ⚠️ LLM prompt updated to prioritize trigger_existing, but needs real-world testing

---

## Open Questions & Future Work

1. **Event triggers** (ADR-031 Phase 4) — Platform webhook integration for real-time deliverable triggering (Slack mention, Gmail arrival, etc.)
2. **Contact drift signals** — Third signal type from ADR-068 (alert when key contacts haven't been contacted in N days)
3. **Multi-destination UI** — Frontend for configuring `destinations` array (currently only backend-supported)
4. **Quality-based feedback loop** — Automatic source adjustment when `quality_trend = "declining"` for N consecutive versions
5. **Signal promotion UI** — Frontend for "Promote to Recurring" button on signal-emergent deliverables

---

## Summary

Deliverables are YARNNN's output layer — structured, versioned, scheduled work products. They are:
- **Configured** by users (or TP on explicit request) or **created** by backend systems (Conversation Analyst, Signal Processing)
- **Executed** by the backend orchestrator (Path B, not TP)
- **Delivered** to platform destinations (Slack, Gmail, Notion) without approval gates (ADR-066)
- **Versioned** immutably — each execution produces a permanent record
- **Type-classified** (ADR-044) to determine execution strategy
- **Origin-tagged** (ADR-068) to record provenance (user vs analyst vs signal)

The deliverable model is the bridge between YARNNN's knowledge systems (Memory, Activity, Context) and the user's operational world (email inbox, Slack channels, Notion workspace). Every deliverable execution is an act of context → content → delivery.
