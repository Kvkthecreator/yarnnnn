# Deliverables

> Layer 4 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Deliverables are structured, recurring outputs — digests, meeting briefs, weekly summaries, drafted emails — that YARNNN generates on a schedule and delivers to a platform destination. They are the reason the other three layers (Memory, Activity, Context) exist: to give the system enough knowledge to produce outputs that are timely, personalised, and accurate.

Every generation run produces a versioned output (`deliverable_version`). Versions are staged for review, approved by the user, and exported to the configured destination (Slack channel, Gmail draft, Notion page, etc.).

**Conceptual analogy**: A deliverable is a standing order — "every Monday at 9am, read #engineering, summarise it, and send it to my Slack DM." The deliverable record is the configuration. The backend orchestrator is the worker that executes it. The version is the build artefact.

---

## What it is not

- Not platform content (emails, Slack messages, Notion pages) — that is Context
- Not what YARNNN knows about the user — that is Memory
- Not a log of what ran — that is Activity (though Activity records a lightweight event per run)
- Not created by TP itself during conversation — TP creates the configuration; the backend orchestrator generates content on schedule (ADR-061)

---

## Tables

### `deliverables` — Standing configurations

A deliverable defines what to read, how to format it, where to send it, and when to run. Each deliverable is self-contained — sources live on the deliverable, not on a separate domain or grouping table (ADR-059 removed `knowledge_domains` for this reason).

| Column | Notes |
|---|---|
| `title` | Human-readable name ("Monday Slack Digest") |
| `deliverable_type` | Type identifier (`digest`, `meeting_prep`, etc.) |
| `status` | `active`, `paused`, `archived` |
| `sources` | `[{platform, resource_id, resource_name}]` — what to read |
| `schedule` | `{frequency, day, time, timezone}` — when to run |
| `recipient_context` | Destination configuration (channel, label, page) |
| `template` | Template settings for the generation prompt |
| `next_run_at` | When the scheduler will next trigger this deliverable |
| `governance` | `manual` (default) or `full_auto` |

### `deliverable_versions` — Generated outputs

Every execution produces a new, immutable version. Status progresses forward; content is never overwritten.

| Column | Notes |
|---|---|
| `version_number` | Increments per deliverable |
| `status` | `generating` → `staged` → `approved` → `published` (or `suggested` for analyst-detected) |
| `draft_content` | LLM output |
| `final_content` | User-approved content (may differ if user edited before approving) |
| `source_snapshots` | JSONB: exactly what sources were read at generation time |
| `generated_at` | When the version was created |
| `approved_at` | When the user approved it |
| `published_at` | When it was sent to the destination |

`source_snapshots` is the audit trail — it records `{platform, resource_id, resource_name, synced_at, item_count}` for each source consulted at generation time.

---

## Lifecycle of a deliverable

### 1. Creation (Path A — TP)

The user asks TP to set up a deliverable. TP creates the `deliverables` record:

```
User: "Set up a weekly digest of #engineering for me"
→ TP: "I'll create a Weekly #engineering Digest, every Monday at 9 AM. Sound good?"
User: "yes"
→ TP: Write(ref="deliverable:new", content={title: "Weekly #engineering Digest", schedule: {...}, ...})
→ "Created. It will run every Monday at 9 AM. You can manage it in /deliverables."
```

TP creates the configuration and sets `next_run_at`. It does not generate content — that is Path B.

### 2. Execution (Path B — Backend Orchestrator)

The backend orchestrator (`unified_scheduler.py`, running every 5 minutes) picks up due deliverables and generates content entirely headless — no user session required:

```
unified_scheduler.py (every 5 min)
  → get_due_deliverables()           — find deliverables where next_run_at ≤ now
  → execute_deliverable_generation() — deliverable_execution.py
  → get_execution_strategy()         — execution_strategies.py (type-driven)
  → strategy.gather_context()        — fetches live platform data
  → fetch_integration_source_data()  — deliverable_pipeline.py
    → _fetch_gmail_data()            — direct REST via GoogleAPIClient
    → _fetch_slack_data()            — MCP gateway
    → _fetch_notion_data()           — direct REST via NotionAPIClient
    → _fetch_calendar_data()         — direct REST via GoogleAPIClient
  → LLM call (DeliverableAgent)
  → create deliverable_version (staged)
  → record source_snapshots
  → write activity_log event (deliverable_run)
  → [if full_auto] auto-approve → deliver to platform
  → send email notification to user
```

