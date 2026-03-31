# Task Surface Redesign — ADR-149/151 Frontend Surfacing

**Status:** Proposed (deferred from backend implementation)  
**Date:** 2026-03-31  
**Depends on:** ADR-149 (task lifecycle), ADR-151 (context domains)  
**Implements:** ADR-149 Phase 6

---

## Context

The backend now supports:
- DELIVERABLE.md quality contracts per task
- memory/feedback.md (user corrections + TP evaluations)
- memory/steering.md (TP management notes)
- /workspace/context/ accumulated context domains
- ManageTask evaluate/steer/complete actions
- Diff-aware output derivation

The frontend task page (`/tasks/[slug]`) currently shows: Output, Task (definition), Schedule, Process. None of the new backend capabilities are surfaced.

---

## Proposed Changes

### Task Detail Page — Left Panel Tabs

**Current tabs:** Output | Task | Schedule | Process

**Proposed tabs:** Output | Deliverable | Context | Schedule | Process

#### Tab: Output (existing, enhanced)
- Latest output (HTML iframe) — no change
- **NEW:** Diff indicator — "What's new this cycle" badge if recurring task
- **NEW:** Evaluation summary card (if ManageTask evaluate has been run): criteria_met, gaps, recommendation

#### Tab: Deliverable (NEW — replaces "Task" tab)
- Renders DELIVERABLE.md as editable sections:
  - Expected Output (format, word count, layout)
  - Expected Assets (persistent + per-output)
  - Quality Criteria (editable list)
  - Audience
  - User Preferences (inferred) — read-only, auto-populated from feedback inference
- Edit actions save via UpdateContext(target="task", feedback_target="criteria"|"objective")
- **Feedback History** section: scrollable list of memory/feedback.md entries
  - Entries tagged: user_edit | user_conversation | evaluation
  - Each entry shows date, source, summary
- **Steering Notes** section: current memory/steering.md content
  - Shows TP's guidance for next cycle
  - Read-only (TP writes via ManageTask steer)

#### Tab: Context (NEW)
- Lists context domains this task reads/writes (from task type's context_reads/context_writes)
- For each domain:
  - Domain name + entity count + latest update
  - Expandable: list of entity folders with file previews
  - Health indicator: active | seeded | empty
- Links to workspace-level context browser (if built)

#### Tab: Schedule (existing, enhanced)
- **NEW:** Mode indicator with explanation:
  - Recurring: "Runs on schedule. Accumulates context. Output emphasizes changes."
  - Goal: "Runs until criteria met. TP evaluates after each run."
  - Reactive: "Runs when triggered. No scheduled cadence."
- **NEW:** Evaluation trigger controls:
  - "Evaluate now" button (calls ManageTask evaluate)
  - "Steer next run" text input (calls ManageTask steer)
  - "Mark complete" button for goal tasks (calls ManageTask complete)

#### Tab: Process (existing, no change)
- Process agents and step definitions
- Run progress for in-flight executions

---

### Workfloor — Context Section

**Current:** Tasks | Context (Identity, Brand, Documents) | Platforms

**Proposed addition:** Context tab gains a "Domains" sub-tab:
- Grid of 6 domain cards (competitors, market, relationships, projects, content, signals)
- Each card: domain name, entity count, file count, latest update, health
- Click → domain detail page (entity list, file browser, synthesis file preview)

This gives users visibility into accumulated context without navigating to individual tasks.

---

### Task List — Mode Indicators

**Current:** Task cards show title, status, schedule, agent

**Proposed additions:**
- Mode badge (recurring | goal | reactive) with color coding
- Context domain tags showing which domains this task touches
- Last evaluation summary (if available): "3/3 criteria met" or "2/3 — steering active"

---

## Implementation Priority

| Feature | Effort | Value | Priority |
|---|---|---|---|
| Deliverable tab (DELIVERABLE.md rendering) | Medium | High | P0 |
| Feedback history in Deliverable tab | Small | High | P0 |
| Mode indicators on task list/detail | Small | Medium | P1 |
| Context tab (domain listing per task) | Medium | Medium | P1 |
| Evaluation controls (evaluate/steer/complete buttons) | Medium | High | P1 |
| Workfloor domains sub-tab | Large | Medium | P2 |
| Diff indicator on output | Small | Medium | P2 |

---

## API Dependencies

All backend support exists. Frontend calls needed:

| Feature | API Call | Exists? |
|---|---|---|
| Read DELIVERABLE.md | `GET /api/tasks/{slug}` (already returns DELIVERABLE.md from workspace) | Verify |
| Read feedback.md | TaskWorkspace read via API | Need endpoint or include in task response |
| Read steering.md | TaskWorkspace read via API | Need endpoint or include in task response |
| Evaluate task | ManageTask(action="evaluate") via chat | Yes |
| Steer task | ManageTask(action="steer") via chat | Yes |
| Complete task | ManageTask(action="complete") via chat | Yes |
| Context domain health | Need API endpoint | New: `/api/workspace/context/health` |
| Domain file listing | Need API endpoint | New: `/api/workspace/context/{domain}` |

---

## References

- [ADR-149: Task Lifecycle Architecture](../adr/ADR-149-task-lifecycle-architecture.md)
- [ADR-151: Shared Context Domains](../adr/ADR-151-shared-knowledge-domains.md)
- [Registry Matrix](../architecture/registry-matrix.md)
- [SURFACE-ACTION-MAPPING.md](SURFACE-ACTION-MAPPING.md)
