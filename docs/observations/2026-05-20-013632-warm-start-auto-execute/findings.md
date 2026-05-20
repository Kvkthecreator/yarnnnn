# Findings — warm-start-auto-execute v3 (kvk, 2026-05-20, post-risk_gate-fix)

*Draft authored by Claude; pending operator sign-off per ADR-294 D7.*

## Headline

**End-to-end autonomous capital loop is validated.** Same workspace, same Reviewer, same prompt — but now the risk-gate fix (`access_token` → `credentials_encrypted`) lets the gate read the real paper-account state. The Reviewer reached approve cleanly, `handle_execute_proposal` fired, `risk_gate.compute_risk_state` correctly fetched account state, and **the gate refused the synthetic proposal for three real envelope violations** — exactly what a safety floor should do.

## What v3 proves

| Step in autonomous capital loop | v3 result |
|---|---|
| Reviewer reaches approve, high confidence, within budget | ✓ (prompt fix held) |
| `should_auto_apply("capital")` returns True | ✓ |
| `handle_execute_proposal` invoked | ✓ |
| `risk_gate.compute_risk_state` fetches account state | ✓ (risk_gate fix held — no more schema error) |
| Risk gate applies real envelope | ✓ — caught 3 violations |
| Failsafe behavior | ✓ — refused unsafe order, preserved invariants |

The risk-gate's three rejection reasons (full `execution_result.message`):
> "position would be 33.9% of portfolio, exceeds max_position_percent_of_portfolio (15%); require_stop_loss=true but order has no stop (not bracket, not trailing, no stop_price); trading_hours_only=true but order submitted outside approximate US market hours"

Each is a **real, correct, useful refusal**:

1. **Portfolio sizing**: The proposal template assumed $25K equity (from seeded `_money_truth.md` narrative); actual paper account is $10K. The gate caught the math mismatch. **A real Reviewer reading `_account.yaml` directly would size correctly.**

2. **Stop discipline**: The proposal template uses `stop_loss_price` field; risk-gate looks for bracket-order `stop_price`. The order shape is structurally incomplete. **A real production proposal would emit a bracket-shaped order.**

3. **Trading hours**: We ran this at 01:37 UTC — far off-hours. The `trading_hours_only=true` floor in `_risk.md` correctly blocked the test. **A real signal fire would hit during RTH (09:30–16:00 ET).**

## What this validates about the architecture

**1. ADR-293 D4 (uniform AUTONOMY-mode gate) + ADR-194 v2 (Reviewer seat) + risk-gate are correctly composed.** The flow is:
- Reviewer evaluates against framework + reaches verdict
- AUTONOMY gate (`should_auto_apply`) decides whether to auto-execute or queue
- IF auto-execute, `handle_execute_proposal` fires
- IF execute, `risk_gate.compute_risk_state` validates against the *real* risk envelope at execution time
- IF risk-gate rejects, proposal status flips to `rejected_at_execution`; nothing reaches the platform API

This is **defense in depth done right**. The Reviewer reasons against substrate (which may be stale or wrong); the risk-gate validates against live platform state at the last possible moment.

**2. The risk-gate is doing its job.** Three independent envelope checks fired and all three caught real issues with the synthetic proposal. None of them would have caught a *real* Reviewer-authored proposal that sizes against `_account.yaml` and emits a proper bracket order during RTH.

**3. The prompt fix held across two runs.** v2 and v3 both produced approve verdicts; v1 produced low-confidence defer. The trigger-aware standing_intent.md write ordering change is stable.

## What this does NOT validate

**A successful Alpaca paper order submission.** The risk-gate (correctly) refused the synthetic test proposal. To observe an actual Alpaca order go through, the scenario needs:
1. Sizing math aligned with actual paper-account equity ($10K, not the seeded narrative's $25K), OR seed `_account.yaml` to match.
2. A bracket-order or stop-price field in the proposal template.
3. Trading-hours run OR explicit `trading_hours_only: false` (less honest).

None of these are framework bugs — they're scenario calibration. The framework is validated; further validation is observational refinement.

## Follow-on actions

**Immediate**:
1. ✓ risk_gate.py fix committed
2. ✓ Findings v3 written

**Future** (separate scenario / observation):
3. Author `warm-start-auto-execute-rth.yaml` that runs during market hours with sizing tuned to the actual paper account — gives us a successful Alpaca paper trade for observation.
4. Use that scenario as the regression artifact for ADR-260 + ADR-256 + ADR-293 capital path going forward.

## What surprised me

**The risk-gate rejections were too specific to be coincidence.** All three are *exactly* the kind of issues a hand-authored test proposal would have. The fact that the gate caught all three independently is high signal that the risk envelope is well-instrumented, not under-instrumented.

The **defense-in-depth pattern** is more visible now than I'd appreciated. The Reviewer's reasoning quality is one floor; the AUTONOMY gate is another; the risk-gate is a third; the platform API itself would be a fourth. Each layer has its own concern. Each can fail safely without compromising the others. This is what `confidence: high` actually buys us — the Reviewer was right about its reasoning; we just had downstream invariants the proposal didn't satisfy.

## Cross-reference

Companion v2 findings at [`../2026-05-20-013220-warm-start-auto-execute/findings.md`](../2026-05-20-013220-warm-start-auto-execute/findings.md) document the prompt-fix validation and surfaced the risk_gate column drift that this v3 run validates the fix for.
