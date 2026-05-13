# 2026-05-13 — Activation-fire wiring — close the cold-start gap

> **Type**: Architectural-shift observation. Records the scheduler + bundle changes that make activation an active substrate-population moment instead of a passive scaffolding-then-silence one. Companion to the same-day regime wiring observation (2026-05-13-regime-wiring.md).
> **Trigger**: Multi-turn architectural discourse on 2026-05-13. Started as "should we have a research workspace / Researcher agent" question; first-principles stress test revealed the actual gap was that *recurrences are over-relied-on as the only first-class shape for substrate accumulation*, and the smallest fix was making activation a fire-trigger.
> **Persona**: bundle-wide change. Verification path against `seulkim88` (alpha-trader persona) workspace.

---

## Classification

- **Objective**: A-system (primary). Activation-fire is structural infrastructure that gates *whether the first cycle has substrate to reason against*.
- **Within-A scope**: systematic-workflow (new scheduler conditional + new bundle recurrence) + substrate-shape (new `/workspace/research/` convention).
- **FOUNDATIONS dimension**: Trigger (new deterministic fire-at-activation pattern within existing periodic umbrella) + Substrate (new research-substrate convention) + Mechanism (scheduler conditional, judgment recurrence).
- **Severity**: declarative-unenforced-by-experience (same trap class as iter-2 L3 + the regime wiring). System's claim of "accumulating, compounding intelligence" was structurally true post-fork but operator-experienced as "scaffolded inbox waiting for cron."
- **Resolution path**: bundle-level evolution + minimal kernel change (one conditional in `compute_next_run_at`). ADR-270 documents the kernel change; bundle changes follow ADR-270 §D6 (operator-authored at bundle layer).
- **Money impact**: indirect. Before this change, the Reviewer's first proposal post-activation had no substrate to reason against (`_money_truth.md` empty + no regime + no per-ticker bars + no historical findings). After: each of those substrate files exists within the first scheduler tick.

---

## What was wrong

The activation experience produced this sequence:

| T+ | What happened | Operator-experienced reality |
|---|---|---|
| 0 | Operator activates persona | Click; spinner; success message |
| seconds | Bundle fork writes files into `/workspace/` | Files exist on disk, invisible to operator surface |
| seconds | `materialize_scheduling_index` runs, populates `tasks` table | Scheduler now knows about the recurrences |
| minutes-to-hours | Wait for next periodic fire | Cockpit faces empty, feed silent, no progress visible |
| eventually | First periodic recurrence fires per its cron | Substrate starts populating |

For US-market-bound recurrences activated outside RTH (e.g., 22:00 KST on a weekday for an alpha-trader workspace), the eventually-window is **11.5 hours**. The operator's first lived YARNNN experience is *nothing happens visibly for 11.5 hours after I clicked activate*.

This is not a bug — every individual piece works correctly. It's a *gap between what canon claims about the architecture* (accumulating, compounding intelligence) *and what the operator's activation experience demonstrates* (dead-quiet substrate). Same trap class as iter-2's three-layer trade-execution gap: substrate declares intent, runtime doesn't enforce it at the moment it matters.

---

## What shipped

Two surfaces of change, both atomic in one commit:

### Kernel (one conditional)

`api/services/scheduling.py::compute_next_run_at` — one branch at the top of the function:

```python
if rec.options.get("fire_on_activation") and last_run_at is None:
    return now_utc
```

The change is structural: recurrences with `fire_on_activation: true` and no prior `last_run_at` return `now` from `compute_next_run_at`, so `materialize_scheduling_index` writes `next_run_at = now`, and the next scheduler tick picks the row up immediately. After the first fire records `last_run_at`, subsequent calls fall through to the regular schedule.

No new dataclass field — `rec.options` (the existing absorb-unknown-keys surface) carries the flag transparently. No new primitive. No new trigger sub-shape. The scheduler is still the single dispatch path; activation fires are just rows that happen to be due immediately.

