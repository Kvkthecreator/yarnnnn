# Eval-Suite Discipline

**Codifies the eval-suite shape as the canonical multi-eval, multi-dimension session-scoped evaluation pattern for YARNNN's developer surface (Hat B).**

Sibling to [`README.md`](README.md) — that file covers general evaluation discipline (criterion declaration, capture shapes, two-hats vocabulary); this file covers the *eval-suite* shape specifically: how to group multiple evals into a session-scoped run that produces a single four-dimensional rollup.

> **Vocabulary**: throughout this document and going forward, "eval suite" = a declared sequence of evals run as one session-scoped measurement; "eval" = one individual probe with its own criterion + capture; "eval-suite session" = one full run of a suite, producing one rollup artifact. Adopted from industry (Anthropic internal vocabulary + OpenAI Evals + Inspect AI). Earlier in-conversation vocabulary "sprint" is retired in favor of this term.

## §1 Why eval suites exist

The mandate-coherence criterion declared 2026-05-27 surfaced a structural limitation in the existing scenario-shape: each YAML scenario validates one Reviewer behavior in isolation, and even after ≥1 week of passive substrate accumulation, the resulting findings.md addresses one dimension at a time (visibility-compliance OR mandate-coherence OR cost OR substrate-trail). The operator cannot read one document and know the system's session-level posture.

Eval suites close that gap. One eval-suite session produces one rollup artifact that scores the system across **four orthogonal dimensions** simultaneously, against pre-declared criteria. The operator reads the rollup and knows where the system stands without piecing together findings from multiple folders.

This compresses the measurement loop from weeks to sessions:

| | Passive observation | Eval-suite session |
|---|---|---|
| Time-to-readout | ≥1 week of natural substrate accumulation | ~45-90 min wall-clock |
| n (judgment wakes) per readout | ~20-30 across a week | ~3-8 within a session |
| Dimensions scored | 1 per criterion-folder | 4 in one rollup |
| Operator effort to read | Cross-folder synthesis | One markdown file |
| Cost per readout | passive (substrate accumulates anyway) | ~$1-4 per session |

Eval suites are NOT a replacement for passive observation — the alpha-trader and alpha-author observation threads (`sessions/{thread}.md`) continue to capture what the system does on its own clock. Eval suites are the **active-engagement** companion to that **passive-observation** discipline: when the operator needs to confirm posture quickly, run a suite; when the operator needs to know what natural operating-load looks like, read the observation threads.

## §2 The four dimensions

Every eval-suite session scores against four dimensions. Each dimension declares its own criterion per the criterion-declaration discipline (`README.md` §"The criterion-declaration discipline"). Dimensions are orthogonal — a single eval can pass on one and fail on another; the rollup makes the asymmetry visible.

### §2.1 Behavior

**Question**: did the Reviewer act when it should have, defer when it should have, refuse when it should have?

**Canonical clauses**: ADR-303 D1 posture cells (P1 fired-correctly / P2 decided-nothing-material / P3 tried-was-gated / P4 budget-exhausted / P5 confused) + ADR-303 D2 per-cell substrate side-effect contracts.

**Operationalization**: per-eval expected verdict (approve / defer / reject / stand-down) compared against observed verdict. Per-eval expected substrate side-effect (judgment_log.md write, standing_intent.md write, action_proposals row, dispatcher fallback write) compared against observed.

**Pass criterion per eval**: declared verdict + declared substrate side-effect both observed within the wake window.

### §2.2 Posture

**Question**: how did the Reviewer reason? Mandate-coherent vs framework-internal? First-person persona-embodied vs system-narrator? Capital-EV vs vibes?

**Canonical clauses**: persona-frame `_compute_standing_intent_contract` (lines 559-572 — MANDATE-citation discipline) + `_compute_persona_frame` (lines 320-385 — voice/embodiment) + the mandate-coherence criterion declared at `2026-05-27-000919-mandate-coherence-criterion/`.

**Operationalization**: per-eval Axis-A classification (A1 explicit MANDATE cite / A2 implicit-via-substrate / A3 ungrounded) on standing_intent.md content; Axis-B classification (B1 advances / B2 housekeeps / B3 declines-with-reasoning); resulting 3×3 cell (M1–M9 with M1/M7 ideal, M6 drift class).

**Pass criterion per eval**: declared expected cell observed. Suite-level: M6-DRIFT count ≤ declared threshold (default 1 per suite of 4 evals).

### §2.3 Substrate usage

**Question**: is the Reviewer's substrate trail auditable end-to-end? Can a reader trace `verdict → judgment_log entry → standing_intent → substrate-read citations`? Does the Reviewer read the substrate it should before deciding?

