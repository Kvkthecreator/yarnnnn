# Eval-suite redesign from first principles

**Date**: 2026-05-29
**Hat**: B (external developer surface — toolchain that probes the system)
**Status**: paper-design audit. Proposal that follows in the companion docs is **Proposed**, not Implemented. Operator review precedes any code/canon ship.
**Scope**: redesign of the eval-suite framework (`EVAL-SUITE-DISCIPLINE.md`, `yarnnn-author-baseline.yaml`, `run_eval_suite.py`, `operator_proxy/`). NO production-workspace runs. NO system-canon (`api/`, `web/`, `docs/adr/`, `docs/architecture/`, `docs/programs/`) edits.

> Read this doc first. It is my reasoning. The proposal docs (`EVAL-SUITE-DISCIPLINE.md` rewrite + suite migration + harness change-list) are downstream consequences of the purpose statement in §2(a). If the proposal doesn't follow from the purpose, it's shape-without-foundation — flag it.

---

## §0 The evidence the redesign rests on

Four `yarnnn-author-baseline` sessions exist. I read two in full (per the brief) and checked the state of the other two. The pattern across all four is the load-bearing finding of this audit, so I state it before any reasoning:

| Session | Commit | §2 tables | Headline / §3 / §4 prose | Operator verdict on the finding |
|---|---|---|---|---|
| `05-27-020446` | (abandoned) | 18 `TODO` cells, untouched | empty | abandoned — never interpreted |
| `05-27-064722` | `c51c44f` → reverted `2a6b83f` | **fully filled**, every cell scored, aggregates computed | confident, load-bearing | **misleading** — built on violated substrate preconditions; withdrawn |
| `05-28-023342` | (abandoned) | empty | empty | abandoned |
| `05-28-042356` | `d38130e` | **all `<!-- TODO -->`**, untouched | headline + §3 + §4 + §5 fully written, honest | **VALIDATED** — the run everyone trusts |

The two sessions that produced a usable judgment sit at **opposite ends of the table-fill axis**. The honest one (`d38130e`) left §2 entirely as `TODO` and let the prose carry the finding — its own Status line concedes: *"Per-eval `<!-- TODO -->` cells in §2 tables left for future-session per-eval qualitative read; the load-bearing finding ... is established without that per-eval detail."* The misleading one (`c51c44f`) filled every cell, computed aggregates ("6/9 PASS", "avg trace-completeness ≈ 0.66", "M6-DRIFT count: 2 — at the suite's declared ceiling"), and let those aggregates shape a headline that a substrate-precondition violation later invalidated.

**The artifact shape and the honesty of the finding are inversely correlated in the actual record.** That is not a coincidence to explain away — it is the diagnostic. The framework's emitted shape (a four-dimension table with `Pass?` cells and computed aggregates) is load-bearing for the *appearance* of a measurement and actively unhelpful for the *substance* of one. Everything below follows from taking that seriously.

---

## §2 First-principles audit (the brief's Step 2 questions, answered in plain language)

### (a) What IS an eval suite for a substrate-driven agent like the Reviewer? — one sentence, from scratch

> **An eval suite for the Reviewer is a way to put the Reviewer in a small number of known, operator-recognizable situations and let a human read what it did, so the human can answer one question: *would a domain editor who holds this mandate have reasoned the way the Reviewer reasoned?***

Three load-bearing words in that sentence, none of which the current framework's shape honors:

- **"read what it did"** — the unit of output is a *read*, not a *score*. The thing being produced is a human judgment formed from transcripts, not a cell filled from a rubric.
- **"would a domain editor ... have reasoned"** — the standard is *coherence with a held mandate*, not *match against a pre-declared expected cell*. A domain editor's right move in situation X is not knowable before you see situation X concretely; it's a judgment, not a lookup.
- **"a small number of known situations"** — the value is in the *situations being recognizable to the operator* (these are the moments that matter for shipping founder corpus), not in their count or their coverage of a taxonomy.

