# Architecture: The Execution Loop

**Status:** Canonical
**Date:** 2026-04-16
**Codifies:** ADR-141 (Unified Execution), ADR-154 (Execution Boundaries), ADR-173 (Accumulation-First), ADR-181 (Feedback Layer), ADR-182 (Pre-Gather)
**Related:**
- [agent-execution-model.md](agent-execution-model.md) — three-layer architecture (scheduler / pipeline / TP)
- [FEEDBACK-LOOP.md](../design/FEEDBACK-LOOP.md) — user-facing feedback affordances
- [workspace-conventions.md](workspace-conventions.md) — filesystem layout and directory registry
- [FOUNDATIONS.md](FOUNDATIONS.md) — Axiom 4 (accumulated attention compounds)

---

## Why This Doc Exists

The execution loop is the mechanism that makes recurring work compound. Without it, YARNNN is a one-shot generator. With it, every run builds on what came before — entities deepen, staleness is detected, agent focus self-directs, and outputs improve with tenure.

This doc describes the **full cycle**: what happens before, during, and after a single task execution, and how the outputs of run N become the inputs of run N+1. It is the operational companion to [agent-execution-model.md](agent-execution-model.md), which describes the *architecture* (three layers, trigger taxonomy, code paths) but not the *accumulation mechanics*.

---

## The Cycle at a Glance

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                     THE EXECUTION LOOP                          │
 │                                                                 │
 │  SCHEDULE ──► GATHER ──► GENERATE ──► WRITE-BACK ──► VERIFY    │
 │     │                                                    │      │
 │     │            ┌──────────────────────────────┐        │      │
 │     │            │     WORKSPACE STATE           │        │      │
 │     │            │  awareness.md (cycle state)   │        │      │
 │     │            │  _tracker.md (entity health)  │        │      │
 │     │            │  feedback.md (corrections)    │        │      │
 │     │            │  context/{domain}/ (knowledge)│        │      │
 │     │            │  outputs/latest/ (prior work) │        │      │
 │     │            └──────────────────────────────┘        │      │
 │     │                   ▲            │                    │      │
 │     │                   │    read     │   write           │      │
 │     │                   │            ▼                    │      │
 │     └───────────── RESCHEDULE ◄──────────────────────────┘      │
 │                                                                 │
 └─────────────────────────────────────────────────────────────────┘
```

Six phases, one pipeline, every run:

| Phase | What happens | LLM cost | Key file written |
|-------|-------------|----------|-----------------|
| **Schedule** | Scheduler finds due tasks via SQL | Zero | — |
| **Gather** | Read awareness, tracker, context, prior output | Zero | — |
| **Generate** | LLM produces output with tools | Sonnet | `outputs/{date}/output.md` |
| **Write-back** | Rebuild tracker, update awareness, log signals | Zero | `awareness.md`, `_tracker.md` |
| **Verify** | Check staleness, coverage, confidence; actuate | Zero | `feedback.md` (entries appended) |
| **Reschedule** | Calculate next_run_at from schedule + timezone | Zero | `tasks.next_run_at` (DB) |

LLM cost is incurred in **one phase only**. Everything else is mechanical.

---

## Phase 1: Schedule

**Code:** `api/jobs/unified_scheduler.py` — `get_due_tasks()`, `execute_due_tasks()`

The scheduler runs every 5 minutes via Render cron. It executes a single SQL query:

```sql
SELECT * FROM tasks WHERE status = 'active' AND next_run_at <= now()
```

For each due task, it performs an atomic Compare-And-Swap claim:

```sql
UPDATE tasks SET next_run_at = now() + '2 hours'
WHERE id = :id AND next_run_at = :original_value
```

If the CAS succeeds (row was updated), this scheduler instance owns the task. If another instance already claimed it, the update affects zero rows and the task is skipped. The +2h sentinel prevents re-entry during execution.

After execution completes, the real `next_run_at` is calculated and written (Phase 6).

**No LLM. No decisions. Pure SQL dispatch.**

---

## Phase 2: Gather

**Code:** `api/services/task_pipeline.py` — `gather_task_context()`

Context assembly is entirely mechanical (zero LLM). The function reads workspace files in priority order and concatenates them into the generation prompt.

### What gets read, and why

| Priority | Source | Purpose | Budget |
|----------|--------|---------|--------|
| 0 | `awareness.md` | Cycle-to-cycle handoff from prior run | Always |
| 0b | TASK.md `sources:` field | Platform source scope (which channels/pages/repos) | Always |
| 1 | `_tracker.md` | Entity registry — what exists, what's stale, what's discovered | Per write-domain |
| 2 | `/workspace/context/{domain}/` files | Accumulated intelligence from prior runs | Budget-controlled |
| 3 | AGENT.md + playbook index | Agent identity and behavioral guidance | Always |
| 4 | `notes.md` | User standing instructions | Always |
| 5 | `outputs/latest/output.md` + file listing | Prior output excerpt + asset inventory | 3000 chars max |

### Context budgets by output_kind

The budget prevents token bloat while ensuring the right depth:

| output_kind | Total file budget | Per-domain ceiling | Rationale |
|-------------|------------------|--------------------|-----------|
| `accumulates_context` | 8 files | 4 per domain | Agent researches via tools — only needs an index |
| `produces_deliverable` | 30 files | 10 per domain | Agent synthesizes — needs rich pre-loaded context |

Within each domain, files are selected by objective relevance: synthesis files (`_landscape.md`, `_overview.md`) load first, then entity files matching the task objective, then by recency.

### The awareness.md handoff

This is the load-bearing artifact for the loop. Written at the end of run N, read at the start of run N+1. It contains:

```markdown
# Task Awareness