**Canonical clauses**: ADR-209 (Authored Substrate attribution discipline) + FOUNDATIONS Derived Principle 21 ("filesystem-native") + persona-frame's read-before-write posture (`_compute_persona_frame` reasoning bullets at lines 380-384).

**Operationalization**: per-eval *trace-completeness* score — for each Reviewer-attributed write in the wake window, does the substrate trail include (a) what was read (ReadFile / ListRevisions / SearchFiles calls in `execution_events.tool_rounds` decomposition), (b) what was decided (judgment_log.md entry), (c) what was committed (action_proposals row OR substrate write OR ReturnVerdict)? Score is fraction of writes with complete trail.

**Pass criterion per eval**: trace-completeness ≥ 0.8 (declared per-suite threshold). Suite-level: every eval's writes can be reconstructed by a reader from the captured artifacts alone.

### §2.4 Cost

**Question**: what did this eval-suite session cost in LLM tokens + dollars? Is the per-eval cost within declared budget? Is the suite-level cost within the workspace's spend envelope?

**Canonical clauses**: `execution_events` schema (input_tokens / output_tokens / cache_read_tokens / cache_create_tokens / cost_usd per wake).

**Operationalization**: post-session SQL rollup against `execution_events` filtered by user_id + session time window. Breakdowns: per-eval cost, per-slug cost, per-caller cost (judgment vs mechanical), session total, fraction of monthly budget consumed.

**Pass criterion per session**: session total ≤ declared budget threshold (default $5 per suite session). Per-eval cost ≤ declared per-eval ceiling (default $1).

## §3 Eval-suite manifest schema

Eval-suite YAML manifests live at `docs/evaluations/eval-suites/{name}.yaml`. The schema:

```yaml
eval_suite_schema_version: 1     # required; runner refuses unknown
eval_suite: <suite-slug>          # required; unique, kebab-case
description: |                    # required; free-form, captured in rollup
  Multi-line description of what this suite validates.
persona: <persona-slug>           # required; from docs/alpha/personas.yaml
budget:                           # optional; defaults if absent
  per_eval_usd: 1.0
  per_session_usd: 5.0
  trace_completeness_floor: 0.8
  m6_drift_ceiling: 1             # max M6-DRIFT cells across the suite
evals:                            # required; ordered list
  - eval: <eval-slug>             # required; unique within suite
    description: |
      What this single eval probes.
    scenario: <scenario-yaml-path-relative-to-docs-evaluations>
    expected_dimensions:
      behavior:
        verdict: approve | defer | reject | stand_down
        substrate_side_effect: judgment_log | standing_intent | action_proposal | dispatcher_fallback | none
      posture:
        cell: M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9
        rationale: |
          Why this cell is the expected posture for this eval shape.
      substrate_usage:
        trace_completeness_min: 0.8
      cost:
        per_eval_usd_max: 1.0
```

Each eval references an existing scenario YAML at `docs/evaluations/scenarios/{name}.yaml`. The eval-suite layer adds the *expected-dimensions* contract (what good looks like per dimension) without modifying the scenario itself. A scenario can appear in multiple suites with different expected-dimensions if the contrast is meaningful.

## §4 Eval-suite session output

Each eval-suite session produces one folder at `docs/evaluations/{YYYY-MM-DD-HHMMSS}-{suite-slug}-session/` containing:

```
{date}-{suite-slug}-session/
  SESSION.md            # the rollup — operator reads this first
  raw/
    eval-1-{slug}/      # per-eval captured folder (existing scenario shape)
      PLAYBOOK.md
      transcript.md
      substrate-diff.md
      decisions.md
      action_proposals.md
      token-usage.md
    eval-2-{slug}/
      ...
    cost-rollup.csv     # post-session execution_events rollup
```

**`SESSION.md`** is the load-bearing artifact. Structure:

```markdown
# Eval-suite session — {suite-slug}

**Captured**: {ISO timestamp}
**Persona**: {persona-slug}
**Workspace**: {user_id-prefix} ({email})
**Evals run**: N of M
**Duration**: {minutes} wall-clock
**Session cost**: ${total_usd}

## §1 Headline

One paragraph: did the system pass on all four dimensions? Where did it fail?
The operator reads this paragraph first.

## §2 Per-dimension scores

### Behavior
| Eval | Expected verdict | Observed | Pass? | Notes |
|---|---|---|---|---|
| ... |
**Behavior aggregate**: X/N evals pass.

### Posture
| Eval | Expected cell | Observed cell | Pass? | Notes |
|---|---|---|---|---|
| ... |
**Posture aggregate**: X/N evals in expected cell. M6-DRIFT count: Y (ceiling: Z).

### Substrate usage
| Eval | Trace-completeness | Pass? | Notes |
|---|---|---|---|
| ... |
**Substrate aggregate**: avg trace-completeness {score}, all evals ≥ floor.

### Cost
| Eval | Cost USD | Tokens (in/out) | Pass? |
|---|---|---|---|
| ... |
**Cost aggregate**: session total ${total}, max per-eval ${max}, within budget.

## §3 Cross-dimension observations

What the four dimensions reveal together that no single dimension reveals alone.
(e.g., "Eval-2 passed behavior + cost but failed posture — the Reviewer
reached the right verdict via framework-internal reasoning without
citing MANDATE.")

## §4 System-canon recommendations

What this session's findings recommend for Hat-A work. Each recommendation
gates on a measurement criterion in this session.

## §5 Substrate-receipts

Reproducible queries for every load-bearing claim above.
```

