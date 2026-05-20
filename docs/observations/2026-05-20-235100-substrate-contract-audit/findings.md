# Substrate contract audit — Step A + B

**Hat**: External Developer of the System (Hat B). Discourse-driven audit; no system canon edits in this folder. Recommendations land in canon via separate ADR/commit if Step B surfaces a class observation worth tightening.
**Time captured**: 2026-05-20T23:51Z.
**Author**: Claude (Opus 4.7).
**Reference**: triggered by the kvk-vs-alpha-trader-2 cadence-authoring asymmetry observed at 2026-05-20T13:46-13:47Z (parent thread: pre-e2e readiness audit + Fix 1B observation folders).

---

## Why this audit exists

On the first natural Reviewer wake post-Fix-1A (signal-evaluation at 13:45-13:47Z 2026-05-20), the alpha-trader-2 Reviewer self-authored three `Schedule(create)` calls honoring `_preferences.yaml` declarations (pre-market-brief, weekly-performance-review, quarterly-signal-audit). The kvk Reviewer, with identical `_preferences.yaml`, identical bundle, identical autonomy, identical signal-evaluation prompt, identical persona frame — wrote only `standing_intent.md` updates and authored no Schedule calls.

This asymmetry surfaced a thesis (formed in parent discourse): **every operator-authored substrate file declares an intent, and each declaration has a contract shape that names what the Reviewer must DO when it reads it.** Some contracts are strong (MANDATE is a hard gate; `_risk.md` is code-enforced). Some are weak (`_preferences.yaml` is verbiage in ADR-275, paraphrased in the kernel persona frame, not enforced anywhere structural).

Compound axiom (named in this discourse):
**A substrate file's contract shape = authorship layer × document purpose.**
- **Authorship layer**: who has authority over this file's existence and schema (system kernel vs program bundle), and who authors its content (operator vs Reviewer vs platform vs system)
- **Document purpose**: what role the file plays in the Reviewer's reasoning (embodiment, framework, declaration, gate, context, accumulation, navigation)

The discipline rule: **separation of concerns must hold both at the authorship layer AND at the document-purpose level**. Conflating produces ambiguous contracts; non-reproducible behavior follows.

This audit walks each operator-relevant substrate file across four axes:

1. **Authorship layer**: kernel-defined (system) | bundle-defined (program) | hybrid (kernel schema + bundle content)
2. **Document purpose**: embodiment / framework / declaration / gate / context / accumulation / workbench
3. **Contract strength**: hard-code-gate / structural-enforcement / soft-persona-frame / unenforced
4. **Prompt-text location**: kernel persona frame / bundle recurrence prompt / both / neither

---

## Step A — Per-file audit

Walking files in the order the Reviewer reads them at wake (envelope assembly order from `reviewer_agent.py::build_user_message`).

### 1. `/workspace/context/_shared/MANDATE.md`

| Axis | Value |
|---|---|
| Authorship layer | **Hybrid** — kernel-defined schema (every workspace has one), bundle-defined skeleton content (per-program template at signup), operator-authored body content |
| Document purpose | **Declaration** (Primary Action + governing intent — what value-moving external write the operation produces) |
| Contract strength | **Hard-code-gate** — `ManageTask(create)` returns `error="mandate_required"` if MANDATE.md is empty (ADR-207) |
| Prompt-text location | Kernel persona frame: "Read MANDATE.md. Now execute against it" (reviewer_agent.py L366) |

**Contract is structurally enforced.** No room for Reviewer judgment ambiguity — the gate fires deterministically pre-task-creation. ✓ Strong.

### 2. `/workspace/context/_shared/IDENTITY.md`

| Axis | Value |
|---|---|
| Authorship layer | **Hybrid** — kernel-defined schema, bundle-defined skeleton, operator-authored persona content |
| Document purpose | **Embodiment** (who the operator IS — voice, posture, decision style; the Reviewer reads it and embodies the operator) |
| Contract strength | **Soft-persona-frame** — kernel persona instructs the Reviewer to read it first and speak in first person as that person (reviewer_agent.py L383: "Read your IDENTITY.md first. Embody it fully. Speak in first person as that person.") |
| Prompt-text location | Kernel persona frame (~L383-385) |