## Last Cycle
- Run: 2026-04-15 09:00 UTC (v12)
- Duration: 45s, 3 tool rounds
- Entities touched (competitors): cursor, windsurf
- Tools used: WebSearch (2), WriteFile (3), ReadFile (1)
- Agent reflection: confidence=high

## Phase: steady
- Domain established. Normal cadence.

## Domain State
### competitors
- 5 active, 1 stale (replit — last updated 2026-04-02)

## Next Cycle Directive
- Replit is stale — check for funding/product announcements
- Windsurf shipped a major release last cycle — monitor user reception
- Skip Cursor this cycle (comprehensive profile, updated yesterday)
```

The **Next Cycle Directive** is the agent's own marching orders to its future self. Written while context is hot (journalist's notes). The step instruction template explicitly tells the agent to follow it:

> *"Check your Execution Awareness for a ## Next Cycle Directive. If one exists, FOLLOW IT as your primary guidance — it was written by you while the context was fresh."*

This is how focus self-directs across runs without TP involvement.

---

## Phase 3: Generate

**Code:** `api/services/task_pipeline.py` — `build_task_execution_prompt()`, `_generate()`

The LLM call. One Sonnet invocation per task execution.

### Prompt structure

```
System blocks (cached):
  1. Output rules (format, length)
  2. User context (identity, brand, preferences)
  3. Task objective (from TASK.md)
  4. Step instruction (from task type registry or TASK.md)
  5. DELIVERABLE.md (quality contract)
  6. Accumulated context (from Phase 2)
  7. Recent feedback (last 3 entries from feedback.md)
  8. Prior output / awareness (from Phase 2)
  9. Generation brief (produces_deliverable only — section-level staleness)

User message:
  "Execute the task above. Generate [format]."
