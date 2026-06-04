# Finding — Temporal awareness is already kernel-first-class; alpha-trader's market-hours friction is an execution-path wiring gap, not a missing feature

**Date**: 2026-06-04
**Hat**: External Developer of the System (Hat B) — this is an evaluation finding. It recommends system-side changes; the fix lands in Hat-A canon (alpha-trader bundle + `risk_gate` wiring).
**Trigger**: Operator (KVK) reported alpha-trader paper accounts "continuously experiencing market-hour difficulty" and asked whether the setup should move to futures (via massive.com) to dodge it. Underlying architectural question raised: *is time/temporal-awareness something that should be a first-class, cross-workspace agent feature, or is it program-specific?*

---

## TL;DR

1. **Massive (massive.com) is a market-DATA provider, not a broker.** It cannot replace Alpaca (the executing broker) — different product class. It *could* replace Polygon as a futures data feed. Trading futures would require a *new execution broker* (Tradovate/IBKR), because **Alpaca does not broker futures**. That path is a large new platform integration, not a config change, and should be decided on strategy grounds — not to dodge market hours.

2. **Time-awareness is already a first-class kernel feature.** ADR-274 + FOUNDATIONS Axiom 4 v8.5 settled it: *"Time is an envelope concern, not a substrate concern."* The kernel injects `now` / timezone / workspace-tenure / **market state** into every Reviewer wake envelope. A real NYSE calendar, a semantic scheduler (`@market_open + 15min`), and a `trading_hours_only` risk-gate parameter all already exist. The operator's intuition ("this might be more fundamental than a client patch") was correct **and already canonized**.

3. **The real bug is a wiring gap, not a missing primitive.** The execution path (`alpaca_client.submit_order`) submits orders blind to the temporal intelligence that exists upstream. The fix is program-scoped (alpha-trader bundle config + connecting the existing `trading_hours_only` gate to order submission). **Nothing in the kernel needs to change.**

4. **Cross-program test confirms market-hours must NOT be promoted to kernel.** No other program needs market hours: alpha-author opts out (`exchange: operator_authored`), alpha-prediction needs expiry-timing, alpha-defi needs block-time (24/7), alpha-commerce needs settlement-timing. "What time is it when I wake" is universal (kernel, already done); "NYSE is open" is alpha-trader policy (program).

---

## Evidence — what the kernel ALREADY has

| Capability | Location | Status |
|---|---|---|
| Operating Context block (`now`, tz, tenure, **market state**) injected into **every** Reviewer wake | `api/services/reviewer_envelope.py:133-212`, unconditionally composed at `:327` | Live |
| Market state delegated to bundle (graceful-degrades to `n/a` when absent) | `reviewer_envelope.py:174-186` (`get_market_context_for_user`) | Live, bundle-gated |
| NYSE calendar — session windows (regular / pre / after), 2026–2027 holidays | `api/services/market_calendars.py` (`NyseUsCalendar`) | Live |
| Semantic scheduler — `@market_open + 15min`, `@every 1min during regular_hours` | `api/services/scheduling.py` (`resolve_semantic_schedule`) | Live |
| Risk gate `trading_hours_only` param | `api/services/risk_gate.py:196-201` | Live; **was** hand-rolled UTC approximation — fixed 2026-06-04 (see Resolution) |
| Scheduler honors market-day semantics (Memorial Day Monday skipped; `next_run_at`→Tue) | Verified in `docs/evaluations/2026-05-26-134500-signal-evaluation-tuesday-rth/PLAYBOOK.md` | Verified in prod |

### Canon framing (FOUNDATIONS Axiom 4 v8.5, ~line 423)

> "Time is an envelope concern, not a substrate concern. Identities perceive *now* when they wake — not by reading workspace state … This mirrors Claude Code's runtime model: time is contextual input on each invocation, not persisted memory between invocations. The Reviewer's wake envelope MUST surface current time + timezone + market context whenever the workspace has standing intent that depends on time."

Derived Principle 18: *"Standing intent implies Trigger-authoring authority."*

---

## Evidence — the gap

`api/integrations/core/alpaca_client.py` (the execution path) consults **none** of the above. `submit_order` sends `time_in_force: "day"` with no clock check, no `extended_hours` flag, no consultation of the `trading_hours_only` gate. There is no `get_clock`/`get_calendar` method on the client at all.

So the temporal intelligence exists upstream (envelope knows market state; scheduler anchors to `@market_open`; risk gate *can* enforce `trading_hours_only`) but is **not connected to the order-submission moment** — or the alpha-trader bundle's recurrences/`_risk.md` aren't actually opting into the `trading_hours_only` gate that already exists.

