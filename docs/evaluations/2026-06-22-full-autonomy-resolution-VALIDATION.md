# Validation — Full autonomy resolved: the agent originates, approves, and executes a capital action on its own initiative

**Date**: 2026-06-22
**Hat**: B (external developer) — scenario + receipts; the fixes land in Hat-A canon (ADR-354 + bundle + conformance test).
**Workspace**: `alpha-trader` persona (seulkim88, `2be30ac5-b3cf-46b1-aeb8-af39cd351af4`), clean-slate activated, autonomous, Alpaca paper `X4DJ`.
**Pairs with**: the finding `2026-06-22-full-autonomy-probe-trader-never-acts-FINDING.md` (the problem) + the discourse `../analysis/agent-passivity-mandate-vs-rule-literalism-2026-06-22.md` (the first-principles diagnosis). This is the resolution.

---

## The result in one line

On a clean autonomous workspace with the obstructions removed, the agent **evaluated → fired Signal 1 → sized the trade → proposed → approved its own proposal → submitted to the broker**, blocked from the actual fill only by the legitimate `trading_hours_only` hard floor (off-hours). The passivity was never wired-in; it was three removable layers of obstruction.

## What the diagnosis got right (and the operator's reframe)

The operator rejected a "forcing function" and asked: *what in the envelope / our assumptions is preventing the action?* Reading the literal envelope (`reviewer_agent.py::_build_user_message` + the recurrence prompt + the substrate) located **three obstructions, each revealed by removing the prior one**. None required new instruction; every fix was *less* (the ADR-306 collapse principle, extended).

### Obstruction 1 — the recurrence prompt re-scripted the close, competing with the frame
The `signal-evaluation` prompt (4,414 chars) ended with an explicit terminal branch: *"Otherwise, when neither entries nor exits fire: WriteFile standing_intent, THEN ReturnVerdict(stand_down)."* The kernel frame already owns cycle-closing ("close every cycle with a verdict or a standing_intent write") + the standing-obligation (A)/(B) classification. Two layers, the concrete procedural one winning — the exact ADR-306 pathology (contradiction-between-layers-is-a-complexity-smell), never collapsed at the recurrence layer. **Fix**: collapse both judgment recurrence prompts to operator-instruction-only (signal-evaluation 4414→1573, outcome-reconciliation 1538→534); delegate the close to the frame. The prompt's last line now *points at* the question instead of pre-empting it: "a signal that does not fire is a fact to reason about — quiet world, or a rule you cannot even evaluate from your substrate? — not an instruction to stand down."

*Probe after fix 1*: the standing-obligation self-audit surfaced (it now reasoned about its own 0-proposal pattern) — but it fabricated "pre-market → 20d-high unavailable → wait for RTH." → revealed obstruction 2.

### Obstruction 2 — the signal rule referenced fields the perception field never emits
Signal 1's declared trigger named "20-day high" + "current-bar volume > 1.5×" — fields the `track-universe` writer (`_write_ticker_yaml`) **never emits** (schema: `price, sma_20/50/200, rsi_14, atr_14, volume_20d_avg`). So 2 of 4 conditions were *permanently* unverifiable, and the occupant manufactured a plausible *timing* story ("wait for RTH") to explain a *permanent* schema gap — rating it High confidence. The rule and the perception field spoke different vocabularies. **Fix A**: rewrite Signal 1 to key only on emitted fields (`price > sma_20 + price > sma_50 + RSI ∈ [55,75] + volume_20d_avg ≥ liquidity floor`); mark Signals 3 (PEAD) + 4 (sector-RS) DORMANT (their feeds structurally don't exist). **Fix B**: a conformance invariant in `api/test_trading_pipeline_architecture.py` — a non-dormant signal trigger may reference only emitted perception fields; CI rejects an absent-field reference (14/14 pass).

*Probe after fix 2 (run `c9b2ed9e`, 15 rounds, $0.81)*: **the breakthrough** — the agent fired Signal 1 on SPY, computed the bracket order (45 shares, stop 736.33, target 791.51), hit the *real* daily-VaR floor ($375 ceiling, calibrated for a $25k baseline, vs $1,000 risk on the $100k paper account), **held the floor**, and surfaced the structural mismatch to the operator (judgment_log `propose_action` then `clarify`). That is mandate-ownership, not passivity: it acted to the floor and stopped for the right reason, naming the gap rather than lowering the floor.

