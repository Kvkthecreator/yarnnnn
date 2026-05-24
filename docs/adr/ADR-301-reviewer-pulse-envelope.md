# ADR-301: Reviewer Pulse Envelope — Schedule Index + Recent Execution as Kernel-Universal Substrate

**Status**: Implemented

**Date**: 2026-05-24

**Companion docs**:
- `docs/architecture/FOUNDATIONS.md` (Axiom 4 v8.5 — Trigger; Derived Principle 19 — "kernel does not compute for the prompt"; Derived Principle 21 — Reviewer is wake-fired and paced by operator-declared pace)
- `docs/architecture/wake-and-time.md` (new in same commit cycle — synthesis canon for the wake + pace + envelope cluster)
- `api/services/reviewer_envelope.py` (extended by this ADR)
- `api/agents/reviewer_agent.py` (`_PERSONA_FRAME` extended; `build_operating_context_block` consolidated into envelope helper)

**Supersedes**: ADR-285 (Proposed 2026-05-17) — this ADR ratifies D3 (recent execution lineage) and refines D4 (mechanical scaffolding) by using the scheduler-tick maintenance phase instead of a kernel-universal recurrence. ADR-285's D5+ alpha-trader world-mirror additions are preserved as future bundle work.

**Amends**: ADR-274 (Operating Context block stays — moves into envelope helper), ADR-275 (Reviewer cadence authoring gets a real substrate basis to reason from), ADR-276 (governance envelope pre-load mechanism reused).

**Preserves**: ADR-209 Authored Substrate attribution; ADR-281 program-shaped envelope mechanism; ADR-296 v2 singular wake gateway; ADR-298 wake_queue + pace; ADR-300 pace as operator-facing surface; Singular Implementation discipline at the envelope assembly point.

## Context

The Reviewer's wake envelope today (post-ADR-274/276/281/284) perceives:
- **What it is**: governance substrate (IDENTITY, principles, MANDATE, AUTONOMY, PRECEDENT, _preferences, _pace)
- **What time it is**: Operating Context block (now, timezone, market state, workspace tenure)
- **Who's in the seat**: OCCUPANT.md (ADR-284)
- **What it was watching for**: standing_intent.md (ADR-284)
- **What the world looks like (bundle-shaped)**: program-declared substrate paths per ADR-281

It does NOT perceive:
- **What its own cadence declares**: literal `schedule:` strings from active `_recurrences.yaml` entries
- **What has actually fired and when**: `tasks.last_run_at` / `next_run_at` from scheduling index
- **Recent execution lineage**: `execution_events` for the last N hours

This gap is the proximate cause of the [2026-05-22 schedule self-misdiagnosis](../observations/2026-05-24-045348-reviewer-schedule-self-misdiagnosis/findings.md) (commit `772a569`): the Reviewer asserted "signal-evaluation failed to fire 3× today as scheduled" when the literal schedule is `@market_open + 15min` (one fire). The Reviewer had no substrate basis for reasoning about its own cadence — only persona-frame instructions to call `ListRevisions` + `GetSystemState` mid-loop, which under a 3-round Sonnet budget it skipped. It made up the schedule literal and stood down on a phantom problem.

ADR-285 D3 anticipated this gap and specified `_recent_execution.md` as a 10th kernel-universal envelope entry. ADR-285 has sat **Proposed since 2026-05-17** (7 days). The schedule self-misdiagnosis is the empirical case it predicted. ADR-301 ratifies the fix with two refinements over ADR-285 as drafted:

1. **Two envelope entries, not one**. `_recent_execution.md` (what fired) is necessary but not sufficient. `_schedule_index.md` (what is supposed to fire and when) closes the schedule-hallucination class explicitly. Both are mechanically-mirrored from data the system already has (`execution_events` table + `tasks` scheduling index + `_recurrences.yaml`).

2. **Scheduler-tick maintenance phase, not kernel-universal recurrence**. ADR-285 D4 proposed a `MirrorRecentExecution` recurrence scaffolded at workspace-init Phase 5. ADR-301 instead piggybacks on the existing scheduler-tick maintenance phase (`unified_scheduler.py:367-371` already runs `reclaim_stale_locks` + `drain_all_users_with_pending` per tick). The two new mirrors run per-tick across all workspaces in the same loop. This: (a) avoids burning `wake_queue` rows for kernel maintenance, (b) requires zero recurrence YAML scaffolding at workspace-init, (c) keeps the kernel/program separation clean — kernel maintenance is scheduler-side; recurrences are workspace work. Same precedent as `reclaim_stale_locks`.

