---
tier: canon
note: "Program-shipped structural rules. Operator may override but typically does not."
---

# Conventions — alpha-trader (template)

> Structural rules every agent in this workspace honors. Universal across the program; operator may edit but most operators leave defaults.

## Substrate conventions

- Signal definitions live at `/workspace/context/trading/_signals.md`.
- Per-instrument entities at `/workspace/context/trading/{ticker}/_thesis.md` and `_signals.md`.
- Performance lives at `/workspace/context/portfolio/_performance.md`. Reconciler-owned, never hand-edited.
- Risk state at `/workspace/context/portfolio/_risk_state.md`. Hand-editable for budget changes; reconciler updates open-risk values.

## Proposal envelope conventions

Every trading proposal carries:
- Named signal (must exist in `_signals.md`)
- Sized stop (distance + dollar amount)
- Risk percent applied (must match `_operator_profile.md` for the position size class)
- Expected expectancy (from rolling history of the signal)
- Var budget impact (must fit current `_risk_state.md`)

Proposals missing any of these are rejected at Reviewer with a structured reason.

## Vocabulary discipline

- "Conviction" → blocked. Sizing comes from formula, not feeling.
- "I think this is going up" → blocked. Edge is named or absent.
- "Feels right" → blocked. Process-first.

## Time conventions

- All timestamps UTC in substrate; rendered in operator's local time at surfaces.
- "Today" means the current trading session, not calendar day.
- Pre-market = before US equity open; post-market = after close.
