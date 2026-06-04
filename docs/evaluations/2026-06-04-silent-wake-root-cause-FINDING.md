# Finding — The silent-wake root cause: manual_fire recurrence wakes were tagged trigger=addressed and silently failed validation

**Date**: 2026-06-04
**Hat**: B (external developer — the finding) → A (the fix landed in system code, same session)
**Status**: Root cause found + fixed. Regression gate `api/test_silent_wake_trigger_fix.py` 7/7. This finding closes the recurring "the agent never starts trading / silently produces nothing" failure that recurred across every prior alpha-trader autonomy run.

---

## The recurring failure this explains

Across multiple separate e2e/eval sessions over weeks, the operator tried to "get the Reviewer to make trades, watch it, judge, improve recursively over multi-day" — and each time it failed to *start trading*. Each session fixed a different proximate cause (prompt size 33K→3K, risk-gate schema drift, round-budget exhaustion, principles/mandate mis-writes) and still failed. The prior audits named the deepest open ambiguity precisely (`2026-05-25-053951-reviewer-behavior-population-audit`: "0 action_proposals across 4 days × 3 personas; cannot distinguish by-design selectivity from silent stand-down"; `2026-05-26-145500-silent-wake-hypothesis-verification`: 11 reproducing silent wakes, text-only-fallback confirmed) but the *root cause* was never isolated — the recommended fix was reverted as "a workaround for an under-specified problem."

This finding isolates it.

## The root cause (substrate receipt)

The 2026-06-04 trader-suite run fired `outcome-reconciliation` (a `mode: judgment` recurrence) via the eval's `{fire: <slug>}` path, which routes through `manual_fire`. Two wakes resulted, both `status=success` with `tool_rounds=None / output_tokens=None / model=None` and **zero substrate writes** — the silent-wake signature. The deployed scheduler logs (`crn-d604uqili9vc73ankvag`, 2026-06-04T07:08:54Z) carry the exact error:

> `ERROR:agents.reviewer_agent:[REVIEWER] context shape violation user=2abf3f96 trigger=addressed: addressed trigger requires non-empty user_message. Got context keys: [..., recurrence_prompt, recurrence_slug, ...]`

immediately followed by:

> `INFO:services.telemetry:[TELEMETRY] judgment/outcome-reconciliation success`

**The mechanism, exactly:**
1. `_invoke_recurrence_wake` (wake.py) handles BOTH `cron_tick` and `manual_fire` recurrence fires. It derived `trigger = "addressed" if wake_source == "manual_fire" else "reactive"`.
2. It builds the **recurrence-fire context shape** (`recurrence_prompt` + `recurrence_slug`, NO `user_message`) for both.
3. For a `manual_fire`, it therefore called `invoke_reviewer(trigger="addressed", context=<recurrence-fire bag>)` — a **contradiction**.
4. `invoke_reviewer`'s `_validate_context_shape` correctly rejected it ("addressed requires non-empty user_message") → returned `None` before any LLM call.
5. The dispatcher recorded `status="success"` anyway (it only treated *raised* exceptions as failures; a `None` return slipped through with NULL tokens).

So a `manual_fire` of a judgment recurrence **structurally could not run the Reviewer** — the validation rejected the trigger/context mismatch on every fire. A `cron_tick` of the same recurrence mapped to `trigger="reactive"` (which matches the recurrence-fire context) and worked. **Every eval that fired a recurrence via manual_fire saw the Reviewer "never run" — not because of selectivity, not because of the model, but because the caller passed a contradictory (trigger, context) pair.**

## Why it masked itself for weeks

Three explanations for "judgment wake produced nothing" were indistinguishable from substrate alone:
1. Correct selectivity (no signal → correct stand-down) — what canon wants.
2. The silent-wake bug (validation rejected the wake; LLM never ran) — the real defect.
3. The eval expecting a trade that shouldn't happen — a criterion mismatch.

Because the dispatcher recorded the bug (#2) as `status=success`, it was **invisible** — it looked identical to #1. Each prior session, reasoning from `success`-labelled telemetry, concluded the Reviewer was being selective or the criterion was wrong, fixed something adjacent, and the bug persisted. The 2026-06-04 run only caught it because (a) the harness's `fire`-as-turn handler was newly added (so manual_fire judgment recurrences fired at all in an eval), and (b) the deployed logs were read directly, surfacing the `context shape violation` line the `success` telemetry hid.

## The fix (two layers)

**Layer 1 — root cause (wake.py `_invoke_recurrence_wake`):** a recurrence fire is `reactive` regardless of manual-vs-cron. `trigger = "reactive"` (was the broken conditional). The manual/cron distinction is carried by the `wake_source` field on the context (which the Reviewer perceives), not the trigger axis. Genuine operator chat turns are `addressed` and never reach this function (they go through the feed/stream_addressed path with a real `user_message`).

**Layer 2 — defense-in-depth (wake.py dispatcher + reviewer_agent.py):** the dispatcher now records a `None` return from `invoke_reviewer` as `status="failed", error_reason="reviewer_returned_none"` (+ a material narrative entry), not `success`. And `invoke_reviewer`'s swallow-to-None path logs the **full traceback** (`logger.exception`) instead of a one-line opaque error. Any future silent failure — from any cause — is now VISIBLE as a failed row with a captured cause, not a `success` with NULL tokens.

## Implication for the eval approach (ADR-318 amendment)

ADR-318 claimed `manual_fire` of a recurrence is "identical context shape to a real cron_tick" and a "faithful proxy" for the autonomous-wake path. That claim was **half-true before this fix and fully-true after it**: the *context shape* was always identical, but the *derived trigger* differed (addressed vs reactive), and only reactive matched the context — so pre-fix, manual_fire was NOT a faithful proxy (it always failed validation). Post-fix, manual_fire and cron_tick derive the same `reactive` trigger with the same context — so the eval's `{fire: <slug>}` path is now a genuine proxy for the autonomous cron-fired recurrence wake. **This fix is what makes the trader eval-suite able to test the autonomous-wake path at all.**

## Receipts

- Deployed error: `crn-d604uqili9vc73ankvag` logs @ 2026-06-04T07:08:54Z + 07:08:57Z — `context shape violation ... trigger=addressed ... recurrence_prompt, recurrence_slug`.
- Silent telemetry: `execution_events` rows for `outcome-reconciliation` @ 07:08:54 / 07:08:57 — `status=success, funnel_decision=escalate, envelope_load_ms=711/624, duration_ms=886/756, output_tokens=NULL, model=NULL`. Envelope load was 711ms of an 886ms wake — the LLM never ran.
- The fix: `api/services/wake.py` (`_invoke_recurrence_wake` trigger derivation + dispatcher None-handling), `api/agents/reviewer_agent.py` (traceback capture).
- Gate: `api/test_silent_wake_trigger_fix.py` 7/7; reviewer suite 33/33 + ADR-317 18/18 no regression.

## What this unblocks

The corrected eval one-liner (cycle-closure precondition) can now be honestly canonized — because a recurrence wake that escalates now either runs the Reviewer to a closed cycle OR records a visible failure. "No proposal" can finally be distinguished: correct stand-down (verdict/standing_intent written) vs. silent failure (status=failed). The next trader run will, for the first time, observe the reconciliation judgment actually run.
