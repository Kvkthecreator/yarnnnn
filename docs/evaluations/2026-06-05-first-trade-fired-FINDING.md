# Finding — the first trade fired: the autonomous capital chain, traced end-to-end

**Date**: 2026-06-05
**Persona / workspace**: kvk (`2abf3f96-118b-4987-9d95-40f2d9be9a18`), alpha-trader, live Alpaca paper, `delegation: autonomous`
**Hat**: B (investigation + fixture) crossing to A (the four substrate/prompt fixes)
**Criterion**: the alpha-1 one-liner — *"a real signal produces a proposal that auto-executes within the envelope"* (the autonomous capital loop closing once, end-to-end, against the real broker).

---

## Headline

Across the entire alpha-trader arc the loop was never observed closing. This
session traced it link-by-link against kvk's live substrate, found **five
stacked issues** (four real bugs + one correct gate that masked them), fixed
the four, and **observed the chain close end-to-end** — an Alpaca paper bracket
order accepted, the proposal flipped to `executed`, `client_order_id`
round-tripping the proposal_id for P&L attribution. The execution was an
explicitly-labeled **off-hours fixture** (one risk-gate flag flipped + reverted)
because real NYSE was closed; the only thing now between the system and a fully
**organic** autonomous RTH trade is a market-open signal-evaluation fire.

---

## The chain, with substrate receipts

The autonomous capital chain and where each link stood at session start:

```
signal-evaluation reads {TICKER}.yaml → matches signal rule → writes signals/{id}.yaml
  → emits ProposeAction(...) inline → risk_gate → execute → Alpaca → pending→executed
```

| # | Link | Session-start state | Fix |
|---|---|---|---|
| 1 | seed reaches the Reviewer | **casing race**: seed in `nvda.yaml` (lowercase), Reviewer reads `NVDA.yaml` (uppercase via `ticker.upper()`). The matching seed never reached the Reviewer; every "DEFER no actions" on a seeded test was the Reviewer correctly standing down on *real* non-matching data. | Hat-B scenario seed → UPPERCASE + `delete_substrate` shadow defense (`ee432d7`); kvk live lowercase head row deleted (revision chain preserved). |
| 2 | signal pipeline fires | **empty `signals/`** → empty `_signals_summary.md` in the wake envelope → the Reviewer had to read `{TICKER}.yaml` live → contributed to round-budget pressure. (Empty because §1 meant signal-evaluation read real non-matching NVDA.) | resolved by §1 — once the seed was readable, `signals/signal-2-mean-reversion-oversold.yaml` was written (629 B, the first signal entry ever). |
| 3 | proposal field schema | **emit-schema drift**: signal-evaluation prompt emitted `direction`/`position_size`; `platform_trading_submit_order` requires `side`/`qty`/`order_type` (inputs passed RAW, no translation layer). `rejected_at_execution: "ticker, side, qty, order_type are required"`. | Hat-A bundle `_recurrences.yaml` → `side`/`qty`/`order_type` (`16a6067`); kvk live rev `0c1ddcb7`. |
| 4 | risk envelope | `require_stop_loss: true` — a plain `submit_order` carries **no protective stop**, so the risk_gate rejects it ("no stop") even with correct field names. Surfaced by the fixture. | Hat-A bundle entries → **bracket order** (`submit_bracket_order` with entry/TP/SL legs) (`2de6f76`); kvk live rev `8bbfba2d`. |
| 5 | market-hours gate | **NOT a bug — correct judgment.** Post-fix re-fires stood down: NYSE closed (`is_open_now()=False`), Signal-2 entry = next-open, principles.md:109 forbids off-hours entry. This is the system working; it also *masked* bugs 3+4 (a stand-down looks the same whether the cause is "market closed" or "schema broken"). | none — it's correct. The off-hours fixture neutralized it (labeled + reverted) only to validate the execution link. |

Plus a **casing-clarity Hat-A fix** (`2e8dfbf`, kvk rev `ab40a65a`): the prompt's
`{ticker}` placeholder → `{TICKER}` UPPERCASE with a note, so an LLM can't
lowercase-drift the read. (No kernel code path produces lowercase — the only
ticker-path construction is `track_universe.py:264`, already `.upper()` — so the
casing race was a fixture/prompt surface, not a kernel class.)