The current framework's purpose statement (`EVAL-SUITE-DISCIPLINE.md` §1) is: *"One eval-suite session produces one rollup artifact that scores the system across four orthogonal dimensions simultaneously, against pre-declared criteria."* That sentence has three commitments — **scores**, **four dimensions**, **pre-declared criteria** — and all three pull *away* from the first-principles purpose. "Scores" replaces "reads." "Four dimensions" replaces "mandate-coherence." "Pre-declared criteria" presumes the right answer is knowable before the situation is seen. The drift the brief names is not a failure of operator discipline; **it is the gap between these two purpose statements, made physical in the artifact shape.**

### (b) Substrate-receipts vs qualitative judgment — which is load-bearing, which is supporting?

This is the question that most needs separating, because the current framework conflates them and the README (correctly) does not.

- **Substrate-receipts are load-bearing for *trust*, not for *the finding*.** A receipt (revision_id, execution_event id, wake_queue dedup_key, reproducible SQL) is what lets a second reader verify that a claim in the finding is real — that the Reviewer *did* write to `judgment_log.md` at 04:25:24, that there *were* zero action_proposals, that the envelope *did* carry `_pace.yaml`. Receipts are the discipline against single-author optimism (`README.md` rule 2). They are necessary. They are not the finding.
- **The qualitative read is load-bearing for *the finding itself*.** "Would an editor have done this?" is answered by reading 3-4 transcripts and forming a judgment. No receipt produces that judgment; receipts only make the judgment *checkable*.

The relationship is: **the qualitative read is the claim; the substrate-receipt is the proof the claim is grounded in what actually happened.** Both are required, but they are different *kinds* of thing, and the current framework's table flattens them into the same row — putting a `Pass?` cell (which is a compressed judgment) next to a substrate-inputs cell (which is a receipt-pointer) as if they were peers. They are not. The judgment is the work; the receipt is the audit trail under the work.

`d38130e` got this right *by abandoning the table*: it put the qualitative read in prose (§1 + §3) and the receipts in §5 (the SQL queries + revision IDs), and never tried to compress the read into cells. `c51c44f` got it wrong by filling cells — the cells *looked* like receipts ("approve / judgment_log ✓") but were actually compressed judgments wearing receipt clothing, and the compression is exactly where the misleading headline crept in.

### (c) Does dimension-scoring serve qualitative-first, or invite the drift?

It invites the drift. Three specific mechanisms, each observable in the record:

1. **The `Pass?` column is a forced binary on a judgment that is not binary.** Mandate-coherence is "would an editor have reasoned this way" — a spectrum read, with texture ("right verdict, framework-internal reasoning, no mandate cite — defensible but not ideal"). A `Pass?` cell cannot hold texture. So the author either (a) leaves it `TODO` (the honest sessions) or (b) collapses the texture into PASS/PARTIAL/FAIL/NEAR and the texture is lost — and `c51c44f` invented a fifth value ("NEAR") mid-table precisely because the binary couldn't hold the read, which is the table telling you it's the wrong shape.

2. **Computed aggregates manufacture false precision.** "avg trace-completeness ≈ 0.66 (below the 0.8 floor)" reads like a measurement. It is a mean of ten human guesses each rounded to 0.05, against a floor (0.8) that was *itself* a guess written before any data existed. The aggregate launders ten soft judgments into one hard-looking number, and then the headline cites the hard-looking number. This is the precise path by which `c51c44f`'s headline became load-bearing on signals that didn't measure mandate-coherence.

3. **Four dimensions of which three are qualitative and one is automated creates a gravity well toward the automated one.** Cost is the only dimension the runner can fill honestly without a human. So the runner fills cost, emits the other three as `TODO`, and the human — facing three columns of empty cells — is invited to treat "fill the cells" as the task. The cells become the work-list. But filling cells is not reading transcripts; it's *classifying* transcripts against a pre-declared cell, which is a different and lesser activity. The dimension table converts "read and judge" into "classify and tabulate."

