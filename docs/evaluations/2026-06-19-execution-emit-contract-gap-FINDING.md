# Finding — full autonomy is blocked by an EMIT-CONTRACT gap, not by judgment, not by an over-strict floor

**Date**: 2026-06-19
**Hat**: B (evaluation). The finding is Hat-B; the fix it recommends lands in Hat-A (the recurrence prompt and/or a propose-time validator).
**Subject**: why kvk's signal-driven capital proposals never reach a real `executed` state — the operator's question "when and how do we get the agent proposing and trading on its own wakes."
**Trigger**: operator frustration that "we're continuously getting gated," with the instinct to relax the mandate/floor to force trades. This finding shows the gate is NOT the problem — the order *serialization* is.

---

## Criterion declared (discipline rule 0)

**What's measured against.** The alpha-trader compliance one-liner: *a real signal produces a proposal that auto-executes within the envelope.* Operationalized as: when `signal-evaluation` fires on a snapshot that satisfies a signal rule under `delegation: autonomous`, the emitted proposal should (a) be the **bracket** primitive the recurrence prompt mandates, with (b) **field names matching the executor's schema exactly**, so that (c) the risk gate sees a well-formed, stop-bearing order and — if hard rules pass and market is open — auto-executes.

**The aperture/floor frame (FOUNDATIONS DP24, ADR-342/343).** The operator's proposed fix ("change the mandate so it trades in full, wipe the per-proposal uncertainty") is a **floor edit under pressure** — exactly what DP24 forbids (*"a dormancy-rationalized floor edit is the pressure-capitulation in a costume"*). This finding tests whether the floor is genuinely the blocker (in which case the frustration is misdirected) by reading the actual rejection causes from substrate.

---

## What the substrate shows: the gate is NOT over-strict — the order is malformed before it reaches the gate

kvk has **23 consequential proposals, 1 executed (a `[FIXTURE]`), 0 real executions.** Reading the non-fixture `rejected_at_execution` rows (proposals the Reviewer judged sound that died at the execution step), the `execution_result` field gives the exact cause per row:

| Proposal | Reviewer's narration | `execution_result.error` | Class |
|---|---|---|---|
| `edaba1bd` (06-05) | "clears all seven hard rules" | `trading_hours_only=true ... outside NYSE hours` | **Timing** (off-hours) — floor correct |
| `126fc0ed` (06-05) | "All hard rules clear" | `ticker, side, qty, and order_type are required` | **Malformed payload** — empty required field |
| `b06d53ed` (05-20) | "sizing ceiling-constrained to 4 shares (15% cap)" | `position would be 33.9% ... no stop ... off-hours` | **Narration≠order** — order was 33.9%, no stop |
| `815ecc18` (05-20) | "all six hard rules satisfied" | `require_stop_loss=true but order has no stop ... off-hours` | **Narration≠order** — claimed stop, order had none |

And the live receipt from **today's** capability run (eval-1, deployed code, `9c3e3555`):

```
primitive: platform_trading_submit_order          ← PLAIN order, not bracket
inputs:    {qty:4, side:buy, ticker:NVDA, order_type:limit,
            limit_price:847.5, stop_loss_price:829.2}   ← stop present, WRONG KEY
```

**None of these is the floor being too strict.** They are three machine-layer faults:

1. **Off-hours (timing)** — structural; the floor is correct to gate it. This is an *aperture* lever (relaxable for a paper test), not a floor issue.
2. **Malformed payload** (`126fc0ed`) — a required field reached `submit_order` empty.
3. **The load-bearing one — EMIT-CONTRACT MISMATCH.** The Reviewer's *reasoning* is correct (sizes to 4 shares, names a stop at 829.20), but the *emitted order object* does not match any executor's schema, so the stop is invisible to the risk gate.

---

## Root cause: the model is not emitting the contract the prompt mandates

The kvk `signal-evaluation` recurrence prompt is **correct and explicit**:

