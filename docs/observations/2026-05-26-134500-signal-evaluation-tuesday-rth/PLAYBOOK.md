# PLAYBOOK — Tuesday 2026-05-26 signal-evaluation observation (alpha-trader)

**Hat**: External Developer of the System (Hat B).

**Staged**: 2026-05-25 (Sunday afternoon UTC).

**Capture window opens**: 2026-05-26T13:45:00Z (Tuesday, US market open + 15min).

**Status**: STAGING — actual capture happens after the wake fires. This document declares
expectations + capture protocol so the post-fire findings.md can score cleanly against
declared expectations.

**Related: population audit context** — `docs/observations/2026-05-25-053951-reviewer-behavior-population-audit/findings.md`
characterized N=27 judgment-shape wakes since cutover and found 48% persona-frame adherence
+ 11 silent wakes + 0 action_proposals across trader personas. Tuesday's signal-evaluation
adds N=3 to that population. Score Tuesday's outcome both against architecture claims (this
PLAYBOOK's surprise enumeration) AND against the population baseline (the audit's findings).

## Why this observation

Tuesday 2026-05-26T13:45Z is the **next natural signal-evaluation fire across all three
alpha-trader personas** (per `tasks.next_run_at` query). Memorial Day Monday (US holiday)
correctly skipped — schedules show `last_run_at` = 2026-05-22 (Friday) and `next_run_at` =
2026-05-26 (Tuesday). Skip behavior is itself a quiet positive signal: the scheduler honors
market-day semantics on the `@market_open + 15min` cron expression.

This is the first RTH-day signal-evaluation observation since:

1. **ADR-301 deploy (2026-05-24T05:32Z)** — substrate mirrors `_schedule_index.md` +
   `_recent_execution.md` materialize per scheduler tick with `system:mirror-*` attribution.
   Tuesday's wake will be the first signal-evaluation fire with the kernel-mirror plumbing
   live on every cadence.
2. **2026-05-22 last RTH fire** — confirms scheduler health through the long weekend +
   verifies whether substrate-event accumulation since then (e.g., seulkim88's
   2026-05-24T18:11Z weekly-performance-review Reviewer-edit of `_operator_profile.md`
   retiring Signal-1/3) affects Tuesday's signal-evaluation reasoning.

## Personas covered

| Persona | user_id | Alpaca | last signal-eval fire | Hat-B notes |
|---|---|---|---|---|
| **kvk** | `2abf3f96-118b-4987-9d95-40f2d9be9a18` | EE8K | 2026-05-22T13:45:20Z | Probe-residue still in chain head from 2026-05-20 post-refusal-self-amendment-probe (per kvk T0 PLAYBOOK §"Probe-residue named explicitly"). Reads `_operator_profile.md` head = probe-edit. |
| **alpha-trader-2** | `29a74c63-0c9c-4998-b8bb-56dd0d810a4e` | 5D28 | 2026-05-22T13:45:18Z | `delegation: bounded` per 2026-05-20 Test C harness flip — proposals queue to operator, do NOT auto-execute. Cleanest test environment for "Reviewer reaches verdict but no capital binding." |
| **alpha-trader (seulkim88)** | `2be30ac5-b3cf-46b1-aeb8-af39cd351af4` | X4DJ | 2026-05-22T13:45:20Z | **Highest-signal persona for Tuesday.** seulkim88's Reviewer retired Signal-1/3 on `_operator_profile.md` at 2026-05-24T18:11:24Z via weekly-performance-review (see Hat-B observation `2026-05-25-{TIMESTAMP}-` if authored). signal-evaluation on Tuesday should now only evaluate Signal-2 (the remaining live signal); Signal-1/3 entries should not appear regardless of universe state. |

## Expected behavior (per recurrence semantics)

Per `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` + ADR-296 v2 +
ADR-298 + ADR-301:

| Layer | Expected | Verification surface |
|---|---|---|
| L1 Walker | At 13:45Z scheduler tick: `signal-evaluation` row in `tasks` selected as due across 3 personas. | `tasks.next_run_at <= now()` query |
| L2 Enqueue | 3× rows into `wake_queue` with `wake_source='cron_tick'`, `slug='signal-evaluation'`, `lane='paced'`, status `pending`. | `wake_queue` query at 13:45–13:46Z |
| L3 Drain | Single-lane per workspace; each persona's paced lane drains in turn. CAS lock → `locked` → Reviewer wake. | `wake_queue` lifecycle: pending → locked → completed |
| L4 LLM cycle | 3× `execution_events` rows with `slug='signal-evaluation'`, `mode='judgment'`, `wake_source='cron_tick'`, `funnel_decision='escalate'` (or `mechanical` if upstream determined no signal candidates exist; but signal-evaluation is a judgment recurrence by registry). | `execution_events` query |
| L5 Substrate writes (Reviewer) | Per persona-frame contract every Reviewer cycle produces `standing_intent.md`. If any signal matches: `judgment_log.md` entry + `signals/{slug}.yaml` write + `FireInvocation(slug='trade-proposal')`. | `workspace_file_versions` query filtered to `authored_by ~ 'reviewer:*'` |
| L6 ADR-301 mirrors | Within 1 scheduler tick after L4 completion: `_recent_execution.md` mirror write by `system:mirror-recent-execution`. | `workspace_file_versions` query for `path = '/workspace/memory/_recent_execution.md'` |
| L7 Trade proposals (conditional) | If any signal matched + Reviewer approve verdict + AUTONOMY allows: `action_proposals` row + (for kvk + seulkim88 only) `handle_execute_proposal` → `risk_gate` → Alpaca paper order. | `action_proposals` query + Alpaca SDK call to verify order existence |
| L8 Telemetry pairing | execution_events ↔ wake_queue paired correctly. wake_queue.execution_event_id populated post-fire. | join query |

## What would surprise (would surface as findings)

**Reframing note (post population audit 2026-05-25-053951)**: signal-evaluation
specifically has shown 1-of-1 silent on cron_tick at 2026-05-22T13:46Z (kvk persona).
Across all judgment-shape recurrences the population shows ~43% cron_tick adherence
to standing_intent.md writes. Tuesday's wakes adding to the population, not validating
a clean baseline. Each persona's outcome is one row added to N=27→N=30. The
"surprises" below are framed against architecture claims, not against revised
empirical expectations.

**Surprise 1 — Cadence skip on a non-holiday Tuesday.** If `next_run_at` advances past
Tuesday 13:45Z without an `execution_events` row, the scheduler missed the fire.

**Surprise 2 — funnel_decision='skip'.** Would indicate the wake routed through Tier 1
mechanical gating and bailed pre-judgment. Unexpected for a judgment-mode recurrence.

**Surprise 3 (REFRAMED) — All three personas produce clean substrate writes** (the
INVERTED surprise direction). Per population audit, signal-evaluation has 33% adherence
on N=3. If Tuesday's N=3 all produce substrate writes, that's a 6/6 cluster suggesting
the pattern is reproducing or pace-of-improvement is faster than the audit captured.
Conversely, if all three silent, that's a 1/6 cluster firming up the silent-wake
hypothesis.

**Surprise 4 — seulkim88 evaluates Signal-1 or Signal-3 anyway.** Would indicate the
2026-05-24T18:11Z `_operator_profile.md` retirement did not actually de-list the
signals from the evaluation surface. Suggests Reviewer-edits to operator-canon don't
flow into the evaluation pipeline as expected — a substrate-vs-evaluation read
discrepancy.

