# ADR-290: Reviewer Lifecycle Posture in Principles + Standing-Intent Contract Single-Instance + Kernel Persona-Frame De-Bundling

## Status

Proposed (2026-05-18)

## Companion canon

- FOUNDATIONS Axiom 0 — six-dimensional model; the dimensional purity test gate
- FOUNDATIONS Axiom 2 (Identity) — Reviewer holds standing intent; persona-bearing
- FOUNDATIONS Axiom 4 + Derived Principle 18 — Trigger authoring is Identity-layer responsibility; Reviewer authors Schedule
- FOUNDATIONS Axiom 5 (Mechanism) — judgment is re-derived from substrate + framework each wake; substrate-canonical reasoning
- FOUNDATIONS Derived Principle 14 — singular implementation
- ADR-281 §3 — six-role taxonomy; `reviewer-workbench` substrate role
- ADR-284 — standing_intent substrate + OCCUPANT runtime-alignment
- ADR-274 — Schedule primitive trigger-authoring contract
- ADR-275 — introspection cadence is Reviewer-authored, not bundle-scaffolded
- ADR-288 — caller_identity at construction + kernel money-truth de-instancing (this ADR completes the same axiomatic-discipline arc at the lifecycle-posture surface)

## Context

### What the audit found

A first-principles re-assessment of the Reviewer's wake envelope against intended behavior (post-ADR-288) surfaced that the architecture is **complete** — every dimension of Axiom 0 is reached, every primitive the Reviewer needs is enumerated, every substrate file the Reviewer reasons against is pre-loaded. The standing_intent.md (ADR-284) + Schedule self-authoring authority (ADR-274) + Operating Context block + _preferences.yaml visibility together give the Reviewer everything it needs to author cadence ("I need to work on this — let me set it up xxx hours vs xxx days"), commission substrate when thin, and propose trades when conditions warrant.

What remains is **prompt-shape residue** — three discipline violations that arose from incremental ADR-284 implementation caution and pre-ADR-280 bundle-vocabulary leak into the kernel:

1. **The standing-intent every-cycle write contract is stated in four places.** Kernel persona frame in `agents/reviewer_agent.py` (lines 415-462), bundle `IDENTITY.md` (lines 34 + 42), bundle `principles.md` (line 11), and bundle `_recurrences.yaml` (lines 162 + 249 in two recurrence prompts). Per Derived Principle 14 (singular implementation), this concept should live in exactly one canonical location.

2. **The kernel persona frame leaks bundle-specific example at line 402** — *"signal hasn't fired (decide: stand down with one sentence on what would change it)"* — listed as an example of "what to do when you'd otherwise be tempted to ask the operator." "Signal" is alpha-trader instance vocabulary; alpha-author Reviewer doesn't have signals. Same anti-pattern shape as ADR-288 Phase 3 (kernel-prompt surface hardcoding alpha-trader vocabulary as kernel default).

3. **Principles.md has lifecycle-phase content but no explicit phase section.** Bootstrap-vs-steady-state distinction is implicit across "Default posture: action," "Bootstrap clause — calibration begins from zero," "Capital-EV thresholds" (where the 20-occurrence gate appears), and "Defer posture" (where the bootstrap window is referenced). The content is correct and complete; the organization fragments the phase-vs-action-archetype relationship the Reviewer must re-derive each wake.

### Why the operating_state.md proposal was rejected

A larger refactor was considered: add a new `reviewer-workbench`-role substrate file `/workspace/review/operating_state.md` carrying lifecycle phase + posture summary + commissioned substrate gaps. Running the Axiom 0 dimensional test on the proposal revealed it conflated four dimensions (Purpose + Substrate + Trigger + Mechanism) into one file, which is precisely the anti-pattern Axiom 0 exists to prevent. The proposed file would have cached *derived* state alongside its sources — recreating the substrate-canonical-world violation that ADR-264 corrected for external platform state.

