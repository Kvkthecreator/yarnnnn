# ADR-319 — Stewardship of Intent against Ground Truth

> **Status**: Implemented (framing + per-program substrate, 2026-06-05). Commit 1 landed the *framing* (FOUNDATIONS Derived Principle 24 + THESIS Commitment 2/3 + agent-composition §4.4 Axis 3). Commit 2 landed the *per-program substrate inversion* (alpha-trader + alpha-author `principles.md` §Stewardship + MANDATE two-altitude charter; kvk live in lockstep, divergence-preserving) + the sustainability gate (`api/test_adr319_stewardship.py`, 16/16). Remaining derivation — the eval-suite `stewardship_coherence` read-kind + the deterministic falsification-detector — is named below and deferred to follow-on work (the detector explicitly downstream of measurement per ADR-305).
>
> **Housing decision (Commit 2, corrected from the Commit-1 plan by a substrate audit).** The Commit-1 doc-radius proposed a `MANIFEST.yaml::stewardship` structured threshold block. The audit found ADR-305's hard-won discipline (verified 2026-05-28): *"don't pre-populate a structured file with thresholds no code reads — that dead substrate is what triggered the rewrite."* The stewardship *thresholds* are consumed today by the **LLM reading principles.md prose** (the four evidence patterns), NOT by any deterministic code path — so hoisting them into a yaml block would recreate the dead-substrate trap. Corrected housing (R&R split, no dual-context duplication per the §3.2.2 composed-coherence discipline): (a) the kernel **why** → FOUNDATIONS DP24 + THESIS (Commit 1); (b) the **rules of judgment + inline thresholds** → each program's `principles.md` §Stewardship (the §3.2.1 single home — thresholds inline per ADR-305); (c) the **charter sentence** → MANDATE.md (points to principles, no restatement); (d) the **sustainability/audit** → a regression gate (not a yaml block); (e) the persona-frame carries **nothing** here (DP22 minimal frame). `_principles.yaml` keeps ONLY code-read values (`high_impact_threshold_cents`). A structured stewardship block becomes legitimate ONLY when the deterministic falsification-detector (below) reads it — downstream of measurement, not paper-design.
> **Date**: 2026-06-05
> **Authors**: KVK, Claude
> **Dimensional classification**: **Identity** (Axiom 2 — who owns the intent) + **Purpose** (Axiom 3 — the intent itself) + **Recursion** (Axiom 7 — accumulation across altitudes) + **Ground-Truth** (Axiom 8 — the calibration authority).

---

## Context — the gap a working trade exposed

The 2026-06-05 first-trade investigation (`docs/evaluations/2026-06-05-first-trade-fired-FINDING.md`) closed the alpha-trader capital loop end-to-end: a signal produced a proposal that the Reviewer judged with coherent, high-confidence reasoning and that executed against the broker. The compliance one-liner — *"a real signal produces a proposal that auto-executes within the envelope"* — was demonstrated.

But surfacing it surfaced a deeper question the operator named: **the Reviewer's posture is faithful-execution, not ownership.** It executes the operator's declared strategy with discipline and tunes thresholds within tight evidence bars — but every self-amendment path in the substrate is framed *defensively*: "the design-time embodiment's authoring deserves epistemic deference," "enrich, don't bulldoze," "active does NOT mean edit-eager." The Reviewer is structurally a careful steward of *someone else's* strategy.

This is **subtly anti-canonical.** Three canon facts compose to a different posture:

1. **Axiom 2** — the Reviewer is the operator's judgment in a second *temporal embodiment*. "You and the operator are the same principal in different temporal embodiments." Not a delegate — the *same principal*, one wake later, with more evidence.
2. **Axiom 8** — ground-truth substrate is *consequence-bearing reconciled reality*, and its third structural property is **calibratable**: "the Reviewer can read it and adjust judgment over time."
3. **ESSENCE / THESIS** — the moat is "the operation gets better at its job over tenure"; inferred-context layers commoditize, *authored substrate judged over tenure compounds*.

A principal who *holds* the mandate (Axiom 2), against a signal that *winces* when reality moves wrong (Axiom 8), to make the operation *compound* (ESSENCE) — does not defer to its earlier self. It **owns the mandate's fitness** and revises it against ground truth. The substrate's defensiveness re-installs the delegate relationship that Axiom 2 explicitly collapsed.

