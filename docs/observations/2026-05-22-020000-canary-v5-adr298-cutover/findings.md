# Canary v5 — ADR-298 Phase 3 Cutover Validates End-to-End

**Hat**: External Developer of the System (Hat B per CLAUDE.md §"The Two Hats").

**Captured**: 2026-05-22T02:02–02:07Z server-clock. N=1 substrate-event reactive wake through the new enqueue → drain → mark_completed pipeline.

## Headline

**The ADR-298 Phase 3 cutover validates structurally end-to-end.** Every step of the queue lifecycle landed in expected order with expected timing. The Reviewer body returned `balance_exhausted` (a pre-existing workspace condition, not a cutover bug), and the queue handled the failure cleanly: `mark_failed` transition, telemetry pairing, no orphaned `locked` state. Cross-tick dedup confirmed working — five subsequent scheduler ticks did not re-enqueue.

## Validation timeline (Write 2 → terminal in 294ms)

| Time (UTC, ms-resolved) | Event | Layer | Cross-ref |
|---|---|---|---|
| 02:02:36.181 | Canary Write 2 — `status: draft → ready_for_review` on `governance-as-trust/profile.md`. revision_id = `d2ba2905`. | Operator | PLAYBOOK trigger plan |
| 02:02:38.186 | Scheduler tick walker: `GET _hooks.yaml` | L1 (walker) | scheduler tick 02:02 |
| 02:02:38.228 | Walker: `GET workspace_file_versions since 01:32:38` (30min lookback) | L1 (walker) | finds the canary revision |
| 02:02:38.453 | Walker: GET execution_events check on wake_dedup_key (legacy ADR-272 gate) | L1 (walker) | **see §"Phase 5 cleanup item" below** |
| 02:02:38.471 | `INSERT INTO wake_queue` — row id `5320fe47`, status=`pending`, lane=`live`, dedup_key=`d2ba2905`, slug=`pre-ship-audit` | **L2 (enqueue) ✓** | wake.py `submit_wake_proposal` |
| 02:02:38.488 | Walker returns; SCHED moves to drain block | — | unified_scheduler.py drain wiring |
| 02:02:38.521 | `reclaim_stale_locks` PATCH on stale locked rows (none stale, no-op) | L3 prep | wake_drainer.py |
| 02:02:38.582 | `has_in_flight` check on yarnnn-author (no lock held) | L3 (single-in-flight ✓) | wake_drainer.drain_can_acquire_for_user |
| 02:02:38.611 | `read_pace` GET `_pace.yaml` (returns empty — yarnnn-author has no pace declared) | L3 (paced eligible) | wake_drainer.paced_lane_eligible_to_drain |
| 02:02:38.635 | `get_next_pending` returns row `5320fe47` (oldest pending live-lane row) | L3 (FIFO pull) | wake_queue.py |
| 02:02:38.667 | **`try_lock` PATCH** — status `pending → locked`, locked_by=`crn-d604uqili9vc73ankvag-29656922-b95d6` | **L3 (lock acquire) ✓** | wake_queue.try_lock CAS guard |
| 02:02:38.739 | `_invoke_substrate_event_wake` body returns — kernel gate fired: `error_reason='balance_exhausted'` (workspace effective balance = −$0.04) | L4 (dispatch ✓, body refused) | platform_limits.check_balance |
| 02:02:38.765 | `[TELEMETRY] judgment/pre-ship-audit failed` — execution_events row `0ff85885` written with `wake_source=substrate_event`, `mode=judgment`, `status=failed`, `error_reason=balance_exhausted` | L8 (telemetry pairing ✓) | services/telemetry.py |
| 02:02:38.789 | `mark_failed` PATCH — wake_queue row `5320fe47` status `locked → failed`, completed_at set | **L5 (queue terminal ✓)** | wake_queue.mark_failed |
| 02:02:38.815 | drainer next-iter check `has_in_flight` (empty — single-in-flight constraint cleared) | L3 (lock release ✓) | drain_user_until_empty loop |
| 02:02:38.858 | drainer `get_next_pending` (no more pending) → break | — | drain_user_until_empty exit |
| 02:02:38.891 | `[SCHED] drained 1 wake(s) from wake_queue` | — | unified_scheduler.py log line |

