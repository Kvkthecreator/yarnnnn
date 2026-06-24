# ADR-360 — A Wake Is a Pre-Authored Ask (The Ask Re-Founding of the Wake Layer)

> **Status**: **Proposed** 2026-06-24 — gated on the build-validation probe (a clock-delivered imperative composes from an empty corpus through the faithful `cron_tick` path). Canon flips to **Implemented** only after the probe passes against the real implementation. The spine + clock-delivery are **already receipt-backed** (see Driving evidence); this ADR proceeds because the cause is proven structural, not because a theory is plausible.
> **Date**: 2026-06-24
> **Authors**: KVK, Claude
> **Supersedes**: [ADR-359](ADR-359-the-occasion-of-work-wake-shape.md) (**Proposed**, never Implemented). ADR-359 correctly located the cause as structural (owed-output un-computed, inaction privileged, do-wake pre-classified as maintenance) but delivered the fix as a *computed header among twenty in a maintenance frame* + an occasion-nudge + a `non_performance` verdict. The spine probe proved the deeper move: deliver the obligation as a present-tense **ask**, and the header/nudge/verdict machinery is unnecessary (it never fired; production happened on the ask alone). ADR-359's `_compute_occasion_fact` survives as the ask-builder's *input*; its D2/D3 machinery is retired.
> **Amends**: [ADR-318](ADR-318-agentic-wake-posture.md) (a wake is a situation, not a task — survives; gains the now/later tense axis ADR-359 proposed, now delivered structurally not as prose), the wake-source taxonomy (ADR-296 v2 — collapses to one ask + provenance + timing), the persona-frame cycle-close contract (`reviewer_agent.py::_compute_minimal_frame`), the silent-exit recovery default (`reviewer_agent.py` dispatcher).
> **Builds on**: ADR-209 (Authored Substrate — `authored_by` becomes the ask's provenance field), ADR-296 v2 (wake architecture — the 5 firing detectors survive as plumbing), ADR-298 (wake queue — already the message queue), ADR-307/352 (consequential gate — reads provenance), ADR-327 (budget — gates later-delivery), ADR-335 (perception field — events raise asks).
> **Foundation docs**: `docs/analysis/the-wake-is-a-pre-authored-ask-2026-06-24.md` (the spine — WHY), `docs/analysis/the-ask-framework-collapse-2026-06-24.md` (the framework — WHAT), `docs/analysis/spine-blast-radius-2026-06-24.md` (the change surface — HOW MUCH). The CC benchmark: `docs/analysis/src_claudeCC/`.
> **Driving evidence (receipts)**: `docs/evaluations/2026-06-24-spine-present-tense-ask-VALIDATION.md` (the ask composes via addressed path), `docs/evaluations/2026-06-24-step3-cron-imperative-VALIDATION.md` (the **clock-delivered** stored imperative composes from empty corpus, no operator present, nudge inert — the autonomy claim). Both single-variable against the 6-probe falsification trail.
> **Honors**: ADR-306 / DP22 (anti-rebloat — this is net-SUBTRACTIVE; it deletes more than it adds, moving load out of prose into the ask's shape), Singular Implementation (one answer to "how does the obligation reach the agent").

---

## 1. Problem statement

A left-alone author agent (netflix-script-author: funded, autonomous, declared weekly scene, empty corpus) **never composed a scene** across six probes (frame/occupant → task-label → heartbeat → prompt-unification → occasion-frame-prose → ADR-359's computed header). Each fix was one layer deeper; all failed at the prose layer. The cause, proven structural: **the wake delivered the obligation as standing state the agent classified itself into caring about** ("assess the operation against its mandate") — and the agent classified it as maintenance and deferred ("routine heartbeat, awaiting production as planned").

The Claude Code benchmark (the extracted source at `docs/analysis/src_claudeCC/`) makes the cause legible: CC composes for millions of use cases because **every turn carries a live present-tense ask** (the user message). CC has no wake-taxonomy, no terminal-move contract, no recovery synthesizer — it infers from a live ask against a world that answers, and stops on silence. YARNNN's reason to exist is to run in the operator's *absence*, so it cannot carry a live request — and to substitute, it grew prosthetics (a ~20-section envelope, a verdict-as-terminal-move, a recovery synthesizer that fabricates `stand_down`) that **simulate a present principal**. Those prosthetics are the complexity, and the maintenance-classification they enable is the failure.

## 2. Decision

**A YARNNN wake is a user message the operator pre-authored and the world delivers on their behalf. The substrate's job is to make the obligation ARRIVE as a present-tense ask — an imperative — not as standing state the agent must classify itself into caring about.** Three decisions.

### D1 — The ask is the unit; provenance and timing are its only axes

The wake-source taxonomy (ADR-296 v2: `cron_tick | addressed | proposal_arrival | substrate_event | manual_fire`) collapses to **one unit and one axis**:

- **The ask** — an imperative + `authored_by` provenance (the ADR-209 taxonomy: `operator | agent-self | world:{event} | foreign:{actor}`).
- **Delivery timing** — *now* (a **message**: operator typed it / the world raised it; presence-warranted) or *later* (a **scheduled** ask: a clock holds and delivers it verbatim, optionally re-enqueuing on a cadence; budget-gated).

The five firing detectors **survive as plumbing** (a cron tick, a substrate diff, an SSE turn still *detect* that an ask is due) but stop being a semantic taxonomy the agent reasons over. The agent receives the ask and its provenance; "which of five sources" is internal. A **recurrence** stops being a distinct concept: it is *a scheduled ask that re-enqueues on a cadence* — a standing imperative + a schedule, indistinguishable from a todo with a due date. The program-agnostic janitorial asks (daily-digest, weekly-cleanup) and a program's owed-output asks (the weekly scene) sit in one list, same shape.

### D2 — The ask-builder: owed-output is delivered as an imperative, not framing

For cadence-fired owed-output (the case with no external event to raise the ask — the author's weekly scene), the schedule must fire **an imperative**, not a stored situation-framing prompt. An **ask-builder** composes the imperative at fire-time from: the owed-output contract (`_expected_output.yaml`), the computed occasion fact (ADR-359's `_compute_occasion_fact`, **repurposed as the builder's input, not a header**), and the produced-vs-owed gap. The schedule says *when*; the ask-builder says *what is being asked*, and it **asks** ("compose this week's scene now") rather than **frames** ("assess the operation"). **The discipline**: a scheduled ask must be an imperative at *authoring* time, because the clock cannot reason — it delivers verbatim.

### D3 — The loop terminates on the ask, not on a verdict contract; inaction stops being privileged

The terminal-move contract ("close every cycle with a verdict or a standing_intent write") and the recovery synthesizer (fabricates `stand_down`/`non_performance` on silent exit) are the mechanisms that privilege inaction — the structural cause #2 the falsification trail isolated. Under the ask:

- A cycle closes by **answering the ask** (producing the owed artifact, firing the warranted action, or — legitimately — naming why it cannot). The agent stops when the ask is answered (CC-style).
- An **unanswered owed ask is visible AS unanswered** — it persists / re-fires — not laundered into a fabricated clean close. `standing_intent` survives as a *useful optional artifact* (what I watched, why I'm waiting), not a *required terminal move*.
- The verdict surface **shrinks to consequential verdicts** (`approve | reject | defer` for proposals/actions). `stand_down` / `non_performance` (ADR-359 D2) are retired: "did nothing on an owed ask" is the unanswered-ask state, visible without a verdict.

### D4 — What survives, untouched (scope guard)

- **Provenance** survives as `authored_by` on the ask — read by the consequential gate (ADR-307/352) for trust. "Operator asked" ≠ "I scheduled myself" ≠ "a foreign write proposed." One field, not five code paths.
- **The budget gate** (ADR-327) survives, gating **later-delivery only** (nobody present to authorize the spend) — exactly where `budget.py` already gates (cron skips on exhaustion; message/reactive warn-but-fire). The model predicts the existing gating.
- **The consequential gate, ground-truth calibration, authored substrate, primitives-as-tools, the wake queue/drainer, mechanical `track-*` intake, reactive hooks** — all untouched. The moat's independence sources (gate + ground-truth, per `judgment-execution-unification.md` §3) are unchanged. This ADR changes *how work is originated*, not *how consequential acts are bound*.
- **Does NOT** add a parallel production pipeline, a `mode: production` recurrence, or a self-reviewing second agent. One agent, ask-shaped wakes.

## 3. FOUNDATIONS impact — Derived Principle 32 (replaces ADR-359's DP32)

**Derived Principle 32: A wake is a pre-authored ask.** Every wake delivers an *imperative* (present-tense, the-wake-is-about-this) tagged with *provenance* (`authored_by`), at one of two *timings*: now (a message, presence-warranted) or later (scheduled, budget-gated, clock-delivered verbatim). The agent answers the ask and stops; an unanswered owed ask is visible as unanswered, never a fabricated clean close. A scheduled ask must be an imperative at authoring time — the clock cannot reason. Composes with DP30 (the standing obligation — the owed-output the ask-builder turns into an imperative), DP24/ADR-343 (the floor never moves to answer an ask), DP22 (net-subtractive: load moves out of prose into the ask's shape). Supersedes ADR-359's DP32 (occasion-as-computed-header); amends ADR-318 (a wake is a situation → a situation read as a present-tense ask, in tenses, LATER earned from IS).

## 4. Implementation sequence (each stage gated; probe-before-canon)

1. **Stage 1** — revert the ADR-359 uncommitted edits; preserve `_compute_occasion_fact` as a standalone helper (the ask-builder's input). [Drops the occasion-nudge + `non_performance` verdict + envelope-header ordering; keeps the computation.]
2. **Stage 2** — build the ask-builder (`reviewer_envelope` or a sibling): owed-output contract + occasion fact + gap → an imperative ask string.
3. **Stage 3** — wire `cron_tick` judgment-recurrence fire (`wake.py::fire_recurrence`) to deliver the ask-builder's imperative for owed-output recurrences (in place of the stored framing prompt). **Validation probe**: a clock-delivered imperative composes from empty corpus through the faithful `cron_tick` path, no operator present. (Already receipt-backed at the prompt level — `step3-cron-imperative-VALIDATION.md`; Stage 3 proves it through the *production* code path, not a probe-injected prompt.)
4. **Stage 4** — shrink `reviewer_agent.py`: retire the recovery synthesizer + terminal-move contract; loop terminates on the answered ask. **IMPLEMENTED 2026-06-24** (per operator decision to proceed ahead of the E2E gate). The silent-exit recovery net (−238 LOC: `_looks_like_verdict`, the verdict-in-prose nudge, `_dispatcher_write_silent_exit_standing_intent`, `_synthesize_silent_exit_verdict`, both call sites) is deleted; a no-tool-call / budget-exhausted exit now `return None` → the caller's existing `wake.py` SILENT-WAKE path records a visible `failed` execution_event + material "produced no judgment" narrative (the "unanswered ask is visible AS unanswered" mechanism already existed — deletion is observability-neutral, not a regression: it replaces a fabricated `stand_down` with an honest `failed`). Frame close-contract rewritten to "answer the ask, ReturnVerdict closes; silence is a fault not a stand-down". `stand_down` retained as a model-authored verdict. Obsolete ADR-303 recovery tests deleted. CHANGELOG `[2026.06.24.2]`. **Note**: the §5 full-loop E2E remains the gate for flipping the ADR Proposed→Implemented — Stage 4's code shipped on the operator's call, but the ADR stays Proposed until the E2E composes.
5. **Test gates** — reviewer / wake / budget suites green; no regression on the trader (whose event-raised asks already work).
6. **Canon cascade** (gated on high validation) — FOUNDATIONS DP32 + ADR-318 amendment + persona-frame + `api/prompts/CHANGELOG.md` + occupant-contract doc. Doc-first amendments **after** code proves out.

## 5. Validation gate (Proposed → Implemented)

Re-run the author probe through the **production** `cron_tick` path (not a probe-injected context): an owed-output recurrence, empty corpus, autonomous, no operator. **PASS**: a `content.md` with real prose composed in-cycle via the ask-builder's imperative, `reviewer:*` attributed; AND a silent/unanswered owed ask is visible as unanswered (not a fabricated `stand_down`). **FAIL**: deferral / framing-classification reproduced → the production wiring is incomplete; revert, learn, do not flip canon. Receipts: `execution_events` + `workspace_file_versions` queried directly.

## 6. Reversibility

Every stage is revertible; the ADR flips to Implemented only after Stage 3's production-path probe composes and the test gates are green. Until then this is a Proposed re-founding with a falsifiable gate — the discipline that killed six prior theories at near-zero canon cost. The blast radius is net-subtractive (~6,500 LOC survives; the change is concentrated deletion in `reviewer_agent.py` + one small ask-builder), so a revert is a clean `git checkout` of a bounded set.
