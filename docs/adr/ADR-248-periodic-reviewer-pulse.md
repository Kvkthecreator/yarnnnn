# ADR-248: Periodic Reviewer Pulse — Autonomy Loop Closure

> **Status**: **Implemented** (2026-05-03, Commits 1–4)
> **Date**: 2026-05-03
> **Authors**: KVK, Claude
> **Builds on**: ADR-247 (three-party narrative model), ADR-218 (reviewer reflection), ADR-211 (reviewer calibration), ADR-194 v2 (Reviewer substrate), ADR-217 (AUTONOMY.md authorship), ADR-209 (Authored Substrate write path)
> **Amends**: ADR-218 (wires the reflection executor as a scheduled recurrence — currently implemented but never triggered), ADR-247 D5 (periodic pulse scoped here)
> **Dimensional classification**: **Trigger** (Axiom 4) primary — adds a periodic sub-shape to the Reviewer's currently reactive-only trigger; **Identity** (Axiom 2) secondary — the Reviewer acts as a longitudinal pattern detector, not just a per-proposal gate; **Substrate** (Axiom 1) tertiary — introduces a pause marker written to AUTONOMY.md

---

## Context

### The gap ADR-247 named

The Reviewer today is purely **reactive-pulsed** — it fires once per proposal creation, renders a verdict, and terminates. The resulting loop is:

```
ACTION declaration fires → agent proposes → Reviewer judges → [execute | queue]
```

When autonomy is `bounded_autonomous` or `autonomous`, approved proposals execute immediately. But nothing reads the accumulated pattern of those executions and asks: *"given the last 14 trading cycles, is this operation still aligned with the mandate?"*

The system has no longitudinal awareness in the execution path. The operator returns to the cockpit and sees the narrative. If a pattern is bad — consecutive losses, win rate drop, position concentration drift — they catch it manually. This is not autonomy; it is automation with deferred human review.

### What already exists

Reading `api/services/back_office/reviewer_reflection.py` and `reviewer_calibration.py` in full reveals the infrastructure is significantly more complete than ADR-247's scoping note implied:

- **`reviewer_reflection.py`** — fully implemented back-office executor. Reads all Reviewer substrate (`IDENTITY.md`, `principles.md`, `PRECEDENT`, `MANDATE`, `AUTONOMY`, recent decisions, `_performance.md` summaries), invokes `reviewer_agent.run_reflection()` (Haiku, ~1-2K tokens), applies write-back via `reflection_writer.apply_reflection_writes()` which writes to `reflections.md` and emits a `role='reviewer'` chat notification for material verdicts. Has a cost floor (≥1 new decision since last reflection, ≥24h since last reflection).

- **`reviewer_calibration.py`** — fully implemented. Rebuilds `calibration.md` from `decisions.md` × `_performance.md` rolling windows. Zero LLM cost, deterministic.

- **`materialize_back_office_task()`** in `workspace_init.py` — auto-routes slug `back-office-reviewer-reflection` → `services.back_office.reviewer_reflection` via the naming convention. No manual wiring needed; the executor just needs a YAML declaration to trigger it.

**The gap is exactly one thing**: no recurrence YAML declaration for `back-office-reviewer-reflection` (or `back-office-reviewer-calibration`) means the scheduler never fires them. They exist but are unreachable.

### What's missing for the autonomy loop

Beyond wiring the existing executors, one piece is genuinely new: **pause authority**. When `reviewer_reflection` detects a pattern that warrants halting autonomous execution, it currently can only note it in `reflections.md`. Nothing reads that note and halts `should_auto_execute_verdict()`.

The pause mechanism requires:
1. A structured pause signal — a field in `AUTONOMY.md` the Reviewer can write
2. `should_auto_execute_verdict()` reading that field
3. The Reviewer writing it via `write_revision()` (ADR-209) with proper attribution
4. An expiry mechanism so the pause doesn't block forever

---

## Decisions

### D1: Wire `back-office-reviewer-reflection` as a recurrence declaration