## Decisions

### D1 — Two kernel-universal envelope entries

`api/services/reviewer_envelope.py::_UNIVERSAL_ENVELOPE_DECLS` grows from 9 to 11 entries:

```python
_UNIVERSAL_ENVELOPE_DECLS: list[tuple[str, str]] = [
    # — Governance (Persona + Framework class) —
    ("identity_md",           REVIEW_IDENTITY_PATH),
    ("principles_md",         REVIEW_PRINCIPLES_PATH),
    ("precedent_md",          SHARED_PRECEDENT_PATH),
    ("mandate_md",            SHARED_MANDATE_PATH),
    ("autonomy_md",           SHARED_AUTONOMY_PATH),
    ("preferences_yaml",      SHARED_PREFERENCES_PATH),
    ("pace_yaml",             SHARED_PACE_PATH),
    # — Seat Occupant + Standing Intent (ADR-284) —
    ("occupant_md",           REVIEW_OCCUPANT_PATH),
    ("standing_intent_md",    REVIEW_STANDING_INTENT_PATH),
    # — Pulse (ADR-301) — Reviewer's own cadence + recent fires —
    ("schedule_index_md",     MEMORY_SCHEDULE_INDEX_PATH),
    ("recent_execution_md",   MEMORY_RECENT_EXECUTION_PATH),
]
```

New path constants in `workspace_paths.py`:
- `MEMORY_SCHEDULE_INDEX_PATH = "memory/_schedule_index.md"`
- `MEMORY_RECENT_EXECUTION_PATH = "memory/_recent_execution.md"`

### D2 — `MirrorScheduleIndex` mechanical primitive

`api/services/primitives/mirror_schedule_index.py` (new). Reads the workspace's `tasks` scheduling-index rows (active + paused) and writes a compact markdown summary to `/workspace/memory/_schedule_index.md`. Diff-aware (no-op when content unchanged). Attribution `system:mirror-schedule-index` per ADR-209.

Schema of `_schedule_index.md`:

```markdown
---
as_of: <iso8601-utc>
recurrences_count: <int>
---

# Schedule Index

| slug | schedule | mode | last_run_at | next_run_at | paused |
|---|---|---|---|---|---|
| outcome-reconciliation | `0 5 * * *` | judgment | 2026-05-23T05:00:18Z | 2026-05-24T05:00:00Z | false |
| signal-evaluation | `@market_open + 15min` | judgment | 2026-05-22T13:46:10Z | 2026-05-26T13:45:00Z | false |
| track-universe | `[@market_open + 15min, @market_open + 3h, @market_close - 1h]` | mechanical | 2026-05-22T20:30:35Z | 2026-05-26T13:45:00Z | false |
| ... | ... | ... | ... | ... | ... |
```

Schedule strings are read literally from `tasks.declaration_path` → `_recurrences.yaml` to preserve semantic shapes (`@market_open + 15min` etc.) — not normalized to cron. Mode column comes from the YAML's `mode:` field. paused flag from `tasks.paused`.

### D3 — `MirrorRecentExecution` mechanical primitive

`api/services/primitives/mirror_recent_execution.py` (new). Reads the workspace's `execution_events` rows over the last 24h window, writes a compact summary to `/workspace/memory/_recent_execution.md`. Diff-aware. Attribution `system:mirror-recent-execution` per ADR-209.

Schema of `_recent_execution.md`:

```markdown
---
as_of: <iso8601-utc>
window: 24h
fire_count: <int>
---

# Recent Execution Lineage

## Last 24h
- 2026-05-23T05:03:39Z · outcome-reconciliation · judgment · success · 28.1s · $0.301
- 2026-05-22T20:30:35Z · track-regime · mechanical · success · 1.6s · $0
- 2026-05-22T13:46:10Z · signal-evaluation · judgment · success · 35.4s · $0.249
- 2026-05-22T05:02:47Z · outcome-reconciliation · judgment · success · 30.5s · $0.265
- ...

## Counts (last 24h)
- judgment fires: 3 · 0 failures · $0.815 total
- mechanical fires: 8 · 0 failures · $0 total
- substrate_event escalates: 1 · pre-ship-audit
- cron_tick escalates: 2 · outcome-reconciliation + revision-audit
```