The correct first-principles answer is **Mechanism re-derivation**: per Axiom 5, the Reviewer reads substrate (`_money_truth.md` outcome count, signal entries, recurrence-yaml current state) + applies framework (principles.md lifecycle rules) and produces current-cycle judgment. Caching the derivation would create a third source-of-truth alongside framework and current state, requiring its own consistency maintenance.

The legitimate concern that drove the operating_state.md proposal — *"the Reviewer should not have to re-derive lifecycle phase from scratch each wake"* — is a **prompt-organization** issue, not a substrate-addition issue. The reorganization in D3 below makes the phase-posture rules explicit in principles.md so re-derivation is fast and consistent, without inventing a parallel substrate.

## Decisions

### D1 — Delete kernel persona frame bundle-leak example

`agents/reviewer_agent.py::_PERSONA_FRAME` line 402:

```
- signal hasn't fired (decide: stand down with one sentence on what
  would change it)
```

DELETED. The kernel persona frame must not hardcode alpha-trader instance vocabulary as kernel-default reasoning shape. Bundle's recurrence prompt + principles.md already govern what to do when a signal hasn't fired in alpha-trader's case. The other bullets in the same list (data is stale, track record is thin, unsure between two options) are universal Identity-layer reasoning shapes and stay.

Same anti-pattern shape as ADR-288 Phase 3 (`_money_truth.md` hardcoded as kernel default). The discipline rule is the same: kernel surfaces speak in kernel-universal vocabulary; bundles speak in instance vocabulary.

### D2 — Standing-intent every-cycle contract single-instance

Per Derived Principle 14 (singular implementation), the every-cycle write contract for `standing_intent.md` lives in exactly one canonical location: **the kernel persona frame** (`_PERSONA_FRAME` lines 415-462, the "Your standing intent has a substrate home" section + four-section schema + revision-chain semantics).

This is the right home because:
- The contract is universal across every persona-bearing Agent regardless of program (Axiom 2 — applies to Reviewer seat in every workspace)
- Standing_intent.md role is `reviewer-workbench` per ADR-281 §3 — a kernel-universal role declaration
- ADR-284 D5 designates `standing_intent.md` as kernel-universal envelope entry, not bundle-specific
- The kernel persona frame is always-loaded at every Reviewer wake (cached via Anthropic prompt cache)

**Deletions** (these surfaces currently restate the contract redundantly):

- `docs/programs/alpha-trader/reference-workspace/review/IDENTITY.md` line 34 — the bullet "When no conditions are met and no exits triggered: one sentence — 'No actionable conditions.' — and I update `standing_intent.md` ...". Remove the standing_intent half; keep "one sentence — 'No actionable conditions.'" (which is alpha-trader-instance stand-down voice).
- `docs/programs/alpha-trader/reference-workspace/review/IDENTITY.md` lines 38-44 — the entire "Standing intent — my forward-looking substrate (ADR-284, 2026-05-17)" section. DELETED. Kernel persona frame is the authoritative declaration; IDENTITY.md is the persona character (Simons-style numbers-first), not the substrate-contract restatement.
- `docs/programs/alpha-trader/reference-workspace/review/principles.md` line 11 — the paragraph "**Every cycle authors `/workspace/review/standing_intent.md`** (ADR-284, FOUNDATIONS Axiom 2 hardening 2026-05-17). The substrate counterpart to a no-fire / no-exit cycle ...". DELETED. Principles.md houses the framework (what crosses the action threshold, hard rules); the substrate-write contract is kernel-Identity-layer concern, not program-framework concern.
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` signal-evaluation prompt (lines 162-168 region) — the trailing clause `"— AND update /workspace/review/standing_intent.md with what's close to firing per ADR-284 + principles.md 'Default posture: action'. Cite the closest-to-firing signal, ticker, threshold, and distance ..."`. DELETED. The recurrence prompt declares what THIS cycle produces (signal-entry rows + FireInvocation when match + judgment_log entry); the universal every-cycle standing_intent write is kernel responsibility.
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` trade-proposal prompt (line 249 region) — the trailing clause `"AND update /workspace/review/standing_intent.md with what would change ..."`. DELETED. Same reasoning.