Add `back-office-reviewer-reflection` as a daily entry in `/workspace/_shared/back-office.yaml` (alongside existing entries). The executor (`reviewer_reflection.py`) is already complete — this is purely the trigger wire.

**Cadence**: daily, offset from `back-office-outcome-reconciliation` and `back-office-reviewer-calibration` (which must run first — reflection reads `calibration.md`). Suggested: reconciliation → calibration → reflection, each ~1h apart. Expressed as cron offsets in the YAML.

**Invocation gate**: ≥5 total decisions in `decisions.md` AND ≥1 new decision since last reflection AND ≥24h since last reflection. If gate fails, executor returns immediately with a `skipped` status. Zero LLM cost when skipped. The minimum of 5 total decisions is a pattern-detection floor — one or two decisions is too thin a sample to detect meaningful drift. The existing `reviewer_reflection.py` has a ≥1 floor; Commit 1 updates it to ≥5 total alongside the YAML wiring.

**Cost**: ~$0.002 per invocation when triggered (Haiku, ~1-2K tokens). ~$0.06/month for a daily trading operation producing 1-2 proposals/day.

### D2: Wire `back-office-reviewer-calibration` as a recurrence declaration

Same: add as a daily entry in `/workspace/_shared/back-office.yaml`. The executor is already complete. Zero LLM cost.

**Cadence**: daily, after `back-office-outcome-reconciliation`. Must precede `back-office-reviewer-reflection`.

### D3: Add pause authority — structured pause field in AUTONOMY.md

Extend the AUTONOMY.md schema with an optional `paused_until` field at the `default` and per-domain level:

```yaml
default:
  level: autonomous
  ceiling_cents: 1500
  paused_until: "2026-05-10T00:00:00Z"   # NEW — optional, ISO-8601
  pause_reason: "Win rate dropped below 35% over 7d. Auto-paused by Reviewer reflection 2026-05-03."  # NEW — optional string
```

**When set**: `should_auto_execute_verdict()` in `review_policy.py` checks `paused_until` before any autonomy gating. If `paused_until` is in the future, the function returns `False` regardless of level — all proposals route to operator Queue.

**When expired**: `paused_until` in the past is silently ignored — autonomy resumes automatically. The Reviewer does not need to "un-pause"; the timestamp expiry handles it.

**Singular implementation**: `should_auto_execute_verdict()` is already the single gate. This adds one check at the top of that function. No new code path.

### D4: Reviewer write path for pause — `reflection_writer.py` extension

When `reviewer_reflection` produces a verdict of `narrow` or the persona's reflection recommends pausing autonomous execution, `reflection_writer.apply_reflection_writes()` (already called by the executor) is extended to:

1. Detect a `pause_autonomy` proposal in the verdict's `proposals` list (new proposal type alongside existing `narrow_principles`, `relax_principles`, `character_note`)
2. If present: read current `AUTONOMY.md`, inject `paused_until` (48h from now by default, overridable by the proposal's `duration_hours` field) + `pause_reason`
3. Write via `write_revision(authored_by="reviewer:{occupant_identity}", message="auto-pause: {reason[:80]}")` — ADR-209 attribution required
4. Emit a `role='reviewer'` narrative entry (same channel as existing material verdicts) surfacing the pause to the operator

**Scope ceiling preserved** (ADR-218 §4): the Reviewer can write to its own directory (`/workspace/review/`) and to the shared substrate it is declared to govern (`AUTONOMY.md` — the delegation contract it was given authority over by ADR-217). It cannot touch `MANDATE.md`, `IDENTITY.md`, `BRAND.md`, or any domain context files.

### D5: YARNNN pause-awareness in working memory

When `AUTONOMY.md` contains a non-expired `paused_until`, `working_memory.py::format_compact_index()` surfaces a one-line signal:

```
⚠ Autonomy paused until 2026-05-10 — Reviewer: "Win rate dropped below 35%"
```

This closes the channel legibility requirement (FOUNDATIONS Derived Principle 12): the operator sees the pause in the next chat session without having to inspect `AUTONOMY.md` directly.

### D6: Pause expiry is time-based, not state-based

The Reviewer does NOT write a second entry to un-pause. `paused_until` expiring naturally resumes autonomy. This is the correct design:
- No state machine to maintain
- No second LLM call to un-pause
- Operator can manually remove `paused_until` via chat at any time (YARNNN routes `WriteFile` to AUTONOMY.md)
- If the condition persists (still losing), the next daily reflection will re-pause

Default pause duration: **48 hours**. The reflection prompt instructs the persona to express short-circuit concerns as 24h-72h pauses, not indefinite blocks.

---

## Governing Philosophy: Runtime Gate, Not Model-Side Reasoning

This ADR follows the Claude Code gate model explicitly.

**Claude Code never asks "am I allowed to do this?" before calling a tool.** It calls the tool; the runtime either executes or surfaces for approval. The permission model is at the tool boundary, not in the model's head.

The same principle governs this ADR's design:

- Production agents always produce the best proposal they can from the substrate they read. They never reason about their autonomy level. They call `ProposeAction`.
- `should_auto_execute_verdict()` is the single runtime gate. It reads AUTONOMY.md. It decides. The model is not in that loop.
- The Reviewer's periodic pulse (this ADR) adds a new *write path* to the gate — the Reviewer can write `paused_until` to AUTONOMY.md, which the gate then reads. This is a substrate mutation, not a model instruction.

**Consequence**: this ADR adds no lifecycle prompt instructions, no document readiness checks, no "if AUTONOMY.md is skeleton, do X" model guidance. If `_operator_profile.md` is skeleton and the agent reads it and finds no signals, the agent naturally produces no proposal or an explicit "standing down — no signals declared" proposal. The gate handles the rest. The model reads substrate and acts; the gate controls execution.

## What This ADR Does NOT Do

- Does not change `reviewer_agent.py` verdict mode (per-proposal judgment unchanged)
- Does not add new LLM calls beyond the existing `run_reflection()` Haiku invocation
- Does not add new primitives
- Does not change `review_proposal_dispatch.py`
- Does not change the four autonomy levels (manual/assisted/bounded_autonomous/autonomous)
- Does not add lifecycle prompt instructions or document readiness checks to the ACTION posture
- Does not add a `pause_autonomy` UI affordance — the operator sees the pause in the narrative and can lift it via chat; no new surface needed

---

## Implementation Plan

### Commit 1 — YAML declarations (zero risk)
Add `back-office-reviewer-calibration` and `back-office-reviewer-reflection` entries to `/workspace/_shared/back-office.yaml` for the alpha-trader reference workspace.

Also add them to `workspace_init.py`'s back-office materialization list so new workspaces get them on first trigger.

**Test**: scheduler's `get_due_declarations()` picks up the new entries. Existing `reviewer_calibration.py` and `reviewer_reflection.py` executors run without modification.

### Commit 2 — AUTONOMY.md schema extension + `should_auto_execute_verdict()` pause check
- `review_policy.py`: add `paused_until` + `pause_reason` to `_KNOWN_AUTONOMY_KEYS`; add expiry check at top of `should_auto_execute_verdict()` — if `paused_until` is in the future, return `False` with `reason="autonomy_paused"` in the gate result
- `working_memory.py`: add pause-state signal to `format_compact_index()` (one line, conditional)

**No write path yet** — this commit only adds the read side. Safe to ship independently.

### Commit 3 — `reflection_writer.py` pause proposal support
- Add `pause_autonomy` as a recognized proposal type in `apply_reflection_writes()`
- Implement AUTONOMY.md patch: read → inject `paused_until` + `pause_reason` → `write_revision(authored_by="reviewer:{occupant}")`
- Add `pause_autonomy` to the reflection-mode prompt's proposal type vocabulary (in `reviewer_agent.py` reflection prompt section)
- Update `api/prompts/CHANGELOG.md`

### Commit 4 — Reference workspace + doc sync
- Update `docs/programs/alpha-trader/reference-workspace/context/_shared/AUTONOMY.md` to document the `paused_until` / `pause_reason` optional fields
- Add ADR-248 entry to CLAUDE.md
- Mark ADR-248 Implemented in the ADR file

---

## Hooks Discipline

Per CLAUDE.md execution rules:

| Rule | Application |
|------|-------------|
| **Singular implementation** | One pause check location — top of `should_auto_execute_verdict()`. One write path — `reflection_writer.apply_reflection_writes()`. No parallel pause mechanisms. |
| **Docs alongside code** | `back_office/__init__.py` docstring updated with new executor entries. ADR-218 status updated (now triggered). `CHANGELOG.md` entry for Commit 3 prompt change. |
| **ADRs first** | ADR-217 owns AUTONOMY.md authorship — pause write must use `write_revision(authored_by="reviewer:{occupant}")` per ADR-209. ADR-218 already scoped reflection write-back ceiling (Reviewer can touch `AUTONOMY.md`). |
| **Prompt changes** | Commit 3 adds `pause_autonomy` to reflection-mode proposal vocabulary → `api/prompts/CHANGELOG.md` entry required. |
| **Render parity** | Scheduler (Unified Scheduler service on Render) picks up new YAML entries via `get_due_declarations()` — no env var changes, no service config changes. YAML is filesystem-read. |
| **Git** | `feat(adr-248):` prefix. Each commit independently green (existing tests pass, new test gate assertions added per commit). |

---

## Test Gate

`api/test_adr248_periodic_reviewer_pulse.py`:

1. `back-office-reviewer-reflection` and `back-office-reviewer-calibration` appear in `_shared/back-office.yaml` for the alpha-trader reference workspace
2. `review_policy.should_auto_execute_verdict()` returns `False` when `AUTONOMY.md` contains a non-expired `paused_until`
3. `review_policy.should_auto_execute_verdict()` returns correct value when `paused_until` is expired (ignored — gate passes to normal level check)
4. `_KNOWN_AUTONOMY_KEYS` in `review_policy.py` includes `paused_until` and `pause_reason`
5. `reflection_writer.py` recognizes `pause_autonomy` as a proposal type
6. `reviewer_reflection.py` executor unchanged (still exports `run()` with correct signature)
7. `reviewer_calibration.py` executor unchanged (still exports `run()`)
8. `working_memory.format_compact_index()` surfaces pause signal when `paused_until` is set and future
9. AUTONOMY.md reference workspace file documents `paused_until` and `pause_reason` optional fields

---

## Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-218 | Wires the reflection executor that ADR-218 implemented but never triggered. D4 extends `reflection_writer.py` which ADR-218 owns. |
| ADR-217 | AUTONOMY.md authorship is operator-authored; this ADR adds a system-write path for the pause fields, attributed to `reviewer:{occupant}` per ADR-209. The operator retains write authority (can override/remove at any time). |
| ADR-209 | All AUTONOMY.md writes go through `write_revision()`. No direct DB writes. |
| ADR-211 | Wires `reviewer_calibration` as a scheduled recurrence. ADR-211 implemented the executor; this ADR pulls the trigger. |
| ADR-194 v2 | Reviewer's reactive pulse unchanged. This adds a periodic pulse alongside it (Axiom 4 — two sub-shapes on one seat). |
| ADR-247 | D5 — this is the follow-on ADR that closes the autonomy loop D5 scoped. |
| FOUNDATIONS Axiom 4 | Reviewer now has two trigger sub-shapes: reactive (per-proposal) + periodic (daily reflection). Both are legitimate per Axiom 4's three sub-shapes. The seat's distinctness (Purpose + Trigger per Axiom 2) is enriched, not confused. |
| FOUNDATIONS Axiom 7 (Recursion) | This closes the recursion loop: `_performance.md` → Reviewer reflection → `reflections.md` + possible `AUTONOMY.md` pause → next proposal sees the pause → operator sees the narrative entry. The loop completes. |
