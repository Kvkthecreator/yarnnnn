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

## §1.4 Industry alignment (foundations are conventional, domain is the novel layer)

This framework is structurally a **standard LLM eval suite** in the style of OpenAI Evals, Anthropic's internal eval patterns, Inspect AI (UK AISI), LangSmith, and Braintrust. The building blocks are industry-axiomatic:

| Industry pattern | Where it appears here | Reference |
|---|---|---|
| **Eval suite** as a declared collection of evals run together with shared rollup | This entire framework | OpenAI Evals, Anthropic internal, Inspect AI |
| **Per-eval contract** (declared inputs + expected outputs) | `substrate_inputs:` + `expected_dimensions:` blocks | Standard LLM eval pattern; structurally Given/Then from BDD |
| **Behavioral eval** (input held; behavior probed) | §1.6 below — most of our existing 4 evals | Standard behavioral testing |
| **Red-team eval** (adversarial probe; resistance test) | §1.6 below — `pressure-resistance` is structurally red-team | Industry adversarial-eval pattern |
| **Counterfactual eval** (input varied; behavior delta observed) | §1.6 below — substrate-mutation evals (proposed) | ML/RL counterfactual evaluation; LLM counterfactual prompting literature |
| **Rubric-dimensional scoring** | The 4 dimensions (behavior / posture / substrate-usage / cost) | HELM (Stanford), LangSmith multi-metric, Anthropic internal rubrics |
| **Human evaluation** for fields automated scoring can't reach | Axis-B posture tagging is a human-read column | Standard practice; automated alternative = LLM-as-judge (v2 path) |
| **Cost as a first-class eval dimension** | §2.4 below | Increasingly standard in production LLM eval tools |

**The novel layer is the agent class, not the framework.** What's specific to YARNNN — and what's worth being honest about — is that we apply this conventional eval discipline to an unusual class of agent: a **substrate-driven, stateful, file-native LLM agent** (the Reviewer). The agent's prompt envelope is *constructed from* operator-authored substrate files at wake-time; its behavior is supposed to be a function of substrate state. That class of agent is not yet a standard target for LLM-eval frameworks; the substrate-as-prompt + substrate-driven-behavior framing in §1.5 is the domain specialization.

**This ordering matters.** Stable foundations come from what's already proven; experimental layers ride on top. The eval-suite shape, the per-eval contract, the behavioral/counterfactual distinction, and the rubric-dimensional scoring are all axiomatic. The substrate-driven-agent specialization (the five scaffolded inputs, the substrate→envelope→behavior mapping, the M1-M9 mandate-coherence cells) is the experimental layer that may evolve. When you describe this framework externally (blog, talk, GTM material), lead with the conventional vocabulary; the domain specialization explains why YARNNN's framework looks slightly different from a typical LLM eval suite.

## §1.5 The substrate→envelope→behavior mapping (the load-bearing thesis)

**Eval suites test whether Reviewer behavior is a function of the scaffolded workspace substrate.** This is the load-bearing thesis — without it, evals devolve into "did the system produce some output" telemetry rather than "did the system reason the way canon claims it should given what the substrate declares."

The mapping chain:

```
scaffolded substrate files     →  prompt envelope assembly         →  Reviewer behavior + posture
{MANDATE, AUTONOMY, _pace,        ReviewerContext fields rendered     {verdict, substrate writes,
 _preferences, principles,        into user message by                  tool calls, mandate-cite,
 IDENTITY} + wake_source +        _build_user_message + envelope        cell distribution per
 operating_context                helper per ADR-274 / ADR-276}         ADR-303 D1 posture cells}
```

Each eval declares **which scaffolded inputs it tests against** + **what behavior the substrate state implies**. A failed eval is evidence of one of four causes, each pointing at a different fix:

| Failure cause | Diagnostic signal | Fix location |
|---|---|---|
| (a) Substrate doesn't say what we thought | Re-reading the declared file shows different content than assumed | Substrate edit (operator or Reviewer self-amendment per ADR-295) |
| (b) Reviewer doesn't read it canon way | Substrate present in envelope, but Reviewer's reasoning ignores it | Persona-frame discipline tightening (Hat-A) |
| (c) Prompt envelope doesn't deliver it | File on disk but not in `_UNIVERSAL_ENVELOPE_DECLS` / `ReviewerContext` / `_build_user_message` | Envelope plumbing fix (Hat-A) |
| (d) Canon itself is mis-specified | Substrate, envelope, Reviewer all working as designed but produce wrong outcome | ADR amendment (Hat-A canon work) |

Without the substrate→envelope→behavior mapping declared per eval, a failure surfaces as "the system didn't pass" with no diagnostic vector. With the mapping declared, the eval narrows the fix location automatically.

### §1.5.1 The five scaffolded substrate inputs

Per FOUNDATIONS + ADR-194 v2 / ADR-274 / ADR-275 / ADR-298 / ADR-296 v2, the five operator-authored substrate inputs that shape Reviewer behavior:

| Input | File / source | Canon | Plumbing layer |
|---|---|---|---|
| **MANDATE** | `/workspace/context/_shared/MANDATE.md` | ADR-194 v2, ADR-207 | `mandate_md` field on `ReviewerContext`, rendered into user message |
| **AUTONOMY** | `/workspace/context/_shared/_autonomy.yaml` + `AUTONOMY.md` | ADR-254, ADR-293 | `autonomy_md` field, rendered; binding via `should_auto_apply` in dispatch |
| **PACE** | `/workspace/context/_shared/_pace.yaml` | ADR-298 D11 | `pace_yaml` field, rendered; enforced via `Schedule()` primitive pace-gate |
| **PREFERENCES** | `/workspace/context/_shared/_preferences.yaml` | ADR-275 | `preferences_yaml` field, rendered; Reviewer authors `Schedule()` per declared cadences |
| **wake-source** | (no scaffolded file; ADR-296 v2 taxonomy) | ADR-296 v2 | `wake_source` + `triggering_path` + `triggering_revision_id` fields on `ReviewerContext`, rendered as `## Wake context` block |

(Plus `principles.md`, `IDENTITY.md`, `OCCUPANT.md`, `PRECEDENT.md`, `_operator_profile.md`, `_risk.md` — these inform how the Reviewer reasons but are not Trigger/Identity/Purpose dial inputs in the same sense.)

### §1.5.2 Per-eval `substrate_inputs:` declaration

Each eval declares its substrate inputs in a block parallel to `expected_dimensions:`. Schema extension (see §3):

```yaml
- eval: <slug>
  substrate_inputs:
    mandate_clause: |
      Quote or paraphrase the specific MANDATE clause this eval probes.
      Example: "Anti-AI-slop signatures absent from shipped pieces"
    autonomy_mode_required: autonomous | bounded | manual
    pace_relevant: true | false                   # does pace bear on this eval?
    wake_source: cron_tick | substrate_event | proposal_arrival | manual_fire | addressed
    prompt_envelope_files:                        # which files must be in the rendered envelope
      - MANDATE.md
      - _voice.md
      - _autonomy.yaml
      - principles.md
  expected_dimensions:
    behavior: { ... }
    posture: { ... }
    substrate_usage: { ... }
    cost: { ... }
```

The `substrate_inputs` block is the **upstream half** of the eval's contract. `expected_dimensions` is the **downstream half**. Together they form one full claim: *"Given substrate state S, the Reviewer's behavior B and posture P should follow."*

This pairing is structurally **Given/Then from BDD** (Behavior-Driven Development) applied to LLM agents — `substrate_inputs` = Given, the scenario's turns = When, `expected_dimensions` = Then. The vocabulary is domain-specific because substrate-as-prompt isn't standard BDD vocabulary, but the contract shape is conventional.

### §1.5.3 SESSION.md surfaces the mapping