> *"Entries are BRACKET orders... a plain submit_order carries no protective stop and the risk gate rejects it ('no stop')... always emit the bracket form below. (Proposal inputs are passed RAW to the platform_trading_submit_bracket_order primitive — names MUST match its schema exactly.)"*
> emit: `action_type="trading.submit_bracket_order"`, `inputs={ticker, side, qty, entry_limit_price, take_profit_limit_price, stop_loss_stop_price, ...}`

The three field-name conventions in play:

| Layer | Stop field | TP field | Entry field |
|---|---|---|---|
| `submit_order` executor (platform_tools.py:2116) reads | `stop_price` | — | `limit_price` |
| `submit_bracket_order` executor (platform_tools.py:2214) reads | `stop_loss_stop_price` | `take_profit_limit_price` | `entry_limit_price` |
| **Prompt instructs the model to emit** | `stop_loss_stop_price` | `take_profit_limit_price` | `entry_limit_price` |
| **What the model ACTUALLY emitted today** (`9c3e3555`) | `stop_loss_price` ✗ | *(none)* ✗ | `limit_price` |

**`propose_action.py` does NOT remap fields** — it stores `(primitive, inputs)` verbatim (line 221; `ACTION_TYPE_TO_PRIMITIVE` is a 1:1 name resolve, ADR-307 D4 deleted the dispatch map). So the stored proposal *is exactly what the model emitted*. The model:
- chose `trading.submit_order` (plain) when the prompt mandates `trading.submit_bracket_order`,
- invented `stop_loss_price` (a key **no executor reads** — not `stop_price`, not `stop_loss_stop_price`),
- omitted the take-profit leg entirely.

**Therefore: the judgment is sound; the serialization is not.** When this proposal executes, `submit_order` reads `stop_price` → `None` → `require_stop_loss` rejects "no stop" — *despite the Reviewer having correctly decided a stop at 829.20.* The floor is doing its job (an order with no machine-readable stop SHOULD be rejected). The fault is that a stop-bearing decision was serialized into a stopless order.

---

## Why this is the answer to "when/how full autonomy"

The operator's intuition — "we keep getting gated, let's loosen the mandate" — would **make this worse and unmeasurable**: relaxing `require_stop_loss` to let the malformed order through means auto-executing **stopless** trades (the exact thing the floor exists to prevent), and the resulting P&L could not be read as "self-improving judgment" because the judgment's stop was dropped. That is DP24's pressure-capitulation-in-costume, with receipts.

The real unblock is **one machine fix**: make the emit contract enforceable so the Reviewer's correct judgment reaches the gate as a well-formed bracket order. Once that lands:
- floor-passing proposals stop dying with "no stop,"
- during market hours, a clean signal auto-executes for real (reliance flips 0→1),
- and the self-improving loop measures *judged* trades, floor intact.

**Full autonomy is ~one serialization fix + a market-hours window away — not a mandate change, not a desire problem at the capital layer.** (The §12 desire question is real and separate; this finding shows the *capital-execution* blocker is mechanical, which means "the agent has never traded on its own" is currently overdetermined by a bug, not by the agent's judgment or the operator's trust.)

---

## Recommended fix (Hat-A) — two options, singular implementation

The gap is "model emits a contract-noncompliant order." A prompt is a soft instruction the model demonstrably ignored today. So the durable fix is a **propose-time validator** for trading capital actions, not (only) a stronger prompt:

**Option A (recommended) — a propose-time emit-contract validator.** In the trading propose path, before the proposal is stored: if `action_type ∈ {trading.submit_order, trading.submit_bracket_order}`, validate the inputs against the executor schema. Reject/repair the known drifts: `stop_loss_price → stop_loss_stop_price`, plain `submit_order` with a stop present → promote to `submit_bracket_order`, require the TP leg. This makes a contract-noncompliant emit fail *loudly at propose time* (a clear error the next wake can correct) instead of *silently at execution* (a "no stop" rejection that looks like a judgment failure). It is a deterministic guard → belongs in a `test_*.py`-gated change.