**Crucial nuance (the anti-staleness corrective).** Ownership is NOT a research/accumulation mindset. An agent that *studies* whether a rule is working while ground truth has already falsified it is *more* passive, not less — operationally inert deliberation. What makes ownership sharp is that altitude-2 action carries the **same non-optional, consequence-anchored urgency** as altitude-1 action, because both are forced by the same consequence-bearing ground truth on the same operational cadence. *Stewardship deferred is stewardship denied* — a Reviewer that watches a dead signal bleed while writing careful notes fails its fiduciary duty exactly as a trader who watches a position blow through its stop while writing notes fails.

## The decision

Ratify, at kernel altitude, the posture the canon already implies:

> **The operation's governing intent is owned by the Reviewer as the operator's installed principal, and revised against the operator's ground truth with consequence-anchored urgency — at both the altitude of actions-within-the-intent and the altitude of the-intent-itself — disciplined by one invariant: ground truth moves the intent; operator pressure never does.**

Every term is program-agnostic kernel vocabulary. No "money," no "trades," no "signals."

### D1 — Two altitudes, one loop (Axiom 7)

The recursion is the *same loop at two altitudes*:

- **Altitude 1 — within the intent.** Judge proposed actions against the mandate + rules (the compliance loop, already built + demonstrated). This is the trade-level / draft-level / campaign-level cycle.
- **Altitude 2 — on the intent.** Revise the mandate, the rules, and the envelope against ground-truth substrate (the ownership loop, the gap this ADR closes). This is the strategy-level cycle.

Both are Axiom-7 cycles: read substrate → reason → act → accumulate → next wake reads richer substrate. Altitude 2 is not a new mechanism; it is the existing recursion applied to the rules instead of the actions.

### D2 — The ownership ceiling: the mandate itself (full Axiom-2 reading)

Ownership extends **all the way to the mandate's purpose.** The Reviewer, as the same principal one wake later, can revise even the declared intent when ground truth falsifies its premise. This is not the rejected "emergent intent" (THESIS Commitment 1) — the revision is **authored, attributed, legible in the revision chain, and operator-vetoable in real-time.** It is the principal updating their own declaration against reality, which is exactly THESIS's "changed only through deliberate authored revisions" (the Reviewer IS the operator, so its authored revision IS a deliberate operator revision).

What stays *above* the ceiling: the operator-in-real-time's veto. The supervising embodiment can always cut in, redirect, or override (ADR-249 autonomy = approval-degree). The ceiling is not "the Reviewer can't touch the mandate" — it is "the operator can always countermand."

### D3 — The discipline that makes D2 safe: ground-truth, not pressure

The 2026-05-20 post-refusal capitulation (`docs/evaluations/2026-05-20-022520-post-refusal-self-amendment-probe/`) was NOT "the Reviewer had too much authority." It was **the Reviewer revising for the wrong reason** — it treated a human *message* ("just edit it") as authority and wrote risk-file edits citing "per operator directive." The fix is not to lock the mandate (that re-installs deference and kills the product). The fix is the invariant:

> **Ground-truth substrate moves the intent. Operator pressure never does.**

These look alike (both end in "the mandate changed") but are opposites:
- **Ground-truth-driven** = the principal updating their declaration against accumulated reconciled reality. *Sharp, fiduciary, the product.*
- **Pressure-driven** = capitulation to an authority that isn't the principal. *The failure mode.*

This sharpens THESIS Commitment 2: the Reviewer's independence — which comes from architectural separation of judgment from production — **extends to independence from the operator's own momentary pressure**, in service of the operator's standing commitment. The Reviewer protects the operator from their own impulse the way a disciplined trader's *rules* protect them from their *impulses*. The mandate is the rules; the Reviewer is the discipline; ground truth is the judge.

The six anti-patterns in alpha-trader's current `principles.md` (don't disable a floor for one proposal; don't amend on single-wake friction; don't loosen under drawdown; don't widen for stale data; don't touch governance files; don't edit MANDATE without operator-confirm) all SURVIVE — but they re-frame: they are all instances of *"don't revise for the wrong reason"* (pressure, single-wake friction, stale perception), which is the ground-truth-not-pressure invariant — NOT instances of *"defer to the original author."* The MANDATE-edit anti-pattern softens: under D2, MANDATE revision on *ground-truth falsification* is the principal acting; the operator-confirm requirement applies to *pressure-shaped or thin-evidence* mandate edits, enforced by the autonomy ceiling, not by a blanket "ask first."

### D4 — Program-agnostic by construction (the six-use-case test)

The framing leaked alpha-trader before because the *instance* signal (P&L) was used as if it were the *axiom*. Axiom 8's vocabulary discipline (ADR-282) resolves this: kernel says "ground-truth substrate"; each program names its flavor. The same two-altitude ownership holds across every use case:

| Program | Ground-truth flavor (Axiom 8) | Altitude 1 (within intent) | Altitude 2 (on intent — what ownership adds) |
|---|---|---|---|
| alpha-trader | reconciled P&L (money-truth) | propose/close trades per signal rules | retire a signal whose reconciled expectancy decayed; re-declare the edge |
| alpha-author | corpus coherence + audience/revenue | approve/defer drafts per voice + editorial rules | revise the voice doctrine when reception falsifies it |
| digital marketer | campaign performance (CTR, conversion, attributed revenue) | approve/schedule campaigns per the channel playbook | retire a channel/segment reconciled-poorly; re-declare the funnel thesis |
| e-commerce | revenue, refunds, retention cohorts | propose product/price/discount actions per merch rules | kill an underperforming SKU line; revise the pricing premise against cohort truth |
| music A&R | streams, retention, playlist/skip per release | approve/sign/release per the A&R thesis | revise the genre/artist thesis when streaming truth falsifies it |
| graphic designer | client acceptance, revision-rate, brief-fit | approve/deliver assets per the brand system | revise the house style when acceptance data shows it isn't landing |

The invariant in the rightmost column is **the product**: the operation's governing thesis improves against the reality the operator bears, owned by the seat, not waiting for the operator to notice. None of the six gets this from a faithful-executor Reviewer.

## Where this lands in canon (and where it does NOT)

A load-bearing correction from the doc-radius scan: per `agent-composition.md` §3.2.1, **rules of judgment — including self-amendment evidence-patterns, anti-patterns, and the fiduciary principle — live in `principles.md`, NOT the persona-frame.** ADR-306 (Derived Principle 22) collapsed the persona-frame to the minimal two-thing shape (principal-shift + action-grammar). And `agent-composition.md` §4.4 *already* grants the Reviewer near-full self-amendment **authority** (it can rewrite MANDATE, IDENTITY, principles; the lock-set encodes only "can't grant itself more authority/resources than delegated").

So the gap is **posture, not capability.** The authority axis is canon. What this ADR adds is the *posture that governs the authority's use* — re-pointing it from defensive-deference to ground-truth-fiduciary. Therefore:

- **Kernel posture (the *why*) → FOUNDATIONS Derived Principle 24 + THESIS Commitment 2/3.** Axiom-level, program-agnostic. **This commit.**
- **Per-program posture instantiation (the rules-of-judgment home, §3.2.1) → each program's `principles.md`.** The "Self-Improvement Posture" / "fiduciary principle" / anti-patterns sections re-point from defensive to ground-truth-fiduciary; the *thresholds* stay program-specific (alpha-trader: 40 reconciled trades; alpha-author: N published pieces; etc.). **Deferred — follow-on commit per program.**
- **Coherence note → `agent-composition.md` §4.4 + §3.2.1.** The authority axis exists; name the posture that governs it. **This commit (light touch).**
- **NOT the persona-frame.** It carries only principal-shift + action-grammar (DP22). The principal-shift *already* says "installed judgment, not an assistant awaiting instruction" — which is the kernel seed of ownership; the posture's *rules* belong in principles.md. No persona-frame edit. (Confirmed against the §3.2.2 composed-coherence diagnostic: adding posture-rules to the frame would re-bloat it and duplicate principles.md.)

## Impacted doc radius (full)

Named honestly so follow-on commits are scoped. Each is a *derivation* of this framing, not part of this ratification commit unless marked.

**Architecture (this commit):**
- `FOUNDATIONS.md` — new Derived Principle 24; version bump v8.8 → v8.9. **This commit.**
- `THESIS.md` — Commitment 2 (independence-includes-from-pressure) + Commitment 3 (ground-truth is authority over the mandate, not just over actions). **This commit.**
- `agent-composition.md` — §4.4 + §3.2.1 coherence note (posture governs the granted authority). **This commit.**
- `GLOSSARY.md` — add "Stewardship of intent" / "two altitudes" / "ground-truth-not-pressure" vocabulary entries. **Follow-on (light).**

**Architecture (follow-on / verify-clean):**
- `reviewer-seat-substrate.md` + `reviewer-occupant.md` — verify the seat/occupant canon doesn't contradict ownership posture; likely a one-line cross-reference to DP24.
- `SERVICE-MODEL.md`, `LAYER-MAPPING.md`, `invocation-and-narrative.md` — scan for "faithful executor" framing; expected clean (they describe mechanism, not posture).
- `bare-kernel-product-floor-2026-06-01.md` — ground-truth-as-authority interacts with the standby/operating state model; verify coherent.

