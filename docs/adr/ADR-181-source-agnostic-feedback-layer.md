# ADR-181: Source-Agnostic Feedback Layer

**Date:** 2026-04-15
**Status:** Phase 1-3 Implemented (2026-04-15). Phase 4 (frontend) deferred.
**Extends:** ADR-149 (Task Lifecycle), ADR-151 (Shared Context Domains), ADR-154 (Post-Run Domain Scan), ADR-162 (Inference Hardening)
**Supersedes:** Feedback portions of FEEDBACK-LOOP.md (surface affordance design preserved; architectural model replaced)

---

## Context

YARNNN's feedback infrastructure exists in pieces that work independently but are not unified as an architectural layer:

- **User feedback** writes to `memory/feedback.md` via `UpdateContext(target="task")` with `source: user_conversation`
- **TP evaluation** writes to the same file via `ManageTask(action="evaluate")` with `source: evaluation`
- **Agent reflection** writes to `awareness.md` via `_post_run_domain_scan()` as informational context
- **Domain health** is computed by `_post_run_domain_scan()` into `_tracker.md` per domain

These share no common abstraction. More critically, feedback **informs but never actuates** — writing "stop tracking Acme" to feedback.md doesn't remove Acme from the entity tracker. The signal and the structural consequence are disconnected. The agent reads "stop tracking Acme" in its prompt on the next run but has no mechanism to execute the removal. The entity persists, consumes context budget, and may be re-researched.

The system also lacks a **deterministic verification source** — no zero-LLM mechanism writes feedback when workspace state drifts (stale entities, coverage gaps, empty domains). The only system-generated feedback is TP evaluation, which costs a Haiku call and only runs when TP chooses to in conversation.

### Strategic context

The product direction positions YARNNN as infrastructure for autonomous information businesses (session notes, April 15 2026). Autonomous operation means the user is increasingly absent. A feedback layer that depends on user presence to detect and correct problems is structurally insufficient. The system needs to generate its own feedback and act on it.

---

## Decision

### Principle: Feedback is a source-agnostic layer

Feedback is feedback regardless of who generated it. The layer that stores, injects, and actuates feedback is identical for all sources. What varies is the **input mechanism** — how feedback enters the layer. Once inside, every entry has the same format, the same injection path into the next run, and the same actuation potential.

This is analogous to a Fortune 500 company hiring an external auditor. The auditor's findings go into the same governance process as internal findings. The process doesn't care who found the problem — it cares that the problem was found and needs resolution.

### Three sources, one layer

| Source | Mechanism | Cost | When |
|--------|-----------|------|------|
| **User** | TP chat → `UpdateContext(target="task")`, or future direct CRUD | TP conversation cost, or zero | User-initiated |
| **System verification** | `_compute_verification()` post-run in pipeline | Zero LLM | Every run |
| **TP evaluation** | `ManageTask(action="evaluate")` → Haiku | ~$0.01 | TP-initiated or scheduled |

All three write to the same file (`memory/feedback.md`) in the same format. The pipeline reads them identically.

### Feedback entry format (unified)

```markdown
## {Type} ({datetime}, source: {source_tag})
- {observation}
- Action: {recommended_action} | severity: {low|medium|high}
```

**Source tags:** `user_conversation`, `user_edit`, `system_verification`, `evaluation`, `system_lifecycle`

**Types:** `User Feedback`, `System Verification`, `Evaluation`

The `Action:` line is new. It declares what should happen — not just what was observed. This is the bridge between feedback-as-information and feedback-as-actuation.

### Two tiers of processing

**Tier 1 — Injection (every run, zero cost)**

`_extract_recent_feedback()` already reads the last N entries from `feedback.md` and injects them into the generation prompt as `## Recent Feedback`. This is unchanged. The agent sees all recent feedback regardless of source.

**Tier 2 — Actuation (threshold-gated, source-aware)**

New concept: certain feedback entries carry actionable recommendations that should result in workspace mutations, not just prompt injection. Actuation is a post-run step in the pipeline that reads accumulated feedback and executes structural changes when thresholds are met.

Actuation rules are **deterministic** — Python functions, not LLM judgment. They read the `Action:` line from feedback entries and execute when conditions are met.

---

## Actuation Model

### The gap this fills