**Contract is "read and embody."** Not enforceable structurally — embodiment is a judgment quality. The contract IS strong in the persona-frame text. ✓ Appropriate.

### 3. `/workspace/context/_shared/AUTONOMY.md` + `_autonomy.yaml`

| Axis | Value |
|---|---|
| Authorship layer | **Kernel-defined** schema + kernel-defined skeleton; operator-authored content via existing UX |
| Document purpose | **Gate** (delegation declaration — what the Reviewer is authorized to auto-execute and what requires operator approval) |
| Contract strength | **Hard-code-gate + structural-enforcement** — `should_auto_apply()` consults `_autonomy.yaml` deterministically; `DEFAULT_REVIEWER_WRITE_LOCKS` prevents Reviewer from editing this file |
| Prompt-text location | Kernel persona frame (read AUTONOMY at every wake, render verdicts within ceiling) + execution-time gate code |

**Contract is structurally enforced + locked from Reviewer self-amendment.** ✓ Strong.

### 4. `/workspace/context/_shared/BRAND.md`

| Axis | Value |
|---|---|
| Authorship layer | **Hybrid** — kernel schema, bundle skeleton, operator content |
| Document purpose | **Embodiment** (voice + brand identity for operator-facing artifacts) |
| Contract strength | **Soft-persona-frame** (Reviewer reads if relevant; producer-roles read for prose generation) |
| Prompt-text location | Kernel persona frame (light mention; bundle-specific prompts may emphasize) |

**Contract is "read when relevant."** Light-touch by design. ✓ Appropriate for its role.

### 5. `/workspace/context/_shared/CONVENTIONS.md`

| Axis | Value |
|---|---|
| Authorship layer | **Bundle-defined** entirely (per-program filesystem conventions, slug-templated paths) |
| Document purpose | **Navigation** (where things live; how slugs template into paths) |
| Contract strength | **Soft-persona-frame** (Reviewer reads when authoring paths or interpreting bundle references) |
| Prompt-text location | Bundle recurrence prompts reference it for path templating |

**Contract is "read for path-shape lookup."** ✓ Appropriate.

### 6. `/workspace/context/_shared/PRECEDENT.md`

| Axis | Value |
|---|---|
| Authorship layer | **Hybrid** — kernel schema (every workspace has one), operator-authored content (boundary-case precedents) |
| Document purpose | **Framework override** (durable boundary-case guidance that overrides conflicting principles.md clauses) |
| Contract strength | **Soft-persona-frame + explicit precedence rule** — kernel persona explicitly names "PRECEDENT.md overrides conflicting clauses in your own principles.md" (reviewer_agent.py L490) |
| Prompt-text location | Kernel persona frame |

**Contract is explicit in the persona frame: precedence is named.** ✓ Strong text-level contract.

### 7. `/workspace/context/_shared/_preferences.yaml` ⚠

