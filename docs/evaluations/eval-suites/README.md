# Eval-suite index — status registry (re-cut 2026-07-31)

The singular declaration of Suite-B manifest status. **`status:` is now a
machine-readable field in each manifest** (2026-07-31 eval-layer audit) and is
gate-checked by `api/test_eval_suite_gate.py`; this table is the human view of
the same fact. The runner refuses `status: superseded` at load; a `dormant`
suite loads but its `requires:` pre-flight refuses honestly until the named
migrations land.

Audit context: the layer sat one commit deep from 2026-07-03 through four canon
waves (ADR-366 governance→contract, ADR-393 mode deletion, ADR-402/403 envelope
collapse, ADR-414 judgment re-homing) — at audit time **zero of nine suites
could fire through `run_eval_suite.py`**. Receipts:
[`../2026-07-31-eval-layer-audit-FINDING.md`](../2026-07-31-eval-layer-audit-FINDING.md).

| suite | subject | status |
|---|---|---|
| `freddie-bare-workspace-steward.yaml` | Freddie (Rung 1, bare workspace, steward defaults) | **current** — the launch-path suite. Repaired 2026-07-31 (persona `bare-kernel`; `absent:` program-marker asserts); pre-flight verified live 4/4. Latest full run: [`../2026-07-03-freddie-bare-steward-sonnet-rerun/`](../2026-07-03-freddie-bare-steward-sonnet-rerun/FINDING.md) |
| `alpha-trader-readiness-gap.yaml` | alpha-trader program | dormant — needs a live hire grant + `requires:` re-point to `agents/{slug}/_autonomy.yaml` (ADR-414 D+E-2) |
| `alpha-trader-stewardship.yaml` | alpha-trader program | dormant — same two blockers |
| `yarnnn-author-judgment.yaml` | alpha-author program | dormant — three migrations owed: autonomy→`agents/{slug}/` (ADR-414) · `_preferences`→`contract/` (ADR-366) · reflection verdict-source→`action_proposals` (ADR-364 D2a) |
| `yarnnn-author-responsiveness.yaml` | alpha-author program | dormant — ADR-414 + ADR-366 path migrations owed (otherwise the healthiest manifest) |
| `author-unified-agent-composes.yaml` | alpha-author program | dormant — one-shot prove-before-canon gate; its canon question was decided by ADR-355/ADR-365b; historical value only |
| `alpha-trader-autonomous-loop.yaml` (+ `.criterion.md`) | alpha-trader program | **superseded** — zero live hire grants (ADR-414 D+E-1 backfill: 13 workspaces, 0 minted); cites deleted `mode: judgment` + nonexistent `REVIEWER_PRIMITIVES`. Re-cut at re-hire, don't re-arm |
| `author-expected-output-origination.yaml` | alpha-author program | **superseded** — its single variable (`governance/_expected_output.yaml`) migrated twice (ADR-366 → `contract/`, ADR-414 → `agents/{slug}/`); it would seed a file nothing reads |
| `author-heartbeat-composes.yaml` | alpha-author program | **superseded** — thesis fired and FALSIFIED 2026-06-23; `author-unified-agent-composes` superseded it explicitly |

Related instruments (probes, not YAML suites — held by
`api/test_probe_staleness_gate.py` since 2026-07-31): the 6-ask addressed probe
(`probe_freddie_addressed_baseline.py`, canonical baseline declared in code as
`CURRENT_BASELINE`) and the bare-steward wake probe
(`probe_freddie_bare_steward.py`, the firing instrument for the CURRENT suite
above — per-condition three-halves read since 2026-07-31).

Vocabulary note: older manifests + EVAL-SUITE-DISCIPLINE.md say "Reviewer" —
per ADR-381 D1 that is the internal seat slug (relabel-keep-slug); the
operator-facing label is Freddie.

Dormant ≠ deprecated: a dormant suite is re-armed by activating its program on
a rig workspace **plus landing the migrations named in its status row** — the
2026-07-03 claim "unchanged" no longer holds post-ADR-414. Superseded ≠
deleted: the manifest stays as historical artifact; the runner refuses it.