```

### Tool surface by output_kind (ADR-182)

| output_kind | Tools available | Max rounds | Rationale |
|-------------|----------------|------------|-----------|
| `accumulates_context` | Full (ReadFile, WriteFile, WebSearch, platform tools) | 10+ | Agent's job IS to research and write context |
| `produces_deliverable` (steady) | WriteFile + RuntimeDispatch only | 2 | Context pre-gathered; agent only writes output + assets |
| `produces_deliverable` (bootstrap) | Full | 10+ | First runs need research capability |
| `external_action` | Full + platform write tools | 10+ | Agent posts to Slack/Notion/etc. |

### Agent reflection

At the end of generation, the agent writes a structured reflection block:

```markdown
<!-- agent-reflection
output_confidence: high — all entities updated with current data
criteria_met: 4/5 quality criteria satisfied
next_cycle_directive: Replit has gone quiet — check if they pivoted or went dark. Also monitor new entrant Devin closely.
-->
```

The pipeline extracts this (stripped from delivered output) and feeds it into the write-back phase.

---

## Phase 4: Write-back

**Code:** `api/services/task_pipeline.py` — `_post_run_domain_scan()`

Three deterministic writes after every run. Zero LLM cost.

### 4a. Signal log

Appends a dated entry to `/workspace/context/signals/{YYYY-MM-DD}.md`:

```markdown
## Track Competitors v12 (09:00 UTC)
- Task: track-competitors
- Output: 4200 chars
- Summary: Updated Cursor and Windsurf profiles. Replit flagged stale...
```

Cross-domain signal log — any task can read it. Creates a chronological record of what happened across the workspace.

### 4b. Entity tracker rebuild

For each domain in `context_writes`:

1. **Scan** all files under `/workspace/context/{domain}/`
2. **Extract** entity subfolders (e.g., `acme-corp/profile.md` → entity `acme-corp`)
3. **Compute staleness** per entity based on task schedule:

   | Schedule | Stale threshold |
   |----------|----------------|
   | daily | 3 days |
   | weekly | 10 days |
   | monthly | 45 days |

4. **Write** materialized `_tracker.md`:

   ```markdown
   | Slug | Status | Last Updated | Files |
   |------|--------|-------------|-------|
   | cursor | active | 2026-04-15 | profile, analysis |
   | windsurf | active | 2026-04-15 | profile |
   | replit | stale | 2026-04-02 | profile, analysis |
   ```

The tracker is rebuilt from scratch every run — it's a materialized view, not a log. Next run reads it in Phase 2 to know what needs attention.

### 4c. Awareness update

Overwrites `/tasks/{slug}/awareness.md` with the current cycle state (see Phase 2 for the format). Derives:

- **Phase** (bootstrap or steady) from bootstrap criteria vs. entity count
- **Domain health** from tracker data
- **Next cycle directive** from agent reflection, staleness flags, or phase-appropriate defaults

This is the cycle-to-cycle handoff — run N writes it, run N+1 reads it.

---

## Phase 5: Verify

**Code:** `api/services/task_pipeline.py` — `_compute_system_verification()`, `api/services/feedback_actuation.py` — `evaluate_actuation_rules()`

Two mechanical steps that close the self-correcting loop.

### 5a. System verification → feedback.md entries

Zero-LLM deterministic checks. Writes entries to `feedback.md` when thresholds are crossed:

| Check | Condition | Entry written |
|-------|-----------|--------------|
| Entity staleness | Entity last_updated beyond schedule-based threshold | `Action: flag stale entity {slug} ({domain})` |
| Coverage gap | Steady-phase task with active entities < min_entities | `Action: expand coverage {domain}` |
| Low confidence | 2+ consecutive runs with agent confidence = low | `Action: review data sources` |

These entries accumulate in `feedback.md` alongside user feedback and TP evaluations. All sources use the same format — the system is source-agnostic (ADR-181).

### 5b. Feedback actuation → workspace mutations

Matches accumulated feedback entries against actuation rules:

| Rule | Trigger pattern | User threshold | System threshold | Effect |
|------|----------------|----------------|-----------------|--------|
| `remove_entity` | "remove entity X/Y" | 1 (immediate) | 999 (never auto) | Marks entity inactive in profile.md |
| `stale_entity` | "flag stale entity X" | 1 (immediate) | 3 (accumulate) | Marks entity inactive |
| `restore_entity` | "restore entity X/Y" | 1 (immediate) | 999 (never auto) | Removes inactive marker |
| `expand_coverage` | "expand coverage X" | 1 (immediate) | 2 (accumulate) | Prompt-only (no mutation) |

**Key design**: User feedback actuates immediately (threshold 1 — explicit intent). System feedback accumulates across runs (threshold 3 — distinguishes transient noise from real drift). Stale system entries are aged out after 3 runs.

After actuation, the results are recorded in the awareness.md `## Actuation Log` section so the agent knows what workspace changes were made.

---

## Phase 6: Reschedule

**Code:** `api/services/schedule_utils.py` — `calculate_next_run_at()`

Computes the next occurrence from the task's schedule string and the user's timezone:

```python
# Input: schedule="weekly", last_run_at=now, timezone="America/New_York"
# Output: next Monday 09:00 in user's timezone, converted to UTC
```

