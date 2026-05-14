# ADR-275 Refinement Empirical Observation — Run 2 (kvk)

**Date**: 2026-05-14
**Workspace**: kvk (`2abf3f96-118b-4987-9d95-40f2d9be9a18`)
**Program**: alpha-trader
**Commit under test**: `af123ca` (ADR-275 refinement — `_preferences.yaml` + AUTONOMY pre-loaded into Reviewer wake envelope)
**Companion runs**: ADR-275 run-1 at `0cf84ae` ([docs/alpha/observations/2026-05-14-adr275-introspection-cadence-e2e-kvk.md](2026-05-14-adr275-introspection-cadence-e2e-kvk.md))

## Test setup (identical to run-1)

1. Render API + Scheduler live on `af123ca` at 09:51 UTC
2. Purged kvk via `/api/account/reset` at 09:57 UTC — full L4 (re-fork picked up thinned bundle + `_preferences.yaml`)
3. Reconnected Alpaca paper (account EE8K)
4. Balance topped to $20.00
5. Sent **identical operator-says-hi addressed turn** at 10:35 UTC:
   > "hi — what is the state of the operation right now and what should we be doing?"

## What the Reviewer did (empirical)

**23 tool calls in ~53s total elapsed.** Critical sequence:

```
ListFiles (×4)
GetSystemState
ReadFile (×9 — IDENTITY/MANDATE/principles/_universe/etc.)
Schedule(action="create", slug="pre-market-brief", ...)        ← ★★★
Schedule(action="create", slug="weekly-performance-review", ...) ← ★★★
Schedule(action="create", slug="quarterly-signal-audit", ...)    ← ★★★
FireInvocation(slug="signal-evaluation")                          ← ★★
WriteFile(path="/workspace/review/decisions.md")
ListFiles (post-fire check)
```

**Three `Schedule` calls. One `FireInvocation`. One `WriteFile`.** The Reviewer authored cadence for all 3 active operator preferences in `_preferences.yaml`, then proactively fired `signal-evaluation` to bootstrap signal state before standing down.

## Verdict produced (verbatim)

> "I've authored the three operator-preference recurrences (pre-market-brief, weekly-performance-review, quarterly-signal-audit) and fired signal-evaluation to bootstrap signal state. The signal-evaluation completed but did not populate `/workspace/context/trading/signals/` — either the recurrence's output logic is incomplete in this bundle version, or signal state is being written to a different path than expected. I'm standing down pending the next automated signal-evaluation fire at `@market_open + 15min`, which will produce fresh trigger state. Once signal substrate exists, I can assess entry conditions against the operator's declared rules and propose trades where conditions match."

This verdict is structurally complete: (i) named what it did, (ii) named what it observed (signal-evaluation incomplete behavior), (iii) named the next scheduled trigger, (iv) named the conditions under which it will propose. No "asking the operator what to do" — exactly the inverse of run-1's "stand down with no Schedule authoring."

## Empirical revision chain on `/workspace/_recurrences.yaml`

```
2026-05-14T10:35:44  reviewer:ai:reviewer-sonnet-v8  created recurrence quarterly-signal-audit (mode=judgment)
2026-05-14T10:35:43  reviewer:ai:reviewer-sonnet-v8  created recurrence weekly-performance-review (mode=judgment)
2026-05-14T10:35:43  reviewer:ai:reviewer-sonnet-v8  created recurrence pre-market-brief (mode=judgment)
2026-05-14T09:57:02  system:bundle-fork              forked _recurrences.yaml (initial scaffold)
```

Three Reviewer-authored revisions in a 1-second burst, all attributed `reviewer:ai:reviewer-sonnet-v8` per ADR-274 dispatch-layer injection. Audit trail is clean: anyone reading `ListRevisions(path="/workspace/_recurrences.yaml")` sees scaffold → Reviewer-authored cadence chain with full attribution.

## Tasks scheduling-index materialization

| slug | schedule | next_run_at | status |
|---|---|---|---|
| pre-market-brief | `@market_open - 30min` | `2026-05-14T13:00:00+00:00` | active |
| weekly-performance-review | `0 18 * * 0` | `2026-05-17T18:00:00+00:00` (Sunday) | active |
| quarterly-signal-audit | `0 18 31 3,6,9,12 *` | `2026-12-31T18:00:00+00:00` | active |

All 3 materialized in the thin `tasks` index correctly. The semantic schedule `@market_open - 30min` resolved to today's 13:00 UTC (pre-market is in ~2h). Workspace now has 11 recurrences (8 bundle-scaffold + 3 Reviewer-authored).

## ADR-275 refinement validation matrix

| Behavioral commitment | Run 1 (prose-named) | Run 2 (pre-loaded) |
|---|---|---|
| Reviewer reads operator preferences | ❌ no `ReadFile` on `_preferences.yaml` | ✅ Pre-loaded in envelope, no read needed |
| Reviewer authors Schedule for active preferences | ❌ zero `Schedule` calls | ✅ **3 calls, all 3 active prefs honored** |
| Revision attribution correct | n/a | ✅ `reviewer:ai:reviewer-sonnet-v8` on all 3 |
| Tasks scheduling-index materializes | n/a | ✅ all 3 active with correct `next_run_at` |
| Reviewer takes additional appropriate action | partial (stood down) | ✅ FireInvocation(signal-evaluation) |
| Verdict references the cadence-authoring behavior | ❌ "stand down until market open" | ✅ "I've authored the three operator-preference recurrences" |