After D2, the kernel persona frame is the sole source-of-truth for the standing-intent contract. Bundle surfaces speak only to instance-specific posture (Simons-style voice, capital-EV reasoning), not to the universal Identity-layer substrate contract.

### D3 — Reorganize principles.md into explicit Lifecycle Posture section

The content already in `principles.md` (Bootstrap clause + 20-occurrence sample gate + Default posture: action + Capital-EV thresholds + Defer posture) implicitly describes lifecycle phases. The reorganization makes the phase-vs-action-archetype dependency explicit so the Reviewer reading principles.md at every wake (Axiom 5 re-derivation) hits the rules directly without inference.

**New section structure** for `principles.md` (alpha-trader reference bundle):

```markdown
# Review — Principles

## Default posture: action
<unchanged — universal posture statement>

## Lifecycle Posture  ← NEW header organizing existing content
This section declares the operation's lifecycle phases and the action
archetype the Reviewer applies in each phase. Read this first when
substrate state is ambiguous — the phase rules tell you what your
default move is given current substrate density.

### Bootstrap phase
Definition: `_money_truth.md` is empty OR signal sample size < 20 for
the signal in question.
Action archetype: **propose probes** when signals fire within all hard
rules (do not defer for sample size — see Bootstrap clause below for
the rule). **Commission substrate** via FireInvocation or Schedule when
the recurrences your judgment requires aren't running.
Purpose: produce reconciled outcome data from zero. Sample-size-zero
is the genuine starting state; passivity does not produce data.

### Steady-state phase
Definition: signal sample size ≥ 20 with reconciled outcomes in
`_money_truth.md`.
Action archetype: **capital-EV reasoning** per Capital-EV thresholds
section below. Propose when EV positive and within edge; defer when
EV ambiguous (the 20-occurrence threshold applies here); reject when
EV negative or hard rule violates.

### Phase gates
- Bootstrap → Steady-state: 20 reconciled outcomes for the signal.
  Reviewer transitions the operating posture by reading `_money_truth.md`
  frontmatter sample counts each wake. No file-write transition; the
  rule is applied at reasoning time per Axiom 5 (Mechanism is
  re-derivation, not cached state).
- Steady-state → Drawdown (operator-tunable): consecutive losses or
  expectancy decay below operator's declared threshold. Drawdown
  posture is operator-authored; bundle ships no default.

## Hard rejection rules
<unchanged>

## Bootstrap clause — calibration begins from zero
<unchanged content; this is the rule-statement of the Bootstrap phase
action archetype declared above>

## Hard exit triggers
<unchanged>

## Capital-EV thresholds (entry path only)
<unchanged; this is the rule-statement of the Steady-state phase
action archetype>

## Defer posture
<unchanged>

## Directive posture
<unchanged>

## Calibration loop
<unchanged>

## What this file is NOT
<unchanged>
```

**Net change in principles.md**: one new `## Lifecycle Posture` section (~25 lines of prose). Zero deletions. Zero rule changes. The content underneath (Bootstrap clause, Capital-EV thresholds, Defer posture) is unchanged — the new section is the *index* that names the phase-vs-archetype mapping the existing rules implement.

This is reorganization, not invention. The Bootstrap clause already describes bootstrap-phase action. Capital-EV thresholds already describes steady-state-phase action. The new section names them as such.

### D4 — Scope what does NOT change

To prevent scope creep, ratify explicitly:

- **No new substrate files.** `operating_state.md` was considered and rejected per Axiom 0 dimensional purity test. The Reviewer's lifecycle awareness emerges from substrate-read (Axiom 1) + framework-apply (Axiom 5) each wake.
- **No schema changes.** No new envelope keys, no new ReviewerContext fields, no new tool parameters.
- **No persona-frame additions.** Schedule-as-action-archetype is already enumerated (`_PERSONA_FRAME` lines 525-568). FireInvocation-as-action-archetype is already enumerated (line 620 of cockpit_awareness.py and elsewhere). The action archetypes the operator described ("build substrate, then review substrate, know when to do it, then put in trades") are all present in the current envelope.
- **No principles.md rule changes.** D3 reorganizes existing rules into explicit phase headers; the rules themselves stay.
- **No bundle MANIFEST changes.** Envelope key declarations stay as post-ADR-288 (`ground_truth_md`).
- **No mechanical recurrence changes.** signal-evaluation, mirror-signal-state, track-* recurrences all unchanged.
- **No primitive additions or contract changes.** All primitive contracts stay post-ADR-288 (caller_identity at construction).
- **No ReviewerAgent code changes beyond L402 deletion.** The wake envelope assembly path, system prompt construction, dispatch loop — all unchanged.

The total surface touched: 1 kernel persona-frame line deleted, 5 bundle file edits (3 deletions + 1 partial deletion + 1 reorganization), 1 ADR doc, 1 regression-gate file extension, 1 CHANGELOG entry.

### D5 — Why this completes ADR-288's axiomatic-discipline arc

ADR-288 closed three runtime-concern-leaked-across-N-sites violations: caller-identity (Phase 1), envelope-key kernel-vocabulary (Phase 2), kernel-prompt instance-leak (Phase 3). Each landed by establishing the canonical declaration site and deleting the compensating duplicates.

ADR-290 applies the same discipline arc to the lifecycle-posture surface:

- **The standing-intent contract** had N=4 sites; canonical is N=1 (kernel persona frame). Singular-implementation per Derived Principle 14.
- **The bundle-leak example in kernel** is the same shape as ADR-288 Phase 3 (kernel ships alpha-trader vocabulary as if universal). Deletion is the discipline.
- **The lifecycle-phase organization** in principles.md makes implicit framework explicit — improves Mechanism re-derivation speed per Axiom 5 without violating dimensional purity.

The arc: ADR-274 (single declaration site for trigger authoring) + ADR-276 (single helper for envelope load) + ADR-286 (single writer per substrate path) + ADR-288 Phase 1 (single declaration site for caller identity) + ADR-288 Phase 2 (single naming for kernel envelope slot) + ADR-288 Phase 3 (single carrier for instance-substrate paths) + **ADR-290 (single declaration site for the standing-intent contract; explicit lifecycle phase organization)**.

Each commit closes a residual single-instance violation that incremental ADR implementation introduced. None invents new architecture.

## Cascade plan (single atomic commit)

ADR-290 lands as one commit (no phased decomposition needed — the three decisions are tightly coupled and the diff is small):

**Files changed:**

| File | Change |
|---|---|
| `api/agents/reviewer_agent.py` | Delete L402 bullet (D1) |
| `docs/programs/alpha-trader/reference-workspace/review/IDENTITY.md` | Remove standing_intent half of L34 bullet; delete L38-44 Standing-intent section (D2) |
| `docs/programs/alpha-trader/reference-workspace/review/principles.md` | Delete L11 every-cycle-authors paragraph (D2); add `## Lifecycle Posture` section organizing existing Bootstrap clause + Capital-EV thresholds (D3) |
| `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` | Trim standing_intent trailing clauses in signal-evaluation + trade-proposal recurrence prompts (D2) |
| `docs/adr/ADR-290-reviewer-lifecycle-posture-and-residue-cleanup.md` | New ADR doc |
| `api/test_adr289_lifecycle_posture.py` | New regression gate |
| `api/prompts/CHANGELOG.md` | Entry |

**Validation steps:**