| Axis | Value |
|---|---|
| Authorship layer | **Hybrid** — bundle-defined schema (alpha-trader bundle ships the file template), operator-authored content (cadence preferences for deliverables) |
| Document purpose | **Declaration** (operator names what deliverables they want, on what cadence; Reviewer must DO something — author Schedule calls to honor each `active: true` preference whose slug isn't already in `_recurrences.yaml`) |
| Contract strength | **Soft-persona-frame, unenforced** — verbiage in ADR-275 + reviewer_agent.py L575-586 paraphrasing it. No structural check exists; no `_preferences.yaml`-honored gate; no first-wake reconciliation enforcement. The Reviewer judges each wake whether to act. |
| Prompt-text location | Kernel persona frame (single paragraph at L575-586) + envelope pre-load (the file is rendered into the wake envelope per the bundle's substrate_abi) |

**Contract is "read every wake and author Schedule for declared preferences."** The text exists in the persona frame, but:
- No structural check confirms reconciliation has happened
- No "first wake post-activation" trigger that forces the audit
- No standing_intent.md template field that requires the Reviewer to declare "I have/have-not reconciled _preferences.yaml this cycle"

This is the file whose weak contract produced the kvk-vs-alpha-trader-2 asymmetry. **The contract IS authored in the persona frame, but at a strength below what its document purpose requires.** ⚠ Weak relative to role.

### 8. `/workspace/context/_shared/_token_budget.yaml`

| Axis | Value |
|---|---|
| Authorship layer | **Kernel-defined** schema + skeleton; operator-authored ceiling |
| Document purpose | **Gate** (compute-resource ceiling on the Reviewer) |
| Contract strength | **Hard-code-gate** (consulted in budget-check code) + **locked** from Reviewer self-amendment |
| Prompt-text location | Kernel persona frame (read but never edit) |

**Contract is structurally enforced.** ✓ Strong.

### 9. `/workspace/context/trading/_operator_profile.md` (alpha-trader instance) ⚠

| Axis | Value |
|---|---|
| Authorship layer | **Bundle-defined** schema + bundle-defined skeleton (template prompts in the body) + operator-authored content (declared signals, universe, edge hypothesis) |
| Document purpose | **Declaration** (operator's strategy declaration — signals to evaluate, universe to scan, edge hypothesis to falsify; Reviewer reads this when authoring proposals + judging them) |
| Contract strength | **Soft-persona-frame** — Reviewer reads this in proposal-arrival wakes + signal-evaluation cron-tick wakes; no structural enforcement that the Reviewer must apply every declared signal vs just some |
| Prompt-text location | Bundle recurrence prompt for `signal-evaluation` (recurrence prompt explicitly instructs "Apply each signal's boolean rule from `_operator_profile.md`") + envelope pre-load |

**Contract is "apply declared signals."** Bundle-recurrence-prompt makes it explicit at the right authorship layer (program-specific). ✓ Appropriate placement.

### 10. `/workspace/context/trading/_risk.md` (alpha-trader instance)

| Axis | Value |
|---|---|
| Authorship layer | **Bundle-defined** schema + skeleton + operator-authored thresholds |
| Document purpose | **Gate** (hard risk thresholds enforced by `risk_gate.py` at execution time) |
| Contract strength | **Hard-code-gate** — `risk_gate.compute_risk_state()` reads thresholds + refuses Reviewer-approved proposals on violation |
| Prompt-text location | Kernel persona frame (light mention) + bundle recurrence prompt (explicit reference) + execution-time gate code |

**Contract is structurally enforced.** ✓ Strong.

### 11. `/workspace/context/trading/_universe.yaml` (alpha-trader instance)

| Axis | Value |
|---|---|
| Authorship layer | **Bundle-defined** schema + bundle template skeleton + operator-authored ticker list |
| Document purpose | **Declaration** (which tickers the signal-evaluation recurrence should scan) |
| Contract strength | **Structural enforcement via recurrence** — `track-universe` mechanical recurrence iterates this list deterministically; `signal-evaluation` iterates it per the recurrence's prompt |
| Prompt-text location | Bundle recurrence prompt (explicit iteration step) |

**Contract is "iterate every ticker."** Recurrence-prompt-level enforcement at the right authorship layer. ✓ Appropriate.

### 12. `/workspace/review/IDENTITY.md` (Reviewer persona)

| Axis | Value |
|---|---|
| Authorship layer | **Hybrid** — kernel-defined schema, bundle-defined skeleton (program-specific Reviewer persona — e.g., Simons-flavored for alpha-trader), operator-authored overrides |
| Document purpose | **Embodiment** (who the Reviewer IS — independent judgment seat, capital-EV reasoner, evidence-pattern adherent) |
| Contract strength | **Soft-persona-frame** (read and embody) |
| Prompt-text location | Kernel persona frame ("Read your IDENTITY.md first") + envelope pre-load |

**Contract is "read and embody."** ✓ Appropriate. Strong embodiment is non-coercible — appropriate that it's soft.

### 13. `/workspace/review/principles.md`

| Axis | Value |
|---|---|
| Authorship layer | **Hybrid** — kernel-defined schema (every Reviewer has one), bundle-defined skeleton + content (program-specific judgment framework — alpha-trader's principles.md ships rich Simons-discipline framework), operator-authorable + Reviewer-authorable under ADR-295 D1 discipline |
| Document purpose | **Framework** (how the Reviewer reasons — declared judgment process, evidence patterns, anti-patterns) |
| Contract strength | **Soft-persona-frame + ADR-295 D1 self-amendment discipline + ADR-209 attribution + revision-message-format gate** |
| Prompt-text location | Kernel persona frame + envelope pre-load + bundle recurrence prompts cite specific sections |

**Contract is "apply this framework in judgment; may self-amend under ADR-295 evidence patterns."** Multi-layered enforcement. ✓ Strong.

### 14. `/workspace/review/_principles.yaml`

| Axis | Value |
|---|---|
| Authorship layer | **Bundle-defined** (per-program machine-parsed thresholds: `high_impact_threshold_cents`, `auto_approve_below_cents`) |
| Document purpose | **Gate threshold** (numeric parameters consumed by `review_policy.py`) |
| Contract strength | **Hard-code-gate** (machine-parsed; consulted in `should_auto_apply()`) |
| Prompt-text location | Not in prompt — consumed by code |

**Contract is structurally enforced.** ✓ Strong.

### 15. `/workspace/review/OCCUPANT.md`

| Axis | Value |
|---|---|
| Authorship layer | **Kernel-defined** (runtime-truth alignment per ADR-284) |
| Document purpose | **Embodiment** declaration (who currently fills the Reviewer seat — AI vs human vs impersonation) |
| Contract strength | **Structural enforcement** (bundle-fork populates with runtime occupant identity; ADR-284 D3 verify gate) |
| Prompt-text location | Kernel persona frame envelope rendering ("## OCCUPANT.md — Your current seat") |

**Contract is structurally honored.** ✓ Appropriate.

### 16. `/workspace/review/standing_intent.md`

| Axis | Value |
|---|---|
| Authorship layer | **Kernel-defined** schema; Reviewer-authored content |
| Document purpose | **Workbench** (the Reviewer's forward-looking judgment substrate — what it's watching for next cycle) |
| Contract strength | **Soft-persona-frame + structural reminder** — kernel persona explicitly names "every judgment-mode cycle updates standing_intent.md"; no-fire judgment cycle still updates (per ADR-284 D2). Verbiage-level enforcement. |
| Prompt-text location | Kernel persona frame extensively (L420-447); envelope pre-load surfaces last-cycle content; bundle recurrence prompts reinforce |

**Contract is "update every cycle."** Multi-layered persona-frame text; no structural code-gate but strong text-contract. ✓ Strong enough — observable behavior shows Reviewers do update standing_intent reliably (both kvk + alpha-trader-2 wrote it on their fires).

### 17. `/workspace/review/judgment_log.md`

| Axis | Value |
|---|---|
| Authorship layer | **Kernel-defined** schema; infrastructure-rendered content (per ADR-281 §5.D2 single-writer contract; renders from Reviewer's structured ReturnVerdict output) |
| Document purpose | **Accumulation** (audit trail of operation-shaping judgment moments) |
| Contract strength | **Hard-code-gate** (`render_lineage_entry_if_material` deterministic gate decides which fires produce entries) |
| Prompt-text location | Kernel persona frame mentions; Reviewer does NOT WriteFile this directly |

**Contract is structurally enforced + single-writer.** ✓ Strong.

### 18. `/workspace/review/calibration.md` + `handoffs.md`

| Axis | Value |
|---|---|
| Authorship layer | **Kernel-defined** schema; Reviewer + system-authored content (calibration via back-office reflection task; handoffs on occupant rotation) |
| Document purpose | **Accumulation** (calibration: Reviewer self-assessment substrate; handoffs: seat-rotation continuity) |
| Contract strength | **Structural — bundle recurrence + code-driven** |
| Prompt-text location | Kernel persona frame mentions |

**Contract is structurally maintained.** ✓ Appropriate.

---

## Step B — Class observations across the table

### Observation 1: contract strength inversely correlates with declaration-purpose ambiguity

Looking down the contract-strength column:

| Strength tier | Files | Common property |
|---|---|---|
| **Hard-code-gate** | MANDATE.md, _autonomy.yaml, _risk.md, _token_budget.yaml, _principles.yaml | Each declares a value that code reads and enforces deterministically at a specific decision point |
| **Structural-enforcement** | _universe.yaml, OCCUPANT.md, judgment_log.md, AUTONOMY.md | Each has code that reads it and acts on it (iterates, populates, renders, gates) without LLM judgment |
| **Soft-persona-frame (strong text)** | IDENTITY.md, PRECEDENT.md, principles.md, standing_intent.md, review/IDENTITY.md, BRAND.md, CONVENTIONS.md | Read-and-be-shaped-by; the Reviewer's reasoning consumes these but no code post-checks compliance |
| **Soft-persona-frame (weak text)** | **`_preferences.yaml`** | Names what the Reviewer should DO when reading, but the persona-frame text is a single paragraph at L575-586; no structural reinforcement |

The first three tiers are appropriately calibrated:
- Hard gates protect operator authority (gate, threshold)
- Structural enforcement honors operator intent that code can deterministically express (universe iteration, occupant identity)
- Soft text appropriately holds judgment-quality contracts (embodiment, framework application, forward-intent)

**The fourth tier is the anomaly.** `_preferences.yaml` is the only file whose contract names a specific Reviewer ACTION (author Schedule calls for declared preferences) but enforces that action through verbiage strength alone — and the verbiage is weaker than the action it commands.

### Observation 2: the kvk-vs-alpha-trader-2 asymmetry is the predicted symptom of Observation 1

Given identical inputs (same `_preferences.yaml`, same persona, same prompt), the only variable that distinguishes the two Reviewer cycles is the Reviewer's judgment about *whether this moment warrants authoring*. A weak contract makes that judgment legitimately ambiguous:
- alpha-trader-2's Reviewer judged "yes, the preferences are unscheduled; I'll author" → 3 Schedule calls
- kvk's Reviewer judged "the preferences are noted; standing intent first" → no Schedule calls

Neither is *wrong* per the verbiage. **The contract permits both readings.** The asymmetry is exactly what you'd expect from a soft contract on an action-shaped command.

The strong-contract files (MANDATE gate, _risk gate, _universe iteration) do NOT produce this asymmetry — because there's no judgment moment. Code reads and acts.

### Observation 3: the authorship-layer dimension is mostly clean

Looking at the authorship-layer column, the system kernel vs program bundle separation holds well:

- Kernel-defined schemas: MANDATE.md (Primary Action concept), IDENTITY.md (persona concept), AUTONOMY.md (delegation concept), PRECEDENT.md (override concept), standing_intent.md (workbench concept), judgment_log.md (audit concept). Each is a workspace-universal concept; the kernel defines the file's existence + schema; bundles ship per-program skeletons; operator authors content.
- Bundle-defined schemas: `_universe.yaml`, `_operator_profile.md`, `_risk.md`, CONVENTIONS.md, `_preferences.yaml` (in alpha-trader's case). Each is program-specific; the kernel doesn't know about these specifically — only the bundle does.

The discipline is mostly correct. **One ambiguity surfaces**: `_preferences.yaml` is bundle-defined at the schema level (alpha-trader bundle ships it; alpha-author bundle ships its own version) but its **contract** ("Reviewer reads every wake and authors Schedule for declared preferences") is cross-cutting kernel-level — the same contract applies to every program. The text in `_preferences.yaml`'s contract lives in the kernel persona frame, which is correct. The file lives in the bundle layer, which is also correct. The cross-layer hand-off is the surface where the contract is weakest.

### Observation 4: the broader class — "operator-declaration files whose contract requires a Reviewer action"

Filtering the table by document purpose:

| File | Document purpose | Contract specifies a Reviewer action? |
|---|---|---|
| MANDATE.md | Declaration | No (read-and-be-bound-by; the *gate* is the code's job) |
| IDENTITY.md | Embodiment | No (read-and-embody is a quality, not an action) |
| AUTONOMY.md | Gate | No (read-and-operate-within; the *gate* is the code's job) |
| BRAND.md | Embodiment | No |
| CONVENTIONS.md | Navigation | No |
| PRECEDENT.md | Framework override | Yes-but-soft (apply when conflict arises; judgment-quality, not specific action) |
| **`_preferences.yaml`** | **Declaration with specified action** | **Yes** — author Schedule calls for declared preferences |
| `_operator_profile.md` | Declaration with specified action | Yes — apply declared signals (action lives in bundle recurrence prompt) |
| `_universe.yaml` | Declaration with specified action | Yes — iterate tickers (action lives in mechanical recurrence) |
| principles.md | Framework | Yes-but-soft (apply framework; judgment-quality) |
| standing_intent.md | Workbench | Yes — update every cycle (kernel persona frame, multi-layered) |

The class of "declaration files whose contract specifies a Reviewer action" splits cleanly into two sub-classes:

- **Declarations where the action is structural / code-driven**: `_operator_profile.md` (recurrence-prompt iteration), `_universe.yaml` (mechanical-recurrence iteration), `judgment_log.md` (infrastructure rendering). **Contracts: strong.**
- **Declarations where the action is Reviewer-judgment-driven**: `_preferences.yaml` (Schedule authoring), `principles.md` self-amendment (ADR-295 D1), `standing_intent.md` (every-cycle update). **Contracts: variable strength.**

Within the second sub-class:
- **`principles.md` self-amendment**: contract is multi-layered (persona frame + ADR-295 D1 evidence patterns + ADR-209 attribution + revision-message-format gate). **Strong.**
- **`standing_intent.md` every-cycle update**: contract is text-only but multi-layered persona-frame text + ADR-284 derivation principle. **Strong-via-text.** Observable behavior is reliable.
- **`_preferences.yaml` Schedule authoring**: contract is a single paragraph in the persona frame. **Weak relative to peer Reviewer-judgment-driven contracts.**

### The candidate insight (Step B output)

**`_preferences.yaml`'s contract is the only weak member of its class.** Every other Reviewer-judgment-driven action contract (principles.md self-amendment, standing_intent.md every-cycle update) has multi-layered enforcement text. `_preferences.yaml` does not. The asymmetry of kvk vs alpha-trader-2 is the natural consequence.

The fix surface is text-level, not code-level. Three text-tightening candidates worth discourse:

**Candidate 1 — Strengthen the persona-frame text** (lowest-friction). Today the cadence-authoring contract is ~12 lines at reviewer_agent.py L575-586. The text says "for each `active: true` preference whose `slug` is NOT yet in `_recurrences.yaml`, author the cadence." Tightening could:
- Promote this to a load-bearing first-cycle responsibility ("Your first natural wake post-activation MUST reconcile `_preferences.yaml` against current `_recurrences.yaml` before proposing any other action")
- Add a standing_intent.md template field ("Have I reconciled `_preferences.yaml` since this workspace activated? Y/N")
- Link the contract explicitly to ADR-275 + cite the kvk-vs-alpha-trader-2 asymmetry as the case that motivated the tightening

**Candidate 2 — Add a structural gate** (medium-friction). On the Reviewer's wake, the dispatch layer could pre-check whether `_preferences.yaml` has `active: true` entries whose slugs are not in `_recurrences.yaml`, and if so, inject an explicit "reconcile preferences before other actions" directive into the envelope. This makes the contract Tier 2 (Structural enforcement) instead of Tier 4 (Soft-weak-text). But it adds a code path; carefully weigh whether the cost is justified vs Candidate 1.

**Candidate 3 — Treat the asymmetry as observation discipline working correctly, no text change** (lightest-friction). The architecture already commits to Reviewer judgment as persona-bearing and non-deterministic. Two Reviewer wakes producing different judgments on the same data is the system's design feature, not a defect. The fix may be observation-discipline-level — wait for a second-cycle data point; if kvk's Reviewer still doesn't author Schedule calls on the second natural fire, *then* the contract is genuinely weak; if it authors on cycle 2 or 3, the contract was strong enough and the asymmetry was Reviewer judgment about timing.

---

## What discipline this audit demonstrates

The walking-through exercise demonstrates the first-principles separation of concerns you named in the parent discourse:

- **Authorship layer separation holds.** Kernel files cover workspace-universal concepts; bundle files cover program-specific concepts. No conflation observable.
- **Document purpose distinction holds.** Each file's role in the prompting strategy is distinct (embodiment, framework, declaration, gate, context, accumulation, workbench, navigation). No file does two roles at once.
- **Contract strength is mostly calibrated.** Hard gates protect operator authority; structural enforcement honors deterministic intent; soft contracts hold judgment-quality embodiment / framework / forward-intent.
- **One contract strength miscalibration found**: `_preferences.yaml`. The action it commands is action-shaped (author Schedule calls); the enforcement layer is text-only-weak.

This is *one* gap, not a class gap. The audit ruled out the wider thesis (multiple weak contracts producing a class problem). The targeted recommendation lives in the discourse around Candidates 1–3 above.

---

## Recommendation to operator

Given the single-gap finding (Observation 4 + Candidate 1/2/3):

**Recommendation R1**: do not pre-fix anything in this session. Wait for the second natural fire (kvk's signal-evaluation at 2026-05-21T13:45Z) and observe whether the Reviewer authors Schedule calls on cycle 2. If yes, the contract is strong enough and the asymmetry was first-cycle judgment about timing — no fix needed. If still no, the contract is genuinely weak and Candidate 1 (persona-frame text tightening) is the right surgical fix.

**Recommendation R2**: regardless of the cycle-2 outcome, capture this audit table as the canonical "substrate contract shape" reference. It's useful operator-side documentation when reasoning about future operator-declaration substrate files — what contract shape does the new file need? At what authorship layer? With what enforcement strength? The four-axis framework + class observations are reusable.

**Recommendation R3**: tighten the alpha-author canary discovery scope to also observe whether yarnnn-author's Reviewer reconciles its `_preferences.yaml` (weekly-corpus-review + quarterly-voice-audit) on its first natural fire post-Fix-1A. Its `_recurrences.yaml` is now bundle-clean (those entries deleted during re-fork); the Reviewer must re-author them. If yarnnn-author authors on its outcome-reconciliation 2026-05-21T05:00Z fire (~6 hours from now), that's a third data point. If yarnnn-author authors but kvk doesn't, the asymmetry is specific to alpha-trader's signal-evaluation prompt, not a `_preferences.yaml` contract weakness.

---

## Cross-references

- Parent discourse: [pre-e2e readiness audit](../2026-05-20-100309-pre-e2e-readiness-audit-adr296-v2/findings.md) + [alpha-trader-2 e2e persona flip](../2026-05-20-105038-alpha-trader-2-e2e-persona-flip/findings.md) + [kvk probe-residue cleanup](../2026-05-20-110814-kvk-probe-residue-cleanup/findings.md)
- ADR-275 — introspection cadence is Reviewer-authored, not bundle-scaffolded
- ADR-296 v2 D3 — Reviewer authority over Schedule + ManageHook + standing_intent
- ADR-194 v2 + ADR-216 — Reviewer as persona-bearing judgment (non-deterministic by design)
- ADR-281 §5 — material-outcome gate for judgment_log entry rendering
- ADR-284 — standing_intent.md substrate home + every-cycle update contract
- ADR-295 D1 — Reviewer self-amendment discipline for operator-canon (the multi-layered enforcement model)
- ADR-209 — Authored Substrate attribution discipline (every revision attributed)
- reviewer_agent.py — kernel persona frame source of truth
- docs/programs/alpha-trader/reference-workspace/_recurrences.yaml — bundle recurrence prompts
