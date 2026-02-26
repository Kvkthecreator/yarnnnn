# Architecture: Deliverables

**Status:** Canonical
**Date:** 2026-02-26
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

31 types across three tiers:

**Platform-Bound** — Single-platform, recurring patterns
- `slack_channel_digest`, `slack_standup`
- `gmail_inbox_brief`, `inbox_summary`
- `notion_page_summary`
- `meeting_prep`, `meeting_summary`, `weekly_calendar_preview`

**Cross-Platform** — Multi-platform synthesis
- `status_report`, `stakeholder_update`, `one_on_one_prep`, `board_update`
- `weekly_status`, `project_brief`, `cross_platform_digest`, `activity_summary`
- `daily_strategy_reflection`, `performance_self_assessment`
- `reply_draft`, `follow_up_tracker`, `thread_summary`
- `newsletter`, `changelog`

**Research / Hybrid** — Web research with optional platform grounding
- `research_brief`, `deep_research`, `competitive_analysis`
- `intelligence_brief` (hybrid: web + platform in parallel)
- `client_proposal` (hybrid)

**Legacy / Deprecated**
- `custom` — generic fallback
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
- `platform_bound` → Single platform focus
- `cross_platform` → Multi-platform search via `platform_content`
- `hybrid` → Web research + platform fetch in parallel

> **Note (ADR-072)**: All strategies now use unified `platform_content` access via TP primitives. The strategy distinction remains for prompt specialization.

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

## Execution Model

**Current implementation (ADR-042 + ADR-045 + ADR-073)**: Strategy-based execution with type-aware context gathering and a single LLM generation call.

When a deliverable is due to run (scheduled, event-triggered, or manual), `execute_deliverable_generation()` in `deliverable_execution.py`:

1. Checks source freshness — skips if no new content since `last_run_at` (ADR-049)
2. Creates `deliverable_versions` row (status=generating) + `work_tickets` row
3. Selects execution strategy by `type_classification.binding` (ADR-045):

| Strategy | Binding | Content Source |
|----------|---------|---------------|
| `PlatformBoundStrategy` | `platform_bound` | Single platform's `platform_content` |
| `CrossPlatformStrategy` | `cross_platform` | All platforms' `platform_content` |
| `ResearchStrategy` | `research` | Web research (Anthropic native `web_search`) |
| `HybridStrategy` | `hybrid` | Web research + platform content in parallel (`asyncio.gather`) |

4. Strategy calls `get_content_summary_for_generation()` — chronological content dump with signal markers (`[UNANSWERED]`, `[STALLED]`, `[URGENT]`, `[DECISION]`), capped at 20 items/source, 500 chars/item
5. User memories appended from `user_context` (fact/instruction/preference keys)
6. Past version feedback appended (if any)
7. `build_type_prompt()` assembles type-specific prompt from template + config + gathered context
8. Single LLM call (Claude Sonnet 4) generates the draft
9. `mark_content_retained()` on consumed `platform_content` records (ADR-072)
10. `DeliveryService.deliver_version()` — email immediately (ADR-066, no approval gate)
11. `activity_log` event written (non-fatal)

### Content source

All content comes from `platform_content` (the unified content layer, ADR-073):
- Retained content (significant, never expires) — accumulated intelligence
- Recent ephemeral content (TTL-bounded) — fresh platform state
- Content is fetched chronologically, not semantically (embedding search infrastructure exists but is not wired into deliverable execution)

`platform_content` is the single source, populated by platform sync (ephemeral) and marked retained by deliverable execution and signal processing.

### Known limitation: No intermediate reasoning step

The current pipeline dumps all gathered content into a single LLM call that must simultaneously determine what's important, cross-reference across platforms, apply user context, and generate formatted output. There is no pre-generation reasoning step that filters, prioritizes, or synthesizes context before the generation call. Signal processing determines *whether* to create deliverables but does not inform *what* the deliverable should emphasize. User memories are appended but not used to guide content selection upstream.

This is the primary quality gap between TP conversations (where the LLM iteratively reasons over content via tool calls) and deliverable generation (single-pass context dump → output).

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
Signal Processing phase runs (hourly, Starter+ tier only)
   ↓
