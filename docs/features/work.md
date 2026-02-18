# Work

> Layer 4 of 4 in the YARNNN four-layer model (ADR-063)

---

## What it is

Work is what YARNNN produces. Scheduled digests, meeting briefs, weekly summaries, drafted emails — any structured output TP generates and delivers to a platform destination. Work is the reason the other three layers exist.

Every generation run produces a versioned output (`deliverable_version`). Versions are reviewed by the user, approved, and exported to the configured destination (Slack channel, Gmail draft, Notion page, etc.).

**Analogy**: Work is the build output — the artifact that the pipeline produces after reading source files (Context) and following configuration (Memory). The pipeline runs headless, on a schedule, and produces a versioned result.

---

## What it is not

- Not the configuration of what to produce — that is the `deliverable` record (see below)
- Not the user's platform content — that is Context
- Not what YARNNN knows about the user — that is Memory
- Not a log of what ran — that is Activity (though Activity records a lightweight event per run)

---

## Tables

### `deliverables` — Scheduled output configurations

A deliverable is the standing configuration for a recurring output. It defines what to read, how to format it, where to send it, and when to run.

| Column | Notes |
|---|---|
| `title` | Human-readable name ("Monday Slack Digest") |
| `deliverable_type` | Type identifier (`digest`, `meeting_prep`, etc.) |
| `status` | `active`, `paused`, `archived` |
| `sources` | `[{platform, resource_id, resource_name}]` — what to read |
| `schedule` | `{frequency, time, timezone}` — when to run |
| `recipient_context` | Destination configuration (channel, label, page) |
| `template` | Template settings for the generation prompt |
| `next_run_at` | When the scheduler will next trigger this deliverable |

**Sources live on the deliverable** — not on a separate domain or grouping table. This was an explicit decision in ADR-059 (removing `knowledge_domains`). Each deliverable is self-contained.

### `deliverable_versions` — Generated outputs

Every run produces a new version. Versions are immutable records of what was generated, from what sources, at what point in time.

| Column | Notes |
|---|---|
| `content` | Full generated text |
| `version_number` | Increments per deliverable |
| `status` | `draft` → `staged` → `approved` → `published` (or `suggested` for auto-detected) |
| `source_snapshots` | JSONB: exactly what sources were read at generation time |
| `generated_at` | When the version was created |
| `approved_at` | When the user approved it |
| `published_at` | When it was sent to the destination |

`source_snapshots` is the audit trail — it records `{platform, resource_id, resource_name, synced_at, item_count}` for each source consulted. This is what ADR-049 calls "context provenance."

---

## How Work is produced

Deliverable execution is fully headless. It requires no user session.

```
unified_scheduler.py (every 5 minutes)
  → get_due_deliverables()           — find deliverables where next_run_at ≤ now
  → execute_deliverable_generation() — deliverable_execution.py
  → get_execution_strategy()         — execution_strategies.py
  → strategy.gather_context()        — fetches live platform data
  → fetch_integration_source_data()  — deliverable_pipeline.py
    → _fetch_gmail_data()            — direct REST via GoogleAPIClient
    → _fetch_slack_data()            — MCP gateway
    → _fetch_notion_data()           — direct REST via NotionAPIClient
    → _fetch_calendar_data()         — direct REST via GoogleAPIClient
  → LLM call (Claude API)
  → create deliverable_version (staged)
  → record source_snapshots
  → write activity_log event (deliverable_run)
  → [if full_auto] auto-approve → deliver to platform
```

**Live reads only**: Deliverable execution never reads `filesystem_items`. Platform data is fetched live at the moment of generation. This ensures the output reflects the actual state of the platforms at generation time, not a cached snapshot from hours earlier.

**OAuth credentials**: Decrypted from `platform_connections` at execution time. Google tokens are refreshed automatically if expired.

---

## Governance modes

| Mode | Behaviour |
|---|---|
| `manual` | Version is created as `staged` — user reviews and approves in the UI |
| `full_auto` | Version is automatically approved and delivered to the platform destination without user review |

`full_auto` is a power-user setting. The default is `manual`, which requires user review before publication.

---

## Delivery

Approved versions are exported to the configured platform destination:
- **Slack**: Posted to a channel via MCP Gateway
- **Gmail**: Created as a draft or sent
- **Notion**: Written to a page
- **Calendar**: Inserted as an event

Delivery is handled by `api/services/delivery.py → deliver_version()`. Each platform has its own delivery handler.

---

## Suggested deliverables (ADR-060)

The Background Conversation Analyst (ADR-060) can create `suggested` deliverable versions — proposals for new recurring deliverables based on detected patterns in the user's conversation history. These have `status = "suggested"` rather than `"draft"`. They appear in the UI as suggestions, not active deliverables. The user can accept (which creates an active deliverable) or dismiss.

---

## Boundaries

| Question | Answer |
|---|---|
| Does Work read from `filesystem_items`? | No — always live reads from platform APIs |
| Is a version mutable after generation? | The content is immutable; `status` progresses (staged → approved → published) |
| Can a deliverable run without an active platform connection? | No — credentials are required at execution time |
| Does deleting a deliverable delete its versions? | No — versions are retained for audit purposes |
| Does the scheduler run even if the user is offline? | Yes — deliverable execution is fully headless |

---

## Related

- [ADR-042](../adr/ADR-042-deliverable-execution-simplification.md) — Simplified execution pipeline
- [ADR-045](../adr/ADR-045-deliverable-orchestration-redesign.md) — Orchestration design
- [ADR-060](../adr/ADR-060-background-conversation-analyst.md) — Suggested deliverables
- [ADR-063](../adr/ADR-063-activity-log-four-layer-model.md) — Four-layer model
- [four-layer-model.md](../architecture/four-layer-model.md) — Architectural overview
- `api/services/deliverable_execution.py` — Main execution entry point
- `api/services/deliverable_pipeline.py` — Source data fetching and version creation
- `api/jobs/unified_scheduler.py` — Schedule trigger