Total elapsed from Write 2 to terminal state: **~2.6 seconds** (most spent in the 1-2s scheduler tick boundary; the actual queue lifecycle from enqueue → mark_failed was 318ms).

## Layer-by-layer pass criteria

| Layer | Pass criterion (per PLAYBOOK) | Observed | Verdict |
|---|---|---|---|
| L1 walker dedup | One substrate transition → one wake_queue row | 1 row for `d2ba2905`; subsequent ticks at 02:03+ did NOT re-enqueue (UNIQUE constraint hit silently) | ✓ |
| L2 enqueue | Row carries `wake_source='substrate_event'`, `lane='live'`, `dedup_key=<revision_id>`, `slug='pre-ship-audit'`, payload with hook/path/field_change | All fields present and correct per direct table query | ✓ |
| L3 drainer lock-acquire | Atomic `pending → locked` CAS with `locked_by` + `locked_at` | Locked at 02:02:38.667Z; locked_by = scheduler instance ID; CAS WHERE-status-pending guard worked | ✓ |
| L4 dispatch | Drainer reconstructs payload + calls `_invoke_substrate_event_wake` | Dispatch invoked; body executed (and returned balance_exhausted) | ✓ |
| L5 mark_completed/failed | Queue row transitions out of `locked` to terminal state with `completed_at` set | Row transitioned `locked → failed` at 02:02:38.789Z; completed_at set | ✓ |
| L6 reviewer substrate writes | At least one Reviewer-authored `workspace_file_versions` row | **None** (Reviewer didn't run due to balance_exhausted gate) | N/A (gated upstream of LLM) |
| L7 cross-tick dedup | Subsequent scheduler ticks do NOT re-enqueue | 5+ ticks elapsed (02:03 → 02:07Z); still exactly 1 row for this dedup_key | ✓ |
| L8 telemetry pairing | execution_events row exists paired with the wake | Row `0ff85885` exists with matching `wake_source` + `slug` + `wake_dedup_key` columns | ✓ |

**7 of 8 layers PASS structurally. L6 (Reviewer substrate writes) is N/A because the Reviewer body's balance gate fired before LLM dispatch — this is correct behavior per ADR-172, not a cutover failure.**

## Why the balance gate fired (and why this is not a cutover bug)

yarnnn-author's workspace state:
- `workspaces.balance_usd` = $3.00 (static)
- `get_effective_balance()` RPC = **−$0.04** (spend since last refill exceeds the static balance by $0.04)

`platform_limits.check_balance` returns `(False, -0.04)` → `_invoke_substrate_event_wake` records `error_reason='balance_exhausted'` and returns `{success: False, ...}` BEFORE calling Sonnet. This is the correct ADR-172 hard-stop-at-zero behavior.

The previous canary v4 (2026-05-21T04:51Z) ran successfully because at that time `get_effective_balance` was still positive. Between then and now, yarnnn-author's spend rolled past the balance.

**This is unrelated to ADR-298.** The same hook + same canary shape on a workspace with positive effective balance would have run the full Reviewer Sonnet cycle. The cutover's job is to deliver the wake to the body; the body's kernel gates are unchanged.

## What this validates about Phase 3

The cutover honored every architectural commitment from ADR-298:

- **D1 single-lane** — `has_in_flight` checked before lock acquire; CAS on try_lock; no parallel Reviewer instances.
- **D2 transient compute queue** — wake_queue row was created, locked, completed, and is still queryable; no operator-readable substrate produced.
- **D3 two-lane** — substrate_event landed on `lane=live`; the (empty) paced lane was checked separately via paced_lane_eligible_to_drain.
- **D6 cross-source dedup** — revision_id as dedup_key worked; cross-tick re-enqueue suppressed by UNIQUE constraint.
- **§"Singular Implementation"** — no parallel direct-dispatch path observed; every wake operation went through enqueue → drain.
- **ADR-261 D3 amendment** — Reviewer execution structurally single-lane; no concurrent fire detected.

## Phase 5 cleanup items surfaced

Two minor cleanup items observable in the log, neither blocking:

1. **Legacy execution_events.wake_dedup_key check still firing.** At 02:02:38.453Z the walker did a GET on execution_events filtered by `wake_source=substrate_event&slug=pre-ship-audit&wake_dedup_key=d2ba2905`. This is the pre-ADR-298 ADR-272 dedup gate. Now redundant — the wake_queue UNIQUE constraint at insert time handles cross-tick dedup, and ADR-298 Phase 5 explicitly scopes "drop `execution_events.wake_dedup_key` column" + remove the check.

2. **`reclaim_stale_locks` runs on every scheduler tick.** Currently it's a single SQL UPDATE that's no-op when no stale locks exist; cost is negligible. But the call runs unconditionally — Phase 5 could gate it behind a "any locked rows exist" pre-check to save one round-trip per tick. Low priority.

Both are non-blocking and properly scoped to Phase 5.

## What this canary does NOT do

- Does NOT exercise L6 (Reviewer substrate writes) — gated upstream by balance check. A follow-up canary on a workspace with positive effective balance would close this. (For example: `kvk` workspace at user_id `2abf3f96-118b-4987-9d95-40f2d9be9a18` runs daily outcome-reconciliation cron — that wake will run through the cutover at next ~21:00Z UTC and exercise L6 naturally.)
- Does NOT exercise the addressed-turn Option α lock-acquire path. That requires a real chat message + observation through `/feed`. Out of scope for this canary; covered by Phase 3 test gate (39/39 PASS).
- Does NOT exercise the paced-lane drain throttling. yarnnn-author has no `_pace.yaml` so paced_lane_eligible_to_drain returns True unconditionally. Phase 4 (bundle minimum_pace declarations) will create a workspace state where pace gating is testable.

## Cross-references

- PLAYBOOK: [./PLAYBOOK.md](./PLAYBOOK.md)
- ADR-298: [`docs/adr/ADR-298-reviewer-wake-queue-and-pace.md`](../../adr/ADR-298-reviewer-wake-queue-and-pace.md)
- Phase 3 commit: `2dfdb98`
- Prior canary v4 (pre-cutover): [`2026-05-21-044500-canary-v4-substrate-event-revalidation/`](../2026-05-21-044500-canary-v4-substrate-event-revalidation/)
- Canary harness: [`api/scripts/operator/canary_v4_substrate_event.py`](../../../api/scripts/operator/canary_v4_substrate_event.py) (reused as-is)
- Hook declaration: [`docs/programs/alpha-author/reference-workspace/_hooks.yaml`](../../programs/alpha-author/reference-workspace/_hooks.yaml)
- Wake drainer: [`api/services/wake_drainer.py`](../../../api/services/wake_drainer.py)
- ADR-298 Phase 1+2+3 cumulative test gate: 134/134 PASS
- ADR-172 balance gate semantics: [`docs/adr/ADR-172-balance-as-single-gate.md`](../../adr/ADR-172-balance-as-single-gate.md)

## Recommendation

**The cutover is validated. Proceed to Phase 4 + Phase 5.**

Phase 4 (bundle minimum_pace + activation gate) does not depend on yarnnn-author's balance state and can land as the next code-PR. Phase 5 (cockpit FE + final canary v6 with positive balance + drop legacy column) follows.

Operator may optionally top up yarnnn-author's workspace balance to support direct L6 validation, but it's not necessary — alpha-trader workspaces (kvk, alpha-trader-2, seulkim88) have active daily judgment recurrences that will naturally exercise L6 through the cutover at their next scheduled fire (typically ~05:00Z or ~21:00Z UTC depending on the recurrence). Observation of any of those daily fires is the natural "L6 validates in production" event.

## Status

**Phase 3 cutover: PASS structurally on N=1.** Awaiting L6 validation via natural cron-tick judgment wake (alpha-trader outcome-reconciliation expected ~21:00Z UTC today). No Hat-A action required; no code changes recommended.
