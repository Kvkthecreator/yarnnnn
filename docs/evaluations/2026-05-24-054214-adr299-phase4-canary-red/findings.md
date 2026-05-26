# ADR-299 Phase 4 canary — RED outcome surfaces two issues

**Hat**: External Developer of the System (Hat B).

**Captured**: 2026-05-24T05:42Z.

**Trigger**: Phase 4 validation canary (operator-proxy substrate-write to flip `pre_ship_audit_summary` `active: true` + substrate-event canary on `governance-as-trust profile.md` to fire `pre-ship-audit` hook) — fired at 05:38:13 UTC, wake completed at 05:39:11 UTC, **email did NOT land in operator inbox**.

**Predecessor**: [`docs/evaluations/2026-05-24-050631-adr299-wire-redundancy/`](../2026-05-24-050631-adr299-wire-redundancy/) — Path X correction that rewired `platform_email_send_to_operator` to system Resend wire. This Phase 4 was the validation observation for that correction.

## Headline

**Phase 4 canary did NOT close clean.** The wake architecture worked end-to-end at the L1-L8 layers (queue, dispatch, LLM cycle, telemetry, completion all green) but the **two load-bearing behaviors at the substrate + delivery layers BOTH failed**:

1. **Reviewer produced ZERO substrate writes** despite a full 43-second LLM cycle ($0.26, 43K input tokens, success status). Persona-frame mandates `standing_intent.md` write every cycle — none happened.
2. **Email did NOT fire** — zero rows in `notifications` table; broader history shows ZERO successful email sends across all users in last 90 days.

Both are real issues worth follow-up. Phase 4 surfaced them; doesn't fix them.

## What I expected vs what I observed

| Layer | Expected | Observed | Verdict |
|---|---|---|---|
| L1 Walker dedup | Hook walker matches transition → wake_queue enqueue | wake_queue row `c90af350` enqueued @ 05:38:28Z | ✅ |
| L2 Drainer lock | Atomic pending → locked CAS | locked @ 05:38:28.215Z | ✅ |
| L3 Reviewer dispatch | `_invoke_substrate_event_wake` invoked with hook envelope | execution_events row `c4f250f2` created | ✅ |
| L4 LLM cycle | Reviewer reads envelope + emits substrate writes + ReturnVerdict | 43s success, 43K input / 3K output tokens, $0.26 cost | ⚠️ ran cleanly but produced nothing? |
| L5 Substrate writes | At minimum `standing_intent.md` per persona-frame contract; optionally `judgment_log.md` for material outcome | **ZERO Reviewer writes** | 🔴 RED |
| L6 Email fire | If `_preferences.yaml::operator_notifications.pre_ship_audit_summary.active: true` + cycle produced material → call `platform_email_send_to_operator` | **ZERO notifications** rows; no email landed | 🔴 RED |
| L7 mark_completed | Queue row terminal | completed @ 05:39:11.450Z | ✅ |
| L8 Telemetry pairing | execution_events paired with wake | paired cleanly | ✅ |

Layers 1, 2, 3, 7, 8 GREEN. L4 ran but L5 + L6 both RED. Wake architecture functioning; behavior on top of it failing.

## Preconditions confirmed satisfied

Verified before drawing conclusions about the Reviewer's behavior:

- ✅ Deploy: `fa733f8` live on both API + Scheduler since 05:32 UTC (the wire correction was deployed before the canary fired at 05:38 UTC)
- ✅ Substrate: live `_preferences.yaml` HAS `operator_notifications:` block with `pre_ship_audit_summary active: true` (verified post-write at 05:39 UTC; my operator-proxy write at 05:38:12 succeeded with revision_id `f02d7c7b`)
- ✅ Canary substrate-event: `governance-as-trust profile.md` status flipped through `ready_for_review → draft → ready_for_review` at 05:38:13 (revision `fb07844c` is the transition the hook walker fires on; matched correctly per the wake_queue row's dedup_key = revision_id)
- ✅ Reviewer engaged: 43K input tokens / 3K output tokens = real LLM call, not fail-open or balance-exhausted skip
- ✅ Adjacent kernel-mirror plumbing alive: `system:mirror-recent-execution` wrote `/workspace/memory/_recent_execution.md` at 05:39:13 (one minute after wake completion), confirming ADR-301 kernel maintenance is firing on the same Scheduler

## Finding 1 — Reviewer produced zero substrate writes (regression against persona-frame contract)

The persona-frame at `api/agents/reviewer_agent.py:_PERSONA_FRAME` explicitly mandates standing_intent.md writes on every cycle:

> *"Reactive recurrence fires + addressed turns + heartbeats: every cycle produces a standing_intent.md write. The substrate counterpart to a no-fire judgment is an updated standing intent. 'No action' without an updated standing intent is not a real judgment, it's drift."*

This canary was a substrate-event reactive wake on `pre-ship-audit`. The Reviewer should have, at minimum, written `standing_intent.md`. It did not. Zero `reviewer:ai:reviewer-sonnet-*` writes in the 05:38-05:42 window.

**Three possible failure modes** (cannot distinguish without LLM trace logs from Render — workspace selection required):

1. **Text-only-fallback** (L4-F2 caveat from 2026-05-22 L6 findings) — the model produced a text-only response instead of calling `ReturnVerdict` + `WriteFile`. Cycle bails to inert stand_down with no substrate write. The morning L6 audit explicitly flagged this branch as the dominant exit pattern post-Option-D (commit `e8017d3`). If true, the new operator_notifications + ADR-301 + MANDATE-citation prose additions may have compounded the cycle complexity past the bandwidth of structural tool-call discipline.

2. **Cycle attempted `platform_email_send_to_operator` but the wire returned error** (see Finding 2 below); Reviewer may have decided the cycle was already failed and bailed without writing substrate.

3. **Reviewer attempted writes but they silently failed** somewhere in the write_revision path (unlikely; revision chain is robust, but possible).

The 43K input token count suggests #1 or #2 — the model engaged with a full envelope. The 3K output tokens is moderate, consistent with composing prose responses that may not have wrapped tool calls correctly.

**Recommendation**: this is a Hat-A investigation in its own right, NOT directly an ADR-299 concern. The canary surfaced it because the canary involved an active cycle that should have produced writes. Suggest follow-up observation that captures the Reviewer's prompt trace + response trace from Render logs (operator-side action: workspace selection in Render MCP) — that data settles which of the three failure modes is at play.

## Finding 2 — System Resend wire empirically unproven

The Path X correction (commit `f1f77e6`, ADR-299 Discovery note 2) rewired `platform_email_send_to_operator` to the system Resend wire at `api/jobs/email.py::send_email`. The wire reads `RESEND_API_KEY` env var on Render.

**DB evidence**: `notifications` table query across all users for last 90 days shows:
```
 total | sent | failed | last_sent | last_err
-------+------+--------+-----------+----------
     0 |    0 |      0 |           |
```

**Zero successful email sends in production history.** The `notifications` table has only two `in_app` rows from 2026-03-20 (over 2 months ago); zero `channel='email'` rows ever.

This means either:
- `RESEND_API_KEY` is not configured on the deployed services (or set to an invalid value)
- Or it IS configured, but the existing operator-addressing wire (`notifications.py` + `daily_update_email.py`) is never being invoked in conditions that would trigger it
- Or the wire fails silently before reaching the `notifications` table write

Either way, the Path X correction wrapped a wire whose operational viability was never validated. ADR-040 + ADR-202 named the wire's existence; my correction's verification was that the code path existed + the env-var reference was present in source. I did not check whether the wire had ever empirically delivered a message — that's the missing pre-flight check.

**This is a recursive discipline lesson** stacking on the morning's two:
- Discovery note 1 (yesterday): correcting class naming requires verifying the existing class accommodates the novelty
- Discovery note 2 (today): correcting class naming requires verifying the wire each class member points at
- **NEW (this finding)**: correcting wire-pointing requires verifying the new wire has empirical evidence of operational viability — not just code-path existence

**Recommendation**: investigate whether `RESEND_API_KEY` is set on Render's deployed services. If yes, dig into why `daily_update_email.py` + `notifications.py` haven't fired (separate from ADR-299 scope but adjacent). If no, decide whether to set it (Path X assumes deployment) OR re-evaluate whether the per-user OAuth wire is actually the correct shape for operator-addressing (re-opening yesterday's question).

This is a real follow-on observation, possibly seed for ADR-299 Discovery note 3 OR an environment-configuration fix that doesn't need ADR amendment if the var is simply missing.

## What's NOT a finding (sanity checks that passed)

- Wake-architecture (ADR-296 v2 + ADR-298) — perfectly green on all 6 plumbing layers
- ADR-301 kernel-mirror plumbing — `system:mirror-recent-execution` fired correctly at 05:39:13
- Substrate-event hook walker (ADR-296 v2 D2) — matched the transition + enqueued + dispatched cleanly
- Operator-proxy substrate writes (ADR-294) — three writes all succeeded with correct attribution
- Singular Implementation of the ADR-299 wire correction — code-path exists, just unproven empirically

## Path 4 status

**The operator-addressing channel does NOT have empirical end-to-end validation as of this observation.** Phase 4 fired but did not close clean. Two real issues surfaced that need follow-up; neither is a wake-architecture bug.

The honest status update for ADR-299:
- Phase 1: Implemented + corrected twice (registry redundancy + wire redundancy)
- Phase 2: Implemented (schema in bundle)
- Phase 3: Implemented (persona-frame nudge)
- Phase 4: **Attempted; surfaced two unrelated red signals; not closed.** Follow-up observations needed for Finding 1 (Reviewer substrate-write regression) + Finding 2 (system Resend wire operational viability).

The line "Phase 4 becomes immediate-testable" from ADR-299 Discovery note 2's optimism was wrong — even with no operator setup ceremony, the end-to-end chain didn't deliver. The architectural shape is correct (path A vs path B was a real distinction); the *practical viability* of path X depends on configuration + Reviewer behavior that weren't verified pre-correction.

## Recommendations

### Recommendation 1 (Hat-A, separate from ADR-299) — Investigate Reviewer zero-substrate-write
- Pull Render Scheduler logs around 2026-05-24T05:38:30Z — workspace `0b7a852d` — slug `pre-ship-audit` — to see the Reviewer's actual prompt + tool-call attempts + the final action that closed the loop
- If text-only fallback: this is the L4-F2 caveat now appearing more frequently; may warrant the tighter prompt-shape work the morning L6 findings deferred
- If tool error: trace the specific error
- If write-path failure: investigate write_revision

This is NOT an ADR-299 follow-up; it's a Reviewer-behavior follow-up that the canary happened to surface.

### Recommendation 2 (Hat-A) — Verify or unblock the system Resend wire
- Check `RESEND_API_KEY` env var status on `srv-d5sqotcr85hc73dpkqdg` (API) + `crn-d604uqili9vc73ankvag` (Scheduler) — operator-side action via Render dashboard (env var values are not readable via MCP)
- If unset: setting it would unblock both ADR-040 notifications + ADR-202 daily-update + ADR-299 operator-addressing path
- If set: investigate why `notifications.py` has never produced a sent row across 90 days. This is a 90-day-old broader issue, not ADR-299 specific

### Recommendation 3 (process) — Pre-flight check for wire correctness shouldn't assume code-path existence proves operational viability
This is the third recursive discipline lesson today. Codify in CLAUDE.md or a future RESOLUTION addendum:

> When correcting an integration's wire-pointing: in addition to verifying the code path exists, verify the wire has empirical evidence of operational viability (recent successful invocations in production DB / logs / artifacts). Code-path existence ≠ operational viability.

The morning's two corrections + tonight's third are all the same shape at different recursion depths. The discipline rule should reflect that.

## Status

**OPEN** — Phase 4 did not close. Two real issues surfaced for follow-up. No code corrections recommended from this finding alone; the corrections depend on the investigation results (Recommendation 1's prompt trace + Recommendation 2's env var verification).

## Cross-references

- ADR-299 (post-Discovery-note-2 shape): [`docs/adr/ADR-299-...md`](../../adr/ADR-299-kernel-universal-operator-addressing-capability.md)
- Predecessor wire-redundancy resolution: [`docs/evaluations/2026-05-24-050631-adr299-wire-redundancy/`](../2026-05-24-050631-adr299-wire-redundancy/) (where the Path X correction was decided)
- Morning L6 findings (L4-F2 text-only-fallback caveat that Finding 1 may be recurring): [`docs/evaluations/2026-05-22-052244-l6-variant-f-clause-validation/findings.md`](../2026-05-22-052244-l6-variant-f-clause-validation/findings.md)
- Phase 4 canary script: `api/scripts/operator/canary_phase4_operator_email.py` (committed in this session's todo flow)
- Canary v4 precedent: [`docs/evaluations/2026-05-21-044500-canary-v4-substrate-event-revalidation/`](../2026-05-21-044500-canary-v4-substrate-event-revalidation/)
- wake_queue row: `c90af350-0dc2-401c-96b5-ae40bc7c3e3a` (substrate_event, live lane, completed)
- execution_events row: `c4f250f2-d26f-4c1b-9013-0c80854319f7` (43s, $0.26, success)
- Substrate writes by canary:
  - `f02d7c7b` — `_preferences.yaml` operator opt-in (operator-proxy)
  - `d37f69f8` — `profile.md` priming flip (operator-proxy)
  - `fb07844c` — `profile.md` canary transition (operator-proxy; dedup_key of the wake)
  - `66814ac0` — `_recent_execution.md` mirror (system:mirror-recent-execution; adjacent ADR-301 kernel plumbing)
- Reviewer substrate writes in canary window: **NONE** (this is the finding)
- notifications.email rows in last 90 days across all users: **0** (this is Finding 2)
