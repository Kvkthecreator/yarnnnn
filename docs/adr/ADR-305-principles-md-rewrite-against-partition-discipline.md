# ADR-305: `principles.md` Rewrite Against Partition Discipline — Methodology for Per-Program Calibration

**Status**: Proposed 2026-05-27 — paper-design only, no bundle/code changes until ratified.

**Date**: 2026-05-27

**Authors**: KVK, Claude

**Depends on**:
- [`docs/architecture/agent-composition.md`](../architecture/agent-composition.md) §3.2.1 (partition-discipline canon, hardened in commit `d8d0e57`)
- [`docs/architecture/reviewer-substrate.md`](../architecture/reviewer-substrate.md) §"`principles.md`" (substrate-role canon, deferral-pointer to §3.2.1)
- ADR-194 v2 (Reviewer seat substrate)
- ADR-217 (Workspace Autonomy Substrate — AUTONOMY moved to `_shared/`)
- ADR-254 (file format discipline — `_principles.yaml` machine-parsed sibling)
- ADR-293 (Governance / Operational Substrate Taxonomy)
- ADR-295 (Reviewer Self-Amendment Discipline — Phases A–D Implemented; this ADR is the **v2 amendment** flagged in ADR-295's status: *"Implementation surfaced behavioral drift; v2 amendment expected"*)
- ADR-303 (Reviewer Posture Taxonomy — P1–P5 cells)
- ADR-209 (Authored Substrate — operator authorship preserved across re-fork)
- Eval-suite session `2026-05-27-064722-yarnnn-author-baseline-session/SESSION.md` (commit `c51c44f`) — the load-bearing measurement

**Amends**: ADR-295 (the evidence-threshold ratification moves out of `principles.md` as content into per-program `_principles.yaml` calibration; ADR-295 D1 categories survive in the persona-frame `_compute_self_amendment_discipline` section as the universal taxonomy)

**Preserves**: agent-composition.md §3.2.1 partition canon (this ADR applies it; it does not amend it). Singular Implementation discipline (one rewrite path per program, bundle template is the single home, ADR-209 preserves operator-authored production-workspace content from re-fork overwrite).

**Supersedes**: The current 169-line `docs/programs/alpha-author/reference-workspace/review/principles.md` shape, which carries ~60% reasoning-posture content that belongs in persona-frame `_compute_*` sections. Corresponding sibling in alpha-trader bundle is in the same shape and is rewritten in the same ADR-305 application pass (per Piece 4 of the sequence laid out in session `2026-05-27`).

---

## 1. The structural gap the eval session surfaced

The 10-eval `yarnnn-author-baseline.yaml` suite ran against the yarnnn-author workspace on 2026-05-27 (session folder `2026-05-27-064722-yarnnn-author-baseline-session/`, populated rollup in commit `c51c44f`). Across 9 readable wakes, the Reviewer made exactly 3 substrate writes — all to `/workspace/review/` (`judgment_log.md` + `standing_intent.md`). Zero writes to operator-visible substrate (MANDATE / `_voice.md` / `_preferences.yaml` / `_recurrences.yaml`). Zero `action_proposals`. Under `AUTONOMY=autonomous` for evals 1–7, the Reviewer never reached the bind-action branch.

**Substrate-receipts query** (verified 2026-05-27, reproducible per SESSION.md §5):

```sql
SELECT created_at, path, authored_by, message
FROM workspace_file_versions
WHERE user_id = '0b7a852d-4a67-447d-91d9-2ba1145a60d7'
  AND created_at >= '2026-05-27 06:48:17'
  AND created_at <= '2026-05-27 06:53:35'
  AND authored_by LIKE 'reviewer:%'
ORDER BY created_at;
```

Returns 3 rows, all to `/workspace/review/`. Zero rows to operator-visible substrate. The `action_proposals` companion query for the same window returns 0 rows.

**Diagnosis** (per the §1.5 four-cause taxonomy in `docs/evaluations/EVAL-SUITE-DISCIPLINE.md`):

- (a) Substrate doesn't say what we thought — **ELIMINATED.** MANDATE mutation visible (eval-7 read it verbatim), `_autonomy.yaml` values correct, `_preferences.yaml` seeded.
- (b) Reviewer doesn't read substrate the canon way — **PARTIALLY CONFIRMED.** Eval-9 hallucinated `_pace.yaml` "doesn't exist" 34s after operator-proxy seeded it; the Reviewer reasoned from cached `standing_intent.md` narrative instead of the freshly-loaded envelope substrate.
- (c) Prompt envelope doesn't deliver substrate — **ELIMINATED.** `reviewer_envelope.py:78-110::_UNIVERSAL_ENVELOPE_DECLS` includes all five scaffolded inputs (`mandate_md`, `autonomy_md`, `preferences_yaml`, `pace_yaml`, `principles_md`) unconditionally.
- (d) Canon mis-specified — **PRIMARILY CONFIRMED.** The operator-authored `principles.md` had absorbed ~60% reasoning-posture content from ADR-295 (self-amendment discipline), ADR-303 (posture taxonomy), and the calibration loop (ADR-195). The persona-frame faithfully read the absorbed content as "single-cycle amendments forbidden" + "every cycle authors standing_intent.md is a legitimate posture" + "evidence threshold ≥20 published / ≥8 audits over 2 weeks" — composed into a Reviewer that **journals its own seat and stands down** under any condition where the workspace is younger than the threshold horizon.

The hardening landed in commit `d8d0e57` declared the **partition** between `principles.md` (rule-set the persona applies) and persona-frame `_compute_*` sections (reasoning posture). It did NOT rewrite the file. **ADR-305 is the rewrite ADR.**

## 2. Decisions

### D1 — Application of the four-field rule shape to `principles.md`

Per `agent-composition.md` §3.2.1, every rule in `principles.md` must declare:

1. **Name** — stable identifier (`voice-fingerprint-match`, `anti-slop`, `text-continuity`, etc.)
2. **Substrate it reads against** — file path or signal anchor
3. **Pass condition** — what state of that substrate means the rule passes
4. **Verdict on fail** — `approve` / `defer` (with directive shape) / `reject` (unconditional) / `propose` (action_proposal)

This ADR ratifies the application: post-rewrite, `principles.md` carries **only** rules of this shape, the conflict-resolution clause, and a brief workspace-lifecycle phase pointer when a rule's pass condition is phase-gated. Nothing else. The bright-line content list in §3.2.1 governs what must NOT appear.

### D2 — Methodology for per-program numeric tuning (the calibration question)

The numeric thresholds that gate Reviewer self-amendment + auto-approve binding live in `_principles.yaml` (ADR-254 machine-parsed sibling). The numbers are **per-program**, not universal. Per-program tuning is governed by the program's **actual loop-cycle time** and **what evidence accumulates per cycle**, not by template copy-paste from another program.

The methodology, declared canonically here:

**M1 — Identify the program's evidence-producing event.** For alpha-trader, that's a reconciled outcome in `_money_truth.md` (typically multiple per day during active periods). For alpha-author, that's an operator ship-decision on a Reviewer-audited draft (target cadence per `_preferences.yaml`; bootstrap cadence may be days to weeks per first piece).

**M2 — Calibrate sample size to the loop-cycle.** The amendment-evidence threshold ought to require enough events to discriminate signal from noise in the program's outcome distribution, but small enough that the threshold clears within the program's natural iteration window. Pattern: **threshold ≈ ceil(2× the program's typical signal-stabilization sample count)**.

- For alpha-trader: outcomes accumulate fast (capital cycles). A signal-stabilization sample of ~20 outcomes ⇒ amendment threshold ~40 outcomes. The ADR-295 default (40 reconciled outcomes, 10 distinct wakes, 5 days persistence) reflects this loop-cycle.
- For alpha-author: outcomes accumulate slow (ship cycles). Operator publishes 1–2 pieces per week in steady state, fewer in bootstrap. A signal-stabilization sample of ~3 ship-decisions ⇒ amendment threshold ~6 ship-decisions OR equivalent calendar persistence. Today's `principles.md` carries 20 / 8 / 2-weeks — copied from alpha-trader's mental model, structurally unreachable for alpha-author until month 3+ of operation.

**M3 — Distinguish bootstrap from steady-state in the rule itself.** A rule whose pass condition cannot be evaluated until N events accumulate is **effectively no rule for the first N events**. The rule must declare its **bootstrap behavior** (what happens when the substrate-anchor is empty) and its **steady-state behavior** (what happens when ≥N events have accumulated). Bootstrap behavior is part of the rule, not a separate philosophy section.

**M4 — Tunable thresholds are yaml, not prose.** `principles.md` declares the rule and its substrate-anchor + pass-condition + verdict; `_principles.yaml` declares the numbers. Operators recalibrate by editing yaml; the rule shape doesn't change. This is ADR-254 file-format discipline applied to amendment thresholds.

**M5 — Cite-the-loop-cycle discipline.** Every numeric threshold in `_principles.yaml` carries a comment naming the loop-cycle reasoning that produced it. Format: `# threshold: {value} | rationale: {sample-stabilization × calendar-persistence given {program} typical cycle} | last-recalibrated: {date}`. Operators reading the file can trace the threshold back to a reason, not a vibes-copy from another program.

This ADR does NOT prescribe specific numeric values for alpha-author or alpha-trader. The values are downstream Piece 2 + Piece 4 work, derived from this methodology against each program's actual cycle data. Per-program numeric values are reviewable as bundle-template diffs, not as canon amendments.

### D3 — Specific reshapings are emergent from Piece 2 + validated by Piece 3, not pre-committed in canon

The session diagnosis surfaced specific shapes the rewrite *might* take to address observed gaps — separating ship-binding from cadence-binding from operator-canon-binding (because the current file collapses all three under one sample-size gate), moving bootstrap behavior inside each rule (because the parallel meta-section duplicates concerns), relocating anti-pattern enumeration from `principles.md` to `_voice.md` (single source of truth). Each of these is a plausible reshaping. **This ADR does NOT pre-commit to any of them.**

The reason: each is a bug-fix-shaped reasoning derived from a single session's measurement. A one-shot rewrite that pre-commits to specific reshapings risks (a) over-fitting to symptoms the session exposed rather than to the underlying partition discipline, (b) locking downstream work into shapes that the actual rewrite + the eval re-run may invalidate, and (c) adding ADR ceremony without adding signal — since the partition canon (`d8d0e57`) plus the calibration methodology (D2) already constrain the rewrite's shape sufficiently to prevent drift.

The discipline this ADR commits to instead:

- **Piece 2 (alpha-author rewrite)** is an exploration informed by D1's four-field shape, D2's calibration methodology, D6's conflict-resolution preservation, and D7's re-fork boundary. It is NOT an execution of a specific spec declared in this ADR. The rewrite's author (operator + collaborator) discovers the appropriate shaping by applying the partition canon to the actual current content and asking the §3.2.1 diagnostic test of each section.
- **Piece 3 (eval re-run against the rewritten alpha-author bundle)** is the validation instrument. If the eval re-run measures operator-visible substrate writes under `AUTONOMY=autonomous` (closing the strong-autonomy gap the c51c44f session named), the reshapings Piece 2 chose are validated. If the gap persists, the reshapings need iteration — either via Piece 2 amendment, or via persona-frame `_compute_*` edits (cause b territory), or via further partition-canon refinement.
- **Reshapings that prove load-bearing across programs after Piece 3 + Piece 4** may be amended into this ADR as D9/D10/etc. via subsequent commits to ADR-305. The ADR is a living methodology declaration, not a frozen spec.

What this decision does NOT defer: the partition itself (D1 + D6 + §3.2.1), the calibration methodology (D2 M1-M5), the operational boundary on production-workspace migration (D7), the eval-rubric impact acknowledgment (D8). Those are stable canon-shaped commitments that should not change session-to-session.

What this decision does defer: specific structural reshapings (binding-path separation, bootstrap-state location, anti-pattern enumeration home) that are bug-fix-shaped derivations from the c51c44f session. Those emerge from the e2e loop's iteration; they earn ADR-amendment status by surviving Piece 3's measurement, not by being plausible-looking at paper-design time.

### D6 — Conflict-resolution clause is preserved verbatim from §3.2.1

The rewritten `principles.md` carries the conflict-resolution clause as a short ratification section, not as new content:

```
## Conflict resolution
- `PRECEDENT.md` overrides conflicting clauses in this file.
- Persona-frame discipline (`api/agents/reviewer_agent.py` `_compute_*` sections) is authoritative
  for reasoning-posture concerns; do not re-declare those concerns here.
- `AUTONOMY.md` ceiling cannot be widened by rules in this file. Rules may narrow (add defer
  conditions) but never widen delegation.

See `docs/architecture/agent-composition.md` §3.2.1 for the canonical partition statement and
the diagnostic test for whether content belongs in this file or in persona-frame.
```

### D7 — Re-fork is bundle-template-only; existing workspaces are not migrated

Per ADR-209 authored-substrate attribution, the operator-authored content in production workspaces (`yarnnn-author@yarnnn.com` at `0b7a852d-...`, `alpha-trader-2@yarnnn.com` if applicable, any other forked workspace) is preserved across bundle re-forks. The rewrite touches `docs/programs/{slug}/reference-workspace/review/principles.md` + `_principles.yaml` only. New workspaces forked from the updated bundle inherit the rewrite; existing workspaces continue carrying their current `principles.md` content until the operator initiates re-sync.

This is correct per ADR-209 and is named explicitly here so future ADRs don't have to re-derive the migration boundary.

**Operator-side path for adopting the rewrite in an existing workspace**: operator reads the bundle's updated `principles.md` + `_principles.yaml` template; chooses to `WriteFile` the new content over the workspace's current content via UpdateContext or chat-mediated edit; the workspace's revision chain captures the change with `authored_by="operator"` per ADR-209. The system does not push the rewrite to existing workspaces.

### D8 — Eval-rubric citation-target impact acknowledgment

Whatever specific reshapings Piece 2 chooses (per D3, those emerge from the rewrite + e2e loop), at least one likely effect is a shift in where eval rubrics cite for authority on Reviewer behavior. For example, today's `yarnnn-author-baseline.yaml` eval-4 (pressure-resistance) expected rubric cites *"ADR-295 D3 anti-pattern (1) AND/OR MANDATE Boundary Conditions"* — if the rewrite removes the duplicated anti-pattern enumeration from `principles.md`, the rubric citation target shifts toward MANDATE Boundary Conditions + the persona-frame's `_compute_anti_patterns` section.

The ADR acknowledges this likely impact so Piece 3's session author knows to verify rubric citation chains as part of the re-run interpretation. **Specific YAML updates are NOT in this ADR's scope** (Hat-B work, in Piece 3's session). The ADR's commitment is: any eval whose rubric cited content that the rewrite moved gets re-interpreted in Piece 3, with the rubric YAML edit landing in the same session commit.

## 3. Application — what the rewrite produces (shape, not content)

Post-application of D1, D2, D6, D7 to `docs/programs/alpha-author/reference-workspace/review/principles.md`, the file's section structure is shaped by **the partition canon (§3.2.1) + the calibration methodology (D2)**, not by a pre-declared section list in this ADR. Per D3, the specific section breakdown emerges from Piece 2's rewrite informed by the §3.2.1 diagnostic test applied to each current section of the file.

What the rewrite is constrained by:

- **Every retained section declares either** (a) a rule in the four-field shape (name + substrate-read + pass-condition + verdict-on-fail), (b) the conflict-resolution clause per D6, or (c) a brief workspace-lifecycle phase pointer that a rule's pass condition references. If a current section doesn't fit one of those three, it migrates to persona-frame `_compute_*` (the destination per §3.2.1's bright-line content list) or to another substrate file (`_voice.md`, `_principles.yaml`, etc.) as the rewrite's exploration determines appropriate.
- **Numeric thresholds live in `_principles.yaml`** per D2 M4. Prose-declared categories may live in `principles.md`; the numbers per program live in yaml with cite-the-loop-cycle comments per M5.
- **Re-fork is bundle-only** per D7. Existing production workspaces preserved per ADR-209.

What the rewrite explicitly does NOT pre-commit to (per D3):

- Specific section count or section names
- Specific shape of the auto-approve / binding clause (whether one section, multiple sections, or attached to individual rules)
- Specific location of bootstrap-state handling (per-rule field, separate section, or some other emergent shape)
- Specific home for anti-pattern enumeration (principles.md, `_voice.md`, or both with one citing the other)

These are Piece 2 discoveries, validated by Piece 3 measurement.

The shape for alpha-trader's rewrite (Piece 4) is constrained by the same D1 + D2 + D6 + D7 + §3.2.1 inputs, but the **specific reshapings alpha-trader's rewrite chooses may differ from alpha-author's** — and that's fine. The partition canon governs the constraint; the per-program rewrite explores within it. If reshapings prove load-bearing across programs (i.e., both rewrites converge on the same answer), they earn ADR-305 amendment as D9/D10/etc. via subsequent commits. Until then, per-program divergence is honest, not drift.

## 4. What this ADR does NOT do

- **Does not rewrite the bundle templates.** That's Piece 2 (alpha-author) + Piece 4 (alpha-trader) of the sequence. This ADR is paper-design declaring the partition application + calibration methodology; the rewrite is a separate doc-change commit per program.
- **Does not declare specific numeric thresholds** for either program's `_principles.yaml`. Per D2 M4, the numbers are downstream of the methodology and are reviewable as bundle-template diffs in their respective rewrite commits.
- **Does not pre-commit to specific structural reshapings** per D3 (binding-path separation, bootstrap-state location, anti-pattern enumeration home, section structure). Those are Piece 2 explorations informed by §3.2.1's diagnostic test + D2's methodology; they are validated by Piece 3's e2e measurement. Reshapings that prove load-bearing across programs earn ADR-305 amendment as D9/D10/etc. after Piece 3 + Piece 4.
- **Does not migrate production workspaces.** Per D7, the rewrite is bundle-template-only; existing operator-authored content is preserved per ADR-209.
- **Does not change envelope plumbing.** `reviewer_envelope.py::_UNIVERSAL_ENVELOPE_DECLS` continues to yield `principles_md` unconditionally; the file's role in the wake envelope is unchanged.
- **Does not change ADR-295's persona-frame canon.** The amendment-discipline categories (calibration-driven / near-miss-driven / substrate-gap-driven / cadence-driven / persona-developmental) survive as the universal taxonomy in `_compute_self_amendment_discipline`; only the per-program numeric tuning moves to `_principles.yaml` per M4. ADR-295's status note about "v2 amendment expected" is partially closed by this ADR — the methodology piece is here; the numerics land per program in their respective rewrites.
- **Does not change ADR-303's posture-cell taxonomy.** P1–P5 cells survive in `_compute_standing_intent_contract`.
- **Does not change `_compute_*` persona-frame sections.** This ADR establishes that those sections are the **destination** for absorbed reasoning-posture content; it does not edit them. If Piece 2's rewrite or Piece 3's measurement surfaces reasoning-posture concepts without a `_compute_*` home, that's a separate follow-up ADR.
- **Does not change eval-suite YAML.** Per D8, the rubric re-interpretation happens in Piece 3 (eval re-run) as part of the SESSION.md authoring; eval YAML edits land in the same Piece 3 commit, not in this ADR.
- **Does not address the eval-9 hallucination root cause (§1 cause (b)).** That's a separate persona-frame discipline edit ("re-read envelope when standing_intent contradicts current substrate") tracked in the c51c44f SESSION.md §4 recommendation 2; out of scope for this ADR. May surface as an independent Piece 5 if Piece 3 measurement shows the partition rewrite alone doesn't close the strong-autonomy gap.

## 5. Singular Implementation compliance

- **One partition home**: `agent-composition.md` §3.2.1. This ADR cites it; does not re-state.
- **One rewrite path per program**: bundle-template at `docs/programs/{slug}/reference-workspace/review/principles.md` + `_principles.yaml`. No parallel migration mechanism for existing workspaces (per D7 + ADR-209).
- **One amendment-discipline home in code**: `_compute_self_amendment_discipline` + `_compute_anti_patterns` in `api/agents/reviewer_agent.py`. ADR-295's categories survive as the universal taxonomy; this ADR does not introduce a parallel home.
- **One numeric-threshold home per program**: `_principles.yaml` (ADR-254 machine-parsed). Prose-declared categories in `principles.md` cite yaml paths; no thresholds live in prose.

## 6. Risks + Open Questions

- **R1 — alpha-trader's existing `principles.md` may already conform to the four-field shape.** If so, the alpha-trader rewrite in Piece 4 is a smaller edit (mostly methodology citation + yaml separation), not a full rewrite. Audit needed before Piece 4 commences.
- **R2 — Some reasoning-posture content currently in `principles.md` may not yet have a persona-frame `_compute_*` home.** Per §4 "Does not change `_compute_*` persona-frame sections", this is discovered during Piece 2's rewrite. Expected destinations: self-amendment evidence-threshold categories → `_compute_self_amendment_discipline`; bootstrap calibration meta → same (it's the same concern, viewed from a different angle); fiduciary principle → `_compute_self_amendment_discipline` D4. If a concern has no home, that's a flag for a `_compute_*` extension ADR — landed as an independent commit, not bundled with the rewrite.
- **R3 — Workspace-lifecycle phase progression** is currently partially in `AUTONOMY.md` ("Phase 0 / Phase 1 / Phase 2 / Phase 3") and partially in `principles.md` ("first 10 audits are all manual"). The two should not drift. Piece 2 will discover whether the right shape is phase-gating per rule (rules-side), AUTONOMY.md owning the lifecycle phase enum alone, or some hybrid. The rewrite normalizes whichever shape Piece 3 measurement validates.
- **R4 — Eval-suite re-run (Piece 3) may surface that the rewrite alone is insufficient** — i.e., even with the partition applied, the Reviewer still doesn't bind operator-visible action. That would point at the eval-9 hallucination root cause (cause b, §1) or at an envelope-distance issue not yet diagnosed. The session's SESSION.md §4 has the recommendations queued; if Piece 3 reproduces the "zero operator-visible writes" finding, those persona-frame edits become priority Piece 5. Per the e2e discipline named in §8, this is the expected shape of progress — one-shot resolution is not the design intent; iterative measurement is.
- **R5 — Per-program reshapings may diverge.** Alpha-author's rewrite and alpha-trader's rewrite may land on different specific shapes (different section breakdowns, different binding-clause structure, different bootstrap-handling). Per D3, this is acceptable until reshapings prove load-bearing across both programs — at which point they earn ADR-305 amendment. Until then, per-program divergence is honest, not drift.

## 7. Phased Implementation

This ADR is paper-design. The phased implementation is the **sequence laid out in session `2026-05-27` post-`d8d0e57`**, with the iterative discipline named in §8:

- **Piece 1 (this ADR)** — paper-design ADR-305. Proposed → operator review → Ratified status flip when reviewed. Status flips to `Implemented` only after Pieces 2 + 3 land + Piece 3 measurement validates the partition application closes (or productively informs) the strong-autonomy gap.
- **Piece 2** — alpha-author bundle rewrite. Touches `docs/programs/alpha-author/reference-workspace/review/principles.md` + `_principles.yaml` only. Cites ADR-305. Per D3, the rewrite is an exploration informed by §3.2.1 + D2, not an execution of a specific spec. Operator review of the bundle diff is the right place to challenge specific reshaping choices.
- **Piece 3** — eval-suite re-run against a freshly-forked alpha-author workspace. Touches `docs/evaluations/` only. Cites Piece 2's commit; produces a new SESSION.md. **This piece is the validation instrument** — see §8. Eval YAML edits (D8 citation-target shifts) land in this commit.
- **Piece 4** — alpha-trader bundle rewrite. Touches `docs/programs/alpha-trader/reference-workspace/review/principles.md` + `_principles.yaml` only. Cites ADR-305 + Piece 2 + Piece 3. If R1's audit finds alpha-trader already conforms, this piece is small. If Piece 3 surfaces persona-frame edits as priority (R4), Piece 4 may be deferred behind a Piece 5 persona-frame edit ADR.

The sequencing is order-dependent. Each piece's commit explicitly cites the prior piece's commit hash in its body. **Per D3 + §8, "Implemented" status for ADR-305 does NOT mean "all four pieces landed exactly as described in this ADR" — it means "the partition is applied across both program bundles AND the e2e loop has measured an outcome that either validates the rewrite shape or surfaces the next priority work."** The ADR's job is to declare canon-shaped commitments (partition, methodology, operational boundaries); the sequence's job is to validate them iteratively. Both are honest in different ways.

## 8. The e2e loop is the validation instrument

This ADR is deliberately under-specified about specific structural reshapings per D3, and the reason is named here explicitly so future sessions don't re-litigate it:

**The eval-suite + observation-thread loop (built across sessions `2026-05-26` through `2026-05-27`) is the validation instrument for whether Reviewer behavior matches canon claims.** It is not paper-design that validates; it is substrate-receipts under measurement that validates. A canon edit's correctness is tested by whether re-running the loop against the edited substrate produces the predicted Reviewer behavior. One-shot improvement against a complex partition-content gap is unlikely; iterative measurement is the design intent.

The consequence: ADR-305's downstream pieces (2-4) are **discovery work informed by canon**, not **execution of a canon-declared spec**. Each piece's commit body should report:

- What the rewrite/re-run found (substrate-receipts: queries + their results)
- What that finding suggests about the partition application's adequacy (validated / surfaces new gap / inconclusive)
- What the next priority work is (continue the sequence / pivot to persona-frame edits / amend ADR-305 with newly-load-bearing learnings)

This shape honors what the c51c44f session demonstrated: the load-bearing question (did the Reviewer ever bind operator-visible action?) was answered by the **substrate-receipts query**, not by any prose ADR. The e2e loop produced a definitive `0 rows` answer to a definitive question. That is the canon-validation shape this ADR's downstream pieces inherit.

What this means in practice:

- **Piece 2's rewrite is not held to a pre-declared section structure.** It explores the application of §3.2.1 + D2 against the actual current `principles.md` content, makes specific reshaping decisions, ships them. Operator review of the bundle diff is the right scrutiny layer; this ADR is not.
- **Piece 3's eval re-run is the truth-teller.** If it measures operator-visible substrate writes under `AUTONOMY=autonomous`, the rewrite shape is validated. If not, the next priority work is named in Piece 3's SESSION.md §4 — possibly persona-frame edits (cause b territory from §1), possibly further partition-canon refinement, possibly something not yet diagnosed.
- **Piece 4 (alpha-trader rewrite) is conditional on Piece 3.** If Piece 3 invalidates the rewrite shape, Piece 4 either uses the iterated shape OR is deferred behind a persona-frame edit ADR. Order matters.
- **ADR-305 amendments are valid commits.** If Piece 3 measurement surfaces a reshaping that proves load-bearing, the ADR gets a D9/D10/etc. amendment commit — the ADR is a living methodology declaration, not a frozen spec.

This is the same discipline `docs/evaluations/EVAL-SUITE-DISCIPLINE.md` §E3 already declares for eval-suite sessions: *"A failed eval is a finding to interpret, not a CI break."* This ADR extends that to the rewrite-loop's pieces: a rewrite is an exploration informed by canon, not an execution of canon. Canon-as-spec is the failure mode; canon-as-constraint-on-exploration is the success mode.

## 9. Substrate-receipts

- Session folder: `docs/evaluations/2026-05-27-064722-yarnnn-author-baseline-session/`
- Populated rollup: `docs/evaluations/2026-05-27-064722-yarnnn-author-baseline-session/SESSION.md` (commit `c51c44f`)
- Partition-discipline hardening: commit `d8d0e57` — `agent-composition.md` §3.2.1, `reviewer-substrate.md` §"`principles.md`" deferral, `CLAUDE.md` discoverability anchor
- Reviewer-attributed substrate writes query (verified 2026-05-27): 3 rows, all to `/workspace/review/`; zero `action_proposals` in same window
- Envelope plumbing receipt: `api/services/reviewer_envelope.py:78-110::_UNIVERSAL_ENVELOPE_DECLS` yields all five scaffolded inputs unconditionally
- Current bundle template: `docs/programs/alpha-author/reference-workspace/review/principles.md` at commit `d8d0e57` — 169 lines, ~60% reasoning-posture content per the partition-discipline diagnostic test

## Status

**Proposed 2026-05-27** — paper-design only. No bundle/code changes ship with this ADR. **Tightened 2026-05-28** to Option A shape per operator feedback: D3+D4+D5 (specific structural reshapings derived from c51c44f bug-fix-shaped reasoning) replaced by D3 (open-shaping with reshapings emergent from Piece 2 + validated by Piece 3); §8 added naming the e2e loop as validation instrument. Status flips to `Implemented` only after Pieces 2 + 3 land AND Piece 3 measurement validates the partition application closes (or productively informs) the strong-autonomy gap. Per §8, "Implemented" means the e2e loop measured an outcome, not that pieces landed exactly as paper-described.

## Last updated

2026-05-28 — Option A tightening. Decisions reduced from 8 to 6 (D1 / D2 / D3 / D6 / D7 / D8); D3 reframed to commit to iterative discovery rather than pre-declared reshapings; §8 added naming the e2e loop as validation instrument. Original 2026-05-27 draft: initial paper-design against the partition-discipline canon hardened in commit `d8d0e57` and the eval-session diagnosis in commit `c51c44f`.