### Bundle (operator-facing changes)

- **Three existing recurrences marked `fire_on_activation: true`**: `track-account` (broker account snapshot), `track-regime` (VIXY + SPY regime substrate per [ADR-269](../adr/ADR-269-capability-flow-wiring.md) flow + the 2026-05-13 regime-wiring change), `track-universe` (per-ticker bar snapshots feeding signal-evaluation).
- **One new recurrence**: `falsify-signals` — `schedule: null` (reactive) + `fire_on_activation: true`. Walks 90 days of historical bars through each operator-declared signal, writes per-signal findings to `/workspace/research/findings/{signal_id}.md`. Bootstrap-only — no periodic schedule, re-fires only on explicit `FireInvocation`.
- **New `/workspace/research/mandate.md`**: operator-facing standing intent for the research substrate. Names fidelity gaps honestly (no slippage model, survivorship bias, no regime conditioning).
- **New `/workspace/specs/falsify-signals.md`**: schema for findings files (frontmatter with sample_size, win_rate, avg_win_R, expectancy_R, source: replay, baseline_status).
- **`/workspace/review/principles.md` extended**: Capital-EV section now references `/workspace/research/findings/{signal_id}.md` alongside `_money_truth.md`. Rule: live data weighs more than replay findings; replay-only-below-baseline is a soft warning not an auto-reject.

### Net diff

~5 files changed, ~250 LOC added. One kernel conditional. Four bundle additions. Zero new primitives, zero new agent classes, zero registry changes.

---

## Why this shape (decision rationale traceable to discourse)

The discourse considered three richer shapes before settling on this one:

| Shape considered | Why rejected |
|---|---|
| Dedicated learning-playbook userspace ("Option A — separate workspace for operator + Claude learning") | Doesn't strongly serve money-truth objective; operator-mediated promotion between workspaces is friction without clear architectural payoff |
| Extended workspace with replay-as-platform-connection (Shape A/B/C from prior turn) | Over-architected for the actual gap; introduces a new platform-connection variant when the existing recurrence machinery can do the work |
| New Researcher Agent class as systemic peer of Reviewer | Stress-test against the primitives matrix showed *no judgment capability is structurally absent from the existing framework* — a Researcher seat would be a recurrence with attribution dressed as a persona |

The first-principled rest after stress-testing: **the framework already supports cold-start substrate population via the existing recurrence machinery; what's missing is a way for bundles to mark recurrences for activation-fire.** ADR-270 is that.

---

## What this does NOT do (deliberate non-actions per ADR-270 §3 "Earned escalation")

Three richer patterns were explicitly deferred:

1. **Chat-callable reactive recurrence invocation as first-class operator gesture.** Today `FireInvocation` exists in the primitive set but has no chat-surface convention for "operator says 'run X now'". Deferred until operator observation shows the verb is wanted often.
2. **Ad-hoc chat exploration writes substrate by default.** Convention discipline ("what counts as substantive enough to retain") wants operator input before shipping. Deferred.
3. **Periodic `falsify-signals` schedule.** Bundle ships it as one-shot. If observation shows ongoing falsification is load-bearing, a future bundle revision adds a periodic schedule. Earned by evidence per `research/mandate.md` §"Earned escalation".

The escalation pattern: ship the smallest version, observe lived experience, promote a deferred piece into shipped substrate when evidence justifies. Same discipline as AUTONOMY.md's Phase 0 → Phase 1 graduation.

---

## Verification path

Post-merge, verification runs against `seulkim88` persona (alpha-trader workspace, user_id `2be30ac5-...`):

1. **`reset.py --persona alpha-trader --confirm`** — purge workspace to cold state. Confirm `tasks` rows are dropped.
2. **`activate_persona.py --persona alpha-trader`** — fork bundle, materialize index. Expect logs to show:
   - `[FORK] materialized scheduling index for 2be30ac5: N rows` (N = total recurrences in bundle)
   - For activation-fired recurrences: `next_run_at` set to fork-time, not next cron tick
