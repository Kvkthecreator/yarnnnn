# ADR-129: Activity Scoping — Two-Tier Model

**Status**: Phases 1-3 Implemented
> **Partially superseded by**: [ADR-138](ADR-138-agents-as-work-units.md) — Project activity tier removed.
**Date**: 2026-03-22
**Extends**: ADR-063 (Activity Log / Four-Layer Model), ADR-124 (Project Meeting Room), ADR-125 (Project-Native Session Architecture)
**Supersedes**: None (refines the activity domain within existing four-layer model)

---

## Context

Activity (Layer 2) was designed as a flat, user-scoped, append-only provenance log (ADR-063). When introduced, YARNNN had no project concept — agents were standalone, and activity served one purpose: "what has YARNNN done for this user recently?"

Since then, the architecture has evolved significantly:

- **ADR-122**: Projects became the unit of organization. All new agents are project-scoped. Every project has a PM.
- **ADR-124**: Project Meeting Room merged activity events with chat messages into a unified project timeline via `mergeTimeline()`.
- **ADR-125**: Sessions became project-scoped (`chat_sessions.project_slug`). Conversation is now a first-class project activity stream.
- **ADR-126**: Agent Pulse introduced high-frequency sense→decide events (`agent_pulsed`, `pm_pulsed`) — dramatically increasing activity volume.
- **ADR-128**: Cognitive files (self-assessment, project-assessment) create an implicit activity trail in workspace.

The result: `activity_log` is structurally flat (user_id-scoped), but the platform has become project-centric. The gap:

| Observation | Impact |
|---|---|
| No `project_slug` column on `activity_log` | Project activity filtered via `metadata->>project_slug` — only 8/34 event types include it |
| Agent lifecycle events lack project context | `agent_scheduled`, `agent_generated`, `agent_pulsed`, `agent_approved`, `agent_rejected` have no project info despite agents having `project_id` |
| Meeting room already merges two streams | `mergeTimeline()` blends activity_log events + session_messages client-side |
| Workspace provides implicit activity trail | File timestamps, contribution writes, assembly manifests — all project-scoped |
| Global activity page shows everything flat | No project grouping; PM events mixed with platform syncs and memory extraction |

---

## Decision

### Two-tier activity model

**Tier 1 — Workspace Activity (macro, user-level)**

The global activity log (`activity_log` table) narrows to workspace-level operational events — things that happened across the user's entire YARNNN workspace. This is the supervision layer: "what did my system do today?"

**Workspace-level event types** (remain in `activity_log`, shown on `/activity` page):

| Category | Events | Rationale |
|---|---|---|
| Platform | `platform_synced`, `content_cleanup`, `integration_connected`, `integration_disconnected` | Platform operations are workspace-wide |
| Composer | `composer_heartbeat`, `agent_bootstrapped`, `project_scaffolded`, `duty_promoted` | Portfolio-level orchestration |
| Memory | `memory_written`, `session_summary_written` | User-level knowledge extraction |
| System | `scheduler_heartbeat` | Infrastructure observability |
| Chat | `chat_session` | Global TP session activity |

**Tier 2 — Project Activity (micro, project-level)**

Projects already have three natural activity substrates. We formalize and enrich these rather than creating a new table:

| Substrate | Mechanism | Content |
|---|---|---|
| **Activity events** | `activity_log` rows with `project_slug` in metadata | PM decisions, assembly, steering, quality assessment, agent pulse/generation |
| **Conversation** | `session_messages` via project sessions (`chat_sessions.project_slug`) | Meeting room dialogue, @-mentions, agent responses |
| **Workspace changes** | `workspace_files` timestamps + folder structure | Contributions, briefs, assessments, output manifests |

### Structural changes

1. **Add `project_slug` to agent lifecycle events**: All `write_activity()` calls for agent events (`agent_scheduled`, `agent_generated`, `agent_pulsed`, `agent_approved`, `agent_rejected`, `agent_run`) include `project_slug` in metadata by resolving `agents.project_id` → project slug. This is a metadata enrichment, not a schema change.

2. **Project activity endpoint enrichment**: `/api/projects/{slug}/activity` expands `PROJECT_EVENT_TYPES` to include agent lifecycle events, filtered by the newly-populated `metadata.project_slug`.

3. **Global activity page becomes supervision dashboard**: The `/activity` page groups by workspace-level categories. Project-specific detail is accessed via project pages, not the global feed. Agent lifecycle events that belong to projects are still queryable globally but de-emphasized in favor of aggregate summaries.

4. **No new tables**: The existing `activity_log` table serves both tiers. The distinction is conceptual (which events belong to which scope) and presentational (where they surface), not structural.

### What this does NOT change

- `activity_log` table schema — no new columns. Project context lives in JSONB metadata (consistent with existing pattern).
- `write_activity()` function signature — unchanged.
- Working memory injection — still reads last 10 events for TP prompt.
- Meeting room timeline merge — `mergeTimeline()` continues to blend activity + chat.
- Append-only semantics — no updates, no deletes.

---

## Rationale

### Why not add a `project_slug` column?

The column approach was considered but rejected:

- Many events are genuinely workspace-scoped (platform syncs, memory extraction, composer heartbeat) — they don't belong to any project.
- Adding a nullable column creates ambiguity: does NULL mean "no project" or "project unknown"?
- JSONB metadata already carries project context for PM events. Extending this pattern to agent events is consistent and requires no migration.
- PostgREST `metadata->>project_slug` filtering works well and is already in production for the project activity endpoint.