**Symptom mechanics off-hours**: a `day` order placed when the market is closed is queued/accepted-but-unfilled until next open → the trading outcome reconciler can't join a fill → ambiguous/dead run → "continuous market-hours difficulty."

---

## Canonical home for the model

The agent-behavior synthesis this finding produced (three planes of time + kernel-universal vs
program-declared perception + the two evolution seams) was captured in canon at
[`docs/architecture/cadence-and-wakes.md` §8b](../../architecture/cadence-and-wakes.md#8b-temporal-model--how-time-reaches-agent-behavior),
with the two seams added to that doc's §15 (Open hardening questions). FOUNDATIONS Axiom 4 and
ADR-268 now point there. Read §8b for the durable model; this finding is the evaluation trail.

## Architectural classification (the answer to the operator's question)

Two-layer structure. Both layers already exist and are correctly placed:

| Layer | Classification | Owner |
|---|---|---|
| Runtime context (`now`, tz, tenure) | **Kernel, first-class, unconditional** | Kernel (`build_operating_context_block`) |
| Market state (RTH open/close) | **Program policy on a kernel primitive** | Bundle declares `market_context` (alpha-trader does; alpha-author opts out) |
| Market-hours enforcement at order time | **Program-specific** | `_risk.md` `trading_hours_only` → `risk_gate` |
| Semantic schedules (`@market_open`) | **Kernel infra, program-shaped** | Kernel scheduler; bundle declares usage |

**Verdict: hybrid, and it's already built correctly.** Promoting "market hours" itself to the kernel would be the scope-bloat the operator feared — and it would be *wrong*, because market-hours is not universal. The universal thing ("what time is it when I wake") is already kernel-first-class. The operator's scope-bloat instinct is vindicated: do **not** generalize further.

---

## Resolution (implemented 2026-06-04)

During implementation the diagnosis tightened once more. The recommended steps 1–2
turned out **already done**: the alpha-trader `_risk.md` already sets `trading_hours_only: true`,
and the `risk_gate` is already wired into the execution path (`check_risk_limits` is called
at 3 trading-tool sites in `platform_tools.py`). So the gate already fired on every order.

The actual remaining gap was a single **Singular-Implementation violation**: the gate's
`_is_us_market_hours()` was a hand-rolled UTC-window approximation that **ignored DST**
("≤1 hour drift") and **ignored NYSE holidays entirely** — while the kernel already had a
DST-/holiday-correct `NyseUsCalendar` (`market_calendars.py`). The crude version, sitting on
the execution path, *was* the "market-hour difficulty": e.g. winter 15:50 EST = 20:50 UTC
fell outside the fixed `13:30–20:00 UTC` window and was falsely rejected though the market
was open; and orders on holidays like Christmas were let straight through.

**Fix shipped (program-scoped, no kernel change):**
1. Added `MarketCalendar.is_open_now(session, now=)` to `market_calendars.py` — the one missing
   "right now" check on the existing calendar (DST-/holiday-correct, generic across calendars).
2. Rewired `risk_gate` `trading_hours_only` to route through `NyseUsCalendar.is_open_now()`;
   **deleted** `_is_us_market_hours()`.
3. Regression gate `api/test_market_hours_gate.py` (12/12) — locks RTH/edges/weekend/holiday/DST
   correctness + asserts the approximation cannot reappear.
4. Doc cascade: ADR-268 §6 reference note updated (both layers now share one source of truth);
   `risk_gate` scaffold docstring corrected.

**Amends**: ADR-187 (execution gate is now DST-/holiday-correct via the kernel calendar) +
ADR-268 (execution layer joins the scheduling layer on one market-calendar primitive). No new ADR.

Steps 3–4 of the original recommendation (off-hours skip-clean narrative; `@market_open`
recurrence anchoring) were found **already working** — the scheduler already honors market-day
semantics (Memorial Day skip verified in the 2026-05-26 RTH eval), and off-hours orders are now
cleanly rejected by the gate with an honest reason string rather than silently queued.

## Futures — dropped from scope

Per operator decision (2026-06-04): with the market-hours friction resolved on the existing
Alpaca broker, the futures discussion is moot. Massive (data-only, not a broker) cannot replace
Alpaca; trading futures would require a new execution-broker integration (Tradovate/IBKR) — a
strategy decision, not a fix for this bug, and explicitly **not** being pursued. Captured here
only so the reasoning isn't re-litigated:

- **Massive = market data only** (CME/CBOT/NYMEX/COMEX). Zero execution/brokerage.
- **Alpaca = broker**, equities/options/crypto. **No futures brokerage.**
- Futures' near-24h sessions would dodge market hours but at the cost of a new broker integration.

**Status: CLOSED.**
