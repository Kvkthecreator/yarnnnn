# Eval-suite index — status registry (re-cut 2026-07-31, retirement executed same day)

`status:` is a machine-readable field in each manifest, gate-checked by
`api/test_eval_suite_gate.py` (persona resolves, scenarios exist, `requires:`
operators supported, exactly one `current` suite). The runner refuses
`status: superseded` at load.

**One suite is live. Eight were retired and deleted 2026-07-31**
(operator-directed — the codebase evolved past the dormant-program approach
through ADR-366/393/402/403/414 while the layer sat untouched from
2026-07-03). Their setups, thesis-verdict states, and re-cut guidance live in
[`RETIRED-SUITES.md`](RETIRED-SUITES.md); the full manifests are retrievable
via `git show 90c7d67:docs/evaluations/eval-suites/<name>.yaml`. Audit
receipts: [`../2026-07-31-eval-layer-audit-FINDING.md`](../2026-07-31-eval-layer-audit-FINDING.md).

| suite | subject | status |
|---|---|---|
| `freddie-bare-workspace-steward.yaml` | Freddie (Rung 1, bare workspace, steward defaults) | **current** — the launch-path suite. Repaired 2026-07-31 (persona `bare-kernel`; supported `absent:` program-marker asserts); pre-flight verified live 4/4. Latest full run: [`../2026-07-03-freddie-bare-steward-sonnet-rerun/`](../2026-07-03-freddie-bare-steward-sonnet-rerun/FINDING.md) |

Related instruments (probes, not YAML suites — held by
`api/test_probe_staleness_gate.py`): the 6-ask addressed probe
(`probe_freddie_addressed_baseline.py`, canonical baseline declared in code as
`CURRENT_BASELINE`) and the bare-steward wake probe
(`probe_freddie_bare_steward.py`, the firing instrument for the CURRENT suite —
per-condition three-halves read since 2026-07-31).

When a program re-hires (the ADR-414 owed operator decision), new suites are
**re-cut from the theses recorded in RETIRED-SUITES.md against the
then-current substrate** — `agents/{slug}/` judgment homes, `contract/`
consumables, `action_proposals` verdict-of-record — not re-armed from the
deleted manifests. Start with the readiness-gap thesis (most portable) and the
yarnnn-author-judgment 7-eval shape (closest to a behavioral regression
suite); copy the responsiveness suite's ordered-arc mechanism for anything
accumulating.