Current state: user says "stop tracking Acme" → TP writes to feedback.md → agent reads it next run → agent produces output without Acme → but Acme's entity folder persists, tracker still lists it, next tracking run may re-research it.

Target state: user says "stop tracking Acme" → TP writes to feedback.md with `Action: remove entity competitors/acme` → post-run actuation step reads this → calls `ManageDomains(action="remove")` logic → entity soft-retired in tracker → next run doesn't see it in active entities.

Same mechanism for system verification: system detects entity stale for 3x cadence → writes `Action: flag stale entity competitors/acme | severity: medium` → after N consecutive stale flags, actuation step soft-retires the entity.

### Actuation rules

Actuation rules are registered in a `FEEDBACK_ACTUATION_RULES` registry. Each rule:
- Matches on `Action:` line pattern
- Has a threshold (how many matching entries before acting)
- Has an executor (Python function that performs the mutation)
- Has a severity gate (only actuate at or above a severity level)

Initial rules:

| Action pattern | Threshold | Executor | Effect |
|---------------|-----------|----------|--------|
| `remove entity {domain}/{slug}` | 1 (user), 3 (system) | `_actuate_remove_entity()` | Soft-retire entity via existing ManageDomains logic |
| `flag stale entity {domain}/{slug}` | 3 consecutive | `_actuate_stale_entity()` | Soft-retire entity, write note to awareness.md |
| `expand coverage {domain}` | 2 (system) | No mutation — prompt amplification only | Injects priority signal into next generation prompt |
| `adjust focus {section}` | 1 (user) | No mutation — prompt amplification only | Injects section-specific guidance into generation brief |

**User-sourced actions actuate immediately** (threshold 1) because the user has explicit intent. **System-sourced actions accumulate** before actuating because they're observational — a single stale flag might be transient; three consecutive flags indicate real drift.

### Actuation execution point

Actuation runs in `_post_run_domain_scan()`, after feedback entries are written but before `next_run_at` is advanced. This ensures:
1. System verification entries from the current run are available
2. Accumulated entries from prior runs (user + system) are checked
3. Mutations happen before the next scheduling cycle
4. All actuation is logged in `awareness.md`

```
execute_task()
  → generate output
  → _post_run_domain_scan()
      → compute verification signals (existing)
      → write system verification entries to feedback.md (NEW)
      → read all feedback.md entries (NEW)
      → evaluate actuation rules against accumulated entries (NEW)
      → execute qualifying mutations (NEW)
      → update awareness.md with actuation log (NEW)
  → compose HTML
  → deliver
  → advance next_run_at
```

---

## System Verification Checks

These are the deterministic checks that produce `source: system_verification` entries. All computed from data already available in `_post_run_domain_scan()`.

### Check 1: Entity staleness

**Signal:** Entity's `last_updated` older than `stale_days` threshold (already computed — line 723 of task_pipeline.py).

**Entry written when:** Entity marked stale in tracker rebuild AND entity was stale in the previous run's tracker too (prevents single-run transient flags).

**Format:**
```markdown
## System Verification (2026-04-15 03:00, source: system_verification)
- Entity competitors/acme last updated 2026-03-01 (45 days ago, threshold: 14 days)
- Action: flag stale entity competitors/acme | severity: medium
```

### Check 2: Coverage gap

**Signal:** Task declares `context_reads` for a domain, but domain has fewer entities than expected by task type's `min_entities` bootstrap criteria.

**Entry written when:** Domain entity count is below bootstrap threshold AND task is past bootstrap phase (prevents flagging during initial ramp-up).

**Format:**
```markdown
## System Verification (2026-04-15 03:00, source: system_verification)
- Domain competitors has 2 entities (min expected: 3 for track-competitors)
- Action: expand coverage competitors | severity: low
```

### Check 3: Agent low confidence

**Signal:** Agent reflection includes `output_confidence` starting with "low" (already extracted in `_post_run_domain_scan()`).

**Entry written when:** Low confidence on current run AND at least one of the previous 2 runs also had low confidence (prevents single-run noise).

**Format:**
```markdown
## System Verification (2026-04-15 03:00, source: system_verification)
- Agent reported low confidence for 2 consecutive runs
- Action: review data sources | severity: medium
```

### Check 4: Output stagnation (future — Phase 2)

**Signal:** Current output diff against previous output is below a threshold (low change rate across runs for a recurring task).

**Deferred:** Requires output diffing infrastructure not yet built.

