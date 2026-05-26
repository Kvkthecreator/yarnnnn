# Findings — warm-start-auto-execute (kvk, 2026-05-20)

*Draft authored by Claude; operator-signed-off 2026-05-20 per ADR-294 D7.*

## Headline

**The Reviewer reached approve-aligned reasoning but never returned the verdict because the 3-round Sonnet budget expired mid-write.** A *fully warmed* workspace — seeded `_money_truth.md` + active mechanical mirrors + populated per-ticker substrate — produced the same outcome as the cold-start Test A: proposal stayed `pending`. This is **structural validation that the cold-start defer hypothesis from 2026-05-20 Test A was incomplete**. Substrate warmth is *not* the bottleneck; the Sonnet round budget is.

## The smoking-gun transcript

Read `transcript.md` carefully — the Reviewer's second turn (proposal-trigger, Sonnet, 3-round budget) walks **the entire six-hard-rule check + autonomy gate + EV check** and explicitly concludes:

> "**All hard rules pass. Sizing math verified. Regime scalar correctly applied. Signal conditions met. EV positive.** One note: sample size is 18, just below the 20-occurrence steady-state threshold — bootstrap clause applies; conditions are unambiguous, propose with the sample note."

Then:

> "Now I'll write my standing_intent.md and return the verdict."

…and the round budget cut it off. The `[REVIEWER] no ReturnVerdict after 3 rounds` log line and the `decided by ai:reviewer-sonnet-v8 (confidence: low)` defer fallback are the *infrastructure failsafe firing*, not the Reviewer's judgment. **The actual judgment was an approve.**

## What this validates

**1. operator-proxy + scenario + capture pipeline works end-to-end.** 10 new revisions captured with correct attribution (`operator-proxy:scenario-runner:acting-as-kvk` on the seed write; `reviewer:ai:reviewer-sonnet-v8` on the Reviewer's own writes; `system:track-*` on mechanical mirrors). 5 new session_messages. 1 new proposal. All 8 capture artifacts produced. ADR-294 Phase 1 stack lands correctly.

**2. operator-proxy attribution is honest and interpretable.** The revision chain reads cleanly:
- `operator-proxy:scenario-runner:acting-as-kvk` — explicitly NOT pretending to be the human operator
- `reviewer:ai:reviewer-sonnet-v8` — Reviewer's own writes still attributed to itself
- The audit trail tells you who *really* did what

**3. The Reviewer correctly reads warmed substrate.** Its reasoning explicitly cites the seeded `_money_truth.md` data (`+0.31R expectancy`, `+0.68 Sharpe`, `sample size 18`), the regime YAML (`vix_regime_active=false, scalar=1.0`), and the per-ticker NVDA.yaml. Substrate-warming worked exactly as designed.

**4. ADR-293 D4 + D5 (uniform gate, single decision surface) is structurally sound at the reasoning level.** The Reviewer's autonomy-gate walk reads:
> "Order notional: 4 × $847.50 = $3,390 = 339,000 cents < ceiling_cents 5,000,000: within auto-execute ceiling. PASS. Action type `trading.submit_order` is NOT in `never_auto` list. PASS."

Had the verdict landed, the gate would have approved auto-execute.

## What this exposes (the real finding)

**Sonnet 3-round budget for capital-review is structurally tight.** The Reviewer's verdict path on a real proposal requires:
1. Read governance envelope (consumes round 1 — pre-load helps per ADR-276 but the Reviewer still issues some reads)
2. Read per-ticker substrate + signal state + regime + portfolio + standing_intent (round 2)
3. Walk the framework checks + write standing_intent.md + ReturnVerdict (round 3 — runs out *during the write-standing-intent step*, before `ReturnVerdict` fires)

This is a **real architectural pressure point on ADR-260 + ADR-256** (Real-Time Reviewer Loop + Unified Reviewer Invocation). Three candidate responses:

- **A — Tighten the Sonnet prompt** to discourage writing standing_intent.md *before* ReturnVerdict on capital-review wakes. Cheap, behavioral, no infrastructure change.
- **B — Bump Sonnet budget to 4** for proposal-trigger wakes only. ~33% more cost per fire; predictable.
- **C — Split the work** into a two-cycle pattern where wake 1 reads + writes a "pending evaluation" entry, wake 2 (reactive a few seconds later) renders the verdict against fully-cached context. Conceptually clean, structurally complex.

**Lean: option A.** The Reviewer is currently behaving as if standing_intent updates gatekeep the verdict; they don't. Standing intent can be written after verdict (or asynchronously). If we shift the order via prompt discipline, we recover ~30% of the round budget without bumping cost or splitting the architecture.

## What this does NOT validate

The auto-execute branch (`should_auto_apply("capital")` → `handle_execute_proposal` → Alpaca submit) was *not* exercised — no verdict landed. ADR-293 unit-test gate covers this deterministically, but on a live persona we still haven't watched the Reviewer ship a paper trade.

## Follow-on actions

1. **Open a discourse on the 3-round budget pressure.** This is the third time it's bitten capital-review (Test A v1, v2, now warm-start). Worth deciding the response before more validation runs — option A first (prompt fix), then re-run.
2. **Re-run warm-start-auto-execute after the prompt/budget change** to see if approve lands. The scenario file is the regression artifact; running it again is one command.
3. **No fixes needed to ADR-294 Phase 1 machinery.** Capture pattern is healthy; the failure mode is upstream of the proxy.

## What surprised me

The Reviewer's transcript reads like a careful checklist walkthrough — every hard rule cited, math verified, autonomy gate computed correctly. **The reasoning is not sloppy.** The system isn't failing because the Reviewer is bad at the job; it's failing because the round budget assumes a tighter execution sequence than the Reviewer's prompt currently produces. The fix is most likely a prompt edit, not an architectural change.