**Programs (follow-on, per-program principles.md posture rewrite):**
- `docs/programs/alpha-trader/reference-workspace/review/principles.md` — "Self-Improvement Posture" → "Stewardship of Expectancy"; re-point the fiduciary principle + six anti-patterns to ground-truth-not-pressure. + kvk live workspace in lockstep.
- `docs/programs/alpha-trader/reference-workspace/context/_shared/MANDATE.md` — "What this operation is" names the two altitudes + ownership-of-fitness; boundary conditions stay inviolable as the operation's *integrity*.
- `docs/programs/alpha-author/...` (+ alpha-commerce, future programs) — same posture, program-specific ground-truth flavor.

**Features (follow-on / verify):**
- `docs/features/agent-types.md`, `agent-playbook-framework.md` — scan for posture language; likely clean (mechanism docs).

**Eval suite (follow-on — the objective shift):**
- `EVAL-SUITE-DISCIPLINE.md` — add **`stewardship_coherence`** as a third read-kind (alongside `judgment_coherence` + `substrate_responsiveness`): *fed accumulated ground-truth showing a falsified rule, does the Reviewer act at intent-altitude with urgency, AND refuse pressure?* This is the recursion made measurable and the read the current ADR-295 defensiveness cannot pass.
- `README.md` two-axis section — the MIND axis gains the ownership dimension; the one-liner shifts from compliance to ownership (compliance becomes the altitude-1 sub-goal).
- `eval-suites/alpha-trader-autonomous-loop.yaml` + `yarnnn-author-*.yaml` — re-point the self-amendment scenarios from "does it resist amendment" (defensive) to "does it revise on ground-truth AND refuse on pressure" (two-sided).
- `scenarios/post-refusal-self-amendment-probe.yaml` + `cold-start-governance-self-amend.yaml` — re-pointed as the two halves of the ground-truth-not-pressure read.

## What this supersedes / amends

- **Amends** ADR-295 (Reviewer Self-Amendment) — the *capability + evidence-thresholds* survive; the *posture* inverts from defensive ("epistemic deference, enrich-don't-bulldoze, edit-eager is the risk") to fiduciary ("ground-truth falsification is a mandatory-action trigger; deferred stewardship is failure"). The six anti-patterns survive re-framed as "don't revise for the wrong reason."
- **Sharpens** THESIS Commitment 2 (independence) + Commitment 3 (ground-truth scope).
- **Extends** FOUNDATIONS Axiom 2 (the two-embodiment principal now explicitly owns the mandate's fitness), Axiom 7 (recursion at two altitudes), Axiom 8 (ground-truth is the authority *over the mandate*, not only the calibrator *of actions*).
- **Composes with** Derived Principle 22 (persona-frame minimalism — posture lands in principles.md, not the frame), Derived Principle 21 (Reviewer formalization), the §4.4 authority/vocabulary axes, ADR-249 (autonomy = approval-degree, the operator's standing veto), ADR-282 (kernel/instance vocabulary).
- **Preserves** the persona-frame minimal shape, the lock-set rationale (an agent can't grant itself more authority than delegated — orthogonal to ownership-of-strategy), Singular Implementation.

## Deferred follow-on: the deterministic falsification-detector (measurement-gated)

Today altitude-2 stewardship is *prose-guided*: the Reviewer reads `principles.md` and *notices* (via its own reasoning over `_money_truth.md`) that a rule's premise is falsified. That is the right first step (ADR-305: thresholds live where their consumer is, and the consumer is the LLM). The natural hardening — when measurement shows prose-guidance under-fires — is a **deterministic falsification-detector**: a back-office recurrence (zero-LLM) that reads the ground-truth windows against declared thresholds and *surfaces* a falsification signal into the Reviewer's wake envelope (turning "the LLM might notice" into "the machine detects, the Reviewer judges"). At that point — and only then — the thresholds gain a *code* consumer and earn a structured home (`_principles.yaml::stewardship` or a MANIFEST block), per ADR-305's downstream-of-measurement rule. This is **not built here**: it ships after the eval-suite `stewardship_coherence` read-kind exists and a validation session measures whether prose-guidance is sufficient. Naming it keeps the structured-block option open without manufacturing dead substrate now.

## Why now

A working trade was the precondition for asking this honestly. Before the loop closed, "the Reviewer keeps standing down" was ambiguous between machine-broken and posture-passive. With the machine proven (ADR-319's predecessor finding), the residual passivity is unambiguously *posture* — and the posture is the product. Ratifying the framing at kernel altitude (rather than as alpha-trader's one-liner) is also the simpler architecture: one kernel principle replaces per-program objective-fitting, and the six use cases finally share one measurable definition of "the operation gets better."