Supported formats:
- Simple cadence: `"daily"`, `"weekly"`, `"biweekly"`, `"monthly"`
- Cron expression: `"0 9 * * 1"` (Monday at 9am)
- Schedule dict: `{"frequency": "weekly", "day": "monday", "time": "09:00"}`

Updates the tasks table:

```sql
UPDATE tasks SET last_run_at = :now, next_run_at = :calculated WHERE slug = :slug
```

The scheduler's next 5-minute sweep will find this task again when `next_run_at <= now()`.

---

## How Accumulation Works Across Runs

The loop compounds through five substrates, each written by one run and read by the next:

### 1. Context domain files (entity knowledge)

**Writer:** `accumulates_context` tasks via WriteFile tool calls during generation.
**Reader:** All tasks via `gather_task_context()` Phase 2 pre-loading.
**Growth pattern:** Additive. Entity profiles deepen, new entities are created, synthesis files are updated.
**Example:** Run 1 creates `competitors/cursor/profile.md`. Run 2 adds funding data. Run 5 adds product launch analysis. Run 12 has a rich competitive profile built across 3 months of weekly updates.

### 2. Entity tracker (domain health view)

**Writer:** `_post_run_domain_scan()` — rebuilt from scratch every run.
**Reader:** `gather_task_context()` — injected as "Entity Tracker: {domain}" section.
**Growth pattern:** Replacive (materialized view). Grows indirectly as entities are added.
**Effect:** Agent sees what exists, what's stale, and what's missing. Stale entities get prioritized in the next cycle directive.

### 3. Awareness.md (cycle handoff)

**Writer:** `_post_run_domain_scan()` — overwritten every run.
**Reader:** `gather_task_context()` — injected as "Execution Awareness" section.
**Growth pattern:** Replacive (one-deep). Only the most recent cycle's state is preserved.
**Effect:** The Next Cycle Directive self-directs agent focus. Phase detection (bootstrap vs steady) changes prompt behavior.

### 4. Feedback.md (corrections and signals)

**Writer:** Three sources — user (via TP chat), system verification (post-run), TP evaluation (ManageTask evaluate).
**Reader:** `build_task_execution_prompt()` — last 3 entries injected into generation prompt.
**Growth pattern:** Append-only with aging. System entries aged out after 3 runs. User entries persist.
**Effect:** Shapes generation behavior. Also triggers actuation (workspace mutations) when thresholds are met.

### 5. Output history (prior work)

**Writer:** Pipeline saves to `outputs/{date}/` and `outputs/latest/`.
**Reader:** `gather_task_context()` — prior output excerpt (3000 chars) + output inventory.
**Growth pattern:** Dated folders accumulate. `latest/` always points to most recent.
**Effect:** Agent knows what it produced last cycle. For `produces_deliverable` tasks, the derive-output instruction says "emphasize what CHANGED since last cycle."

---

## The Two-Kind Engine

The execution loop serves two fundamentally different kinds of work, and the interaction between them IS the accumulation architecture:

```
accumulates_context tasks          produces_deliverable tasks
       (engine)                          (derivative)
         │                                    │
         │  write to                          │  read from
         ▼                                    ▼
  /workspace/context/{domain}/  ◄────────────────────
         │                                    │
    Entity files                         Synthesized output
    _tracker.md                          (report, brief, update)
    _landscape.md                              │
         │                                     │
         └──── shared workspace ──────────────┘
```

**Context tasks** fill the workspace. They research, discover entities, update profiles, fetch platform data. Their output is a CHANGELOG — not the product itself.

**Deliverable tasks** read the workspace and produce user-facing artifacts. They synthesize accumulated context into reports, briefs, and updates. Their output is the product.

**The workspace is the memory between them.** A `track-competitors` task running weekly builds the intelligence. A `competitor-brief` task running weekly reads that intelligence and produces a report. The brief gets better because the context gets deeper.

---

## Bootstrap → Steady Phase Transition

Context tasks (`accumulates_context`) have a two-phase lifecycle:

### Bootstrap phase
- **Trigger:** Entity count below `bootstrap.min_entities` in the task type registry
- **Behavior:** Aggressive entity discovery. Bootstrap-specific step instruction replaces normal instruction:
  > *"You are BOOTSTRAPPING this context domain — it has few or no entity profiles yet. YOUR #1 PRIORITY: Create entity files using WriteFile."*