Reads platform_content for behavioral signals (ADR-073)
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

**Source scope**: Content is fetched from `platform_content` filtered by `(platform, resource_id)` per source, ordered by `source_timestamp DESC`, limited per source. The `scope_config` field exists in the schema but scope modes (`delta`, `fixed_window`) are not implemented — all fetches use chronological recency.

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

## Quality Metrics (ADR-018) — NOT IMPLEMENTED

The schema supports quality tracking but the computation is not wired:

| Metric | Schema | Status |
|---|---|---|
| `quality_score` | Edit distance between `draft_content` and `final_content` | **Not computed** |
| `quality_trend` | Trend over last 5 versions | **Not computed** |

Quality signal currently flows through: (1) user feedback on deliverable edits → memory extraction (ADR-064), and (2) past version context appended to generation prompts.

---

## Relationship to Other Systems

| System | Relationship |
|---|---|
| **TP (Thinking Partner)** | TP can create `user_configured` deliverables on explicit user request. TP does NOT generate deliverable content — the backend strategy pipeline does (ADR-061 Path A/B boundary). |
| **Backend Orchestrator** | `unified_scheduler.py` triggers due deliverables. `deliverable_execution.py` runs the strategy pipeline. Signal processing creates/triggers deliverables on a separate schedule. |
| **Memory (Layer 1)** | User memories (facts, instructions, preferences) are appended to the generation context but are not currently used to filter or prioritize content upstream. |
| **Activity (Layer 2)** | Each deliverable execution writes an `activity_log` event. Activity log is read for signal processing deduplication. |
| **Context (Layer 3)** | Deliverables read Context via `platform_content` (unified layer, ADR-072). TP primitives provide access. |
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

## Execution Metadata & Audit Trail

Every deliverable execution captures metadata across multiple storage layers, enabling both debugging and future UI surfacing:

### What's Captured

| Data | Storage Location | Populated? |
|------|-----------------|------------|
| Generated content | `deliverable_versions.draft_content` / `final_content` | Yes |
| Strategy used | `activity_log.metadata.strategy` | Yes |
| Source snapshots (immutable) | `deliverable_versions.source_snapshots` | Yes |
| Execution stages (started/completed/failed) | `work_execution_log` | Yes |
| Content length, sources list | `work_execution_log.metadata` | Yes |
| Delivery status/error | `deliverable_versions.delivery_status` / `delivery_error` | Yes |
| Delivery timestamp | `deliverable_versions.delivered_at` | Yes |
| Analyst confidence (suggested only) | `deliverable_versions.analyst_metadata` | Yes (ADR-060) |
| Platform content IDs retained | `platform_content.retained_reason` / `retained_ref` | Yes |
| `source_fetch_summary` | `deliverable_versions` column | **Not populated** (schema exists) |
| `context_snapshot_id` | `deliverable_versions` column | **Not implemented** |
| `pipeline_run_id` | `deliverable_versions` column | **Not used** (ADR-042) |

### Querying Execution History

```sql
-- Execution log for a specific version's work ticket
SELECT stage, message, metadata, timestamp
FROM work_execution_log
WHERE ticket_id = (SELECT pipeline_run_id FROM deliverable_versions WHERE id = '<version_id>')
ORDER BY timestamp;

-- Activity log with strategy info
SELECT metadata->>'strategy', metadata->>'final_status', created_at
FROM activity_log
WHERE event_type = 'deliverable_run'
  AND metadata->>'deliverable_id' = '<deliverable_id>'
ORDER BY created_at DESC;

-- Source snapshots for audit trail
SELECT source_snapshots FROM deliverable_versions WHERE id = '<version_id>';
```

### Frontend Surfacing (ADR-066)

The `/deliverables/[id]` detail page now surfaces per-version execution metadata:
- **Content**: Rendered markdown (ReactMarkdown + Tailwind typography) as the hero element
- **Per-version**: Delivery status badge, timestamp, version number, word count, source snapshot pills
- **Delivery history**: Click version rows to switch the content area (replaces accordion)
- **Failed versions**: Error banner with `delivery_error` message and Retry button