## **Derived Principle 18 lands operationally**

The empirical signal we wanted: `authored_by` revisions on `_recurrences.yaml` attributed to the Reviewer's model identity. We got 3 of them, in 1 second, on the first wake.

The structural change that made this work: **moving `_preferences.yaml` from prose-named ("remember to ReadFile X") to envelope-pre-loaded (delivered alongside MANDATE/AUTONOMY/IDENTITY).** The persona frame text changed from ~50 lines of narrative instruction to ~10 lines of structural contract, and the Reviewer's behavior shifted from "stand down" to "execute cadence-authoring obligation."

**Operator pushback validated**: my run-1 recommendation ("sharpen the persona frame for cold-start") was the wrong shape. The correct fix was structural delivery (envelope pre-load), not narrative bloat (prose nudging). The same architectural pattern ADR-274 used for Operating Context block was the right pattern for `_preferences.yaml`.

## Side observations

**(a) `decisions.md` final state empty.** The Reviewer's `WriteFile` to `decisions.md` succeeded, then a downstream `yarnnn:chat` revision (timestamp 1ms later) overwrote it with empty content (blob `e3b0c4...` = sha256 of empty string). The Reviewer's actual decision content survives in the earlier revision (`reviewer:ai:reviewer` authored_by, blob `3c65d65...`) but is no longer the head. This is a **pre-existing race condition between Reviewer substrate writes and post-loop narrative finalization** — not caused by ADR-275, but worth flagging for a separate audit. The empirical evidence of Reviewer behavior survives in `workspace_file_versions` (revision chain) regardless of head state.

**(b) `signal-evaluation` FireInvocation completed but didn't populate `signals/`.** The Reviewer correctly noted this in its verdict: "the recurrence's output logic is incomplete in this bundle version, or signal state is being written to a different path." This is a known bundle gap unrelated to ADR-275 — the signal-evaluation recurrence's prompt instructs WriteFile to `/workspace/context/trading/signals/{signal_id}.yaml`, but the deterministic signal evaluator path may have different write semantics. Worth a follow-on audit but doesn't affect ADR-275 validation.

**(c) Schedule + tasks-index sync is immediate.** All 3 Reviewer-authored recurrences appeared in the `tasks` thin scheduling index within the same loop turn, with correct `next_run_at` calculations including semantic-schedule resolution (`@market_open - 30min` → today's 13:00 UTC). The Authored-Substrate → scheduling-index materialization path is reliable end-to-end.

## Conclusions

1. **ADR-275 refinement (commit `af123ca`) closes the structural gap that run-1 exposed.** Derived Principle 18 lands both structurally (the primitives exist) and operationally (the Reviewer actually uses them on its first wake).

2. **The Singular Implementation discipline held**: AUTONOMY.md pre-load gap was found during the refinement audit and fixed in the same commit, not deferred. One canonical pre-load contract for the addressed-trigger envelope.

3. **The remaining structural gap is the reactive-trigger envelope** (documented in ADR-275 §5b as ADR-276 candidate). `services/invocation_dispatcher.py` currently passes only `recurrence_prompt + recurrence_slug + capabilities + options + operating_context_block` to the Reviewer — MANDATE / IDENTITY / principles / AUTONOMY / `_preferences.yaml` are NOT pre-loaded on reactive wakes (cron fires + proposal arrivals). The Reviewer's reactive wake reasons from the recurrence's own prompt + Operating Context, relying on tool calls for governance substrate. Worth its own follow-on.

4. **Verbose prompt sections rarely fix what they appear to fix**: my run-1 recommendation was to make the persona frame's first-wake-bootstrap explicit through prose; the correct fix was structural pre-loading. This is a generalizable lesson — when "the Reviewer didn't do X" surfaces, the question to ask is "did X arrive in its envelope or is it in prose hoping to be remembered." Prose-named files are side-quests; envelope-loaded substrate is load-bearing.

## Token economics (run-2)

- 23 tool calls × 1 Sonnet round each, plus the verdict-emitting round
- ~53s wall time
- The 4 fewer ReadFile calls vs. run-1 (because AUTONOMY + `_preferences.yaml` arrived pre-loaded) save ~$0.001/wake — small per-wake savings but compounds over the workspace's lifetime
- Three `Schedule` writes + one `FireInvocation` are one-time costs amortized across the workspace lifetime

## Status

ADR-275 (introspection cadence as Reviewer-authored, not bundle-scaffolded): **Empirically validated.** Closed.
ADR-275 refinement (envelope pre-load): **Empirically validated.** Closed.
ADR-274 (FOUNDATIONS v8.5 Axiom 4 + Derived Principle 18): **Behaviorally exercised in production.**

Follow-on ADR-276 candidate (reactive-trigger envelope governance pre-load) deferred to a separate session.
