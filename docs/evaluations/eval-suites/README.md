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

| suite | subject | kind | status |
|---|---|---|---|
| `freddie-bare-workspace-steward.yaml` | Freddie (Rung 1, bare workspace, steward defaults) | `thesis` | **current** — the launch-path suite. Repaired 2026-07-31 (persona `bare-kernel`; supported `absent:` program-marker asserts); pre-flight verified live 4/4. Latest full run: [`../2026-07-03-freddie-bare-steward-sonnet-rerun/`](../2026-07-03-freddie-bare-steward-sonnet-rerun/FINDING.md) |
| `settings-surfaces-click-pass.yaml` | the two settings doors, owner × member | `browser` | **current** — registered 2026-07-31, not yet run. Portable form: [`../OPERATOR-PACKET-settings-click-pass.md`](../OPERATOR-PACKET-settings-click-pass.md) |
| `studio-editing-click-pass.yaml` | the Studio editing surface, `document` × `deck` | `browser` | **current** — registered 2026-07-31, **not yet run** (browser tools were not present in the authoring session; they freeze at session start). Covers the interaction-polish pass (`4318904`), the ADR-509 insert re-cut (`817eecd`), the colour swatch row (`f5a9515`) and the four interaction debts (`9c79a57`) — every one of which is keyboard/scroll/focus-shaped and therefore invisible to a static gate. Baseline receipts EXECUTED against prod before registration. |

## The two suite kinds

`suite_kind: thesis` is Suite B — fired by `run_eval_suite.py` against a persona
workspace, read as a forensic trace. `suite_kind: browser` is the **E2E
human-parity lane** (VERIFICATION.md): a click-pass manifest driven by a BROWSER
principal, never by the LLM runner. The separation is gate-asserted
(`test_llm_runner_refuses_browser_suites`) — `VALID_SUITE_KINDS` in the runner
stays `{"thesis"}`, because firing a click-path as a wake would silently produce
a thesis read of a suite that has no scenario.

The "exactly one current suite" rule governs the **thesis** registry only; a
current browser manifest does not contend for that slot (different firing
instrument, different failure mode).

A browser manifest's load-bearing field is per-step `mutates:` — any step that
changes state MUST carry a `receipt:` (the substrate query proving it) and a
`restore:` (how the change is reversed). The gate enumerates those steps and
names the specific one that is missing a receipt; a browser pass without one is
narrative, not evidence.

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