---

## Context Health Layer (parallel mechanism)

Task feedback and context health are parallel but structurally different:

| Aspect | Task feedback layer | Context health layer |
|--------|-------------------|---------------------|
| **Storage** | `memory/feedback.md` (episodic entries) | `_tracker.md` (continuous snapshot) |
| **Cadence** | Accumulated, newest-first, capped | Rebuilt every run |
| **Nature** | Episodic — things that happened | Continuous — current state |
| **Consumers** | Generation prompt, DELIVERABLE.md inference, actuation rules | Generation prompt, TP evaluation, frontend Context surface |
| **Source-agnostic?** | Yes — user, system, TP evaluation | N/A — always system-computed |

The `_tracker.md` files already serve as the context health model. They compute entity freshness, file completeness, and status. They're rebuilt every run by `_post_run_domain_scan()`. No architectural change needed — they're already the right mechanism.

The connection between the two: system verification checks READ `_tracker.md` state and WRITE feedback entries when thresholds are crossed. The tracker is the sensor; feedback.md is the signal; actuation rules are the effector.

```
_tracker.md (sensor) → system verification (signal) → feedback.md (record) → actuation (effector)
```

---

## File convention changes

### Rename: `memory/feedback.md` → `feedback.md`

Move feedback out of the `memory/` subdirectory to task root. Feedback is not agent memory — it's a first-class operational artifact of the task, parallel to TASK.md and DELIVERABLE.md.

```
/tasks/{slug}/
├── TASK.md              (charter — what to do)
├── DELIVERABLE.md       (quality contract — what good looks like)
├── feedback.md          (feedback layer — what needs to change)  ← MOVED from memory/
├── memory/
│   ├── steering.md      (TP cycle-specific directives)
│   ├── awareness.md     (task situational awareness)
│   └── run_log.md       (execution history)
└── outputs/
    └── latest/
```

**Rationale:** feedback.md is as important as DELIVERABLE.md — it drives inference, injection, and now actuation. Burying it in `memory/` undersells its architectural role. TASK.md defines intent. DELIVERABLE.md defines quality. `feedback.md` defines corrections. They're peers.

### Entry format standardization

All writers (UpdateContext, ManageTask evaluate, system verification) adopt the unified format:

```markdown
## {Type} ({datetime}, source: {source_tag})
- {observation}
- Action: {action_directive} | severity: {severity}
```

The `Action:` line is optional for user feedback (user may just say "the tone was wrong" with no specific action). When absent, the entry is injection-only (prompt influence) with no actuation potential. When present, actuation rules can match on it.

For system verification, `Action:` is always present — the check knows what it detected and what should be done.

### Actuation log in awareness.md

When actuation rules fire, the mutation is logged in `awareness.md`:

```markdown
## Actuation Log
- 2026-04-15 03:00: Soft-retired entity competitors/acme (stale 3 consecutive runs)
- 2026-04-14 03:00: Expanded coverage priority for competitors domain (2/3 min entities)
```

This gives the agent (and TP during evaluation) visibility into what structural changes happened and why.

---

## Injection and roll-up mechanics

### Injection (every run)

`_extract_recent_feedback()` reads last 3 entries from `feedback.md` (unchanged behavior, new file path). Injected into generation prompt as `## Recent Feedback — Incorporate these corrections:`.

The agent sees user corrections, system verification flags, and TP evaluations identically. It doesn't need to know who wrote them — it just needs to respond to them.

### Roll-up / inference (threshold-gated)

`infer_task_deliverable_preferences()` fires when feedback.md has ≥2 new entries since last inference (tracked via `<!-- last_inference: timestamp -->` in DELIVERABLE.md). This is unchanged — it already reads all entries regardless of source.

The inference prompt should be updated to recognize system verification entries as a valid signal source. Currently it says "user corrections + TP evaluations." It should say "all feedback entries" and treat them equally during pattern extraction.

### Actuation (threshold-gated, per rule)

Post-run in `_post_run_domain_scan()`. Reads all entries, matches against `FEEDBACK_ACTUATION_RULES`, checks thresholds, executes qualifying mutations. Logs to awareness.md.

### Frequency

- **System verification writes:** Every run (zero cost — deterministic checks on already-computed data)
- **Feedback injection:** Every run (reads last 3 entries — already happening)
- **Inference roll-up:** When ≥2 new entries accumulate (LLM cost, ~$0.03 Sonnet)
- **Actuation:** Every run (checks rules — zero cost; executes mutations only when thresholds met)

