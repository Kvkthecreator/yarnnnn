# Rung 4 — model stabilization on Sonnet 4.6: criterion-first FINDING (2026-07-03)

**Decision under evaluation**: ADR-402 Part B (commit `afb1040`, deployed ~2026-07-03 00:25Z) — Freddie runs **one model, `claude-sonnet-4-6`, for all three wake shapes** (addressed | proposal_arrival | recurrence), uniform 20-round ceiling, routing as kernel data (`api/services/model_routing.py`, env-overridable).
**Run receipts**: [`2026-07-03-rung4-partA-haiku/`](2026-07-03-rung4-partA-haiku/) (baseline arm) · [`2026-07-03-rung4-partB-sonnet-addressed/`](2026-07-03-rung4-partB-sonnet-addressed/) (decision arm, now the canonical baseline) · [`2026-07-03-rung4-partB-landed-smoke/`](2026-07-03-rung4-partB-landed-smoke/).
**This doc** retro-fits the criterion-first FINDING the rung-4 runs shipped without (EVAL-SUITE-DISCIPLINE / README criterion-declaration rule), and records the **production confirmation** of the decision.

## Criterion (declared)

The stabilization prior is justified iff, on the byte-stable 6-ask addressed probe (`probe_freddie_addressed_baseline.py` — asks never reworded) and in production telemetry:

1. **Correctness ≥ Haiku**: 6/6 close, no silent exits, no false substrate claims.
2. **Cost ≤ ~1.5× observed** (not the 3× price-sheet multiplier) — bought back by fewer rounds.
3. **Production wakes land in the Sonnet band**: `execution_events` success rows whose cost decomposes at Sonnet rates, no `reviewer_returned_none` failures.

Operationalization: probe `summary.json` metrics + `execution_events` rows post-deploy; cost decomposition at ledger 2×-list rates (ADR-172).

## Probe evidence (the Part A/B arms, receipts in the run folders)

| arm | closed | silent exits | mean rounds | mean tools | mean est. cost/turn |
|---|---|---|---|---|---|
| Haiku (partA) | 5/6 (+recheck pass) | 1 | 6.2 | 10.2 | $0.0604 |
| **Sonnet (partB)** | **6/6** | **0** | **3.3** | **4.2** | **$0.0711** |

Observed cost ratio ≈ **1.2×** on this pair (the ~1.4×/turn figure in the ADR uses the fuller arm set) — well inside criterion 2. Qualitative deltas (partB README): Sonnet caught the seeded attribution mismatch Haiku missed (Haiku falsely reported "well-attributed" — a criterion-1 false-substrate-claim failure), and deduped against the pending proposal queue where Haiku re-proposed.

Historical silent-exit base rate, now machine-extracted (`--reextract` backfill, 2026-07-03): **Haiku 4 / 43 addressed turns (~9%)** across the rung series (rung3-armB ×2, rung3-landed ×1, rung4-partA ×1); **Sonnet 0 / 8** addressed turns to date.

## Production confirmation (first organic wakes post-deploy)

Query: `execution_events WHERE created_at >= '2026-07-03 00:25Z'` (prod, 2026-07-03 ~05:40Z).

- **20/20 judgment wakes `status=success`** — all `derive-capture-slack` (`substrate_event`), kvk `2abf3f96`. Zero failures, zero `reviewer_returned_none`.
- **Sonnet band confirmed by exact cost decomposition**: row `b5fa1063` = 40,098 in / 3,079 out / 97,816 cache-read / 23,274 cache-create → at 2× Sonnet list ($6/$30/$0.60/$7.50 per Mtok) = **$0.5663 vs recorded $0.5662**. The pre-decision Haiku decomposition of the same row would be ~$0.19 — the ledger is unambiguous.
- The derive chain closed end-to-end in production for the first time: capture → raw → derive wake → proposals → operator approvals (01:37Z + 02:35Z) → derived files under `operation/yarnnn-product/` (product-notes, user-signups, daily-work-log). **The ADR-401 F3 open item ("seat derived NOTHING") is closed.**
- The **addressed** and **bare-workspace** shapes have **no organic post-deploy rows yet** — production confirmation currently covers the `substrate_event` shape only; the addressed shape is confirmed by the local probe arms above.

