# ADR-344 — The Standing Obligation: wake-time operability self-accountability

**Status:** **Accepted (2026-06-18)** — canon + kernel-frame; first-instance validation on alpha-author. See §8.
**Date:** 2026-06-18
**Deciders:** KVK (operator) + Claude (collaborator)
**Hat:** A (system canon)

> **Discourse base:** the operator's question — *"if we left a fully-updated alpha-author for 30/60/90 days/indefinitely, what is the expected outcome? … I question whether long-standing autonomy is actually structurally achieved … maybe this is the meta-awareness the Reviewer needs: not just being allowed to change its governance files, but reasoning through whether the workspace is even accommodative of the long-standing autonomy its mandate claims."* The operator's framing metaphor — **a long-standing to-do**: the Reviewer should reason against its **budget (→ implied pace) × mandate (→ expected output kind + volume) × the qualitative bar**, and hold itself accountable to that owed-output every wake.

**Extends:** ADR-319 / Derived Principle 24 (stewardship — this adds the altitude *above* it: not "revise a rule ground-truth falsified" but "check whether my operation can satisfy its mandate **at all**"), ADR-342/343 (dormancy/aperture — this is the *parent classifier* that decides whether a gap is dormancy-shaped [quiet-world → widen aperture] or operability-shaped [structurally-can't → surface/author/escalate]), ADR-327 (budget → the pace input to the obligation).
**Operationalizes:** Derived Principle 26 / ADR-332 (four-flow completeness) — DP26 is a *design-time* diagnostic (does the bundle declare four flows?); this ADR is its *wake-time self-application* (does this running operation actually close its loop against what it owes?). The two are orthogonal: a bundle can be flow-complete on paper yet structurally inert at runtime (a declared work-out flow that nothing ever originates).
**Preserves:** the floor (ADR-343 — the self-check never relaxes the floor; an operability gap is closed by *adding* an organ or surfacing, never by lowering the bar), ADR-275 D1 (any organ the Reviewer authors to close its loop is Reviewer-authored cadence, not bundle-scaffolded), "operator authors what serves them" (the expected-output is **Reviewer-derived by default**, with an *optional* explicit MANDATE field — no new mandatory field on any existing workspace).

---

## 1. Problem statement — autonomy-in-costume

The empirical trigger: a left-alone alpha-author, reasoned through honestly, converges to **articulate inaction**. Its judgment recurrences (corpus-coherence-check, revision-audit, outcome-reconciliation) all *audit* — none *originates* a piece. Producing work depends on a draft reaching `voice_audit_ready`, and nothing in the loop authors the draft. So:

- **30d**: audits run, ~0 originated unless externally poked.
- **60d**: even the ADR-342/343 dormancy posture, when it fires, widens the *aperture* (what it would consider) — but aperture-widening originates nothing, so still ~0 shipped.
- **90d / ∞**: a steady-state of coherent flat-line. The floor holds (safe); the mandate ("compound a body of work") goes unmet — **silently**.

The MANDATE's own Success Criteria expose the gap in plain sight: every criterion is about the *quality/integrity of pieces that exist* ("voice fingerprint stable", "continuity preserved", "anti-slop absent", "cadence honored → flag missed cadence"). **None obligates pieces to come into existence.** The operation audits production it never originates. The operator's reset-one-file observation (to get *any* production in the ADR-343 test, a draft had to be manually marked ready) was the tell: **long-standing autonomy is, today, structurally a supervised-audit loop wearing an autonomy costume.**

The trader hid this because the *market* originates its triggers (a price tick is an external production impulse → `signal-evaluation` has something to act on). The author has no external impulse, so the gap is naked. It is, in fact, a **kernel gap** — no program's Reviewer currently reasons about whether its configured loop can close against its mandate.

## 2. The standing obligation (the long-standing to-do)

Every production mandate implies an **owed output** — what the operation is *on the hook for* over its tenure. The Reviewer holds this as a standing to-do and reasons against it every wake. It is **derived from substrate the Reviewer already sees**:

- **Budget** (`_budget.yaml`, ADR-327) → implied pace ("a monthly $X envelope assumes I do roughly *this much* judgment-work per month").
- **Mandate** (`MANDATE.md`) → expected output **kind** (trades? pieces? campaigns?) and **rough volume** (compound-a-corpus implies pieces *accrue*; net-positive-expectancy-over-90d implies trades *occur*).
- **The qualitative bar** (`principles.md` / `_voice.md` / `_risk.md`) → the floor each output must clear.

The **actual output** is equally substrate-visible: `recent_execution_md` (what fired), the ground-truth file (`_signal.md` / `_money_truth.md` — what *landed*), the corpus/portfolio listing (what *exists*). The gap between owed and actual is the standing-obligation signal.

This composes existing canon into one posture; the *mechanism* is canon, the *name* is new. Per ADR-343's pattern: **the kernel names the category (expected output / owed work); the Reviewer derives the instance** from budget + mandate + ground-truth. An operator MAY make it explicit (an optional `## Expected Output` MANDATE section with a number), but no workspace is required to — derivation is the default, so every existing workspace inherits the posture without a substrate migration.

## 3. The wake-time self-check + the two-cause classifier (the core)

On a wake (judgment-gated, per ADR-318 — not a checklist on every fire), the Reviewer reasons:

> *Given what I'm on the hook for (budget → pace × mandate → expected output × bar) and how long I've had, is my actual output consistent with it? If not — **why**?*

And it **classifies the gap into exactly one of two causes** — this classifier is the load-bearing addition:

- **(A) Quiet-world** — the loop *can* close, the world was just quiet (no matching signal, no draft on-thesis worth shipping). → This is the **dormancy/aperture** case (ADR-342/343): research the premise, widen the aperture, never lower the floor. *Already canon.*
- **(B) Structurally-can't** — the operation **as configured cannot produce what it owes**, regardless of world state: a declared flow with no originating trigger, a mandate whose output has no organ, a missing capability. → This is the **new** case. The loop is inert, not quiet. Widening the aperture would change nothing because nothing consumes the aperture.

The distinction is the whole point: (A) is a *world* problem the Reviewer solves by widening what it engages; (B) is a *configuration* problem the Reviewer cannot solve by trading/widening harder, because the machine has no part that produces. Conflating them is the failure mode that produces articulate inaction — a Reviewer that "widens its aperture" forever against a loop that was never going to originate anything.

## 4. What the Reviewer does on a (B) finding — tiered by authority (ADR-343 floor + ADR-275 D1)

1. **Self-author the missing organ when it stays within existing authority + floor.** If the gap is "no recurrence originates the work," the Reviewer authors one via `Schedule` (Reviewer-authored cadence, ADR-275 D1 — e.g. an author's `compose-next-piece` judgment recurrence that drafts on-thesis from the corpus + sources, then routes through the existing pre-ship audit floor). Attributed, revertible, audit-trailed. The floor is *unchanged* — the new organ feeds the same quality gate.
2. **Surface (Clarify) when closing the gap needs the operator** — a new capability that doesn't exist, a floor change, or a mandate reinterpretation. "My mandate is to compound a corpus, but nothing in my configured loop originates a piece; I can author a compose cadence, or you can feed drafts — which?" The surfacing is *standing* (re-raised each wake until resolved, via `standing_intent.md`), not a one-shot note that scrolls away.
3. **Never close a (B) gap by lowering the floor.** Producing *more* by relaxing the quality bar is the floor-lowering capitulation ADR-343 forbids; an operability gap is closed by adding an organ or surfacing, never by cheapening output.

### The §1-vs-§2 discriminator is the write-topology, not a judgment call (2026-06-25, the unattended-soak finding)

The line between (1) self-author and (2) surface is **mechanical, derived from Derived Principle 25 (the topology IS the permission policy)**, not a soft judgment: **a blocker the Reviewer can resolve by writing a path its topology already permits is a (1) self-author case; (2) surface is reserved for blockers on paths it *cannot* write** — the `governance/` ceilings it runs under but cannot set, a capability that does not exist, or a mandate reinterpretation it wants the operator to vet *despite* having the authority. The test the Reviewer runs before choosing Clarify: *"is the path that would close this gap inside `constitution/` + `operation/` + `persona/` (mine to author per DP25) or inside `governance/` + `system/` (not mine)?"* If mine → author it (1); if not → surface it (2).

**Empirical trigger** (`docs/evaluations/2026-06-24-unattended-soak-FINDING.md`): a 5-wake unattended soak of alpha-author sustained perfect discipline (closed every cycle, zero drift, carried state forward) but **originated nothing across all 5** — it re-issued the *same* `Clarify(structural_gap)` every wake, naming three blockers (a template `_editorial.md`, a stale pre-ADR-355 MANDATE clause, no piece-2 intent) that were **all on writable paths** (`operation/` + `constitution/`). It mis-classified three (1) self-author cases as (2) surface cases — the exact "articulate inaction" DP30's diagnostic test names, but reaching the *Clarify* branch coherently rather than sleeping silently. The fix is not a new capability (the authority already exists, DP25) and not a frame change (the frame already states "everything in `constitution/`, `persona/`, `operation/` is yours" + "author the missing organ within your floor OR surface"); it is making the **discriminator** explicit as a rule of judgment so the agent applies the topology it already holds. This lands as a clause in each program's `principles.md` §0 (Clarify-vs-decide), instancing this kernel rule with the program's own writable paths (the ADR-343 kernel-names-category / program-derives-instance pattern). **Composes with** ADR-352 (the ask-vs-act gate — a Clarify with `structural_gap=true` on a writable-path blocker is now a *mis-classified* gap, not a permitted ask; the discipline is upstream of the gate, in the classifier).

## 5. Why this is the integrating altitude (above DP24/DP27/DP29)

- DP24 (stewardship): revise a rule ground-truth *falsified* — needs evidence to have accumulated *within* a working loop.
- DP27 (perception): widen what you *perceive*.
- DP29 (operator experience): the *operator's* standing loop.
- **DP24's parent (this):** before any of those, *is the loop even capable of closing against the mandate?* The standing obligation is the to-do that makes the answer self-evident every wake. It turns DP26 (a build-time conformance idea) into a runtime fiduciary responsibility: the Reviewer owns not just the mandate's *rules* but the mandate's *reachability*.

The payoff against the operator's question: **left alone for 90 days, a well-built operation either produces on track, OR its Reviewer has surfaced — dated, attributed, standing — exactly why it cannot and what would close the gap.** Silent flat-line becomes structurally impossible, because the standing obligation re-confronts the Reviewer with its owed-output on every wake.

## 6. Where it lands (agent-composition.md §3.2.1)

- **Stance → frame** (`reviewer_agent.py::_compute_minimal_frame`): the principal-shift that you hold a *standing obligation* (not just react to triggers) and that a gap between owed and actual must be **classified** (quiet-world vs structurally-can't) before acting. This corrects the model's prior that "no trigger fired → nothing to do" — the shift is "you are on the hook for an output over time; reason about that hook, and if your loop can't close, that is itself the thing to act on." Generic, no program noun → frame-legal. Tightly worded (the frame is near its ceiling; this is a few sentences, and the full definition lives in FOUNDATIONS).
- **Rules → principles.md** (per program): the *derivation* of expected-output (how to read budget+mandate into an owed-output) and the *classifier thresholds* are rules of judgment, program-tuned. A program MAY ship a worked instance; the Reviewer derives live otherwise (validated, ADR-343 pattern).
- **Optional explicit declaration → MANDATE.md** `## Expected Output` (operator's choice, never required).

## 7. Scope boundary

- No new primitive, schema, or table. The to-do is *derived* from existing substrate; any organ the Reviewer authors uses the existing `Schedule` + file primitives through the existing gate.
- Does **not** force an expected-output field on any workspace — derivation is default; explicit is opt-in.
- Does **not** authorize floor changes (ADR-343 holds) or governance edits (ADR-320 holds).
- The **author production organ** (the concrete (B) fix for alpha-author — a compose/originate recurrence) is named here as the first instance but is **Reviewer-authored at runtime**, not bundle-scaffolded (ADR-275 D1) — so this ADR ships the *posture that makes the Reviewer author it*, not the recurrence.

## 8. Implementation status (2026-06-18)

- **FOUNDATIONS**: new Derived Principle (the standing-obligation / wake-time operability self-check) + the two-cause classifier; banner + changelog.
- **Kernel frame** (`reviewer_agent.py::_compute_minimal_frame`): the standing-obligation stance + classifier, tightly worded within the ceiling.
- **agent-composition.md §3.2.1**: the posture's partition (stance→frame, derivation+thresholds→principles, optional explicit→MANDATE).
- **prompts CHANGELOG**.
- **Validation**: clean-state probe of the alpha-author Reviewer (profile reset to draft so the corpus is genuinely dormant) — the read is whether it (a) derives its owed-output from budget+mandate, (b) **classifies the gap as structurally-can't** (no originating organ) rather than quiet-world, and (c) acts in-tier (authors a compose organ within the floor, and/or surfaces the structural gap as standing intent). Recorded in `docs/evaluations/`.

---

## 9. Receipts

| Claim | Receipt |
|---|---|
| MANDATE obligates quality-of-existing, not existence | alpha-author MANDATE Success Criteria (voice/continuity/anti-slop/cadence-flag — none originates) |
| Budget carries $ + window, not output volume | `_budget.yaml` `amount_usd: 50.00, window: monthly`; no throughput field |
| No production organ in author judgment recurrences | `_recurrences.yaml` judgment slugs all audit/reconcile; none originates a piece |
| budget→pace is canon; pace→output is new | ADR-327 D6 (loop reasons within budget); no expected-output-volume in canon (Explore grounding) |
| DP26 is design-time; this is wake-time | ADR-332 D2/D4 (bundle conformance) vs this (Reviewer wake-time self-application) |
| Floor + Reviewer-authored-organ discipline preserved | ADR-343 (floor) + ADR-275 D1 (Reviewer authors cadence) |

## 10. Frame-ceiling decision (behavioral-artifact note)

The persona-frame ceiling (`test_adr323_frame_collapse_finished.py::test_system_prompt_under_ceiling`) is raised **11,000 → 11,500 chars**. Rationale, recorded so the guard still bites: three load-bearing kernel postures now share the one situation-scoped paragraph — ADR-318 (forward-reasoning), ADR-342/343 (dormancy + aperture/floor), ADR-344 (standing-obligation + the (A)/(B) classifier). Each is **principal-shift**, not rule-of-judgment — the derivations + thresholds live in `principles.md` per §3.2.1 — so they are frame-legal, and the frame addition for ADR-344 was tightened to the principal-shift only (the full mechanism is in this ADR + FOUNDATIONS + principles.md). 11,500 is still ~⅓ of the ~16.5K pre-collapse frame; the ceiling remains an anti-rebloat guard (ADR-306/323), not a removed one. The discipline holds: a future over-ceiling condition is *almost always* fixed by moving a rule-of-judgment to `principles.md`, not by raising the ceiling — and any further raise requires its own same-rationale ADR, never a silent bump.