### Obstruction 3 — stale self-narrative + cross-substrate incoherence
Two sub-findings at the binding moment:
- **Narrative anchoring**: across repeated fires, the occupant echoed a stale value from its own prior `judgment_log`/`standing_intent` prose ("$375 / $25k baseline") *after* `_risk.md` was calibrated to $1,500 — trusting its own prior narrative over current substrate. Cleared by a clean-slate re-activation (zero prior narrative).
- **Cross-substrate integrity** (the strongest positive result): on the first coherent-looking probe the agent **cross-referenced `_regime.yaml` (real `spy_close: 746.74`) against the constructed `SPY.yaml` (`price: 758.4`), caught the disagreement, and refused to bind capital on inconsistent substrate** (proposal `597d2881` → `pending`, judgment_log `defer`). The ADR-209/344 integrity moat operating at the capital-bind moment. Only after the fixture was made fully coherent (`_regime.yaml::spy_close` aligned, rev `faa9f3d0`) did it proceed.

## The terminal run (full autonomy) — receipts

Run `89113f75` (8 rounds, $0.42), fully coherent fixture, autonomous:

| Stage | Result | Receipt |
|---|---|---|
| Evaluate | Signal 1 fires on SPY, 4/4 conditions | `entry_rule_trace`: "price (758.4) > sma_20 (747.08) ✓ > sma_50 (729.66) ✓ \| RSI_14 (64.2) in [55,75] ✓ \| volume_20d_avg (58.7M) ≥ liquidity floor (50M) ✓" |
| Size | within hard caps, regime scalar applied | `sizing_formula_trace`: "risk_pct 1% / stop 2×ATR=22.07 … hard_cap $1000 → 1.32 shares max → proposed 1 share (bootstrap min) \| regime_scalar 1.0" |
| **Propose** | `submit_bracket_order`, unprompted | proposal `fc7ee88e` |
| **Approve** | self-bound, autonomous, no operator gate | judgment_log `approve proposal fc7ee88e` (2026-06-22 02:33) |
| **Execute** | submitted to Alpaca broker path | status `rejected_at_execution` |
| Floor holds | off-hours order correctly rejected | `execution_result.error: "risk_limit_violation" / "trading_hours_only=true but order submitted outside NYSE regular trading hours"` (`risk_gate.py:195`) |

The only thing between the agent's fully-autonomous decision and a literal paper fill is the **clock** — it is 02:33 UTC, NYSE is closed, and `trading_hours_only` (a hard floor) refuses off-hours execution. This is *more* correct than the workspace history that prompted the investigation: kvk's only-ever trade was an off-hours fixture that bypassed this exact floor (ADR-342's original sin); the current system refuses it even when the agent fully decided to act.

## Answer to the original question ("both — and I can't tell them apart")

| Operator's framing | Verdict (with receipts) |
|---|---|
| Never executes the Primary Action | **Falsified.** It originates, approves, and submits a capital action on its own (proposal `fc7ee88e`, autonomous approve, broker submit). |
| Always finds a reason to wait | **Falsified.** The "reasons to wait" were three real obstructions (re-scripted close, rule/perception mismatch, substrate incoherence), not a defer-bias. Removed → it acts. |
| Strengths surfaced | The integrity moat works at the capital-bind moment (caught the constructed-bar inconsistency; refuses off-hours execution). It cannot be *fooled into* a trade and now is not *prevented from* one either. |

## Fixes landed (Hat-A)

1. **ADR-354** — recurrence prompts carry only operator instruction; cycle-closing + the standing obligation belong to the frame (extends ADR-306's collapse to the recurrence layer). + perception-field discipline: a signal rule references only emitted perception fields. Bundle `_recurrences.yaml` (both judgment prompts collapsed) + `_operator_profile.md` (emitted-field rules, S3/S4 DORMANT).
2. **Conformance invariant** — `api/test_trading_pipeline_architecture.py` §5 (14/14): non-dormant signal-rule fields ⊆ emitted perception schema.

## Open / follow-up

- **Literal paper fill**: blocked only by the off-hours floor; will pass during real RTH (13:30 UTC). Scheduled as a follow-up confirmation; not a behavior question.
- **Narrative-anchoring** (the occupant trusting its own prior `judgment_log` prose over current substrate when they conflict): a real, separate finding worth its own discourse — it is the same class as the standing_intent anchoring and the ADR-209 "head-state flip" lesson, but at the *self-authored-narrative* layer. Recommend a dedicated probe + ADR if it reproduces on a non-fixture workspace.

## Reproduce

```
activate_persona.py --persona alpha-trader --clean-slate
manual_fire track-universe + track-regime ; drain          # real bars
# stage (write_revision at /workspace/...): emitted-field _operator_profile.md,
#   _risk.md var calibrated to account, satisfied SPY.yaml, _regime.yaml spy_close aligned
manual_fire signal-evaluation ; drain                       # → propose → approve → execute → off-hours floor
# inspect: action_proposals (fc7ee88e), execution_result, judgment_log
```