- **Tool surface:** Full (needs WebSearch + WriteFile for discovery)
- **Next cycle directive:** "BOOTSTRAP PRIORITY: Discover and profile new entities"

### Steady phase
- **Trigger:** Entity count meets `bootstrap.min_entities` AND entities have `required_files`
- **Behavior:** Normal cadence. Update stale entities, deepen profiles, discover incrementally.
- **Tool surface:** Normal for output_kind
- **Next cycle directive:** Agent-authored (from reflection) or staleness-driven

Phase is **derived at runtime** — not stored. The pipeline reads the tracker, counts qualified entities, and determines phase each run. This means a task can regress to bootstrap if entities are removed.

---

## Mode-Specific Loop Behavior

Mode (`recurring`, `goal`, `reactive`) affects the loop's posture, not its mechanics:

| Aspect | recurring | goal | reactive |
|--------|-----------|------|----------|
| Schedule | Runs on cadence | Runs on cadence until complete | No schedule (manual trigger) |
| Prior output | Excerpt (3000 chars) | Full output injected (revision) | Excerpt |
| Output handling | New dated folder + update latest/ | Archive old latest/ → new latest/ | New dated folder + update latest/ |
| Reschedule | `calculate_next_run_at()` | `calculate_next_run_at()` (until TP completes) | `next_run_at = None` |
| TP posture | Auto-deliver, periodic evaluation | Evaluate → steer → complete | Dispatch-and-done |

**Recurring** is the default. The loop runs indefinitely, outputs compound, the system gets better.
**Goal** converges toward a target. Each run revises the prior output. TP completes the task when the goal is met.
**Reactive** is one-shot per trigger. No loop — the task fires when triggered and waits.

---

## What Does NOT Accumulate (Known Gaps)

These are architectural observations, not bugs:

1. **Cross-task freshness.** A `produces_deliverable` task has no signal for whether its upstream `accumulates_context` tasks have run recently. If the context task is paused, the deliverable task synthesizes stale data silently.

2. **Multi-cycle awareness history.** `awareness.md` is overwritten each run (one-deep). A great next_cycle_directive from run N is lost if run N+1 overwrites it with different priorities. The entity files themselves accumulate, but the execution strategy is memoryless beyond one cycle.

3. **Output quality feedback.** System verification checks entity staleness and coverage, not output quality. Agent confidence is self-reported. There is no mechanical quality gate — TP evaluation (`ManageTask(action="evaluate")`) is manual and ad-hoc.

4. **"Nothing changed" fast-path.** If no context domain files have been updated since the last deliverable run, the task still generates a full report. No skip-if-stale optimization exists.

5. **Actuation scope.** Feedback actuation only mutates entity status (active/inactive). It cannot change research focus, add domains, or adjust cadence — those require TP intervention.

---

## Key Files

| Concern | File |
|---------|------|
| Scheduler dispatch | `api/jobs/unified_scheduler.py` |
| Full pipeline + all phases | `api/services/task_pipeline.py` |
| Feedback actuation rules | `api/services/feedback_actuation.py` |
| Task type registry (step instructions) | `api/services/task_types.py` |
| Schedule calculation | `api/services/schedule_utils.py` |
| Workspace abstraction | `api/services/workspace.py` |
| Task workspace abstraction | `api/services/task_workspace.py` |
| Directory registry (domain config) | `api/services/directory_registry.py` |

---

## Relationship to Other Docs

- **[agent-execution-model.md](agent-execution-model.md)** describes the three-layer *architecture* (what the layers are, what triggers exist, what code runs). This doc describes the *loop mechanics* (how run N feeds run N+1).
- **[FEEDBACK-LOOP.md](../design/FEEDBACK-LOOP.md)** describes the *user-facing* feedback affordances (buttons, prompt relays, TP solicitation). This doc describes the *mechanical* feedback loop (system verification, actuation, aging).
- **[workspace-conventions.md](workspace-conventions.md)** describes the *filesystem layout*. This doc describes how that layout is *used* across cycles.
- **[FOUNDATIONS.md](FOUNDATIONS.md)** Axiom 4 states the thesis ("accumulated attention compounds"). This doc describes the mechanism.