**Option B — prompt-only hardening.** Tighten the recurrence prompt with the exact failing example. Weaker: the model already had a correct, explicit prompt and still emitted `stop_loss_price`/plain-order today. Prompt-only is likely to recur.

**Recommendation: Option A, with the failing cases (`stop_loss_price`, plain-order-with-stop, missing-TP) as the test battery.** This is the machine fix the operator's "fix execution first" decision correctly prioritized — and it must land *before* any clean-test-account throughput run, or that account will only reproduce `rejected_at_execution`.

**Floor stays intact throughout.** Nothing here relaxes a risk rule. The fix makes the Reviewer's *already-correct* stop reach the gate; it does not weaken the gate.

---

## RESOLUTION (2026-06-19, same session — Option A implemented)

Option A shipped (Hat-A): `services/primitives/trading_emit_contract.py::
validate_and_repair_trading_emit`, wired into `handle_propose_action` before
primitive resolution (it can promote `submit_order → submit_bracket_order`).
Deterministic repairs: `stop_loss_price → stop_loss_stop_price`; plain order
carrying a stop → bracket (stop survives the gate); drifted entry/TP aliases
renamed. Unrepairable emit → loud `trading_emit_contract` error at propose
time. Repairs recorded on `decision_context.emit_repairs` (audit honesty).

Validated: `api/test_trading_emit_contract.py` **31/31** — every receipt case
above (9c3e3555 promote-then-loud-error-on-missing-TP, 126fc0ed missing-fields,
b06d53ed qty-untouched-floor-intact). Regression: risk-gate battery **14/14**
unchanged. CHANGELOG `[2026.06.19.2]`.

**Floor discipline proven by test**: the 100-share oversized case repairs to a
bracket but its qty is untouched, so `max_position_percent_of_portfolio` still
rejects it downstream — the validator fixes shape, never values.

**Remaining to close the loop to a real autonomous trade** (not this finding's
scope): (1) the deployed scheduler picks up this fix on next deploy of `main`;
(2) a clean signal must fire during US RTH so a now-well-formed bracket reaches
the open-market gate and auto-executes — flipping reliance 0→1.

---

## Receipts

| Claim | Receipt |
|---|---|
| Today's live emit is plain-order + wrong stop key | `action_proposals 9c3e3555` (2026-06-19): primitive=`platform_trading_submit_order`, inputs.`stop_loss_price`=829.2, no TP |
| Reviewer narration was correct (sized, stopped) | `9c3e3555` reasoning + the four `rejected_at_execution` reasoning fields ("all hard rules clear", "stop at...", "4 shares 15% cap") |
| Execution died on machine cause, not judgment | `rejected_at_execution.execution_result.error`: `require_stop_loss ... no stop` / `ticker, side, qty ... required` / `trading_hours_only` |
| Prompt mandates bracket + exact field names | kvk `_recurrences.yaml` signal-evaluation Step 4: "always emit the bracket form... names MUST match its schema exactly" → `stop_loss_stop_price` |
| Executor field names | `platform_tools.py:2116` submit_order reads `stop_price`; `:2214` submit_bracket reads `stop_loss_stop_price`/`take_profit_limit_price` |
| propose_action stores verbatim (no remap) | `propose_action.py:221` stores `(primitive, inputs)`; ADR-307 D4 deleted ACTION_DISPATCH_MAP |
| Capability run: machine fires, judgment runs | session `2026-06-19-024212-alpha-trader-autonomous-loop-session`: 4/4 evals fired, 13 wakes (4 judgment), $1.02; eval-1 emitted a real proposal |
| Floor is NOT the blocker | every `rejected_at_execution` cause is timing OR malformed-order, none is "the rule was too strict for a well-formed order" |