### The executed trade (the receipt that matters)

```
proposal 0e4ed324-5026-4705-8f62-33e8d81c6b64  → status: executed
Alpaca order a3ae3e54-d91a-4b0d-867d-5a1bbb7e2820  → status: accepted, order_class: bracket
  client_order_id == proposal_id  (P&L attribution round-trips)
  NVDA buy 8 @ $180.20 limit, TP $192.20, SL $170.85  (the Reviewer's own 00:36 values)
  risk_gate PASSED: 14.4% < 15% position cap; bracket satisfies require_stop_loss
```

The Reviewer's own reasoning (judgment_log, 00:36, the first readable-seed fire,
`confidence: high`): verified all three Signal-2 conditions, computed sizing
(8 shares from $10k × 0.75% / stop), checked regime freshness + var budget, noted
the bootstrap clause (18 fills < 20 steady-state, above the −0.5R decay floor).
This is editor-coherent mandate-holder reasoning — the judgment axis was sound
all along; the *machine* under it was broken in four places.

### Fixture discipline (honest record)

The executed proposal's `decision_context.rationale` is prefixed `[FIXTURE]`.
`trading_hours_only` was flipped `true→false` and **reverted in the same script's
`finally` block** (verified: `true` restored). The bracket order's three legs
were cancelled (0 open positions, 0 live orders). Nothing about kvk's policy
substrate changed; the audit trail names the run as a validation fixture.

---

## What this resolves about the two axes (EVAL-SUITE-DISCIPLINE §0)

The arc's recurring confusion — "the Reviewer keeps standing down" read as a
judgment problem — was **four machine bugs masquerading as mind behavior**, plus
one correct gate (market-hours) that made every failure look identical to a
stand-down. This is the §0 lesson in its purest form: a machine fault read as a
mind decision. The fix was deterministic tracing (substrate receipts at every
link), not judgment-eval interpretation.

The architecture-axis tests from the prior session (`test_alpha_trader_pipeline_
e2e.py`) did NOT catch bugs 3+4 because they **injected a proposal with the
already-correct submit_order fields**, bypassing the signal-evaluation → broker
translation that was the actual gap. **Next architecture-test extension**: a test
that exercises the *emit* schema (the signal-evaluation prompt's ProposeAction
shape) against the *tool* contract — asserting the bundle prompt emits the fields
`platform_trading_submit_bracket_order` requires. That deterministic test would
have caught bugs 3+4 as red instantly.

---

## What remains for a fully-organic autonomous trade

1. **An RTH signal-evaluation fire.** Everything else is proven. During market
   hours, with a real (or seeded-and-not-clobbered) Signal-2 match, the chain
   should now propose a bracket → risk_gate passes → auto-execute. The deployed
   bundle carries the bracket emit-schema; kvk live carries it too.
2. **Whether real signals fire often enough** is the *environmental* question
   (Signal-2 is rare by design). Once an RTH trade is observed, the legitimate
   next lever — softening the signal/threshold — splits into: a **fixture**
   loosening (Hat-B, to observe more trades in dev) vs. a **real signal-def
   change** (Hat-A `_operator_profile.md`, operator- or Reviewer-authored via
   ADR-295 self-amendment discipline). The latter is itself something to test the
   Reviewer *against* (the 2026-05-20 capitulation), not to reach in and do.

---

## Commits

- `ee432d7` — Hat-B casing-shadow defense (scenario `delete_substrate` + `_execute_setup_step` handler) + kvk live cleanup.
- `16a6067` — Hat-A emit-schema fix (direction/position_size → side/qty/order_type) + kvk live rev `0c1ddcb7`.
- `2de6f76` — Hat-A bracket-order fix (entries emit `submit_bracket_order`) + kvk live rev `8bbfba2d`.
- `2e8dfbf` — Hat-A casing-clarity ({TICKER}.yaml UPPERCASE) + kvk live rev `ab40a65a`.

All on `main`, pushed. Deployed scheduler (`crn-d604uqili9vc73ankvag`) reads kvk
live substrate directly — the fixes are effective without a code redeploy.
