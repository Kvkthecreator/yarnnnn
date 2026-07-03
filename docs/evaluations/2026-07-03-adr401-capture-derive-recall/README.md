# Eval: ADR-401 Phase 3 — the connector capture→derive→recall chain, live

**Date:** 2026-07-03 · **Hat:** B (external developer) · **Workspace:** kvk (`2abf3f96`)
**Scenario:** the first live end-to-end run of the connector perception chain — capture fires → raw lands in `inbound/slack/` → the lane proposes ONE derive wake (ADR-401 D5) → the funnel escalates → the seat wakes with the derive-and-cite ask → (derive → embed → recall).
**Code under test:** ADR-401 Phases 0–4 (`9ef979d`, `fc992b3`, `277e40f`, `9daeeed`, `bae3e33`) deployed live on API + Scheduler (both on `56b7fa9` lineage at observation time).

## Expected

1. After the one-shot index repair (`adr401_rematerialize_capture_index.py`), `capture-slack` gains a real `next_run_at` under the fixed bare-interval grammar.
2. The scheduler tick (every 1 min) fires the capture at/after `next_run_at`; raw lands per-channel at `inbound/slack/{channel}/{observed_at}.md`, attributed `system:*`.
3. The lane records a capture `execution_events` row (`funnel_decision=capture`) and writes the health signal.
4. Exactly ONE `substrate_event` wake proposal (`derive-capture-slack`) enqueues for the run.
5. The drainer wakes the seat with the derive ask; the wake completes; a derived `operation/` file carrying `derived_from:` cites the raw; the post-wake sweep embeds it; `recall` finds it.

## Observed (receipts)

| # | Expected | Observed | Verdict |
|---|---|---|---|
| 1 | Index repair schedules the row | Dry-run receipt: 1 workspace with `_captures.yaml`, 1 stuck row (`capture-slack`, `next_run_at=NULL`, un-paused). Post-apply: `next_run_at=2026-07-03T00:28:59Z`. | ✅ (and confirms the never-fired diagnosis) |
| 2 | Capture fires, raw lands | Fired `00:35:33Z` (tick after due). Two revisions `00:35:31–32Z`: `inbound/slack/c096dh6tmu3/unknown.md` (32,253 chars — the real daily-work channel) + `inbound/slack/c0a6p2ws4hl/unknown.md` (1,610 chars), `authored_by=system:sync-platform-state`. `next_run_at` advanced to `00:50:33Z`. | ✅ with defect: **filename is `unknown.md`** — the lane never threaded `observed_at` into the primitive args. Un-ageable by the retention GC (the window reads the filename stamp). **Fixed** (`4fcd4bd`), gate 25. |
| 3 | Capture telemetry row | **ZERO `execution_events` rows for `capture-slack`, ever.** Root cause: the `funnel_decision` CHECK constraint never gained `'capture'` (migration drift vs ADR-393's lane code); `record_execution_event` swallows insert errors, so the rejection was silent. Health signal wrote fine (`ok`, 2 items). | ❌→✅ **Fixed**: migration 196 (applied to prod) + `4fcd4bd`. |
| 4 | ONE derive proposal per run | `wake_queue` row `derive-capture-slack`, `wake_source=substrate_event`, enqueued `00:35:33.877Z` — exactly one for the 2-file run. | ✅ (the D5 batching contract holds live) |
| 5 | Seat wakes, derives, embeds, recall | Wake drained + **completed `00:36:46Z`** (~73 s). `execution_events`: `slug=derive-capture-slack, trigger_type=reactive, wake_source=substrate_event, funnel_decision=escalate, status=success`. **But the seat authored NO derived file** — post-wake revisions are system mirrors only; no `operation/` file cites the raw; nothing new to embed; recall unchanged. | ⚠️ **Partial.** The route works (the ask reached judgment); the judgment declined to derive 32KB of substantive operator content. See finding F3. |

## Findings

- **F1 (fixed, `bae3e33`): the seeded cadence was unresolvable — connector captures could never fire.** `@every 15min` was classified semantic; bare workspaces raised on missing market context, program workspaces failed the `during <session>` grammar → `next_run_at` stayed NULL. The bare-interval grammar + the one-shot repair close it. This was the real cause behind the standing "never observed e2e" gap.
- **F2 (fixed, migration 196 + `4fcd4bd`): capture telemetry silently rejected** by CHECK-constraint drift; and **raw filenames un-stamped** (`unknown.md`) because the lane didn't thread `observed_at`. Both invisible to the pure-Python gates — only the live run surfaced them. The two `unknown.md` residue files are left in place (kept-fresh-forever by the GC's fail-safe; superseded by stamped snapshots from the next run).
- **F3 (open, judgment-layer): the seat's first derive wake produced no derivation and no visible narrative.** The D5 prompt explicitly permits "deriving nothing is a valid judgment" for noise — but the larger raw was substantive operator work-log content, and no narrative note explaining the judgment was found in the recent sessions. One sample is not conclusive: possible causes range from a fair noise call, to the envelope diluting the ask (see `feedback_envelope_removal_over_addition` — suspect dilution before adding prompt weight), to the seat lacking a legible place to say "nothing worth deriving." **Next probe:** observe 2–3 subsequent capture wakes with genuinely new content; if derive never fires, run the byte-stable ask directly against the seat with the raw present and diff the reasoning stream.
- **F4 (observation): diff-aware batching behaves.** The second run (due `00:50:33Z`) only proposes if new content landed — an unchanged world proposing nothing is the designed behavior and should be recorded as such, not as a failure.

## Second run — under the `4fcd4bd` fixes (observed 00:51Z)

The next capture fired at `00:51:23Z` with the fixes deployed:

- **Capture telemetry now inserts**: `execution_events` row `{slug: capture-slack, status: success, funnel_decision: capture, trigger_type: capture}` — migration 196 verified live. ✅
- **Raw filenames now stamped**: `inbound/slack/{channel}/2026-07-03T00:51:17Z.md` — the retention GC can age them. ✅
- **Second derive wake proposed + completed**; again no derivation authored (F3 now has two samples, though the second run's content was near-identical to the first).
- **F5 (found by reasoning over run 2, fixed same session): stamped filenames defeated diff-awareness.** `_write_if_changed` compared against the *same path*; with a fresh stamp per run the path never pre-exists, so **every** run rewrote **every** selector — snapshot bloat plus a derive wake every 15 minutes on an unchanged world. Fix: the diff baseline is now the sub-lane's **latest snapshot** (stamped files preferred, so legacy `unknown.md` residue — which sorts after digits — never shadows them); an unchanged selector writes nothing and an unchanged world proposes nothing. Gate: test_adr394 6b/6c (40/40).

## Chain status after this eval

capture ✅ → raw ✅ (stamped post-fix) → propose ✅ → wake ✅ → **derive ⚠️ (route proven; judgment un-validated)** → embed (unexercised — nothing derived yet) → recall (unexercised). The mechanical floor of ADR-401 is live and verified; the judgment tail is the remaining open loop, tracked by F3.