Pure substrate read + deterministic markdown composition. No pattern detection / no LLM derivation per Derived Principle 19. Optional future Phase 2 (after ADR-301 ships) could add a "Notable patterns" section with kernel-deterministic comparisons (e.g., "signal-evaluation: 0 fires in 24h vs declared daily cadence — overdue") — out of scope for this ADR.

### D4 — Scheduler-tick maintenance phase

`api/jobs/unified_scheduler.py` extends the maintenance phase (around line 367) with two new steps per tick:

```python
# Existing maintenance steps
reclaimed = reclaim_stale_locks(supabase)
drained = await drain_all_users_with_pending(supabase)

# New per-tick mirrors (ADR-301)
from services.kernel_mirrors import (
    mirror_schedule_index_for_all_users,
    mirror_recent_execution_for_all_users,
)
schedule_mirrored = await mirror_schedule_index_for_all_users(supabase)
exec_mirrored = await mirror_recent_execution_for_all_users(supabase)
```

New helper module `api/services/kernel_mirrors.py` wraps the primitives in a per-workspace iteration that handles errors per workspace (one workspace's mirror failure does not block others). Diff-aware writes mean most ticks produce zero substrate revisions — the cost is two cheap SELECT queries per workspace per tick, no writes when nothing changed.

This avoids the "kernel-universal recurrence" scaffolding question entirely. Same precedent as `reclaim_stale_locks` (kernel maintenance, not workspace work, runs per-tick).

### D5 — Operating Context block consolidation

`build_operating_context_block` moves from `api/agents/reviewer_agent.py` to `api/services/reviewer_envelope.py`. The envelope helper now assembles all envelope content — governance + occupant + standing-intent + schedule-index + recent-execution + program-shaped + operating-context — in one place. `_build_user_message` in `reviewer_agent.py` reads `ctx["operating_context_block"]` exactly as today; only the assembly location changes.

This is Singular Implementation cleanup. Pre-ADR-301 the envelope had two homes (substrate in `reviewer_envelope.py`, time-context in `reviewer_agent.py` composed by `wake.py` at three call sites). Post-ADR-301 there is one envelope assembly home.

### D6 — `_PERSONA_FRAME` "Pulse Discipline" section

`api/agents/reviewer_agent.py::_PERSONA_FRAME` gains a new section instructing the Reviewer how to use the two new envelope entries:

> **Pulse Discipline (ADR-301):**
>
> Your wake envelope carries two pulse files you read before reasoning about cadence or recent activity:
>
> - `_schedule_index.md` — the literal schedule + last_run_at + next_run_at for every recurrence in this workspace. Before claiming a recurrence missed an expected fire, read this. The schedule literal is canonical; do not reason about cadence from memory.
> - `_recent_execution.md` — what has fired in the last 24h with outcomes. Before claiming "nothing has happened" or "the system has been silent," read this.
>
> Both files are mechanically mirrored from substrate the system already holds (the scheduling index + execution_events table). They are kernel-maintenance writes, not Reviewer-authored. You read them; you do not write them.

This is the prompt-side closure of the schedule-hallucination class. The Reviewer can no longer plausibly hallucinate "3× RTH fires expected" when the envelope literally contains the schedule string `@market_open + 15min` and the last-fire timestamp.

### D7 — Mirror cadence: every scheduler tick

Both mirrors run every scheduler tick (currently every 5 minutes). Diff-aware skips mean revision-chain noise is bounded — typically zero writes per tick across most workspaces. When `_recent_execution.md` is re-composed and the content changed (a new execution_events row appeared), exactly one revision is written; same for `_schedule_index.md` when a recurrence's `last_run_at` or `next_run_at` advances.

The 5-minute cadence is fine-grained enough that the Reviewer's perception of recent activity is at most 5 minutes stale at envelope-assembly time. For sub-minute precision the Reviewer can always call `GetSystemState` mid-loop — but the envelope satisfies the common case.

### D8 — Out of scope (deferred)

- **Bundle world-mirror additions per ADR-285 D5** (`MirrorTickerSnapshot` + `MirrorPositionState` for alpha-trader). Separate work; landing depends on the alpha-trader bundle author's discretion.
- **Pattern detection in `_recent_execution.md`** (drift / anomaly flags). Phase 2 of this ADR if pressure surfaces. Kernel-deterministic only — no LLM derivation.
- **Operator-facing schedule_index surface**. Out of scope here. The envelope helper writes the file; the operator can browse it via the existing Files surface. If pressure surfaces for a richer cockpit surface, that's a separate ADR.

## Implementation surface

| Layer | File | Change |
|---|---|---|
| Kernel constants | `api/services/workspace_paths.py` | Add `MEMORY_SCHEDULE_INDEX_PATH` + `MEMORY_RECENT_EXECUTION_PATH` |
| Kernel envelope | `api/services/reviewer_envelope.py` | `_UNIVERSAL_ENVELOPE_DECLS` grows 9→11; consolidate `build_operating_context_block` import-site; export `assemble_envelope()` returning envelope dict including `operating_context_block` |
| Kernel persona | `api/agents/reviewer_agent.py` | Add "Pulse Discipline" section to `_PERSONA_FRAME`; `_build_user_message` renders new envelope keys; `build_operating_context_block` thin shim re-exporting from envelope helper for backward-compat with existing test gate |
| Kernel primitives | `api/services/primitives/mirror_schedule_index.py` (new) | MirrorScheduleIndex primitive |
| Kernel primitives | `api/services/primitives/mirror_recent_execution.py` (new) | MirrorRecentExecution primitive |
| Kernel registry | `api/services/primitives/registry.py` | Register both new primitives in HANDLERS |
| Kernel maintenance | `api/services/kernel_mirrors.py` (new) | Per-workspace iteration helpers `mirror_schedule_index_for_all_users` + `mirror_recent_execution_for_all_users` |
| Scheduler | `api/jobs/unified_scheduler.py` | Maintenance phase invokes the two new helpers per tick |
| Prompt CHANGELOG | `api/prompts/CHANGELOG.md` | Entry for `_PERSONA_FRAME` Pulse Discipline addition |
| Synthesis canon | `docs/architecture/wake-and-time.md` (new) | Names the wake + pace + envelope cluster as one architecture |
| Test gate | `api/test_adr301_reviewer_pulse_envelope.py` (new) | Asserts envelope contains schedule_index_md + recent_execution_md; persona frame contains "Pulse Discipline" section; mirrors registered; scheduler invokes maintenance helpers |
| ADR-285 status | `docs/adr/ADR-285-holistic-wake-envelope.md` | Status banner: D3 superseded by ADR-301; D5+ alpha-trader world-mirror entries remain Proposed for separate bundle work |

## Why this is structurally right

The Reviewer's autonomy aspiration (FOUNDATIONS Derived Principle 21) requires it to reason correctly about its own pulse — what its cadence is, what has happened on it. Today the Reviewer perceives time (Operating Context) and standing intent (last cycle's watching) but has no substrate basis for reasoning about its actual schedule or actual recent fires. The gap was real, the schedule hallucination was its predictable failure mode, and the operator's "I'm not seeing it" intuition was tracking the predictable downstream symptom.

ADR-301 closes the loop with two cheap kernel-maintenance writes per scheduler tick. The mirrors compute nothing the system doesn't already have — they project existing substrate (tasks + execution_events + _recurrences.yaml) into envelope-friendly compact summary substrate. Derived Principle 19 honored (kernel doesn't derive at prompt-assembly time; it derives at known cadence and writes substrate). Derived Principle 21 honored (the Reviewer perceives its own pulse and can reason from it).

The choice to use scheduler-tick maintenance over kernel-universal recurrence is the right factoring: kernel maintenance lives in the kernel maintenance phase, where reclaim_stale_locks already lives. Recurrences are workspace work. The mirrors are kernel work performed on every workspace's substrate — they're scheduler-side, not workspace-side.

The companion synthesis canon (`docs/architecture/wake-and-time.md`) closes the legibility gap the operator's intuition surfaced — that wake + pace + envelope had accumulated across 10 ADRs with no synthesis surface. The new doc names the cluster as one architecture, points at the ADRs for the deep-dives, and is the page anyone (the operator, a future Claude session, a future contributor) reads to grok the architecture without first reading 10 ADRs.