3. **`connect.py alpha-trader`** — wire Alpaca paper credentials.
4. **Wait one scheduler tick (60 seconds max).** Within the first minute post-connect:
   - `/workspace/context/portfolio/_account.yaml` exists with broker account snapshot
   - `/workspace/context/trading/_regime.yaml` exists with current VIXY + SPY regime (or `data_stale: true` if outside RTH)
   - `/workspace/context/trading/{ticker}.yaml` exists for each universe member
   - `/workspace/research/findings/{signal_id}.md` exists for each declared signal with `source: replay` frontmatter
5. **Feed surface check**: 4-7 system-attributed entries within the first minute (activation burst).
6. **`verify.py alpha-trader`** — invariant check should pass (existing invariants unchanged; new substrate doesn't break old assertions).

### What would falsify the change

If `/workspace/research/findings/` ends up empty post-activation (no findings files written), the L3 capability flow may still have a bug on the `falsify-signals` recurrence's specialist dispatch path. Per iter-2's observation, capability-flow wiring is still queued for full E2E validation. Falsify-signals exercises that path as a high-volume historical-bar fetch — a useful stress test.

If activation-fired recurrences fire but periodic recurrences don't subsequently follow their normal schedule, the `last_run_at` update path post-activation is broken. Should not happen — the scheduler's `record_task_run` path is unchanged.

---

## Friction (honest list)

1. **Activation outside RTH still produces stale-ish data.** `track-universe` activation-fires regardless of RTH state, fetching whatever bars Alpaca returns (which may be stale if activated on a weekend). The recurrence prompt handles stale data (`data_stale: true` flag in ticker.yaml) but the cockpit doesn't yet visually distinguish stale-from-activation vs stale-from-failure. Cosmetic, not load-bearing.

2. **`falsify-signals` is expensive on cold-start.** Walks 90 days × 1Hour bars × N tickers × N signals through the Reviewer's specialist dispatch path. First activation could consume meaningful tokens. Token budget pressure surfaces if `_autonomy.yaml::ceiling_cents` is low — but this is a one-shot cost, amortizable.

3. **Operator may re-reset and re-activate often during alpha.** Each cycle re-fires `falsify-signals` (intended per ADR-270 D3), which means re-paying the token cost each time. Acceptable during alpha when activation is intentional; would want a "skip falsify-signals on re-activation if findings are fresh" gate before scaling — but that's future scope.

4. **Bootstrap exception in `principles.md` is now layered.** Rule 7 has a bootstrap exception for missing `_regime.yaml`; rule on the new research-findings layer has its own "trade them anyway" disposition. Two bootstrap clauses with similar shape. Probably fine; watch for confusion when both fire in the same cycle.

---

## Links

- **ADR**: [ADR-270 Fire-on-Activation Recurrences](../adr/ADR-270-fire-on-activation-recurrences.md)
- **Kernel change**: `api/services/scheduling.py::compute_next_run_at` — one conditional at the top of the function
- **Bundle changes**: `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`, `review/principles.md`, new `research/mandate.md` + `specs/falsify-signals.md`
- **Companion observation (same day)**: [2026-05-13-regime-wiring.md](./2026-05-13-regime-wiring.md) — regime substrate wired, predates and motivates this change
- **Predecessor framing**: [2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md](./2026-05-13-iter2-three-layer-trade-execution-gap-kvk.md) — iter-2 named the trap class this change addresses at a different layer
- **Discourse summary**: this observation doc + ADR-270 §7 (Discourse context for trace) — multi-turn architectural conversation that converged from "should we have a Researcher Agent" to "activation should be an active substrate-population moment"
- **Verification persona**: `seulkim88@gmail.com` → persona slug `alpha-trader` → user_id `2be30ac5-b3cf-46b1-aeb8-af39cd351af4` → workspace_id `b7e1b9bc-ffb3-478e-bd05-dcae01a8a6b1`
