# Research Mandate — alpha-trader

> **Operator: this file is the standing intent for the research substrate at `/workspace/research/`.** It is read by the `falsify-signals` recurrence (ADR-270 bootstrap) and any future research recurrences. Customize what's here; the Reviewer reads `/workspace/research/findings/*.md` at proposal time per `principles.md` Capital-EV thresholds.

## Purpose

Populate substrate the Reviewer can reason against in the first cycle, before `_money_truth.md` has accumulated live evidence. Without research substrate, the Reviewer's first-cycle proposals fall through to the principles.md Bootstrap clause ("trade them; let _money_truth.md accumulate") — defensible but slow to converge.

Research substrate's job is to give the Reviewer historical context to weigh against operator-declared signals. It is **not money-truth**. Every finding written here carries `source: replay` in frontmatter, and `principles.md` weights live `_money_truth.md` evidence higher when both exist.

## What "research" means in this workspace

Quantitative, deterministic falsification of operator-declared rules against historical bars. Not:

- Not narrative speculation about whether a signal will work
- Not LLM-generated trading ideas
- Not market commentary

The `falsify-signals` recurrence walks every signal in `_operator_profile.md` against 90 days of historical Alpaca bars, computes synthetic outcomes deterministically (stop hit / target hit / max-hold), and writes per-signal findings to `/workspace/research/findings/{signal_id}.md` per the schema in `/workspace/specs/falsify-signals.md`.

## Fidelity gaps (named honestly)

Synthetic outcomes are not real outcomes. The fidelity gaps the operator should know:

1. **No slippage model.** Limit fills are assumed at limit price; market fills at the bar close. Real fills deviate.
2. **No spread cost.** Bid-ask spread is not deducted from R-multiples.
3. **Survivorship bias.** Tickers in `_universe.yaml` are the current universe; some may not have traded the full 90-day window.
4. **No regime conditioning.** Falsification treats all triggers equally regardless of VIX state when they fired.
5. **Walk-forward assumption.** Bar data is treated as available the moment the bar closes; in reality there's a fill delay.

The Reviewer is aware of these gaps via `principles.md` Capital-EV section's note that live `_money_truth.md` outcomes weigh more than replay findings.

## Earned escalation

Per ADR-270 §"Earned escalation," research lives as a one-shot bootstrap recurrence today. If observation across multiple workspaces or multiple weeks of operation shows that ongoing falsification is load-bearing — for example, signals drift faster than the quarterly audit catches — the bundle adds a periodic schedule to `falsify-signals` in a future revision. **Authoring a periodic research cadence is earned by evidence, not pre-emptive.**

## What this file is NOT

- Not Reviewer's principles. Those live at `/workspace/review/principles.md`.
- Not signal definitions. Those live at `/workspace/context/trading/_operator_profile.md`.
- Not the schema of findings files. That lives at `/workspace/specs/falsify-signals.md`.
- Not a permanent research function. Research today is bootstrap-only.