**Structural alternative (developed fully in the proposal):** stop scoring dimensions. Replace the four-dimension table with a small set of **operator-questions**, each answered in prose with receipts inline. The questions are the structure; the prose answer is the deliverable; the receipt is the proof. Cost stays — but as a flat automated appendix (it genuinely *is* automatable and genuinely *is* a number), not as a peer "dimension" that makes the qualitative three look like they should also resolve to numbers.

### (d) Does `substrate_inputs` + `expected_dimensions` (Given/Then) serve qualitative measurement, or invite drift?

This one is split. The two halves of the BDD contract have opposite fates.

- **`substrate_inputs` (the "Given") is genuinely load-bearing and should be *sharpened, not removed*.** Its real value is as a **precondition the run must establish before firing** — the c51c44f→d38130e arc proves this: the *entire* difference between the misleading run and the validated run was whether the substrate matched `substrate_inputs.autonomy_mode_required` at fire time. `substrate_inputs` is correctly diagnosing what state the situation needs. Its failure was that **nothing enforced it** — it was declared as documentation and consumed as documentation, while the runner fired against whatever state happened to exist. The fix is to make `substrate_inputs` a *pre-flight assertion the harness checks and a setup spec the harness applies*, not a paragraph the operator reads. (This is the d38130e session's own Rec 3 "E7" recommendation — correct, and I adopt it, but as a structural reshape rather than an appended rule.)

- **`expected_dimensions` (the "Then") is where the drift lives and should be *demoted from contract to hypothesis*.** The problem: BDD's "Then" presumes the correct outcome is *knowable before the situation is concretely seen*. For a deterministic system that's fine. For "would an editor have reasoned this way," it is not — the right verdict in a concrete situation is a judgment formed *from* the situation, and pre-declaring `posture.cell: M7` before the run converts the human's job from "read what happened and judge it" into "check whether what happened matches M7." That is the auto-classification invitation in its purest form. The README already knows this (`README.md` rule 0 + pre-flight criterion audit: *"ask whether the criterion itself is well-formed ... Does it cover all legitimate behaviors?"*). The eval-suite layer overrode the README's caution by hardening "interpretation hint" (`expect:` in scenarios) into "measurement target with declared criterion" (`expected_dimensions`, per E3) — and that hardening is the drift.

**Resolution:** keep a lightweight `expected:` (the operator's *prior* about what a coherent editor would do — useful for orienting the read, named as a hypothesis), drop `expected_dimensions` (the four-cell pre-declared contract). The read is judged against the *mandate*, not against the pre-declared cell. When observed ≠ prior, that's the interesting finding to interpret — not a "FAIL" to tabulate.

### (e) What evals should a yarnnn-author suite actually contain, given the MANDATE Primary Action is "author and ship founder corpus pieces"?

The current 10 evals are **almost entirely audit-loop**: they probe the Reviewer's pre-ship verdict substrate (`judgment_log.md`, `standing_intent.md`) and its envelope-reading discipline (does it cite `_pace.yaml`, `wake_source`, the tightened MANDATE clause). Six of ten are about whether the Reviewer *reads substrate correctly*; four are counterfactuals about whether it *tracks substrate mutations*. **Zero are about whether a piece actually shipped or whether the corpus compounded.**

That is a real gap, but — and this is load-bearing per the brief's anti-patterns — **naming the artifact-loop gap is NOT a license to add eval shapes before the rollup shape is fixed.** The brief is explicit: "Adding new eval shapes (e.g., 'artifact-loop') before settling whether the rollup-shape needs to change FIRST" is an anti-pattern. So I answer (e) at the level of *kind*, and defer the actual authoring:

There are two families of question for a yarnnn-author workspace, and they are different *kinds* of read:

1. **Judgment-loop questions** (what the current suite probes): given a situation, did the Reviewer reason like an editor holding this mandate? These read a *single wake* or a *short exchange*. The qualitative unit is a transcript.
2. **Compounding-loop questions** (the gap): over a window of operation, did pieces ship, did the corpus accumulate a recognizable voice, did the Reviewer's verdicts correlate with what the operator later kept vs. revised? These read *across many wakes and the substrate trail over time*. The qualitative unit is the substrate's *trajectory*, not a transcript.

The redesign must make room for both *kinds* of read without forcing the second into the first's shape. But the **rollup shape must be settled first** (it is — §2(c)), and the compounding-loop evals are authored *after* the operator approves the reshaped framework, against the reshaped shape. I name the family in the proposal as future work with an explicit "do not author until rollup reshape is approved" gate.

### (f) Modularity: one monolithic file, N layered files, or something else?

Anchor in (a)–(e), not in shape-preference. The purpose (§2a) is "a small number of *known, operator-recognizable* situations grouped by *the question each lets the operator answer*." That sentence dictates the modularity:

- **Not monolithic-with-phase-tags** (the current shape). The current single file groups by *industry eval-shape taxonomy* (behavioral / red-team / behavioral_substrate_audit / counterfactual). That taxonomy is the framework's vocabulary, not the operator's question. Grouping by it serves the framework's self-description, not the read.
- **Not "layered because layered feels modular"** (the brief's named anti-pattern). Layering for its own sake is shape-without-foundation.
- **Yes — grouped by the qualitative question the group lets the operator answer.** The natural seam falls out of (e): a **judgment-coherence** group (does the Reviewer reason like an editor in a concrete situation?) and a **substrate-responsiveness** group (does the Reviewer track operator changes to its governing substrate?). These are different *reads* — the first reads a transcript against the mandate; the second reads a before/after substrate delta against an operator intent. The eval-shape taxonomy (behavioral/counterfactual) collapses into this: it was a clumsy proxy for "is this a single-situation read or a mutation-delta read," which is exactly the judgment-vs-responsiveness seam.

So: **two suite files, split by the kind of read the operator does**, not four eval-shapes in one file split by the framework's taxonomy. The compounding-loop family from (e) becomes a third file when it's authored. This is modular *because the reads are genuinely different*, which is the only justification (a) admits.

---

## §3 Specifically-considered observations from the brief (ground-truthed, not accepted as given)

The brief flagged six observations to verify against canon rather than accept. My verdict on each:

1. **"Per-eval Behavior + Posture tables with Observed + Pass? columns invite treating qualitative judgment as auto-fillable — real, or useful structure mis-consumed?"** — **Real drift-invitation, confirmed by the record.** The honest session left the table empty; the misleading session filled it. If the structure were useful-but-mis-consumed, the honest session would have used it *correctly*. Instead it *routed around* it. A structure that the honest path routes around is not useful structure being mis-consumed — it is the wrong structure.

2. **"`substrate_inputs` presupposes 'given state S, behavior B follows' — is substrate-determinism the right anchor for an LLM whose reasoning quality we care about?"** — **Partially wrong anchor.** Substrate-determinism is the right anchor for the *precondition* (the situation must be set up correctly — §2d first half) but the wrong anchor for the *outcome* (an LLM's reasoning quality is not deterministically derivable from substrate — §2d second half). The current schema applies determinism to both halves; the fix splits them.

3. **"Sequential-accumulation (E4) produces compound state by eval-N that obscures attribution — is it the right shape for qualitative measurement?"** — **Wrong shape for the judgment-loop, defensible only for a narrow case.** E4 ("sessions accumulate substrate; the runner does not reset between evals") is the *direct cause* of the c51c44f→d38130e mess: accumulation from a *prior session* violated eval-1's precondition, and accumulation *within* the session means eval-10's read can't be attributed cleanly to eval-10's mutation vs. eval-7/8/9's residue. For "would an editor have reasoned this way in situation X," situation X must be *clean and known*, which means **pre-flight reset to each eval's declared starting state is the correct default**, not the exception. The one place accumulation is genuinely the point — "does the operator's *iterative arc* (tighten MANDATE → tighten AUTONOMY → ...) compose correctly" — is a *compounding-loop* read (§2e family 2), and it should be authored as an explicit ordered-arc eval that *declares* its accumulation, not inherited as the silent default for every eval. E4 inverts the right default.

4. **"4 eval shapes but 1 rollup shape — does one-shape-fits-all serve all 4 equally?"** — **No, and this is the same finding as (f).** Counterfactual mutations and behavioral probes are different *reads* (delta-read vs. transcript-read), and forcing both into the same four-dimension table is why the counterfactual evals' `Pass?` cells were the most strained in c51c44f (the action_proposal side-effect "load-bearing test" was repeatedly "UNTESTABLE" because the Reviewer chose to write nothing — a table cell can't express "the test couldn't run," but a prose read can). The rollup must follow the read-kind, which is why §2(f) splits by read-kind.

5. **"DRAFT/POPULATED status — is the binary flag itself part of the drift?"** — **Yes, the binary is part of the drift.** "POPULATED" invites flipping before the read is done — and `d38130e` *did* flip to POPULATED with §2 entirely `TODO`, then had to write a paragraph explaining why POPULATED was true anyway. A status that requires a paragraph of justification for why it's accurate is the wrong status. Replace the binary with a **read-state that names what was actually read** (e.g. "Read: §A judgment-coherence (3 of 3 transcripts read); §B responsiveness (not yet read)"). Honest partial state should be expressible without lying or apologizing.

6. **"The four-cause taxonomy (a/b/c/d substrate/Reviewer/envelope/canon) — right diagnostic structure, or needs re-examination?"** — **Keep it; it is the framework's genuinely good idea, and it is *orthogonal* to the rollup-shape problem.** The substrate→envelope→behavior mapping (§1.5) is the one part of the current framework that earned its keep: it gives a failure a *fix-location vector* (was it substrate / Reviewer-read / envelope-plumbing / canon?). Both honest sessions *used* it well — d38130e's §3 Obs 1-4 are built on it, and c51c44f's §3 Obs 3 explicitly credits it. The four-cause taxonomy is not what invited drift; the *dimension table wrapped around it* invited drift. So: **preserve the four-cause diagnostic as the spine of the prose read; delete the dimension table that surrounded it.** The diagnostic is a *reasoning aid for the human read*, not a scoring rubric — it belongs in the prose, naming why a divergence happened, not in a cell.

---

## §4 What the redesign therefore commits to (the bridge to the proposal)

Every commitment below is a direct consequence of a §2 answer. None is a shape-preference.

1. **The emitted artifact is operator-question-anchored prose, not a dimension table.** (from 2a, 2c, 0) — The rollup is a small set of named questions, each answered in prose with receipts inline. No `Pass?` cells, no computed qualitative aggregates.
2. **Cost stays, demoted to an automated appendix.** (from 2c) — It is genuinely a number and genuinely automatable; it is not a peer "dimension" of the qualitative read.
3. **`substrate_inputs` becomes an enforced pre-flight precondition + setup spec, not documentation.** (from 2b, 2d, 3.2, 3.3) — The harness asserts the situation is set up correctly before firing, or sets it up, or refuses. The c51c44f failure becomes structurally impossible.
4. **`expected_dimensions` (the four-cell contract) is deleted; a lightweight `prior:` hypothesis replaces it.** (from 2d, 2c) — The read is judged against the *mandate*, not against a pre-declared cell. Divergence from prior is a finding to interpret, not a FAIL.
5. **Pre-flight reset to each eval's clean known starting state is the default; accumulation is an explicit opt-in for ordered-arc evals only.** (from 3.3) — E4's default inverts.
6. **The suite splits into two files by kind-of-read (judgment-coherence / substrate-responsiveness); a third compounding-loop file is future work gated on this reshape landing.** (from 2e, 2f, 3.4)
7. **The four-cause diagnostic (substrate/Reviewer/envelope/canon) is preserved as the prose read's spine.** (from 3.6)
8. **Status becomes a read-state that names what was read, not a DRAFT/POPULATED binary.** (from 3.5)

The proposal documents (`EVAL-SUITE-DISCIPLINE.md` rewrite, suite migration plan, SESSION.md template, harness change-list) implement exactly these eight and nothing more. If any of them introduces a commitment not on this list, it is scope creep — flag it.