**Not yet surfaced** (data exists in DB):
- Strategy used (`work_execution_log` / `activity_log`)
- Quality trend across versions
- Execution trace (expandable `work_execution_log` stages)

See [docs/features/email-notifications.md](../features/email-notifications.md) for the related in-app delivery channel consideration.

---

## Delivery Routing

### Current State (2026-02-24): Resend-First Email Delivery

Deliverable content is delivered via **Resend API** (server-side, no user OAuth required). This is the default `"email"` platform handler.

| Component | Service | Purpose |
|-----------|---------|---------|
| **Content delivery** | Resend API (`ResendExporter`) | Full deliverable content, HTML-formatted. Works for all users. |
| **Gmail drafts/sends** | Gmail API (`GmailExporter`) | Premium: create drafts or send as user's own address (requires Google OAuth). |
| **Status notifications** | Resend API (`send_email`) | Skipped when content was already delivered via email (same inbox). |

**Why Resend over Gmail API for default delivery:**
- Works for **all users** regardless of platform connections (no OAuth required)
- Server-side API key (no token refresh issues, no `invalid_grant` errors)
- Consistent sender: `noreply@yarnnn.com`
- Pricing: Free tier 3,000 emails/month; Pro $20/mo for 50k

**Notification email consolidation:** When the deliverable's destination is `platform: "email"` or `platform: "gmail"`, the content email IS the notification — the separate "Your deliverable is ready" notification email is skipped. Failure notifications still send regardless.

### Exporter Registry Pattern

Delivery is abstracted via the exporter registry (`api/integrations/exporters/registry.py`):

```
deliver_version() → ExporterRegistry.get_exporter(platform) → ResendExporter (platform="email", default)
                                                              → GmailExporter (platform="gmail", OAuth)
                                                              → SlackExporter
                                                              → NotionExporter
                                                              → (future: AppExporter)
```

The `ResendExporter` uses `generate_gmail_html()` for HTML formatting (same variant-aware templates as GmailExporter), then delivers via `send_email()` from `jobs/email.py`.

### Future: In-App Delivery Channel

See [docs/features/email-notifications.md — Future Consideration](../features/email-notifications.md) for documented architectural path to in-app delivery. The `destinations` array (ADR-031) supports multi-destination delivery, enabling email + in-app simultaneously.

---

## Open Questions & Future Work

1. **Event triggers** (ADR-031 Phase 4) — Platform webhook integration for real-time deliverable triggering (Slack mention, Gmail arrival, etc.)
2. **Contact drift signals** — Third signal type from ADR-068 (alert when key contacts haven't been contacted in N days)
3. **Multi-destination UI** — Frontend for configuring `destinations` array (currently only backend-supported)
4. **Quality-based feedback loop** — Automatic source adjustment when `quality_trend = "declining"` for N consecutive versions
5. **Signal promotion UI** — Frontend for "Promote to Recurring" button on signal-emergent deliverables
6. **In-app delivery channel** — `AppExporter` for richer content presentation + execution metadata surfacing (see Delivery Routing above)
7. **Populate `source_fetch_summary`** — Schema exists but execution code doesn't fill it; useful for debugging and UI

---

## Summary

Deliverables are YARNNN's output layer — structured, versioned, scheduled work products. They are:
- **Configured** by users (or TP on explicit request) or **created** by backend systems (Conversation Analyst, Signal Processing)
- **Executed** by the backend strategy pipeline (Path B, not TP) — strategy selects context, single LLM call generates
- **Delivered** to platform destinations (email via Resend, Slack, Notion) without approval gates (ADR-066)
- **Versioned** immutably — each execution produces a permanent record
- **Type-classified** (ADR-044) to determine execution strategy
- **Origin-tagged** (ADR-068) to record provenance (user vs analyst vs signal)

The deliverable model is the bridge between YARNNN's knowledge systems (Memory, Activity, Context) and the user's operational world (email inbox, Slack channels, Notion workspace). Every deliverable execution is an act of context → content → delivery.

**Known gap**: The current pipeline lacks an intermediate reasoning step between context gathering and generation. See Execution Model section for details.
