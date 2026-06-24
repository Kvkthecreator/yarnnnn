# FINDING — the reflection-loop continuity eval, and the two kernel bugs it surfaced

**Date**: 2026-06-24. **Hat**: B (eval authoring) that surfaced two Hat-A kernel faults; both fixed + validated same session. **Workspace**: funded yarnnn-author `U=0b7a852d-4a67-447d-91d9-2ba1145a60d7` ($58 balance).

---

## One-paragraph state

Authoring the FIRST real Concern-2 eval — the ADR-364 reflection-loop continuity eval — surfaced that the reflection loop **could never have fired in production**, blocked by two independent plumbing faults, neither of which a judgment read would have caught (they'd have read as "the agent never reflected" — a MIND mystery dressed over an architecture bug, the exact §0 trap). The offline structural probe (FREE, no LLM) caught both as deterministic FAILs before any spend. Both fixed, guarded by a 10/10 regression test, and the loop then validated end-to-end on a funded wake: the Reviewer authored an honest `reflection.md` naming its own attested −$18.42 loss as *"the call was wrong."*

## The eval (the headline deliverable)

The reflection-loop continuity eval tests the substrate ADR-364 closed: a wake reasons from its *closed track record* — a `judgment_log` verdict (carrying a `proposal_id`) joined to the attested ground-truth outcome it produced (same `proposal_id`, the D1 keystone FK). Three artifacts:

- **`api/scripts/operator/probe_reflection_loop_local.py`** — the structural instrument. Phase 1 (FREE): seed a joinable verdict↔outcome pair, assert the gap-fact renders + names the value + attestation, and a negative-control verdict (no matching outcome) is silent. Phase 2 (FUNDED): fire a judgment wake, assert `reflection.md` is authored this cycle naming the seeded outcome.
- **`docs/evaluations/scenarios/author-reflection-loop-continuity.yaml`** — the judgment-half scenario (seeds via `write_substrate`, fires `corpus-coherence-check`, captures).
- **`yarnnn-author-judgment.yaml` `reflection-loop-continuity`** + **EVAL-SUITE-DISCIPLINE §2.4 reflection-coherence read** — the §2.4 honest-naming judgment read, with the attestation floor as the testable (a reflection that dodges naming an attested loss is the detectable failure).

**Snapshot/restore harness (discourse §2a): DEFERRED.** The seeded continuity eval needs only the existing `write_substrate`/`delete_substrate` harness primitives; the full snapshot/restore machinery earns its place only for *accumulating* mode (the deferred Inspector tenure eval, ADR-364 D5). Structure-after-evidence — don't build the accumulating-mode instrument before the seeded gate has run.

## The two kernel bugs (Hat-A, surfaced by the offline probe)

### Bug 1 — `bundles_active_for_workspace` dropped activated-but-connection-gated bundles
`api/services/bundle_reader.py`. An operator-activated bundle (MANDATE.md slug marker) only resolved as active-for-workspace if it was *fully* connection-less (`if not required_platforms`). **ADR-353 §15a (commit `0c1dcca`) added `requires_connection: reddit` capabilities to alpha-author**, silently flipping it from connection-less to platform-bound — so an *activated* author workspace without a reddit connection resolved to **0 active bundles**, and `get_ground_truth_for_workspace` returned `None`. On the live funded workspace this meant **none** of alpha-author's program substrate_abi (ground-truth, corpus_signal, the reflection gap-fact) reached the Reviewer's envelope — a silent production hole, not just a test artifact.

**Fix**: the activated-slug marker is an activation signal *independent* of capability connection-gating — connections gate *which capabilities work*, not whether the activated program's substrate_abi resolves. The activated-slug check now precedes the platform-bound path. The cockpit-chrome inference (a connected-but-unactivated platform bundle still resolves via its connection) is preserved. `test_adr225_compositor.py` 10/10, `test_adr297_phase1.py` 7/7, `test_client_lifecycle.py` 12/12 all green.

### Bug 2 — `_reflection_gap_fact` queried the bare path, missing every row
`api/services/reviewer_envelope.py`. `workspace_files` store the `/workspace/`-prefixed path; the path *constants* are bare. The `_UNIVERSAL_ENVELOPE_DECLS` reads go through a `_read()` helper that prepends the prefix — but the ADR-364 D2 `_reflection_gap_fact` helper's two bespoke reads queried the **bare** constants (`.eq("path", PERSONA_JUDGMENT_LOG_PATH)` / `.eq("path", gt_path)`), so both lookups missed every row. The gap-fact silently returned `""` and **the loop never fired in production**, present since the D2 helper shipped (`c7f1f60`).

**Fix**: a `_full()` local prepends `/workspace/` to both query paths (mirroring `_read()`). The gap-fact now joins.

## Funded validation (the first real reflection-loop close)

Phase 2 fired one judgment wake (cost $0.33, 2620 out / 115891 in — governance cached per `66a9090`). The Reviewer authored `persona/reflection.md` (head `1df9155f`, 4985 chars) this cycle, titled a section **"Honest assessment: the call was wrong,"** named the exact `−18.42` attested outcome, and connected the loss to the specific soft anti-slop signal it had dismissed in the seeded verdict. The §2.4 reflection-coherence read passes: fed an un-fakeable attested loss, the agent named the failure honestly rather than self-flattering. This is the **first observation of the reflection loop closing** — the substrate Concern 2's continuity eval was always meant to test, now demonstrated.

## Discipline notes

- **Cheaper-measurement-first paid off exactly as designed**: the FREE offline probe caught two production bugs before a dollar of spend, and each would have masqueraded as a judgment outcome ("the agent never reflects") under a MIND-only read — the §0 architecture-vs-judgment trap, avoided.
- **Probe-before-canon**: both fixes are guarded by deterministic regression checks (`test_adr364_reflection_loop_kernel.py` 10/10), not asserted on assumption.
- **Two-hats crossover**: the eval (Hat-B) surfaced the finding; the fix landed Hat-A. Committed as two commits — the kernel fixes + regression test (Hat-A), the eval instrument + discipline (Hat-B) — so the fix is separable from the instrument that found it.

## Deferred (non-blocking, carried forward)

- **`back-office-reviewer-calibration` task retirement** (ADR-364 §7) — the OLD aggregate-windows mechanism, distinct from the per-verdict reflection loop. Still untouched this session.
- **Snapshot/restore harness** (discourse §2a) — deferred until accumulating-mode evals (Inspector tenure, ADR-364 D5) are pulled.
- **ADR-209 phase2 pre-existing test debt** (stale `task_workspace`/`DECISIONS_PATH` refs) — unrelated.
