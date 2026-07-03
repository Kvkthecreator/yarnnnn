# Eval-suite index — status registry (2026-07-03)

The singular declaration of which Suite-B manifests are **current** vs
**dormant**. The evaluation subject moved with the activation ladder
(ADR-380/381/383): the launch-path agent is **Freddie, the Rung-1 substrate
steward**; the trader/author programs are **Rung-2** persona-agent dogfood —
off the critical path, kept for the exogenous track-record clock, NOT deleted
(their theses remain valid for program workspaces when Rung 2 resumes).

| suite | subject | status |
|---|---|---|
| `freddie-bare-workspace-steward.yaml` | Freddie (Rung 1, bare workspace, steward defaults) | **CURRENT** — the launch-path behavioral suite. Latest run: [`../2026-07-03-freddie-bare-steward-sonnet-rerun/`](../2026-07-03-freddie-bare-steward-sonnet-rerun/FINDING.md) |
| `alpha-trader-autonomous-loop.yaml` (+ `.criterion.md`) | alpha-trader program | dormant (Rung 2) |
| `alpha-trader-readiness-gap.yaml` | alpha-trader program | dormant (Rung 2) |
| `alpha-trader-stewardship.yaml` | alpha-trader program | dormant (Rung 2) |
| `author-expected-output-origination.yaml` | alpha-author program | dormant (Rung 2) |
| `author-heartbeat-composes.yaml` | alpha-author program | dormant (Rung 2) |
| `author-unified-agent-composes.yaml` | alpha-author program | dormant (Rung 2) |
| `yarnnn-author-judgment.yaml` | alpha-author program | dormant (Rung 2) |
| `yarnnn-author-responsiveness.yaml` | alpha-author program | dormant (Rung 2) |

Related instruments (probes, not YAML suites — see `../README.md` §Current
instruments): the 6-ask addressed probe (`probe_freddie_addressed_baseline.py`,
canonical baseline declared in code as `CURRENT_BASELINE`) and the bare-steward
wake probe (`probe_freddie_bare_steward.py`, the firing instrument for the
CURRENT suite above).

Vocabulary note: older manifests + EVAL-SUITE-DISCIPLINE.md say "Reviewer" —
per ADR-381 D1 that is the internal seat slug (relabel-keep-slug); the
operator-facing label is Freddie. Dormant ≠ deprecated: a dormant suite is
re-armed by activating its program on a rig workspace, unchanged.
