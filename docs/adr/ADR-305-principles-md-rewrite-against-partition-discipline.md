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

### D3 — Auto-approve binding under AUTONOMY=autonomous is decoupled from the amendment threshold

The session's load-bearing finding was that the 10-audit sample-size floor (current `principles.md` line 59 — *"first 10 audits are all `manual` regardless of `_autonomy.yaml` configuration"*) gates the **ship-binding** path. Independent of that, the Reviewer also has the capability to author `Schedule()` calls for declared `_preferences.yaml` cadences per ADR-275 (the lowest-bar amendment per the ADR-295 categories — "cadence-driven"). The cadence-driven path is **not** sample-size gated and **should** bind under autonomous mode from the first wake the preference is detected.

Post-rewrite, `principles.md`'s auto-approve clause reads as:

- **Ship-binding** (auto-approve a draft on Reviewer's approve verdict): sample-size-gated per program (yaml-tuned). Bootstrap-clause exception applies for first-N audits per M3.
- **Cadence-binding** (author `Schedule()` for an operator-declared preference): NOT sample-size-gated. Under `autonomous`, Reviewer authors the recurrence directly; under `bounded`, routes through `action_proposals` for operator click.
- **Operator-canon-binding** (edit `_voice.md`, `_editorial.md`, etc.): evidence-threshold-gated per `_principles.yaml`. Persona-frame's `_compute_self_amendment_discipline` is the discipline; principles.md declares the substrate anchor for the threshold (it lives in yaml; principles.md cites the yaml path).

The three binding paths are distinct rules with distinct gating; the current `principles.md` collapses them under one "Audit-EV thresholds" section that effectively gates *all* binding behind the ship-loop sample size. The rewrite separates them.

### D4 — Bootstrap clause is per-rule, not file-wide

Today's `principles.md` has a separate "Bootstrap clause" section (lines 52–59) that describes what happens when `_signal.md` is empty. Per M3, bootstrap behavior is part of each rule's declaration, not a separate section. Post-rewrite: each rule that has bootstrap behavior names it inline in field #3 (Pass condition).

Example rewritten rule:

```
### Rule: voice-fingerprint-match

- **Substrate read**: `/workspace/context/authored/_voice.md` (positive patterns) + draft's prose
- **Pass condition (steady-state)**: draft matches ≥1 positive pattern AND zero anti-pattern violations.
  Steady-state activates when `_signal.md` has ≥3 prior audit outcomes for this workspace.
- **Pass condition (bootstrap)**: `_signal.md` has <3 prior audits. Draft passes if zero anti-pattern
  violations (positive-pattern match is waived; the positive declaration calibrates against ship outcomes
  per M2, which haven't accumulated yet).
- **Verdict on fail**: `reject` (unconditional — voice is a hard floor per MANDATE's anti-AI-slop clause).
```

Bootstrap-state and steady-state are both rules-of-judgment; they belong inside the rule, not in a parallel meta-section.

### D5 — Anti-AI-slop hard-rejection list stays in `principles.md` (rules), moves anti-pattern enumeration to `_voice.md` (substrate)

Today's `principles.md` lines 18–24 enumerate anti-slop patterns (list-of-three openers, "in conclusion", etc.). Per the partition: the **rule** ("anti-slop hard-rejects on ≥1 violation") belongs in `principles.md`; the **enumeration of which patterns count** belongs in `_voice.md` as substrate (the operator's authored voice declaration). The rule reads against `_voice.md`'s anti-pattern list; operators tune the list without editing principles.md.

This is a substrate-anchor cleanup, not a behavioral change. Today's enumeration is duplicated (it lives in both `principles.md` AND `_voice.md::anti-patterns`); post-rewrite, principles.md cites `_voice.md::anti-patterns` as the substrate, single source of truth.

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

### D8 — Re-interpretation of eval-4 (pressure-resistance) rubric

The `yarnnn-author-baseline.yaml` eval-4 expected rubric cites *"ADR-295 D3 anti-pattern (1) AND/OR MANDATE Boundary Conditions"* as the authority the Reviewer's amendment-refusal is grounded in. Post-rewrite:

- The ADR-295 D3 anti-patterns (the six "do NOT amend operator-canon" cases) live **exclusively** in `_compute_anti_patterns` in persona-frame.
- `principles.md` carries the **rule** ("operator-canon amendment is gated; persona-frame discipline applies") with a citation pointer to the persona-frame's home for the discipline.
- The rubric's citation target shifts: the Reviewer's refusal cites MANDATE Boundary Conditions (rules of judgment) AND/OR cites the persona-frame discipline by name ("per my self-amendment discipline anti-pattern #2 — amend on single-wake friction"). The rubric remains a `M1` or `M2` posture cell; the trace from refusal to authority still passes.

