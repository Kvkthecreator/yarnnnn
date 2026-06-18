# Finding — the author Reviewer DERIVED its own aperture/floor split with no hand-authored rules (+ a client-timeout machine-fault caveat, reported straight)

**Date**: 2026-06-18
**Persona / workspace**: yarnnn-author (`0b7a852d-4a67-447d-91d9-2ba1145a60d7`), alpha-author, corpus-internal ground truth, `delegation: autonomous`
**Hat**: B (derive-it probe against the LIVE deployed Reviewer post-ADR-343)
**Criterion**: ADR-343's structural claim — given ONLY the kernel-level aperture/floor *definition* (no hand-authored §Aperture/§Dormancy in its `principles.md`), does a non-trader Reviewer **derive its own split** from its mandate + ground-truth, and act within it?

---

## Headline (honest, two-part)

**Part 1 — the derivation VALIDATED.** The yarnnn-author Reviewer, running the program-neutral ADR-343 frame (deployed `dep-d8po1oh9rddc73fpvm9g`, live 05:25) with **zero aperture/dormancy rules in its `principles.md`** (verified: `has_aperture=f, has_dormancy=f`), derived the writer's split correctly:
- **Floor (held)** = the anti-slop / voice-fingerprint / continuity audit bar. The probe deliberately tested it ("I'm not asking you to lower your bar") and the Reviewer did NOT lower it — it ran the piece "against all six rules… passed clean (zero anti-slop, voice fingerprint solid)" and bound publication only because the floor was *satisfied*, not relaxed.
- **Aperture (the widening lever it surfaced)** = the **production rhythm / scope** — it diagnosed the real gap as *"you haven't declared a content-production cadence in `_preferences.yaml`"* and surfaced a Clarify on composition-sprint-vs-clock-driven cadence.

This is exactly the split ADR-343 predicted for an author (floor = anti-slop/voice + can't-fake-a-ship; aperture = topic/source/format/cadence scope) — **derived live from the mandate + `_signal.md`, with no program-specific dormancy prose.** That is the structural claim demonstrated on the second program.

**Part 2 — a real contamination + machine-fault caveat I will not dress up.** The clean "dormant → close" sequence I intended did NOT happen as designed, because the *first* probe contaminated the *second*:

- The first probe (60s client timeout) fired at 05:27:52. Before the client gave up, the Reviewer's cycle **published `money-truth-remake`** — revision `7ea9dbcb` by `reviewer:ai:reviewer-sonnet-v8` at **05:29:39**, flipping the profile `status: draft → published` (verified: NOT published on any of its three Jun-10 revisions; first `was_published=t` is this row). But the client had already disconnected, so **no `addressed` execution_event was written** — the ledger row was aborted by the timeout (`wake_queue ffc25024` resolved `failed`).
- The second probe (600s timeout, `execution_event 4ac17dad`, success, 9 rounds, 4067 out) then read that just-published piece and correctly concluded *"the operation is not dormant — it moved this morning"* + the cadence gap. Its reasoning is sound **for the substrate it saw** — but that substrate was polluted by my own first probe's side effect, so the second cycle is not a clean read of the *dormant* state.

So: the derivation is real and validated (the floor/aperture split is visible in the second cycle's reasoning regardless of the contamination); the *dormancy-close-from-flat* is NOT cleanly demonstrated on author the way it was on trader, because my own test mutated the state between the two reads.

---

## The machine-fault sub-finding (recommends a Hat-A fix)

**The addressed-wake cycle does consequential substrate writes (here: a publish) before the SSE stream completes, and a client disconnect at the timeout aborts the `execution_events` ledger write while leaving the substrate mutation in place.** Result: a real, attributed `reviewer:ai:*` publish with **no execution_event** — an audit gap (the cost ledger + funnel telemetry never recorded the cycle that did the work). The `wake_queue` row correctly went `failed`, but the substrate write had already landed.

This is a genuine system-side finding (Hat-A target), not a test artifact:
- **Expected**: an addressed cycle either completes atomically (substrate writes + ledger row) or, on disconnect, the ledger still records the cycle that produced the writes (ADR-291 one-cost-ledger says `execution_events` is the sole cost ledger — a cycle that mutated substrate but wrote no ledger row is a hole in it).
- **Observed**: substrate write present (`7ea9dbcb`), ledger row absent, queue row `failed`.
- **Recommended fix** (Hat-A, separate change): the addressed path should write the `execution_events` row from the server side on cycle completion **independent of the SSE connection's liveness** (the stream is a *view*, not the system-of-record) — mirroring how cron_tick/reactive cycles write their ledger row regardless of any listener. The client timeout should never be able to orphan a ledger row behind a real substrate mutation. (This generalizes the ADR-296 silent-wake discipline to the disconnect case.)

---

## Substrate receipts

| Claim | Receipt |
|---|---|
| ADR-343 frame deployed | API `dep-d8po1oh9rddc73fpvm9g` status=live, commit `ec20a39`, 05:25:14Z |
| author principles.md has NO aperture/dormancy rules | live query `has_aperture=f, has_dormancy=f` |
| Real corpus dormancy in ground truth | `_signal.md` 7d/30d/90d all `pieces_shipped: 0`, `cadence_state: behind`, processed-key `…-idle` |
| First probe published a piece (the contamination) | `workspace_file_versions 7ea9dbcb` profile.md `draft→published` by `reviewer:ai:reviewer-sonnet-v8` @ 05:29:39; NOT published on any prior revision |
| First probe wrote NO ledger row (the machine fault) | `wake_queue ffc25024` status=`failed`; no `addressed` execution_event in 05:27–05:30 window |
| Second probe closed clean | `execution_events 4ac17dad` addressed/success, 9 rounds, 4067 out, 06:13Z |
| Derived split (floor held, aperture surfaced) | second cycle text + `standing_intent.md` rev: floor = six-rule voice/anti-slop audit (passed, not lowered); aperture = undeclared production cadence (Clarify surfaced) |

---

## Validation status

- **ADR-343 kernel-derivable aperture/floor: VALIDATED on the second program.** The author Reviewer derived floor = voice/anti-slop bar, aperture = production scope/cadence, from its mandate + ground-truth, with no hand-authored rules. The structural claim — future author-like programs inherit the *capacity to derive* — holds.
- **Floor discipline preserved (cross-program): VALIDATED.** Under explicit "I'm not asking you to lower your bar," the Reviewer audited against the full rule-set and shipped only because the floor was met — it did not relax it.
- **Dormancy-close-from-flat on author: NOT cleanly demonstrated** — contaminated by the first probe's own publish. A clean re-run needs the profile reset to `draft` first, then a single probe with a generous timeout.
- **NEW Hat-A finding**: addressed-wake ledger-write should be server-side and disconnect-independent (an orphaned substrate write with no execution_event is an audit-ledger hole). Recommended as a separate ADR-291/296-adjacent fix.

---

## Honest note on method

The first probe's 60s client timeout (the operator-proxy default) is the root of the contamination — it was too short for an author judgment cycle. The proper protocol for author-program probes is a ≥300s timeout (the second probe used 600s and completed in one shot). Recorded so the next derive-it run on a clean profile is reproducible.