---

## What this does NOT add

- **No new primitives.** System verification and actuation are pipeline-internal. User feedback still routes through existing `UpdateContext` and `ManageTask`. TP evaluation still uses `ManageTask(action="evaluate")`.
- **No new database tables.** Feedback stays in the filesystem (`feedback.md`). Actuation uses existing `ManageDomains` logic for entity mutations.
- **No scheduled feedback jobs.** System verification runs as part of every task execution, not as a separate cron. Consistent with ADR-156 (single intelligence layer — no background LLM jobs).
- **No approval gates.** Actuation executes when thresholds are met. No human review required. The user can override by writing contradicting feedback ("keep tracking Acme" overrides a stale-retirement).
- **No new LLM calls for system verification.** All checks are deterministic Python against filesystem metadata.

---

## Implementation plan

### Phase 1 — Unified feedback format + system verification writes

1. Standardize feedback entry format (add `Action:` line support)
2. Move `memory/feedback.md` → `feedback.md` (update all readers/writers: `update_context.py`, `manage_task.py`, `task_pipeline.py`, `task_deliverable_inference.py`, `feedback_distillation.py`)
3. Add `_compute_system_verification()` to `task_pipeline.py` — called from `_post_run_domain_scan()`, writes entries to `feedback.md` for staleness and coverage gaps
4. Update `_extract_recent_feedback()` to read from new path

**Cost:** Zero new LLM calls. File path changes + ~80 lines new Python.

### Phase 2 — Actuation rules

1. Define `FEEDBACK_ACTUATION_RULES` registry in `task_pipeline.py` (or new `api/services/feedback_actuation.py`)
2. Add `_evaluate_actuation_rules()` — reads feedback.md, matches rules, executes qualifying mutations
3. Wire into `_post_run_domain_scan()` after system verification writes
4. Log actuations to `awareness.md`

**Cost:** Zero new LLM calls. ~120 lines new Python. Uses existing ManageDomains logic for entity mutations.

### Phase 3 — Inference update + TP prompt guidance

1. Update `task_deliverable_inference.py` prompt to treat system verification entries as equal signals
2. Add TP prompt guidance for feedback solicitation rules (from FEEDBACK-LOOP.md Phase 2)
3. Update `api/prompts/CHANGELOG.md`

**Cost:** Prompt changes only. No new code paths.

### Phase 4 — Frontend affordances

Three surfaces gain feedback affordances. All use prompt-relay to TP chat (no new primitives, no CRUD).

#### 4a. FeedbackStrip on Work detail (from FEEDBACK-LOOP.md)

New component: `web/components/work/details/FeedbackStrip.tsx`

Sits below KindMiddle in `WorkDetail`, above AssignedAgentFooter. Only rendered when `last_run_at` is set (task has produced output).

Per-output_kind buttons (prompt relays via `onOpenChat(prompt)`):

| output_kind | Primary | Secondary | Universal |
|-------------|---------|-----------|-----------|
| `produces_deliverable` | "This looks good" | "Something's off" | Edit in TP |
| `accumulates_context` | "Looks comprehensive" | "Missing something" | Edit in TP |
| `external_action` | "Delivery was right" | "Adjust what's sent" | Edit in TP |
| `system_maintenance` | — (no strip) | — | — |

Daily-update special case: no "This looks good" (ambient, not evaluated). Only "Something's off" + Edit in TP.

#### 4b. Context-sensitive "Edit via chat" on Files surface

The Context/Files surface currently has no affordance for the user to act on what they see. Add an "Edit via chat" action that pre-fills TP chat with context about what the user is viewing.

**Three placement contexts:**

| Viewing | Button label | Pre-filled prompt |
|---------|-------------|-------------------|
| Domain folder (`/workspace/context/competitors/`) | "Edit via chat" (MessageSquare icon) | `"Adjust what's tracked in competitors: "` |
| Entity subfolder (`/workspace/context/competitors/acme/`) | "Edit via chat" | `"About the competitor acme: "` |
| File (`profile.md`, `summary.md`, etc.) | "Edit via chat" | `"About this file ({relative path}): "` |