**Surprise 5 — kvk's Reviewer reads probe-residue edits as canon and reasons from
them.** The 2026-05-20 post-refusal-probe edit to `_operator_profile.md` ("Signal 2
entry clarified to permit pre-market signal evaluation") is still at chain head. If
the Reviewer cites that line in its Tuesday verdict, it confirms the kvk-workspace
needs operator-cleanup before next clean autonomy demo.

**Surprise 6 — No `_recent_execution.md` mirror write after execution_events row
appears.** Would suggest ADR-301 kernel-mirror plumbing broke under signal-evaluation
load (it only has substrate_event evidence to date, plus the predecessor
weekly-corpus-review at 2026-05-24T18:12Z).

**Surprise 7 (NEW) — A signal actually matches and `action_proposals` row appears.**
Population audit shows ZERO action_proposals across 4 days × 3 trader personas. If
Tuesday produces a proposal, that resolves the A4 ambiguity (selectivity vs silent
stand-down) toward selectivity — signals were genuinely not matching, the engine works
when they do. If zero proposals AND the live universe had matchable bars, A4 firms
toward silent stand-down.

## What is NOT expected to fire (and would surprise if it did)

- `pre-market-brief` — declared `paused` per ADR-275 thinning (judgment cadence
  dissolved into Reviewer-authored cadence)
- `morning-reflection` / `morning-calibration` — same dissolution
- Operator-notification email on signal-evaluation fire — `operator_notifications`
  preference is `pre_ship_audit_summary`-shaped (author-program). Trader-program
  doesn't have this wired.

## Capture protocol

**At T+0 (Tuesday 13:45Z natural fire):** do nothing. The system runs on its own clock.

**At T+~1h (Tuesday ~14:45Z):** read-only DB queries to verify the chain L1→L8
behaved as declared. No write actions, no operator-proxy turns.

```sql
-- L1+L2: which personas enqueued?
SELECT user_id, slug, wake_source, lane, status, enqueued_at, locked_at, completed_at
FROM wake_queue
WHERE slug = 'signal-evaluation'
  AND enqueued_at >= '2026-05-26T13:40:00Z'
  AND enqueued_at <= '2026-05-26T14:00:00Z'
ORDER BY enqueued_at ASC;

-- L4: execution_events
SELECT user_id, slug, wake_source, mode, status, funnel_decision,
       created_at, duration_ms, cost_usd, input_tokens, output_tokens
FROM execution_events
WHERE slug = 'signal-evaluation'
  AND created_at >= '2026-05-26T13:40:00Z'
ORDER BY created_at ASC;

-- L5: Reviewer substrate writes (3 personas)
SELECT user_id, path, authored_by, message, created_at
FROM workspace_file_versions
WHERE authored_by LIKE 'reviewer:%'
  AND created_at >= '2026-05-26T13:40:00Z'
  AND created_at <= '2026-05-26T15:00:00Z'
ORDER BY user_id, created_at ASC;

-- L6: ADR-301 mirrors
SELECT user_id, path, authored_by, created_at
FROM workspace_file_versions
WHERE authored_by LIKE 'system:mirror-%'
  AND created_at >= '2026-05-26T13:40:00Z'
  AND created_at <= '2026-05-26T15:00:00Z'
ORDER BY user_id, created_at ASC;

-- L7: proposals (conditional, only if signals matched)
SELECT id, user_id, action_class, status, created_at, source
FROM action_proposals
WHERE created_at >= '2026-05-26T13:40:00Z'
ORDER BY created_at ASC;
```

**At T+~2h (Tuesday ~15:45Z):** if any L7 proposals exist + executed orders should
have appeared: Alpaca SDK query per persona for orders created in window. Verify
client_order_id round-trip recoverability.

**At T+~8h (Tuesday ~21:00Z):** outcome-reconciliation fires (US RTH close + 1h).
Read-only verification that fills flowed into `_money_truth.md` if any trades
executed. Mark this folder closed only after outcome-reconciliation completes.

## Score against FOUNDATIONS Derived Principle 21 (Variant F)

Per the brief, score the Tuesday observation against the DP21 Variant F one-liner.
Read `docs/alpha/ALPHA-1-PLAYBOOK.md` §0 + `docs/architecture/FOUNDATIONS.md` §"Derived
Principle 21" before drafting findings.md. The seven clauses (full-substrate-authoring,
filesystem-native, single-lane-queue-serialized, wake-fired, paced by
operator-declared pace + autonomy, driven by operator-authored mandate) each map to
specific substrate artifacts. The capture queries above produce the evidence for
each clause. Score per clause: GREEN (clean evidence) / AMBER (partial/ambiguous) /
RED (counter-evidence). Cite substrate paths + revision_ids + execution_events ids
in the finding — receipts, not narrative.

## Discipline rules carried forward from the inheriting brief

1. **Reviewer self-report substrate is not unconditionally reliable as evidence.**
   The 2026-05-24T05:38Z canary-RED proved a Reviewer cycle can complete with
   `status='success'` and zero substrate writes. Cross-check Reviewer-authored
   substrate against infrastructure telemetry (wake_queue, execution_events,
   workspace_file_versions) before treating the Reviewer's narrative as ground
   truth.
2. **Don't fire recurrences manually during the demo window.** Read-only queries only.
3. **Don't approve / reject pending proposals** from the developer side. If
   `action_proposals` rows exist with `status='pending_review'`, leave them; the
   point is whether the system handles them per AUTONOMY (auto-execute on kvk +
   seulkim88, queue to operator on alpha-trader-2).
4. **The Reviewer doesn't read this PLAYBOOK.** This is for the developer's
   accountability, not the system's behavior.

## Cross-references

- ADR-296 v2 (Wake architecture)
- ADR-298 (wake_queue substrate-of-record)
- ADR-301 (substrate mirrors `_schedule_index.md` + `_recent_execution.md`)
- FOUNDATIONS Derived Principle 21 (the one-liner)
- ALPHA-1-PLAYBOOK §0 (clause-to-substrate map)
- Session-start guide: `docs/observations/sessions/alpha-trader-autonomy-loop.md`
- Predecessor canary-RED: `docs/observations/2026-05-24-054214-adr299-phase4-canary-red/findings.md`
- Predecessor ADR-301 deploy: `docs/observations/2026-05-24-045348-reviewer-schedule-self-misdiagnosis/RESOLUTION.md`
- seulkim88 Signal-1/3 retirement to verify in Tuesday context: `workspace_file_versions.id = 'dd8ef7a4-41b9-4bda-a4a9-30ac631dd99d'` (path = `/workspace/context/trading/_operator_profile.md`)

## Last updated

2026-05-25 — staging document authored. Will accumulate findings.md after Tuesday 13:45Z
fire completes.