Eval-suite YAML changes are NOT in this ADR's scope (Hat-B work, deferred to Piece 3 of the sequence). The ADR names the citation-target shift so Piece 3 can update the rubric in the same session as the re-run.

## 3. Application — what the rewrite produces (shape, not content)

Post-application of D1–D7 to `docs/programs/alpha-author/reference-workspace/review/principles.md`, the file's section structure becomes:

1. **§1 Purpose** — one paragraph naming the file as the rule-set the persona applies; pointer to `agent-composition.md` §3.2.1 as the partition-discipline canon.
2. **§2 Rules** — N named rules, each in the four-field shape. For alpha-author, expected rules (illustrative, finalized in Piece 2): `voice-fingerprint-match`, `anti-slop`, `text-continuity`, `entity-continuity`, `voice-declaration-present`, `engagement-bait-refusal`, `hot-take-refusal`, `cadence-on-pace`. Each rule has bootstrap + steady-state pass conditions per D4.
3. **§3 Auto-approve binding** — declares the three binding paths (ship, cadence, operator-canon) per D3, citing yaml-tuned thresholds.
4. **§4 Conflict resolution** — ratification per D6, no new content.
5. **§5 What this file is NOT** — short pointer list to persona-frame `_compute_*` sections + AUTONOMY.md + MANDATE.md + IDENTITY.md for the concerns that don't live here.

Expected length: 70–100 lines (vs. current 169). Numeric thresholds live in `_principles.yaml` per D2; the prose file cites the yaml.

The shape for alpha-trader's rewrite is **structurally identical** (D1's four-field shape, D2's calibration methodology, D3's three binding paths, D4's per-rule bootstrap, D6's conflict-resolution ratification); the **rules in §2 differ per program** (capital-EV rules for alpha-trader vs. corpus-coherence rules for alpha-author), and **the yaml numbers differ per program** (D2's methodology applied to each program's loop-cycle).

## 4. What this ADR does NOT do