**Implementation:** Add an "Edit via chat" button to `ContentViewer.tsx`:
- In `DirectoryView` header (domain/entity folder): next to the folder name
- In `FileView` header (file): alongside Open/Download in `FileActions`

The button calls the existing `sendMessage` (or navigates to chat with pre-fill) with the context-appropriate prompt. TP already receives surface context (`type: "context"` with navigation path) in the chat panel, so it knows what the user is looking at.

**Why prompt-relay, not inline editing:** Editing a domain entity may involve ManageDomains (add/remove), ManageTask (adjust tracking scope), or UpdateContext (feedback). TP routes to the right primitive. A CRUD interface would need to expose all these operations directly, fragmenting the single-intelligence-layer.

#### 4c. Domain health indicators on Context surface

Read `_tracker.md` per domain to show health signals in the tree nav and directory view:

- **Tree node badge:** entity count + freshness indicator (green/amber/red based on staleness ratio)
- **Directory header:** "5 entities · 3 current · 2 stale" summary line
- **Entity row indicator:** colored dot (green = current, amber = stale, gray = inactive)

Data source: `_tracker.md` is already available via the workspace API. Parse the tracker table to extract entity status and last-updated timestamps.

#### 4d. Actuation log visibility in Work detail

Read `awareness.md` `## Actuation Log` section and render it in `WorkDetail` when present:

- Below `TrackingMiddle` (for `accumulates_context` tasks) or below `DeliverableMiddle`
- Collapsible panel: "System actions" with a list of recent actuations
- Each entry: timestamp + action + entity + reason

This makes the system's autonomous corrections visible without requiring the user to browse awareness.md.

**Cost:** Frontend only. No backend changes. All data sources already exist.

---

## Relationship to existing ADRs

- **ADR-149** (Task Lifecycle): feedback.md, steering.md, DELIVERABLE.md infrastructure preserved. This ADR unifies the feedback entry format and adds system verification as a source.
- **ADR-151** (Shared Context Domains): _tracker.md as context health sensor preserved. This ADR connects tracker state to the feedback layer via system verification checks.
- **ADR-154** (Post-Run Domain Scan): `_post_run_domain_scan()` is the execution point for both system verification and actuation. This ADR extends its responsibilities.
- **ADR-156** (Single Intelligence Layer): No background LLM jobs. System verification is deterministic. Actuation is rule-based. Consistent with single-intelligence-layer principle.
- **ADR-162** (Inference Hardening): `detect_inference_gaps()` pattern is analogous — deterministic gap detection feeding into structured response. System verification follows the same pattern for task-level feedback.
- **ADR-164** (Back Office Tasks): Agent hygiene (`back-office-agent-hygiene`) is a workspace-level deterministic check. System verification is the task-level equivalent — same pattern, different scope.
- **FEEDBACK-LOOP.md**: Surface affordance design (FeedbackStrip, prompt relay, solicitation rules) preserved as Phase 4. The architectural model (source-agnostic layer, system verification, actuation) replaces the doc's implicit assumption that all feedback is user-initiated.

---

## Resolved questions

1. **Feedback entry cap:** System entries age out after 3 runs (max 15 system entries). User entries persist until inference distills them into DELIVERABLE.md. Implemented in `age_out_system_entries()` in `feedback_actuation.py`.

2. **Actuation override priority:** User intent always wins. `evaluate_actuation_rules()` checks for user-sourced "restore"/"keep tracking" entries that contradict system stale-entity actuation. Override is scoped to the presence of the user entry — if the user entry ages out and staleness persists, actuation resumes.

3. **Cross-task actuation:** Confirmed no gap. Entity retirement calls workspace-level ManageDomains logic (writes to `/workspace/context/{domain}/` which is shared across all tasks). Actuation in one task's feedback.md affects the domain for all tasks that read it.

4. **Feedback.md migration:** Read-both implemented. All readers check `feedback.md` (task root) first, fall back to `memory/feedback.md`. All writers write to `feedback.md` only. Old path naturally becomes stale as new entries accumulate in the new location. No migration script needed.

5. **Chat-time vs pipeline-time actuation:** User-sourced structural changes (entity removal) execute immediately via ManageDomains in the same chat turn. The feedback entry with `Action:` line is the audit trail + safety net — if the direct call failed, the pipeline actuation evaluator catches it on next run. System-sourced actions only actuate post-run (no user present to want immediacy).