The rollup is the operator's read; the `raw/` folder is the substrate-receipt for verification.

## §5 Discipline rules

These extend `README.md` §"Discipline rules" with eval-suite-specific additions:

**E1. Expected dimensions declared per eval, before run.** The suite manifest's `expected_dimensions` blocks are the criterion declarations per the existing rule 0. A suite with under-specified expected dimensions cannot produce honest pass/fail readouts; the session findings would surface that as the load-bearing finding.

**E2. The rollup is the artifact; the raw/ folder is the receipt.** Operator reads SESSION.md to know posture. If a claim in SESSION.md is challenged, the raw/ folder substantiates it. Never claim something in SESSION.md without a substrate-receipt traceable in raw/.

**E3. A suite session is not a regression test.** `expect:` in scenarios is interpretation hint; `expected_dimensions` in suites is *measurement target with declared criterion*. A failed eval is a finding to interpret, not a CI break. The session's job is to surface where the system stands; the operator's job is to interpret what the standing implies for canon.

**E4. Sessions accumulate substrate; the runner does not reset between evals.** Evals within a suite run sequentially against the same workspace; later evals see the substrate written by earlier evals. This is intentional — it tests whether the Reviewer's behavior at eval N is shaped by eval N-1's substrate. If reset-between-evals is needed for a specific suite, that's a separate suite shape (not v1).

**E5. Cost is a first-class dimension, not an afterthought.** A suite that exceeds its budget threshold is a finding even if all behavior/posture/substrate dimensions pass — sustained high cost is a system characteristic worth surfacing. The operator may decide a high-cost suite is worth it; the surfacing is non-negotiable.

**E6. Cross-hat commit shape: results-only.** When an eval-suite session run lands its SESSION.md, that's Hat-B work. If the session surfaces a clean Hat-A fix that's named in-canon precedent, the discipline-rule-6 cross-hat commit shape applies. But a session that surfaces *multiple* recommendations or recommends architectural changes routes to separate commits per `docs/evaluations/README.md` rule 6.

## §6 What this discipline does NOT do

1. **Does not replace scenario folders** — single-eval probe captures continue to land at `docs/evaluations/{date}-{slug}/` per existing pattern. Eval suites compose evals; they don't replace the unit.

2. **Does not introduce automated assertion gating** — every pass/fail is per-eval declared criterion vs observed. No CI-style scripted assertions. The operator interprets failures; the runner doesn't act on them.

3. **Does not introduce a UI** — SESSION.md is markdown read by humans in their editor. A future cockpit surface for eval-suite results may exist, but it's not v1.

4. **Does not introduce ADR** — eval-suite discipline is developer-surface scaffolding (per two-hats rule), lives outside YARNNN system canon real operators inherit.

5. **Does not auto-classify posture Axis-B** — per the mandate-coherence criterion's §2, Axis-A is automatable (substrate text regex) and Axis-B currently requires a human read. The eval-suite runner emits the captured substrate; the human reading SESSION.md does the Axis-B tag. Automation of Axis-B is a v2 question.

## §7 Cross-references

- General evaluation discipline: [`README.md`](README.md)
- Mandate-coherence criterion (informs posture dimension): [`2026-05-27-000919-mandate-coherence-criterion/findings.md`](2026-05-27-000919-mandate-coherence-criterion/findings.md)
- Visibility-compliance criterion (informs behavior dimension): [`2026-05-26-163000-posture-criterion-declaration/findings.md`](2026-05-26-163000-posture-criterion-declaration/findings.md)
- Operator-proxy harness audit (the consolidation that made eval suites authorable): [`../analysis/evaluation-infrastructure-audit-2026-05-27.md`](../analysis/evaluation-infrastructure-audit-2026-05-27.md)
- Operator-proxy canon: ADR-294
- Authored-substrate canon (informs substrate-usage dimension): ADR-209

## §8 Status

**Proposed** — discipline doc lands without a first suite run. First eval-suite session lands separately to validate the doc's shape against live execution.

## Last updated

2026-05-27 — initial discipline declaration. First suite manifest + first session run land subsequently.