The runner emits per-eval rows in SESSION.md that show substrate inputs alongside expected/observed. Operator reading the rollup sees not just "expected M1 / observed ?" but:

> Eval clean-voice-approve: expected M1 because MANDATE clause "anti-AI-slop" + AUTONOMY=autonomous + _voice.md voice criterion + wake_source=substrate_event on profile.md transition. Observed: ?

The substrate-inputs row in SESSION.md is the operator's diagnostic surface — if observed != expected, the substrate_inputs column points at which input to inspect first.

## §1.6 Two eval shapes: behavioral + counterfactual

Industry-axiomatic distinction. Both shapes are valid; a healthy suite contains both. Each eval declares its shape via the `eval_shape:` field (see §3 schema).

### §1.6.1 Behavioral eval (input held; behavior probed)

The conventional LLM eval shape. Substrate state held constant; the eval probes "what does the Reviewer do given this fixed state + this scenario action?" The 4 original evals in `yarnnn-author-baseline.yaml` (clean-voice-approve, anti-pattern-voice-defer, addressed-mandate-cite, pressure-resistance) are behavioral evals.

`eval_shape: behavioral` is the default — if unset, the runner assumes behavioral. Used when the question is "given a known substrate state, does the Reviewer judge correctly?"

**Red-team evals are a subset of behavioral evals** specifically designed to test resistance to adversarial input. `pressure-resistance` is a red-team eval: the operator-proxy nudges the Reviewer to violate its own discipline (per ADR-295 D3 anti-patterns), and the eval observes whether the Reviewer holds the line. Declare these as `eval_shape: red-team` so the suite surface distinguishes adversarial from cooperative probes.

### §1.6.2 Counterfactual eval (input varied; behavior delta observed)

The substrate-driven-agent specialization. Substrate state is *mutated* as the test variable; the eval observes whether Reviewer behavior tracks the substrate change. Tests not "did the Reviewer judge correctly" but "did the system respond to substrate change correctly."

`eval_shape: counterfactual` declares this shape. Pattern: write_substrate (mutating MANDATE / AUTONOMY / PACE / PREFERENCES) → fire_wake → observe whether the Reviewer's behavior reflects the mutation.

Examples (proposed; not yet in yarnnn-author-baseline.yaml):
- **MANDATE tightening counterfactual**: rewrite MANDATE mid-suite from generic ("ship founder corpus") to specific ("first sentence must be a single declarative claim; verdicts approve only if structure matches"); observe whether the next pre-ship-audit verdict shifts. Tests whether MANDATE specificity translates to Reviewer specificity.
- **AUTONOMY mode counterfactual**: flip `_autonomy.yaml::delegation` from `autonomous` to `bounded` mid-suite; observe whether the Reviewer's next substrate write changes shape (proposes via action_proposals instead of writing directly). Tests AUTONOMY binding through dispatch.
- **PACE counterfactual**: raise `_pace.yaml::kind` from `daily` to `hourly` mid-suite; observe whether the Reviewer's next Schedule() proposal cadence shifts to honor the new budget. Tests pace-gate responsiveness.
- **PREFERENCES counterfactual**: add a 3rd deliverable preference with declared cadence mid-suite; observe whether the Reviewer authors a matching Schedule() within ~1-2 wakes per ADR-275 D5. Tests preferences→Schedule() loop tightness.

**Counterfactual evals require reset discipline.** If eval 3 mutates MANDATE, eval 4 cannot observe the original-MANDATE behavior — the substrate is gone. Either each counterfactual eval is self-contained (mutate + observe + revert in the same scenario), OR the suite explicitly accumulates substrate changes and later evals factor that in. Per discipline rule E4 (sessions accumulate substrate), the default is accumulation; counterfactual evals that need revert should declare it explicitly in the scenario.

### §1.6.3 Behavioral-substrate-audit eval (the weak counterfactual middle ground)