**Live reads only**: Execution never reads `filesystem_items`. Platform data is fetched live at the moment of generation — the output reflects the actual state of platforms at generation time, not a cached snapshot.

**OAuth credentials**: Decrypted from `platform_connections` at execution time. Google tokens are refreshed automatically if expired.

### 3. Execution strategies (type-driven, ADR-045)

The orchestrator selects a strategy based on `type_classification.binding` on the deliverable type:

| Binding | Strategy | Description |
|---|---|---|
| `platform_bound` | PlatformBoundStrategy | Single platform focus, platform-specific synthesis |
| `cross_platform` | CrossPlatformStrategy | Parallel fetch across platforms, cross-platform synthesis |
| `research` | ResearchStrategy | Web search via Anthropic native `web_search` tool |
| `hybrid` | HybridStrategy | Web research + platform in parallel |

Complexity lives in the strategy, not in agent proliferation. All strategies produce output via a single `DeliverableAgent` with a single LLM call (ADR-042).

### 4. Review and approval

After generation, a `staged` version appears in the user's UI (`/deliverables`). The user reviews and:
- **Approves** (with or without edits): version → `approved` → delivered to platform destination
- **Rejects**: version archived; next scheduled run will produce a fresh version

### 5. Delivery

Approved versions are exported to the configured destination:
- **Slack**: Posted to a channel via MCP Gateway
- **Gmail**: Created as a draft or sent
- **Notion**: Written to a page
- **Calendar**: Inserted as an event

Delivery is handled by `api/services/delivery.py → deliver_version()`.

---

## Governance modes

| Mode | Behaviour |
|---|---|
| `manual` | Version created as `staged` — user reviews and approves before publication |
| `full_auto` | Version automatically approved and delivered without user review |

`full_auto` is a power-user setting. The default is `manual`.

---

## Suggested deliverables (ADR-060)

The Backend Orchestrator's daily Analysis Phase runs `analyze_conversation_patterns()` — a service function (not a separate agent) that reviews recent sessions, detects recurring user requests, and creates `suggested` deliverables with confidence scores.

Suggested deliverables have `status = "suggested"`. They appear in the UI as proposals:
- **Accept**: Creates an active deliverable with the suggested configuration
- **Dismiss**: Archived

This is a background process — TP does not prompt the user about suggestions mid-conversation.

---

## Boundaries

| Question | Answer |
|---|---|
| Does execution read from `filesystem_items`? | No — always live reads from platform APIs at generation time |
| Is a version mutable after generation? | Content is immutable; `status` progresses forward only |
| Can a deliverable run without an active platform connection? | No — credentials are required at execution time |
| Does deleting a deliverable delete its versions? | No — versions are retained for audit |
| Does the scheduler run if the user is offline? | Yes — execution is fully headless |
| Does TP generate deliverable content during conversation? | No — TP creates the configuration; the orchestrator generates on schedule |

---

## Related

- [Backend Orchestration](./backend-orchestration.md) — How the scheduler, analysis phase, and execution pipeline work
- [ADR-061](../adr/ADR-061-two-path-architecture.md) — Two-Path Architecture (TP = Path A, Orchestrator = Path B)
- [ADR-042](../adr/ADR-042-deliverable-execution-simplification.md) — Simplified single-call execution pipeline
- [ADR-045](../adr/ADR-045-deliverable-orchestration-redesign.md) — Type-aware execution strategies
- [ADR-060](../adr/ADR-060-background-conversation-analyst.md) — Suggested deliverables (background analyst)
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- `api/services/deliverable_execution.py` — Main execution entry point
- `api/services/deliverable_pipeline.py` — Source data fetching and version creation
- `api/services/execution_strategies.py` — Type-driven strategy selection
- `api/jobs/unified_scheduler.py` — Cron trigger and orchestration loop
