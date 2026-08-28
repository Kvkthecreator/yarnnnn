# ADR-618: Standing work is bounded by the pool

**Status**: Ratified + implemented 2026-08-28. Found by auditing the standing-run path after the operator asked whether it was "incomplete in its set-up, because we essentially sunset all prior approaches."

**Builds on**: ADR-172 (the balance hard-stop) · ADR-396 (the pool) · ADR-445 §9 / ADR-491 Phase 3 (`check_draw`, the member-facing gate) · ADR-569 (strings) · ADR-592 (radar deleted for this exact property) · ADR-603 D5 (recurrences retired).

## Context

The audit's hypothesis was that standing work is incomplete. It is not: the strings lane is the most complete lane in the tick — discovery → index (with the never-run commitment fix) → CAS claim → dual executor → confined write with citations → embed → two `execution_events` → schedule advance → desk projection. **It is complete and, as of 2026-08-24, has zero production tenants** (0 `_string.yaml` files, 0 `kind='string'` rows).

That combination is what made the gap invisible. A prose string's derive is **metered judgment spend**, and the only thing between a declared string and an operator's balance was `AGENT_ENABLED` — which defaults ON.

**This is the precise property that got radar DELETED rather than hidden.** The scheduler says so in its own words, in the comment block that sits immediately above the strings lane:

> *"It drained every tick and each sweep was metered judgment spend… That is why Radar was deleted outright rather than hidden behind `stage: internal`: an app nobody can reach must not keep spending an operator's balance, and a dormant spend lane is precisely the ambiguity a future session would have to re-derive."*

The next comment then introduces strings as radar's *"sibling, same posture."* It inherited the posture without inheriting the guard. Every member-facing costed entry — lanes, Studio, images, feed — calls `check_draw`; `services/strings.py` called nothing.

## Decision

### D1 — A string's run is gated on the pool, before the fetch

`run_string_sweep` checks the balance and refuses when the pool is exhausted.

**`check_balance`, not `check_draw`.** Standing work attributes to the OWNER, who is never member-capped, so `check_draw`'s second half is a no-op here — and reaching for it would imply a per-member bound this lane does not have. This is the convention the wake lane already holds, and which `check_draw`'s own docstring names: *"NOT called on the wake/recurrence lane: standing work attributes to the owner… the wake path keeps its own `check_balance`."*

**Before the FETCH, not merely before the derive.** The fetch is $0 in model terms, but it writes retained observations and reaches connectors — work whose only purpose is to feed a derive that cannot run. A gate that lets the pointless half proceed is a half-gate.

**A refusal is a RECORDED run.** It emits a `string-sweep` event with `error_reason="balance_exhausted"`, so the desk can say why nothing moved. A silent skip reads as a broken string rather than an empty balance — the ADR-373 D6 incorrect-success class in its quiet form.

**Fail-OPEN when the check cannot RUN**, matching `wake.py` exactly: a DB hiccup must not silently strand an operator's standing work. This is narrower than it sounds — `check_balance` already returns `0.0 → blocked` on a balance-read failure, so this covers only the case where the check itself could not execute.

### D2 — The manual fire takes the same CAS claim as the scheduled drain

`POST /strings/{topic}/run` called `run_string_sweep` inline with no `claim_string_run`, so a Run-now racing a scheduled tick executed the string **twice** — two derives, two writes, two charges — and both callers then called `record_string_run`, rewriting the schedule anchor twice from two different "now"s.

The route's own docstring already promised *"exactly one scheduled run's body."* That has to mean the claim too, or it is only the body and not the run. `read_string_task_row` is added so the manual door can read the current `next_run_at` to claim against (the drain already holds it from its due-scan).

**Losing the claim is a SUCCESSFUL no-op**, not an error: the string IS running, just not on this caller's thread. A 409 would tell the operator something went wrong when nothing did.

**A never-indexed string stays claimable.** A string declared since the last tick has no index row; reading that `None` as a lost race would make a brand-new string permanently un-fireable by hand.

## Consequences

- Standing work can no longer overdraw a workspace. The lane keeps its own convention (pool hard-stop, owner-attributed) rather than borrowing the member-facing one.
- Run-now is idempotent against the scheduler.
- The gate is the reason this lane can now safely acquire its first tenant.

## What this does NOT decide

- **Whether recurrences should be un-creatable.** They are retired by *population*, not by *construction*: `Schedule` remains on three tool rosters (chat, specialist, and the Reviewer's own self-scheduling), `materialize_scheduling_index` still runs, and program activation still forks ~430 lines of bundled `_recurrences.yaml`. One `Schedule` call re-animates the retired lane into the Reviewer. Disarming that is a scope decision, not a cleanup, and it belongs with ADR-596 D3 phase (a).
- **The tick's observability.** The hourly heartbeat and the final `Completed:` line still count only recurrence outcomes (always 0); a total strings-lane failure logs at WARNING and is invisible in the summary. Named here so it is assigned rather than forgotten.
- **`standing_declarations.py` generalization.** It has zero runtime callers and `DECLARATION_KEYS` governs no parser — deliberate per ADR-603 D6, which gates it on a second declaration kind that does not yet exist.

**The rule this ADR leaves behind**: an unattended lane that spends must name its bound. "Nobody has declared one yet" is a population fact, not a guard.
