# Backend Orchestration

> Path B of the YARNNN Two-Path Architecture (ADR-061)

---

## What it is

Backend Orchestration is the async, scheduled, headless processing system that runs independently of user sessions. It is the counterpart to the Thinking Partner (TP), which is real-time and conversational.

The orchestrator does not interact with users. It runs on a schedule, processes due work, and surfaces results (deliverable versions, suggested deliverables, email notifications) that the user sees when they next open the product.

**Conceptual analogy**: The orchestrator is like a CI/CD pipeline. The user pushes a configuration (creates a deliverable). The system builds on schedule (runs the execution pipeline). The artefact (version) is staged for review. The user approves and ships. The pipeline itself runs headlessly in the background.

---

## What it is not

- Not the Thinking Partner — TP is real-time (Path A); this is async (Path B)
- Not triggered by user messages — triggers are time-based (cron) or event-based
- Not the same domain as conversational session management — the UTC-midnight cron cadence is an infrastructure scheduling concern, independent of when a user's "conversation" conceptually begins or ends

---

## Entry point

`api/jobs/unified_scheduler.py` — Deployed on Render, runs every 5 minutes via cron:

```
schedule: "*/5 * * * *"
command: cd api && python -m jobs.unified_scheduler
```

A single invocation runs multiple phases. Each phase has its own frequency gate.

---

## Phases

### Phase 1 — Deliverable Execution (every 5 minutes)

Runs every invocation. Finds deliverables where `next_run_at ≤ now` and generates content.

```
get_due_deliverables()
  → for each due deliverable:
       should_skip_deliverable()    — ADR-031: skip if no new context since last run
       process_deliverable()
         → get_execution_strategy() — type-driven (ADR-045)
         → strategy.gather_context() — reads from platform_content (ADR-072)
         → DeliverableAgent LLM call
         → create deliverable_version (staged)
         → record source_snapshots
         → write activity_log event
         → [if full_auto] deliver to platform
         → send email notification
         → update next_run_at
```

**Freshness check (ADR-031)**: Before generating, the scheduler checks if there is new context since the last run. If nothing has changed on the source platforms, the deliverable is skipped and `next_run_at` is advanced. This prevents generating identical versions.

**Live reads**: Execution fetches platform data directly at generation time via:
- Gmail/Calendar: `GoogleAPIClient` direct REST
- Slack: MCP gateway
- Notion: `NotionAPIClient` direct REST

Content is accessed via the unified `platform_content` table (ADR-072).

### Phase 2 — Work Tickets (every 5 minutes)

Legacy path from ADR-017. Runs every invocation alongside deliverable execution.

Finds `work` records where `is_active=true AND next_run_at ≤ now`. Executes via `process_work()`. This path handles non-deliverable recurring work (e.g., standalone reports created before ADR-061 consolidated the model).

### Phase 3 — Hourly jobs (`:00` each hour, first 5 minutes)

Runs when `now.minute < 5`:

- **Weekly digests**: `get_workspaces_due_for_digest()` → `process_workspace_digest()`
- **platform_content TTL cleanup**: Removes expired non-retained content (ADR-072)
- **Event trigger cooldown cleanup**: Removes expired rate-limit entries

### Phase 4 — Analysis Phase (daily, gated at midnight UTC)

Runs when `now.hour == 0 AND now.minute < 5`:

**Conversation pattern detection (ADR-060)**:
```
get_active_users(last 7 days)
  → for each user:
       run_analysis_for_user()
         → get recent sessions (7-day window)
         → analyze_conversation_patterns()  — single LLM call with structured output
         → for suggestions with confidence ≥ 0.50:
              create_suggested_deliverable() — status: "suggested"
         → notify_suggestion_created()      — email if user has this notification on
         → [if no suggestions] notify_analyst_cold_start()
```

This is not a separate agent — it is a service function (`analyze_conversation_patterns()`) that makes a single LLM call with structured output. No agent prompt, no tool loop.

**Memory extraction (ADR-064)**:
```
get sessions from yesterday (session_type = "thinking_partner")
  → for each session with ≥ 3 user messages:
       get session_messages
       process_conversation(user_id, messages, session_id)
         → LLM reviews conversation for learnable facts
         → upsert to user_context (key-value store)
```

Memory extraction runs at midnight UTC and processes all prior day's sessions in batch. A preference stated by the user in a conversation today is available in working memory tomorrow morning.

### Phase 5 — Import Jobs (every 5 minutes)

Processes pending platform import jobs from `platform_import_jobs`. Recovers stale jobs from crashed processes before finding new ones.

---

## Phase frequency summary

| Phase | Frequency | Gate |
|---|---|---|
| Deliverable execution | Every 5 min | `next_run_at ≤ now` per deliverable |
| Work tickets | Every 5 min | `next_run_at ≤ now` per work item |
| Weekly digests | Hourly | `now.minute < 5` |
| filesystem cleanup | Hourly | `now.minute < 5` |
| Event cooldown cleanup | Hourly | `now.minute < 5` |
| Conversation analysis | Daily | `now.hour == 0 AND now.minute < 5` |
| Memory extraction | Daily | `now.hour == 0 AND now.minute < 5` |
| Import jobs | Every 5 min | pending queue |

---

## The domain distinction

The orchestrator's cron cadence (midnight UTC for daily jobs) is an **infrastructure scheduling concern** — chosen because it is a clean boundary for batch processing and aligns with international timezones reasonably. It is not the same domain as conversational session management.

| Domain | Concern | Current boundary |
|---|---|---|
| Backend orchestration | When do batch jobs run? | Cron cadence (UTC midnight for daily, every 5 min for execution) |
| Conversational sessions | When does a "conversation" start and end? | Currently also UTC midnight (`scope="daily"`) — a known conflation |

The session boundary (UTC midnight) was set to match the cron cadence. This was incidental, not intentional architecture. They should be treated as independent concerns — see [Sessions](./sessions.md) for the ongoing discourse on decoupling these.

---

## What the orchestrator is not responsible for

| Responsibility | Who owns it |
|---|---|
| Real-time platform actions (send Slack, create draft) | TP (Path A) |
| Responding to user messages | TP (Path A) |
| Reading filesystem_items during deliverable generation | Nobody — execution always reads live |
| Writing session history | chat.py (per message) |
| Writing working memory | working_memory.py (at session start) |

---

## Related

- [Deliverables](./work.md) — What the orchestrator produces
- [Memory](./memory.md) — Memory extraction (nightly cron)
- [Activity](./activity.md) — Activity log written by orchestrator
- [Sessions](./sessions.md) — Conversational sessions (different domain)
- [ADR-061](../adr/ADR-061-two-path-architecture.md) — Two-Path Architecture
- [ADR-042](../adr/ADR-042-deliverable-execution-simplification.md) — Simplified execution pipeline
- [ADR-045](../adr/ADR-045-deliverable-orchestration-redesign.md) — Type-aware strategies
- [ADR-060](../adr/ADR-060-background-conversation-analyst.md) — Conversation analyst (analysis phase)
- [ADR-064](../adr/ADR-064-unified-memory-service.md) — Memory extraction
- `api/jobs/unified_scheduler.py` — Orchestrator entry point
- `api/services/deliverable_execution.py` — Execution pipeline
- `api/services/execution_strategies.py` — Strategy selection
- `api/services/memory.py` — Memory extraction service