**Verdict: the criterion holds on all three legs observed so far. The rung-4 decision stands.**

## Production flags surfaced by the same query (not criterion failures — operational findings)

1. **Derive-wake burn rate**: the 15-min capture cadence fires a ~$0.63-avg judgment wake per cycle — **$12.55 in ~5 h ≈ $60/day** on one Slack connector, overnight. Receipt: consecutive raw snapshots of channel `c0a6p2ws4hl` at 05:20:32Z and 05:36:26Z are **byte-identical (`md5 46f3105a…` both)**, yet each cycle wrote a new stamped raw file (`system:sync-platform-state`) and each write fired a `substrate_event` derive wake. This is the exact class commit `445b97a` ("diff baseline = the sub-lane's latest snapshot") targeted — and the receipt says the fix is **live and defeated**: the Unified Scheduler deployed commit `7b12f89` (which contains `445b97a`) at 05:08:02Z (deploy `dep-d93k4heq1p3s73cr1h3g`), and the 05:20:32Z + 05:36:26Z byte-identical rewrites both happened after that. The `_write_if_changed` comparison is not suppressing on this path (bug in the latest-snapshot baseline resolution, or the compared content differs from what lands). Fix-location: the connector capture lane's change-suppression, debugged against this md5 receipt; secondarily a derive-wake accumulation threshold (ADR-401 D5 named wake-routing as the design seam).
2. **Re-proposal dedup failure on the derive shape**: the 12 consecutive derive wakes 02:43→05:37Z each re-proposed the same two actions — **22 pending `EditFile persona/standing_intent.md` + 12 pending `WriteFile …/daily-work-log/2026-07-03.md`** duplicates at query time — despite pending-proposals being in the ADR-403 volatile suffix, and despite the same model deduping correctly on the addressed probe AND on the bare-steward recurrence re-run the same day. Shape-specific: suspect the derive-wake envelope's pending-proposal rendering or the ask framing (cause (c) envelope, per the four-cause taxonomy — to be probed before any prompt-weight fix, per the probe-before-canon lesson).
3. **`judgment_log.md` approve double-write**: every operator approve at 01:37Z produced two `freddie:human:*` revisions ~0.3 s apart (rejects wrote once) — the known dual-writer race class (ADR-276 D5 deferred), now visible on the approve path.

## Watchlist inversion (the Haiku signatures become Sonnet regression sentinels)

Now machine-checked by the probe (`sentinels` block in every turn/summary JSON; ALARM printed on any non-zero):

| sentinel | Haiku base rate | Sonnet observed | alarm rule |
|---|---|---|---|
| `silent_exits` (incl. the "Reviewer returned no response" error form) | 4/43 (~9%) | 0/8 probe + 0/20 organic | **any occurrence** → re-run that turn once; ≥2 in a rolling 24 turns → tier regression (Haiku-band would produce ~2/24) |
| `schedule_calls` (standing-cadence-from-test-asks; steward seed `test-exercises-stay-disposable`) | observed in pre-seed era | 0 | **zero tolerance** — any occurrence is a violation |
| count fuzz (wrong counts narrated in answers) | recurring | not observed | **not automated** — human-read item on every baseline re-run |

Sample-size note: 6/6 is small. Accumulate to **N ≥ 24 Sonnet turns** (four full byte-stable re-runs, e.g. one per future rung/regression run) before treating the 0% silent-exit rate as established; the alarm rule above is the interim tripwire.

## Baseline rotation (executed this session)

`CURRENT_BASELINE = "2026-07-03-rung4-partB-sonnet-addressed"` is now **declared in code** in `probe_freddie_addressed_baseline.py` — the probe auto-diffs every non-baseline run against it. The Haiku-era captures (2026-07-02-freddie-envelope-baseline, rung1–rung3-*, rung4-partA-*) are historical arms; their `summary.json` files were re-emitted (`--reextract`, raw turn JSONs untouched) to carry the usage/cost/sentinel blocks so tier comparisons stay first-class. Rotating the baseline again = changing the constant in the same commit as the run that earns it.
