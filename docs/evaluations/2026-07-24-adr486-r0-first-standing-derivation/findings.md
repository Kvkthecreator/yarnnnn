# ADR-486 R0 — the first standing derivation (Hat-B eval, 2026-07-24)

**Scenario**: declare one real radar hub in the live workspace, let the actual
Render cron fire it, and verify the full unaddressed loop — intake → derive →
cited brief → embed → meter — with substrate receipts. Before this run, every
`revision_kind='derivation'` in prod traced to a human act (the ADR-486 §2
audit); the expected outcome was the first machine-initiated derivation in the
workspace's history.

**Setup**: hub `ai-frontier` at `/workspace/operation/ai-frontier/_radar.yaml`
(HN front page RSS + simonwillison.net Atom; daily `0 21 * * *` UTC;
`fire_on_activation: true`; steer: frontier-AI moves relevant to an
agent-native OS). Declared via
`api/scripts/oneshot/adr486_declare_first_hub.py --apply` through
`write_revision` (revision `5236ff54-84cc-4e31-a45b-cc2beca60d03`). Code
deployed on the scheduler cron at 05:29:49Z (deploy `dep-d9hfg7f15fvs73fd5ocg`,
commit `a301425`).

## Expected vs observed

| # | Expected | Observed | Receipt |
|---|---|---|---|
| 1 | First tick discovers + materializes + fires the hub | 05:30:58Z tick: LIKE scan → `kind='radar'` row → CAS claim → sweep, no manual trigger | scheduler logs 05:30:58–05:31:24Z |
| 2 | Intake retains raws + distills the signal | 2 observation raws (`inbound/web/{hn-front,simonwillison}/2026-07-24T053058Z.xml`, `revision_kind='observation'`) + `_watch_signal.yaml` | `workspace_file_versions` rows |
| 3 | One bounded derive lands a cited brief | Brief rev `353e8c5d-dd27-4d44-80c6-3e6af69f6fa8`, `revision_kind='derivation'`, `authored_by='system:radar'`, `derived_from=[signal, raw, raw]`, embedded. Content: on-steer, every claim linked to a signal entry, "Watching:" tail | ledger row + brief at `operation/ai-frontier/briefs/2026-07-24-runaway-ai-agent-incident-….md` |
| 4 | Both sweep phases metered on the one ledger | **FAILED first run** — `funnel_decision='radar'` violated `execution_events_funnel_decision_check`; both rows dropped loudly (`LEDGER-DROP`, $0.019 unrecorded) | scheduler error logs 05:31:00Z + 05:31:24Z |
| 5 | (After migration 222 + re-arm) meter rows land; empty sweep honest | 05:36Z sweep: `radar-sweep` mechanical/success + `radar-brief` judgment/**skipped**/`no_brief` ($0.010758) — the model correctly judged nothing changed in 5 minutes and returned `NO_BRIEF` | `execution_events` rows `05:36:28` + `05:36:37Z` |

## Findings

1. **The standing loop works end-to-end on the real cron** — declaration →
   scheduled fire → intake → derive → placed cited brief → embed → meter, with
   nobody present. The ADR-401-Phase-3-shaped gap ("no derive has ever fired
   unaddressed") is closed.
2. **Defect found + fixed in-run**: the `funnel_decision` check constraint
   predated lane markers beyond `'capture'` — the meter rows dropped while the
   substrate writes succeeded (exactly the failure the `LEDGER-DROP` log line
   exists to surface). Migration 222 extends the vocabulary; the 05:36Z sweep
   re-proved both rows land. One-ledger invariant restored.
3. **The NO_BRIEF path is real, not theoretical**: the second sweep produced
   the honest empty — metered as `skipped/no_brief`, nothing written, nothing
   embedded. Falsifier 4 (sweep→brief yield) reads directly off these rows.
4. **Adjacent latent bug**: the recurrence-side scheduling-index materializer
   would have deleted any non-judgment (`capture`/`radar`) index row as stale —
   the ADR-393 kind-disjointness invariant existed only on the capture side.
   Fixed in the same slice (`kind='judgment'` filters), gated.
5. **Manual re-arm lesson**: bumping `next_run_at` alone is clobbered by the
   per-tick materializer (it recomputes from the declaration + `last_run_at`).
   A manual re-fire needs `last_run_at=NULL` too (re-triggering
   `fire_on_activation`). Correct behavior — declarations stay authoritative —
   but worth knowing for future evals.

**Recommendation carried forward**: none blocking. The R2 FE mount (hub-typed
folder view in the Files viewer) waits on the projection layer settling +
D7's R3 unveil discipline. Falsifier window (D8) opens from today's baseline:
1 hub · 1 brief · 1 honest empty.