### Why not a separate `project_activity` table?

- Violates singular implementation discipline — two tables for the same concept.
- The existing table handles both scopes via metadata filtering.
- Project activity is already naturally multi-substrate (events + conversation + filesystem). A dedicated table would only formalize one of the three substrates.

### Why lean into the three-substrate model?

Projects already have richer activity than `activity_log` alone could provide:

1. **Conversation** (session_messages) captures the WHY — decisions, discussions, @-mentions, agent responses. This is higher-fidelity than event summaries.
2. **Workspace** (workspace_files) captures the WHAT — actual files written, contributions made, briefs authored. Timestamps and paths tell the story.
3. **Events** (activity_log) capture the WHEN — structured, filterable, injectable into prompts.

Together, these three substrates provide a complete project activity picture without duplicating data.

---

## Consequences

### Positive
- Agent lifecycle events gain project context — project timelines become rich
- Global activity page becomes a focused supervision dashboard
- No schema migration required — metadata enrichment only
- Consistent with existing patterns (PM events already use metadata.project_slug)
- Three-substrate model leverages existing data instead of creating new stores

### Negative
- JSONB filtering is less efficient than column filtering (acceptable at current scale)
- Frontend needs to understand which events are "workspace-level" vs "project-level"
- Workspace changes (file writes) are not formal "events" — they're queryable by timestamp but don't appear in activity_log

### Risks
- Volume: With agent pulse events enriched with project_slug, project timelines may become noisy. Mitigation: frontend filtering by category; `wait` pulse decisions can be excluded from project view.
- Migration: Existing agent lifecycle events in activity_log lack project_slug in metadata. Historical events won't appear in project timelines. Acceptable — forward-only enrichment.

---

## Implementation Phases

### Phase 1: Agent event enrichment (backend) — IMPLEMENTED
- `resolve_agent_project_slug()` + `resolve_agent_project_slug_full()` utilities in `activity_log.py`
- `agent_pulse.py`: `_log_pulse_event()` enriches `agent_pulsed` metadata with project_slug
- `unified_scheduler.py`: `agent_scheduled` + `agent_generated` enriched with project_slug; `project_id` added to agent select
- `agent_execution.py`: Both PM and regular `agent_run` events enriched with project_slug
- `project_registry.py`: `scaffold_project()` sets `type_config.project_slug` on contributor agents at creation time (closes gap where only PM agents had project_slug in type_config)
- `routes/agents.py`: `agent_approved` + `agent_rejected` enriched with project_slug; `type_config` added to agent select
- `routes/projects.py`: `PROJECT_EVENT_TYPES` expanded to include `agent_pulsed`, `agent_run`, `agent_scheduled`, `agent_generated`, `agent_approved`, `agent_rejected`, `pm_pulsed`, `project_file_triaged`

### Phase 2: Global activity page refinement (frontend) — IMPLEMENTED
- Added missing EVENT_CONFIGs: `project_quality_assessed`, `project_contributor_steered`, `project_file_triaged`, `project_scaffolded`
- CATEGORY_EVENT_TYPES expanded: projects category now includes all 9 project event types
- Navigation targets: agent events with `project_slug` link to project page (prefer project over agent)
- Metadata detail renderers: all project events get dedicated renderers (heartbeat, quality, steer, triage, assembly, escalation, scaffold)
- Agent event renderers enriched with `project_slug` detail row
- Fixed `project_escalated` icon (Play → AlertTriangle)

### Phase 3: Project timeline enrichment (frontend) — IMPLEMENTED
- ACTIVITY_EVENT_CONFIG expanded with agent lifecycle events: `agent_run`, `agent_scheduled`, `agent_generated`, `agent_approved`, `agent_rejected`
- `formatActivitySummary()` handles all new event types with personified labels
- `mergeTimeline()` unchanged — already handles any event type from the activity endpoint
- `mergeTimeline()` already handles this — just needs the data from enriched endpoint

### Phase 4: Documentation
- Update `docs/features/activity.md` — version-controlled domain explanation
- Update `docs/architecture/four-layer-model.md` — Layer 2 section
- Update event type registry in `docs/features/activity.md`

---

## Key Files

| File | Role |
|---|---|
| `api/services/activity_log.py` | `write_activity()`, `VALID_EVENT_TYPES` |
| `api/routes/projects.py` | `PROJECT_EVENT_TYPES`, `/api/projects/{slug}/activity` |
| `api/routes/memory.py` | `/api/memory/activity` (global) |
| `api/services/agent_execution.py` | Agent lifecycle event writes |
| `api/services/agent_pulse.py` | Pulse event writes |
| `api/jobs/unified_scheduler.py` | Scheduler event writes |
| `web/app/(authenticated)/activity/page.tsx` | Global activity page, EVENT_CONFIG |
| `web/app/(authenticated)/projects/[slug]/page.tsx` | Project timeline, ACTIVITY_EVENT_CONFIG, mergeTimeline() |

---

## Related

- [ADR-063](ADR-063-activity-log-four-layer-model.md) — Activity layer origin
- [ADR-124](ADR-124-project-meeting-room.md) — Meeting room timeline (mergeTimeline)
- [ADR-125](ADR-125-project-native-session-architecture.md) — Project-scoped sessions
- [ADR-126](ADR-126-agent-pulse.md) — Pulse events (high-frequency activity source)
- [ADR-128](ADR-128-multi-agent-coherence-protocol.md) — Cognitive files (implicit workspace activity)
