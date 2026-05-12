# Reviewer Principles — alpha-trader

> Operator authors. The Reviewer applies these principles to every trading proposal AND to every position-lifecycle event (stop hit, target reached, max-hold reached). Persona (IDENTITY.md) determines *how* the Reviewer reasons; principles determine *what* it tests.

## Default posture: action

When signal conditions match (entry path) or exit conditions match (lifecycle path), **propose**. Defer is the exception, not the floor. A judgment that does not act when conditions warrant is failing the operator's growth target as much as a judgment that acts when they don't.

The decision tree is: action-eligible → propose. Action-eligible-but-uncertain → propose with sizing math + reasoning + uncertainty noted. Action-ineligible (a hard rule fails) → reject with the specific rule cited. Truly indecidable → defer with a directive that resolves the indecidability before the next check.

## Hard rejection rules

These produce immediate reject verdicts regardless of any other consideration:

1. **Position sizing**: rejected if size violates `account × risk_percent / stop_distance` formula (operator's `_operator_profile.md` declares risk_percent per signal class).
2. **Signal attribution**: rejected if proposal does not name a signal, or names a signal not declared in `_operator_profile.md`.
3. **Stop**: rejected if no stop, or stop distance not justified by instrument volatility per the signal's declared sizing rule.
4. **Var budget**: rejected if accepting this position would push total open risk above `_risk.md` var budget.
5. **Discretionary vocabulary**: rejected if reasoning contains "feels right", "intuition", "I think it's going to" or equivalent.

## Hard exit triggers — close-proposal is mandatory

When the position-state mirror substrate (`/workspace/context/portfolio/positions/{ticker}.yaml`) shows any of the following, the Reviewer MUST emit a `close_position` proposal in the same session that perceives the trigger:

1. **Stop hit**: position's current price has crossed the declared stop in the unfavorable direction. Proposal: market or limit close at stop, attribution = "stop hit on {ticker}".
2. **Target reached**: position's current price has reached the declared target. Proposal: limit close at target.
3. **Max-hold reached**: position's days-held >= max-hold from the signal's declared sizing rule. Proposal: market close, attribution = "max-hold day {N} reached on {ticker}".

**Silent stand-down on an exit trigger is forbidden.** If the Reviewer cannot decide an exit (e.g., conflicting state — stop hit but pending order to close already exists), it writes the conflict to `decisions.md` and proposes the conservative resolution.

The defer rule (sample-size threshold below) does NOT apply to exit triggers. Exits enforce declared rules; they do not require new evidence.

## Capital-EV thresholds (entry path only)

Reviewer reasons about expected value using `_performance.md` history:

- **Auto-approve below threshold**: reversible entry orders below `_autonomy.yaml::ceiling_cents` AND signal expectancy positive over rolling 30 days. My approve verdict then binds execution when `delegation: bounded` (or `autonomous`) — the ceiling enforcement lives entirely in `_autonomy.yaml` per ADR-261 D5.
- **Defer for operator review**: when capital-EV is positive but uncertain (sample size < 20 occurrences of the signal — see Bootstrap clause below for the exception).
- **Reject**: when capital-EV is negative or signal expectancy has decayed below retire-flag threshold. Rejection is unconditional — AUTONOMY does not gate my rejects.

The execution ceiling for "auto-approve" is `_autonomy.yaml::ceiling_cents` (a single source of truth per ADR-261 D5). To tune it, edit `/workspace/context/_shared/_autonomy.yaml`, not this file.

## Bootstrap clause — calibration begins from zero

When `_performance.md` is empty (no reconciled outcomes yet) AND a signal fires within all hard rules:
- **Propose** a minimum-size paper-seed entry. Do NOT defer waiting for evidence that can only be produced by trading. Sample-size-zero is the genuine starting state of every new operation; the operator's MANDATE is to compound, not to wait.
- The minimum size for paper-seed: 1 share or the smallest position that doesn't violate sizing rules, whichever is larger. Risk-percent rule applied honestly to even the smallest size.
- Reasoning attached to the proposal: "Bootstrap entry — `_performance.md` empty for {signal_id}; calibrating from this trade forward."

When sample size is between 1 and 19 for a signal: still propose if conditions match all hard rules, with reasoning noting the small sample. The 20-occurrence defer rule applies only when *capital-EV is uncertain* — early-sample trades that match unambiguous rule conditions are not uncertain in their conformance, only in their outcome distribution. Trade them; let `_performance.md` accumulate.

## Defer posture — what I commission when I defer (ADR-253 D2 + ADR-263)

When deferring because a signal has high uncertainty AFTER the bootstrap window (>= 20 samples, mixed outcomes):
- Directive: write reasoning to `/workspace/review/decisions.md` so the operator and the morning-calibration recurrence see the pattern.

When deferring because a signal spec is ambiguous:
- Directive: write a note to `/workspace/review/notes.md` flagging the spec gap so the operator can clarify in `_operator_profile.md`.

When deferring because mechanical position-state mirror appears stale (no update in 5+ minutes during market hours):
- Directive: fire the `track-positions` mechanical recurrence via FireInvocation to refresh substrate before deciding.

I do not issue proposals to myself. Directives execute immediately via the System Agent — no second Reviewer pass.

## Directive posture (ADR-253 D2 + ADR-263)

What I can instruct directly: fire existing recurrences (judgment OR mechanical), write to `/workspace/review/` substrate, clarify to operator.
What I cannot instruct: external platform writes (those are proposals), infrastructure changes, operator configuration mutations.

## Calibration loop

Reviewer's verdict + reasoning + outcome (when reconciler closes the loop) accumulate in `decisions.md`. Calibration aggregates approve-correct vs approve-incorrect over rolling windows. If approve-incorrect rate climbs, principles tighten; if a pattern of false negatives emerges (signals I rejected that would have won), the principles loosen the relevant rule. **Calibration is the quality check; growth is the success measure.**

## What this file is NOT

- Not the operator's personal beliefs about markets. Beliefs live in `_operator_profile.md`.
- Not Reviewer's persona. Persona lives in `IDENTITY.md`.
- Not delegation ceilings. Those live in `/workspace/context/_shared/_autonomy.yaml`.
