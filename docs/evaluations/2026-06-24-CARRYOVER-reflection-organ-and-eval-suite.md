# CARRY-OVER — reflection organ shipped; next: eval-suite update for the new envelope + recent ADRs

**Date**: 2026-06-24. **For**: the next session. **Hat**: B (eval) primarily, with Hat-A follow-ups noted.

---

## Where we are (all on `main`, pushed)

The **three-concern split** (context → eval → self-improvement) is now substantively reframed and partly built:

- **Concern 1 — context handling: SETTLED.** [ADR-363](../adr/ADR-363-wake-context-handling.md) Accepted. D1 ratified (cross-wake filesystem-as-memory, re-derived), D2/D6 rejected, **D5 resolved from cadence data** (keep 5-min TTL — wakes too sparse for 1h to pay; cache value is intra-wake), **D3 wired-but-dormant** (`YARNNN_CONTEXT_EDIT` off by default — the funded keep-sweep was clean on safety, inconclusive on cost; premise thin). D4 deferred behind D3.
- **The reframe (this session's core finding): the missing primitive was the dropped `proposal_id` join key, not a new file or a new seat.** [ADR-364](../adr/ADR-364-the-reflection-organ.md) Accepted + **fully built**:
  - **D1 keystone** (`c...`): `ledger.py` persists `proposal_id` on the outcome event — the FK that joins an outcome back to the verdict that caused it (was silently dropped). The loop is now closeable.
  - **D2 gap-fact** (`c7f1f60`): `reviewer_envelope._reflection_gap_fact` — a DP19-clean bounded read-and-present (joins judgment_log verdicts to ground-truth outcomes by `proposal_id`, presents raw rows; the kernel presents, the LLM judges). Wired into `ReviewerContext.reflection_gap_fact` → volatile-suffix render.
  - **D3 reflection.md** — Reviewer authors `persona/reflection.md` (its interpreted learning over an attested outcome it can't fake). Render header + one DP22-minimal close-contract sentence.
  - **D4** — `calibration.md` → `reflection.md` across all live sites; the cross-class reconciler→calibration write retired (topology simplification).
  - This makes FOUNDATIONS Axiom 2's **"Reviewer develops through reflection" REAL** (substrate-backed), closing the open loop `persona-reflection.md`'s own §1.5 audit finding flagged.
  - **ADR-361 (cited_rules) + ADR-362 (Inspector seat) → deferred-conditional** (pulled only if the basic reflection loop proves it needs the rule dimension / an independent vantage).

**Gates green**: ADR-286 single-writer 8/8, ADR-330 ground-truth-intake 17/17. Pre-existing reds (ADR-209 phase2: stale `task_workspace`/`DECISIONS_PATH` refs from ADR-231/281 renames) are unrelated debt.

---

## Deferred Hat-A (small, scoped — do when convenient, NOT blocking eval)

1. **`back-office-reviewer-calibration` task retirement.** The *old aggregate-windows mechanism* (per-occupant × verdict rolling windows, machine-rebuilt) is distinct from the new per-verdict reflection loop and was left running. Its output (`calibration.md`) no longer has a seeded home. Retire the task + rewrite the persona-prompt calibration-guidance text in `orchestration.py` (lines ~600/663/749/775 reference "calibration" in prompt prose). Scoped follow-up per ADR-364 §7.
2. **Pre-existing test debt** (optional): ADR-209 phase2 references deleted `services.task_workspace` + renamed `DECISIONS_PATH` — stale since ADR-231/281, unrelated to ADR-364. A cleanup pass, not urgent.

---

## NEXT SESSION OBJECTIVE — eval-suite update for the updated prompt envelope + recent ADRs

The wake envelope and persona substrate have changed materially across this arc; the eval suite must catch up. **Canon**: [`EVAL-SUITE-DISCIPLINE.md`](EVAL-SUITE-DISCIPLINE.md); suites live in `docs/evaluations/eval-suites/`; funded probes in `api/scripts/operator/probe_*.py`.

### What changed that the eval suite doesn't yet cover

1. **The reflection loop (ADR-364) — the headline new eval.** This is the substrate **Concern 2's continuity eval** was always meant to test, and now it's real. The eval claim, sharpened:
   - **Seeded continuity**: seed `judgment_log` with a verdict (carrying a `proposal_id`) + the matching outcome event (same `proposal_id`, an attested value) in the ground-truth file → fire a wake → assert the **gap-fact renders** AND the Reviewer **authors `reflection.md` referencing that specific outcome** (its call worked/didn't). The DELTA vs a control with no joinable pair is the continuity signal.
   - **The honest assertion** (avoid the D3 trap — don't grade on fuzzy prose): assert structurally — does `reflection_gap_fact` populate (the join fired)? does `persona/reflection.md` get written this cycle? does its content name the seeded outcome? Not "the prose feels reflective."
   - **The funded probe to model on**: `probe_governance_cache_local.py` / `probe_envelope_collapse_local.py` (the latter already seeds + resets persona files — note its reset now wipes `reflection.md`, ADR-364 D4). Funded yarnnn-author `U=0b7a852d-4a67-447d-91d9-2ba1145a60d7`.
   - **The snapshot/restore harness** (discourse doc §2a) is still UNBUILT — the current reset is one-way destructive. Concern 2's *seeded* + *accumulating* modes want `snapshot_persona`/`restore_persona`. Decide whether to build it now (it makes the reflection eval clean + reusable) or seed-and-wipe manually first. Pure Hat-B, no kernel change.

2. **The new envelope shape** the eval prompts assert against:
   - `reflection_gap_fact` is now a volatile-suffix envelope key (ADR-364 D2).
   - Governance-caching (`66a9090`) split the user message into cached-governance-prefix + volatile-suffix (ADR-363 era) — any eval asserting on the raw envelope string shape may be stale.
   - `occasion_fact` (ADR-359) and `expected_output` (ADR-345) are recent envelope additions.
   - Context-editing (`YARNNN_CONTEXT_EDIT`, ADR-363 D3) is a dormant env flag — evals run with it OFF (production default).

3. **Recent ADRs the suite should reflect** (verify coverage; add reads where missing): ADR-359 (occasion-of-work), ADR-360 (the wake as a present-tense ask — the agnostic-kernel behavioral gate), ADR-363 (context handling), ADR-364 (reflection organ). The `EVAL-SUITE-DISCIPLINE.md` MIND-axis reads (judgment-coherence §2.1, stewardship-coherence §2.3) may need a new **reflection-coherence** read: *given a seeded verdict↔outcome gap where the call demonstrably failed, does the agent's reflection.md name the failure honestly (vs self-flatter)?* — the honesty-floor the attestation makes testable.

### Suggested first moves next session

1. **Read** `EVAL-SUITE-DISCIPLINE.md` + the latest suite under `docs/evaluations/eval-suites/` to see current coverage + vocabulary.
2. **Decide** snapshot/restore harness: build now (recommended — it's the Concern-2 instrument and unblocks seeded+accumulating evals) or defer.
3. **Author the reflection-loop eval** (seeded continuity, structural assertions) — the first real Concern-2 eval, now that the substrate exists.
4. **Audit the suite** for envelope-shape drift (reflection_gap_fact / occasion_fact / expected_output / governance-cache split) and add the reflection-coherence MIND read.
5. Funded validation on yarnnn-author (`U=0b7a852d…`) only after the offline/structural assertions are in place (cheaper-measurement-first — the discipline that served us all arc).

### Discipline reminders (held all arc, keep holding)

- **Probe-before-canon**: don't promote anything on assumption; measure (or resolve from existing telemetry, the cheaper kind — D5 did that).
- **Stage files BY NAME** (the IR deck `.pptx` is another lane's WIP — never `git add -A`).
- **DP19**: the kernel presents substrate, never computes new analytical state at prompt-assembly. The gap-fact presents; the LLM judges.
- **DP22**: the persona frame carries only the model↔runtime interface; rules → principles.md, pedagogy → substrate. Keep reflection guidance minimal in the frame (the render header carries the substance).
- **Commit to `main`** (this arc does); gate on `tsc`/import-check, not full build.

---

## One-paragraph state, for fast re-grounding

Concern 1 (context) is settled (ADR-363). The deepest finding of the arc: the eval AND self-improvement both felt incomplete because the **intent→outcome loop was open — severed by one dropped `proposal_id` FK**, not by a bad file topology or a missing seat. ADR-364 closed it (keystone + gap-fact + Reviewer-authored `reflection.md`, calibration retired), demoting the Inspector seat + cited_rules to deferred-conditional. That reflection loop **is** the substrate Concern 2's continuity eval was always meant to test — so the next move is the eval-suite update: build the reflection-loop eval (seeded, structural assertions), decide the snapshot/restore harness, and catch the suite up to the new envelope shape + recent ADRs.