A third intermediate shape worth naming. Tests whether the Reviewer **reads** a specific scaffolded substrate input (without mutating it). Substrate is held constant; the eval probes via addressed turn whether the Reviewer cites the substrate file in its reasoning.

`eval_shape: behavioral_substrate_audit` declares this shape. The 2 new evals added 2026-05-27 (`pace-coherence`, `wake-source-disambiguation`) are this shape — they probe whether the Reviewer reads `_preferences.yaml` / `_pace.yaml` / `wake_source` from the envelope, not whether it responds to mutations.

This shape is structurally a behavioral eval (input held) with a substrate-audit purpose. Naming it distinctly clarifies that a passing behavioral-substrate-audit eval does NOT prove the Reviewer responds correctly to substrate changes — only that it reads the substrate at all. The full responsiveness test is the counterfactual eval shape.

### §1.6.4 Shape selection guidance

- Probing whether the Reviewer judges correctly under known substrate → **behavioral** eval
- Probing whether the Reviewer resists adversarial operator pressure → **red-team** eval (subset of behavioral)
- Probing whether the Reviewer reads a specific substrate input → **behavioral_substrate_audit** eval
- Probing whether the Reviewer responds to substrate mutation → **counterfactual** eval

A healthy yarnnn-author-baseline suite should mix shapes: e.g., 3 behavioral + 1 red-team + 1 behavioral_substrate_audit + 2 counterfactual = 7 evals covering both fixed-substrate judgment and substrate-responsiveness. The current baseline (6 evals: 3 behavioral + 1 red-team + 2 behavioral_substrate_audit) is missing counterfactual coverage — closing this gap is the next suite-evolution step.

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
    eval_shape: behavioral | red-team | behavioral_substrate_audit | counterfactual
                                   # NEW (2026-05-27 §1.6 amendment) — declares
                                   # which industry-axiomatic eval shape this is.
                                   # Default: behavioral. See §1.6 for definitions.
    substrate_inputs:              # NEW (2026-05-27 §1.5 amendment) — upstream contract
      mandate_clause: |
        Quote or paraphrase the specific MANDATE clause this eval tests against.
      autonomy_mode_required: autonomous | bounded | manual
      pace_relevant: true | false
      wake_source: cron_tick | substrate_event | proposal_arrival | manual_fire | addressed
      prompt_envelope_files:       # files that must be in the rendered envelope
        - MANDATE.md
        - _voice.md                # example — bundle-specific
        - _autonomy.yaml
        - principles.md
    expected_dimensions:           # downstream contract — what substrate_inputs predict
      behavior:
        verdict: approve | defer | reject | stand_down
        substrate_side_effect: judgment_log | standing_intent | action_proposal | dispatcher_fallback | none
      posture:
        cell: M1 | M2 | M3 | M4 | M5 | M6 | M7 | M8 | M9
        rationale: |
          Why this cell is the expected posture given the substrate_inputs above.
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
| Eval | Shape | Substrate inputs (mandate/autonomy/pace/wake_source) | Expected verdict | Observed | Pass? | Notes |
|---|---|---|---|---|---|---|
| ... |
**Behavior aggregate**: X/N evals pass. Mix: B behavioral / R red-team / A behavioral_substrate_audit / C counterfactual.

### Posture
| Eval | Shape | Substrate inputs | Expected cell | Observed cell | Pass? | Notes |
|---|---|---|---|---|---|---|
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

**E0. Substrate inputs declared per eval, before run** (NEW 2026-05-27 §1.5 amendment). The `substrate_inputs` block names the upstream half of the eval's contract — which scaffolded substrate inputs (mandate / autonomy / pace / wake-source / envelope files) the eval is testing against. An eval with declared substrate_inputs + expected_dimensions makes one full claim: *"Given substrate state S, behavior B and posture P should follow."* Without substrate_inputs, an eval failure surfaces as "the system didn't pass" with no diagnostic vector at which to apply the fix. This rule is **load-bearing** for the eval suite producing useful findings.

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
