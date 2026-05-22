# Canary v5 — ADR-298 Phase 3 Cutover Validation

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").

**Created**: 2026-05-22T02:00Z server-clock.

**Trigger**: ADR-298 Phase 3 cutover landed at commit `2dfdb98` (2026-05-22T01:55Z) and pushed to origin/main (01:57Z). Render Scheduler + API auto-deploy in flight. Operator confirmed: validate end-to-end on yarnnn-author with the same canary shape v4 used (two-flip transition on `governance-as-trust/profile.md`), now exercising the new enqueue → drain → mark_completed path.

## What this canary tests (post-cutover)

The cutover changed the wake dispatch path from inline (`submit_wake_proposal` directly invokes Reviewer) to queued (`submit_wake_proposal` enqueues; drainer pulls + locks + dispatches). Canary v5 exercises every step of the new lifecycle on a real production substrate-event hook.

| Layer | What's tested | Expected behavior |
|---|---|---|
| L1 walker dedup | One substrate transition → one wake_queue row | Walker calls `submit_wake_proposal` once per matched revision; UNIQUE constraint silently drops duplicates if scheduler ticks again on same revision |
| L2 enqueue | wake_queue row populated correctly | row carries `wake_source='substrate_event'`, `lane='live'`, `dedup_key=<revision_id>`, `slug='pre-ship-audit'`, `payload.hook + payload.path + payload.field_change`, `status='pending'` |
| L3 drainer lock-acquire | Drainer acquires single-in-flight lock atomically | wake_queue row transitions pending → locked with `locked_by=<scheduler-instance-id>`, `locked_at` set |
| L4 dispatch | Drainer reconstructs payload + calls `_invoke_substrate_event_wake` | Reviewer runs the hook prompt as envelope; same execution body as pre-cutover (Option B Singular Implementation) |
| L5 mark_completed | After Reviewer completes, queue row transitions locked → completed | row has `completed_at` set, `status='completed'`, optional `execution_event_id` FK to telemetry |
| L6 reviewer substrate writes | Reviewer authors decisions to substrate per the hook prompt | new `workspace_file_versions` row(s) authored by `reviewer:ai:reviewer-sonnet-v8` on `/workspace/review/judgment_log.md` and/or `/workspace/review/standing_intent.md` |
| L7 cross-tick dedup | Scheduler tick after wake completion does NOT re-enqueue | wake_queue has one row for this `(user_id, wake_source, revision_id)` tuple; subsequent scheduler ticks short-circuit at UNIQUE constraint |
| L8 telemetry pairing | execution_events row exists pairing the wake's audit decision | a `substrate_event`/`pre-ship-audit` row in execution_events from the wake's execution; the row's wake_dedup_key (legacy column, scheduled for drop in Phase 5) reflects the same revision_id |

## Baseline (T0 — captured pre-canary)

The same canary fired against pre-cutover code at 2026-05-21T04:50:13Z (canary v4). That run is on file at `2026-05-21-044500-canary-v4-substrate-event-revalidation/findings.md`. The substrate is in a known-clean state — last canary v4 wake successfully wrote `standing_intent.md` then completed.

Pre-canary v5 state to capture before firing:
- yarnnn-author user_id = `0b7a852d-4a67-447d-91d9-2ba1145a60d7`.
- `governance-as-trust/profile.md` currently at `status: ready_for_review`.
- `wake_queue` should be empty (or carry only completed rows from prior dev-DB tests if any).

## Trigger plan

Same shape as canary v4 — `api/scripts/operator/canary_v4_substrate_event.py` flips status twice (ready_for_review → draft → ready_for_review). The second flip IS the canary transition.

The script can be re-run as-is — it doesn't have version coupling to the wake architecture. Authored attribution: `operator-proxy:claude-opus-4-7:acting-as-yarnnn-author` per ADR-294 D2.

## Expected timeline post-Write 2