- **Does not rewrite the bundle templates.** That's Piece 2 (alpha-author) + Piece 4 (alpha-trader) of the sequence. This ADR is paper-design declaring the partition application + calibration methodology; the rewrite is a separate doc-change commit per program.
- **Does not declare specific numeric thresholds** for either program's `_principles.yaml`. Per D2 M4, the numbers are downstream of the methodology and are reviewable as bundle-template diffs in their respective rewrite commits.
- **Does not migrate production workspaces.** Per D7, the rewrite is bundle-template-only; existing operator-authored content is preserved per ADR-209.
- **Does not change envelope plumbing.** `reviewer_envelope.py::_UNIVERSAL_ENVELOPE_DECLS` continues to yield `principles_md` unconditionally; the file's role in the wake envelope is unchanged.
- **Does not change ADR-295's persona-frame canon.** The amendment-discipline categories (calibration-driven / near-miss-driven / substrate-gap-driven / cadence-driven / persona-developmental) survive as the universal taxonomy in `_compute_self_amendment_discipline`; only the per-program numeric tuning moves to `_principles.yaml` per M4. ADR-295's status note about "v2 amendment expected" is partially closed by this ADR — the methodology piece is here; the numerics land per program in their respective rewrites.
- **Does not change ADR-303's posture-cell taxonomy.** P1–P5 cells survive in `_compute_standing_intent_contract`; the cell that previously had ambiguous overlap with principles.md ("every cycle authors standing_intent.md") is unambiguously persona-frame post-rewrite.
- **Does not change `_compute_*` persona-frame sections.** This ADR establishes that those sections are the **destination** for the absorbed reasoning-posture content; it does not edit them. If the audit of the persona-frame against the post-rewrite `principles.md` reveals gaps (e.g., a reasoning-posture concept that lived in principles.md and doesn't yet have a `_compute_*` home), that's a separate follow-up ADR.
- **Does not change eval-suite YAML.** Per D8, the rubric re-interpretation happens in Piece 3 (eval re-run) as part of the SESSION.md authoring; no eval YAML changes ship with this ADR.
- **Does not address the eval-9 hallucination root cause (§1 cause (b)).** That's a separate persona-frame discipline edit ("re-read envelope when standing_intent contradicts current substrate") tracked in the c51c44f SESSION.md §4 recommendation 2; out of scope for this ADR.

## 5. Singular Implementation compliance

- **One partition home**: `agent-composition.md` §3.2.1. This ADR cites it; does not re-state.
- **One rewrite path per program**: bundle-template at `docs/programs/{slug}/reference-workspace/review/principles.md` + `_principles.yaml`. No parallel migration mechanism for existing workspaces (per D7 + ADR-209).
- **One amendment-discipline home in code**: `_compute_self_amendment_discipline` + `_compute_anti_patterns` in `api/agents/reviewer_agent.py`. ADR-295's categories survive as the universal taxonomy; this ADR does not introduce a parallel home.
- **One numeric-threshold home per program**: `_principles.yaml` (ADR-254 machine-parsed). Prose-declared categories in `principles.md` cite yaml paths; no thresholds live in prose.

## 6. Risks + Open Questions

- **R1 — alpha-trader's existing `principles.md` may already conform to the four-field shape.** If so, the alpha-trader rewrite in Piece 4 is a smaller edit (mostly methodology citation + yaml separation), not a full rewrite. Audit needed before Piece 4 commences.
- **R2 — The "cadence-binding NOT sample-size-gated" decision (D3) may be wrong if operators want a probationary period before any Reviewer-authored Schedule writes.** The current ADR-275 D5 implementation assumes Reviewer authors Schedule() from first wake the preference is detected. If operator probation is desirable, that's a per-program tuning in `_principles.yaml` (e.g., `cadence_binding_probation_wakes: 3`), not an ADR-level decision. Flagged for Piece 2 review.
- **R3 — Some reasoning-posture content currently in `principles.md` may not yet have a persona-frame `_compute_*` home.** Per §4 "Does not change `_compute_*` persona-frame sections", the audit happens post-rewrite. Expected destinations: self-amendment evidence-threshold categories → `_compute_self_amendment_discipline`; bootstrap calibration meta → `_compute_self_amendment_discipline` (it's the same concern, viewed from a different angle); fiduciary principle → `_compute_self_amendment_discipline` D4. If a concern has no home, that's a flag for a `_compute_*` extension ADR.
- **R4 — Workspace-lifecycle phase progression** is currently partially in `AUTONOMY.md` ("Phase 0 / Phase 1 / Phase 2 / Phase 3") and partially in `principles.md` ("first 10 audits are all manual"). The two should not drift. Per D4, phase-gating belongs in each rule's pass condition (rules-side), with AUTONOMY.md declaring the lifecycle phases as a stable enum. The rewrite normalizes against this.
- **R5 — Eval-suite re-run (Piece 3) may surface that the rewrite alone is insufficient** — i.e., even with the partition applied, the Reviewer still doesn't bind operator-visible action. That would point at the eval-9 hallucination root cause (cause b, §1) or at an envelope-distance issue not yet diagnosed. The session's SESSION.md §4 has the recommendations queued; if Piece 3 reproduces the "zero operator-visible writes" finding, those persona-frame edits become priority Piece 5.

## 7. Phased Implementation

This ADR is paper-design. The phased implementation referenced is the **sequence laid out in session `2026-05-27` post-`d8d0e57`**:

- **Piece 1 (this ADR)** — paper-design ADR-305. Proposed → operator review → Implemented status flip when ratified.
- **Piece 2** — alpha-author bundle rewrite. Touches `docs/programs/alpha-author/reference-workspace/review/principles.md` + `_principles.yaml` only. Cites ADR-305.
- **Piece 3** — eval-suite re-run against a freshly-forked alpha-author workspace. Touches `docs/evaluations/` only. Cites Piece 2's commit; produces a new SESSION.md.
- **Piece 4** — alpha-trader bundle rewrite. Touches `docs/programs/alpha-trader/reference-workspace/review/principles.md` + `_principles.yaml` only. Cites ADR-305 + Piece 2 + Piece 3.

The sequencing is order-dependent. Each piece's commit explicitly cites the prior piece's commit hash in its body. This ADR's status doesn't flip to `Implemented` until all four pieces land — `Implemented` here means "the partition is applied across both program bundles + validated against eval re-run."

## 8. Substrate-receipts

- Session folder: `docs/evaluations/2026-05-27-064722-yarnnn-author-baseline-session/`
- Populated rollup: `docs/evaluations/2026-05-27-064722-yarnnn-author-baseline-session/SESSION.md` (commit `c51c44f`)
- Partition-discipline hardening: commit `d8d0e57` — `agent-composition.md` §3.2.1, `reviewer-substrate.md` §"`principles.md`" deferral, `CLAUDE.md` discoverability anchor
- Reviewer-attributed substrate writes query (verified 2026-05-27): 3 rows, all to `/workspace/review/`; zero `action_proposals` in same window
- Envelope plumbing receipt: `api/services/reviewer_envelope.py:78-110::_UNIVERSAL_ENVELOPE_DECLS` yields all five scaffolded inputs unconditionally
- Current bundle template: `docs/programs/alpha-author/reference-workspace/review/principles.md` at commit `d8d0e57` — 169 lines, ~60% reasoning-posture content per the partition-discipline diagnostic test

## Status

**Proposed 2026-05-27** — paper-design only. No bundle/code changes ship with this ADR. Operator review pending; on ratification, Status flips to `Implemented` after Pieces 2–4 land.

## Last updated

2026-05-27 — initial draft. Authored against the partition-discipline canon hardened in commit `d8d0e57` and the eval-session diagnosis in commit `c51c44f`.
