# Conventions — alpha-trader

> Structural rules every agent in this workspace honors. Universal across the program; operator may edit but most operators leave defaults.

## Substrate conventions

- **Signal definitions** live in `_operator_profile.md` (operator-authored). Each signal declares trigger / entry / stop / target / position-sizing / max-hold / historical-baseline.
- **Per-instrument fundamentals**: `/workspace/context/trading/{ticker}.yaml` — refreshed by `track-universe` (judgment) per spec at `/workspace/specs/ticker-snapshot.md`.
- **Per-position state**: `/workspace/context/portfolio/positions/{ticker}.yaml` — refreshed every minute during market hours by `track-positions` (mechanical, ADR-264 SyncPlatformState). Reviewer reads substrate, never broker APIs as primary perception.
- **Account state**: `/workspace/context/portfolio/_account.yaml` — refreshed every 5 min by `track-account` (mechanical).
- **Open orders**: `/workspace/context/portfolio/_orders.yaml` — refreshed every minute by `track-orders` (mechanical).
- **Signal fires**: `/workspace/context/trading/signals/{signal_id}.yaml` — appended by `signal-evaluation` (judgment).
- **Performance** (money-truth, ADR-195 v2): `/workspace/context/trading/_money_truth.md`. Reconciler-owned, never hand-edited.
- **Risk envelope** (operator-authored): `/workspace/context/trading/_risk.md`. Hand-editable for budget changes; declared once, read by Reviewer + signal-evaluation + reports.

## Proposal envelope conventions

Every trading proposal carries:
- **Named signal** (must be declared in `_operator_profile.md`)
- **Sized stop** (distance + dollar amount)
- **Risk percent applied** (must match `_operator_profile.md` for the position size class)
- **Expected expectancy** (from rolling history of the signal in `_money_truth.md`)
- **Var budget impact** (must fit current `_risk.md` envelope)

For close-position proposals (exit path):
- **Exit reason** (stop_hit | target_reached | max_hold_reached)
- **Position state trace** (the substrate snapshot from `/positions/{ticker}.yaml` that triggered the close)

Proposals missing any required field are rejected at Reviewer with a structured reason.

## Vocabulary discipline

- "Conviction" → blocked. Sizing comes from formula, not feeling.
- "I think this is going up" → blocked. Edge is named or absent.
- "Feels right" → blocked. Process-first.

## Time conventions

- All timestamps UTC in substrate; rendered in operator's local time at surfaces.
- "Today" means the current trading session, not calendar day.
- Pre-market = before US equity open; post-market = after close.

## Recurrence mode discipline (ADR-263)

Every recurrence in `/workspace/_recurrences.yaml` declares `mode: judgment | mechanical`:
- **`mechanical`** — `prompt` is a `@primitive: ...` directive; dispatcher executes deterministic Python; no Reviewer wake; zero LLM cost. Used for substrate mirroring (track-positions, track-account, track-orders).
- **`judgment`** — `prompt` is a Reviewer message; wakes the Reviewer with the prompt as the addressed-equivalent envelope. Used for everything that requires capital judgment, framework reasoning, or composition.

Operators authoring new recurrences via YARNNN are guided to declare mode at create time. Default at parse time when absent: `judgment` (preserves backward compatibility).