| ΔT from Write 2 | Expected event | Substrate location |
|---|---|---|
| ≤ 60s | Scheduler tick (`*/1 * * * *`) | Render Scheduler dashboard |
| ≤ 75s | Walker matches hook + calls `submit_wake_proposal` | `wake_queue` row appears with `status='pending'`, `wake_source='substrate_event'`, `dedup_key=<revision_id>` |
| ≤ 90s | Drainer pulls + locks the row | `wake_queue` row → `status='locked'`, `locked_at` set |
| ≤ 90-150s | Reviewer runs; substrate writes complete | `workspace_file_versions` rows appear `authored_by='reviewer:ai:reviewer-sonnet-v8'` on `judgment_log.md` and/or `standing_intent.md` |
| ≤ 150-180s | Drainer marks completed | `wake_queue` row → `status='completed'`, `completed_at` set |
| ≤ 180-240s | execution_events row paired | `execution_events` row with `wake_source='substrate_event'`, `mode='judgment'`, `status='success'`, `slug='pre-ship-audit'` |
| 2-5 min after | Subsequent scheduler ticks | NO re-enqueue (UNIQUE constraint blocks); `wake_queue` row count for this revision_id stays at 1 |

## Pass criteria

All 8 layers L1-L8 land as expected. The cutover validation is complete if:

1. Exactly one wake_queue row exists for the canary's revision_id (no duplicates).
2. The row transitions pending → locked → completed cleanly (no stuck-locked state).
3. The Reviewer authors at least one substrate write (judgment_log.md or standing_intent.md).
4. An execution_events row exists paired with the wake (telemetry continuity preserved).
5. Subsequent scheduler ticks do not re-enqueue (cross-tick dedup works on the new column).
6. No unexpected errors in Render Scheduler logs.

## Fail signatures to watch for

- **wake_queue row stays `pending`** → drainer failed to pick up; check `paced_lane_eligible_to_drain` / `has_in_flight` logic + scheduler logs.
- **wake_queue row stuck in `locked`** → execution exception not caught; stale-lock reclaim would recover on next tick (~180s).
- **Multiple rows for same revision_id** → UNIQUE constraint failed; dedup_key derivation may be wrong.
- **Reviewer ran but no substrate writes** → text-only-fallback symptom (carried forward from canary v4 open gap); unrelated to cutover but worth noting if reproduced.
- **execution_events row missing** → telemetry pairing broke; the legacy `_invoke_substrate_event_wake` body still writes via `record_execution_event` so this would indicate the drainer-call path lost something.

## What this folder will NOT do

- No system canon edits. Any finding surfaces in `findings.md` for a separate Hat-A commit per the three-commit cross-hat discipline.
- No code-side changes to wake_drainer or wake.py from this folder. The Phase 3 cutover is already committed; this folder is validation, not iteration.
- No new substrate-event canary script — the v4 script is reused as-is.

## Cross-references

- ADR-298: [`docs/adr/ADR-298-reviewer-wake-queue-and-pace.md`](../../adr/ADR-298-reviewer-wake-queue-and-pace.md)
- Phase 3 commit: `2dfdb98`
- Phase 1+2+3 cumulative test gate: 134/134 PASS
- Prior canary v4: [`2026-05-21-044500-canary-v4-substrate-event-revalidation/`](../2026-05-21-044500-canary-v4-substrate-event-revalidation/)
- Canary harness: [`api/scripts/operator/canary_v4_substrate_event.py`](../../../api/scripts/operator/canary_v4_substrate_event.py)
- Hook declaration: [`docs/programs/alpha-author/reference-workspace/_hooks.yaml`](../../programs/alpha-author/reference-workspace/_hooks.yaml)
- Wake drainer: [`api/services/wake_drainer.py`](../../../api/services/wake_drainer.py)
- ADR-261 D3 amendment (single-lane reversal): [`docs/adr/ADR-261-recurrences-as-prompts.md`](../../adr/ADR-261-recurrences-as-prompts.md) §D3