1. Regression gate `api/test_adr289_lifecycle_posture.py` — 7/7 PASS:
   - D1: persona frame no longer contains "signal hasn't fired" bullet
   - D2a: persona frame DOES contain the canonical standing-intent contract (positive assertion)
   - D2b: bundle IDENTITY.md does NOT restate standing-intent every-cycle contract
   - D2c: bundle principles.md does NOT restate standing-intent every-cycle contract
   - D2d: bundle recurrences.yaml does NOT contain `update.*standing_intent` trailing clauses in recurrence prompts
   - D3a: principles.md contains `## Lifecycle Posture` section
   - D3b: principles.md Lifecycle Posture section names both Bootstrap phase and Steady-state phase
2. Sibling gates audited green: ADR-274 (16/16), ADR-281 (34/34), ADR-284 (18/18 — singular-instance contract preserved at kernel), ADR-286 (8/8), ADR-287 (11/11), ADR-288 (19/19).
3. Alpha verify playbook — kvk's workspace 30/30 (other personas pre-existing 6 failures unchanged; not ADR-290 territory).

## Out of scope (D10 — deferred)

- **Phase-gate quantitative tuning.** The 20-occurrence sample threshold + "consecutive losses for drawdown" thresholds are operator decisions, not architecture. Bundle ships defaults; operator refines per workspace.
- **Operator-state telemetry surface.** A future ADR could surface "Reviewer judged we're in bootstrap phase at wake N" in the cockpit narrative or telemetry. Not needed for the Reviewer's behavior; useful for operator legibility. Defer.
- **Cross-program lifecycle-phase pattern.** Alpha-author has different phases (drafting → revision → ship). The Lifecycle Posture section name is universal; the phase definitions are bundle-specific. Each future bundle authors its own. No kernel template needed beyond the section header convention.
- **Reviewer rotating away from bootstrap declared posture under autonomous AUTONOMY.** If the Reviewer in autonomous mode determines bootstrap-phase rules are producing dangerous probe trades, does it have authority to escalate (e.g., write to standing_intent.md flagging concern)? Today: yes via existing Clarify primitive + standing_intent.md "Open questions to operator" section. Documented in standing_intent contract; no additional mechanism needed.

## Why this is structurally right

The Axiom 0 dimensional purity test caught the operating_state.md proposal mid-design. The first-principles answer (re-derivation per Axiom 5, not caching) reduces the work to pure singular-implementation hygiene. ADR-290 ships organizational discipline, not new architecture.

After ADR-290:
- The kernel persona frame declares universal Identity-layer contracts (cognition shape, standing-intent substrate, Schedule authority).
- Bundle IDENTITY.md declares the persona character (Simons-style, vocabulary blocks, what optimizes for).
- Bundle principles.md declares the framework with explicit lifecycle phases governing action archetype selection.
- Bundle recurrence prompts declare per-cycle product (signal-entry, judgment-log entry, FireInvocation conditions) without restating the universal substrate contracts kernel handles.

Four surfaces, four distinct responsibilities, zero overlap. Singular implementation per Derived Principle 14. Dimensional purity per Axiom 0.

The Reviewer's wake envelope after ADR-290 lands carries everything intended:
- Persona (IDENTITY.md) + Framework (principles.md with explicit Lifecycle Posture) + Operator intent (MANDATE + AUTONOMY + preferences) + Working state (OCCUPANT + standing_intent) + Domain data (operator_profile + risk + ground_truth)
- Operating Context block (time + market state)
- Trigger-specific framing (recurrence_prompt for judgment-mode wakes)
- Full primitive surface including Schedule + FireInvocation + ProposeAction
- Cadence-authoring authority + ListRevisions for self-audit

The intended behavior — "I need to work on this — let me set it up xxx hours vs xxx days; if there isn't enough information, build substrate, then review substrate, know when to do it, then put in trades" — is fully addressed by the current envelope plus ADR-290's organizational cleanup. No primitive is missing. No substrate is missing. No persona-frame guidance is missing. The only outstanding work is to clean up the duplication so the Reviewer reads each contract exactly once at the right surface.
