# Reviewer Substrate

> **Status**: Canonical
> **Date**: 2026-04-23
> **Authors**: KVK, Claude
> **Scope**: The architectural layer that renders judgment on proposed actions. The filesystem substrate that expresses the Reviewer seat, the occupant declaration and rotation protocol, the operational modes vocabulary, the calibration trail semantics, and the prospective-attribution contract with chat surfaces.
> **Upstream**: [THESIS.md](THESIS.md) — the Reviewer commitment is the thesis's second architectural commitment. [FOUNDATIONS.md](FOUNDATIONS.md) — Axiom 2 (Identity, four cognitive layers), Derived Principle 14 (Roles persist; occupants rotate).
> **Implementation**: ADR-194 v2 (current code lands Phases 1 + 2a + 2b + 3).

---

## Purpose

This document is the technical canon for the Reviewer layer. It specifies what the Reviewer substrate *is*, independent of the current implementation, so that future occupants (human, internal AI, external AI) and future implementations can be evaluated against a stable specification.

It is sibling to [authored-substrate.md](authored-substrate.md): where `authored-substrate.md` is the canon for how files are written with attribution, this document is the canon for how the seat of judgment reads those files and renders verdicts.

---

## The claim

**The Reviewer is an architecturally independent cognitive seat that reads the operator's declared intent, the accumulated track record, and a proposed action; renders a verdict with reasoning; and maintains a durable trail of judgment that calibrates over time.**

The seat is interchangeable between occupant classes — human, YARNNN-internal AI, external AI service — without architectural change. The architectural value compounds in the **seat** (the substrate it reads and the trail it writes), not in the **occupant** (who happens to be rendering verdicts this cycle). This is Derived Principle 14 ("Roles persist; occupants rotate") applied to its canonical case.

---

## The five substrate files

The Reviewer seat is expressed as a filesystem subtree at `/workspace/review/`. The substrate is the seat: there is no in-memory abstraction that persists between verdicts, no parallel config table, no reviewer ABC. Every aspect of the seat — who occupies it, what principles it judges by, what modes it operates in, how it has calibrated, what it has decided — lives in files.

### `IDENTITY.md` — who the seat is

Persona-agnostic statement of the role. What the seat is for, what its scope is, what its reasoning posture is. This file describes the *role*, not the occupant. It is largely static after scaffolding and edited rarely.

*Written by*: operator (at scaffold time and on rare revisions).

### `OCCUPANT.md` — who currently fills the seat

Declares the current occupant of the seat. One of:

- `human:<user_id>` — the operator themselves, filling the seat via approval UX
- `ai:<model>-<version>` — a YARNNN-internal AI reviewer (e.g., `ai:sonnet-v2`)
- `external:<service>-<identifier>` — an external AI service filling the seat via adapter
- `impersonated:<admin_user_id>-as-<persona_slug>` — admin alpha-stress-testing mode

The file also declares occupant-level configuration that is not architecturally universal: for AI occupants, the confidence threshold at which the occupant auto-acts vs. defers; for human occupants, availability expectations (if any); for external occupants, the adapter contract.

When the occupant rotates, `OCCUPANT.md` is overwritten and a handoff entry appends to `handoffs.md` (below).

*Written by*: operator (rotation is operator-initiated) or system (when a rotation trigger fires, e.g., human unavailable for > threshold).

### `principles.md` — operator-declared judgment framework

The operator's stated preferences for how judgment should be rendered in this workspace. Seeded with sensible defaults at scaffold. Operator-editable at any time via Context surface or chat with YARNNN.

Principles include (non-exhaustive):
- Capital horizons that matter (daily / weekly / quarterly / multi-year)
- Reversibility thresholds — above what cost/scope does an action require the human occupant regardless of mode
- Domain-specific auto-approve bounds (e.g., `trading: auto_approve_below_cents: 5000`)
- Ambiguity resolution posture (prefer defer, prefer reject, prefer approve-with-note)

This file is the operator's authored intent on *how* they want to be judged on behalf of. It is read by every occupant of the seat. It is independent of the occupant class.

*Written by*: operator.

### `modes.md` — operational modes of the seat

The Reviewer seat operates along continua, not switches. `modes.md` declares the current operational configuration along three axes:

- **Autonomy level** — where along the spectrum from "occupant decides everything" to "occupant defers everything" the seat is currently operating. Typically expressed as per-domain thresholds.
- **Scope** — which domains the current occupant has authority over. A human may retain authority over trading while an AI occupant handles commerce in the same workspace. Cross-domain occupant mixing is legitimate and common.
- **On-behalf posture** — when the occupant defers, does it defer with (a) a recommendation, (b) a ranked shortlist of options, (c) a pass-through with no opinion. This is the gradient between the seat acting as *advisor* vs. *agent*.

`modes.md` is read at the start of every verdict rendering. Changes to it take effect on the next verdict.

*Written by*: operator (modes are operator-declared policy) or YARNNN (on operator instruction via chat).

### `decisions.md` — append-only verdict trail

The canonical judgment trail. Every verdict the seat renders, regardless of occupant, appends one entry here. No sibling table, no audit log elsewhere — this file is the audit.

Each entry records:
- Timestamp
- `proposal_id` (the action being judged)
- `reviewer_identity` (who filled the seat for this verdict — matching the occupant taxonomy above)
- Verdict (`approve` / `reject` / `defer`)
- Reasoning (short natural-language rationale)
- Confidence (when the occupant is AI and reports one)
- Pointer to the proposal's post-execution outcome, once reconciliation lands (enables calibration — see below)

*Written by*: the occupant currently filling the seat, at verdict time.

### `handoffs.md` — occupant rotation history

Append-only log of seat rotations. Each entry records when the occupant changed, from what to what, why (operator-initiated / threshold-triggered / emergency-fallback), and which decisions.md range the new occupant is responsible for going forward.

This file makes Principle 14 (Roles persist; occupants rotate) legible in substrate. An operator (or future auditor) can reconstruct the full occupancy history of the seat without reference to external state.

*Written by*: system at rotation time; optionally annotated by operator.

### `calibration.md` — how the seat's judgments have aligned with outcomes

The calibration trail. Periodically (per ADR-195 v2's outcome reconciliation task), this file is rebuilt from `decisions.md` × reconciled outcomes in `_performance.md` across domains.

Calibration captures:
- For each verdict category (approve / reject / defer), aggregate outcome metrics over rolling windows
- Per-occupant calibration (does AI occupant v1 over-approve? does human occupant under-approve on low-stakes reversible writes?)
- Divergence signals — proposals the occupant judged confidently that outcomes contradicted

This file is read by the operator when evaluating whether to rotate the occupant, when tightening or loosening `modes.md`, and when reviewing `principles.md`. It is read by AI occupants as prior context for future verdicts. It closes the money-truth → future-judgment loop per FOUNDATIONS Axiom 7 (Recursion).

*Written by*: back-office reconciliation task (zero-LLM, deterministic).

---

## The prospective-attribution contract

Retrospective attribution exists in `decisions.md`. Prospective attribution is a contract with the chat and cockpit surfaces: **the operator must be able to see who currently occupies the seat before they rely on a pending verdict.**

The contract, stated as invariants:

- **I1**: Any surface that displays a pending proposal displays the current occupant identity (from `OCCUPANT.md`) alongside it.
- **I2**: When a verdict renders, the verdict card displays the occupant identity inline with the verdict — not only in the audit trail.
- **I3**: When `OCCUPANT.md` changes (seat rotation), the chat surface emits a handoff event that is legible to the operator in real time.
- **I4**: The operator has a single command path in chat to inspect `OCCUPANT.md`, `modes.md`, and recent `handoffs.md` entries without leaving the conversation.

Why this matters architecturally: Principle 14 says the seat is interchangeable. Interchangeability that is invisible to the operator is not interchangeability — it is opacity. The substrate makes the seat knowable; the attribution contract makes the seat knowable *in the moment of relying on its verdicts*.

---

## Operational modes vocabulary

The three axes on `modes.md` deserve named vocabulary so that operator-facing surfaces and prompts can refer to them consistently.

**Autonomy level** — positions along the continuum:

- `manual` — every verdict deferred to human, regardless of reversibility or stakes
- `assisted` — AI occupant renders recommendation, human occupant renders verdict
- `bounded_autonomous` — AI occupant auto-acts below declared thresholds; defers above
- `autonomous` — AI occupant auto-acts on all verdicts within the seat's scope; escalates only on declared exception conditions

These are not modes the seat *is in globally* — they are per-domain or per-proposal-class configurations within `modes.md`.

**Scope** — a list of `(domain, occupant, autonomy_level)` triples. Any verdict in a domain not covered by a triple defaults to `manual`. This makes scope omission safe.

**On-behalf posture** — when the current occupant defers to the next tier (usually AI → human), the posture declares:

- `silent_defer` — pass the proposal upward with no opinion
- `recommend` — pass with a single recommended verdict and reasoning
- `shortlist` — pass with ranked options and reasoning per option

---

## The calibration loop

The Reviewer seat gains value over tenure via the calibration loop:

1. Verdict renders → `decisions.md`
2. Proposal executes (if approved) → outcome lands in platform → ADR-195 reconciliation detects outcome → `_performance.md` updates
3. Reconciliation cross-references verdict with outcome → `calibration.md` updates
4. Future verdicts read `calibration.md` as prior (AI occupants) or consult it for mode tuning (human occupant)
5. Occupant rotation decisions reference `calibration.md` (was AI occupant over-confident? → tighten thresholds in `modes.md` or rotate back to human)

This loop is the ground on which the seat's judgment improves. It is also the mechanism by which seat rotation is evidence-based rather than speculative: an AI occupant's suitability for a given `modes.md` configuration is not asserted but measured.

---

## Review orchestration vs. reviewer entity — the split

Two structurally distinct things live inside what we call "the Reviewer." Conflating them is the first source of confusion for anyone encountering the architecture, and making the split explicit is canon.

### Review orchestration (the mechanics)

The **review orchestration** is the runtime coordination that moves a proposal from creation to verdict to execution or rejection:

- `ProposeAction` creates a proposal → status `pending`
- Reactive trigger fires the `review-proposal` task
- Task pipeline dispatches to the current occupant declared in `OCCUPANT.md`
- Occupant reads inputs (proposal, `_performance.md`, principles, modes, calibration), reasons, renders verdict
- Verdict writes to `decisions.md` with proper `authored_by` attribution
- On approve: verdict triggers `ExecuteProposal` callback
- On reject: verdict triggers `RejectProposal` callback
- On defer: proposal remains pending with annotation

This is **orchestration machinery** — runtime coordination, dispatch, callbacks. It is implemented in `review_proposal_dispatch.py`, `reviewer_audit.py`, task pipeline integration. It is part of the orchestration framework (in the philosophical sense — not a renamed module, but the same class of work as other task dispatch and pipeline mechanics). **This machinery is not where agency lives.** It is plumbing.

### The reviewer entity (the agent-in-the-strict-sense)

The **reviewer entity** is the persona/occupant that applies judgment. When a human occupies the seat, the operator is the entity. When an AI occupies the seat, the AI occupant is the entity. In either case, the entity:

- Holds standing intent (the operator's declared principles, which live in the seat's substrate)
- Reasons from that intent against track record and proposal
- Renders a verdict on behalf of the operator's declared judgment framework

This is **agency in the strict principal-agent sense** (see [THESIS.md](THESIS.md) "Vocabulary: production layers vs. judgment layers"). The reviewer entity is the fiduciary representative of the operator's judgment. Today the AI occupant is implemented as a `thinking_partner`-class agent (sharing substrate with the YARNNN producer-layer agent); this is an implementation choice, not an architectural commitment. Future AI occupants may be distinct entity classes purpose-built for the judgment role.

### Why the split matters

- **The orchestration is interchangeable and low-novelty.** Another system could implement the same dispatch-and-callback pattern; the interesting thing isn't the mechanics.
- **The reviewer entity is where YARNNN's architectural differentiation concentrates.** A judgment-bearing, intent-holding, principal-representing seat is the thing most "agentic frameworks" lack.
- **Implementation going forward should respect the split.** Code that touches review orchestration (dispatch, callbacks, audit) is plumbing and should be named/structured accordingly. Code and substrate that touches the reviewer *entity* (IDENTITY, OCCUPANT, principles, calibration, judgment logic) is where agency is expressed and should be treated as first-class architectural concern.

### Implementation alignment going forward

From 2026-04-23 onward, every design decision that touches the Reviewer should explicitly answer: *"is this orchestration (mechanical runtime coordination) or entity (judgment, persona, principles)?"* The two are not renamed in code today, but the split is enforceable at the design-review level — a mechanic that conflates them is drift.

Examples:
- Prospective-attribution contract (invariants I1–I4 below) is **entity** — it surfaces who is occupying the seat, which is about agency legibility.
- Dispatch routing from `ProposeAction` to occupant is **orchestration** — pure runtime plumbing.
- Calibration loop feedback into future verdicts is **entity** — it shapes how the entity judges.
- `decisions.md` write discipline is **both** — the write path is orchestration (how the entry lands); the content of the entry (the reasoning) is entity-output.

---

## What the Reviewer seat is not

- **Not a safety layer.** Safety layers reject bad things. The Reviewer layer makes *judgments* — approve, reject, defer — against declared principles. Safety is one of many possible framings of what a judgment evaluates; the seat is general over all of them.
- **Not coupled to proposal review exclusively.** Today the seat's primary action is rendering verdicts on `action_proposals`. The substrate supports the seat taking a broader judgment role (evaluating accumulated context for stale entries, flagging drift in domain principles, etc.) without architectural change. The proposal-review action is the first use case, not the only one.
- **Not a human-in-the-loop feature.** Human-in-the-loop frames AI as primary and human as safety net. The Reviewer seat is primary; the occupant (human or AI) fills it. The loop is not about human oversight — it is about independent judgment with occupant-interchangeable rendering.
- **Not an ABC, interface, or pluggable abstraction in code.** Per ADR-194 v2 retraction of v1, the seat is substrate — the files at `/workspace/review/` — not an in-memory abstraction. Occupant rotation is a file write, not a dependency injection.
- **Not identical with review orchestration.** The orchestration is plumbing; the reviewer entity is where agency lives. See "Review orchestration vs. reviewer entity — the split" above.

---

## Relationship to other canons

- [THESIS.md](THESIS.md) — second architectural commitment ("Independent judgment — the reviewer is a durable role, not a safety feature") states the philosophical claim. This document specifies the substrate expression of that claim.
- [FOUNDATIONS.md](FOUNDATIONS.md) — Axiom 1 (Substrate) requires the seat be filesystem-expressed; Axiom 2 (Identity) establishes Reviewer as the fourth cognitive layer; Derived Principle 14 ("Roles persist; occupants rotate") makes occupant-interchangeability structurally enforceable.
- [authored-substrate.md](authored-substrate.md) — every write to `/workspace/review/` (including `decisions.md` append, `OCCUPANT.md` rotation, `handoffs.md` entry) flows through the Authored Substrate with required `authored_by` attribution.
- [ADR-194 v2](../adr/ADR-194-pluggable-reviewer-and-impersonation.md) — current implementation. Phases 1 + 2a + 2b + 3 shipped. This document describes the *target substrate*; ADR-194 v2 describes *what is implemented today*. Gaps between this document and ADR-194 v2 are roadmap items, not bugs.
- [ADR-195 v2](../adr/ADR-195-money-truth-outcome-ledger.md) — money-truth substrate that calibration.md reads from.

---

## Revision discipline

This document changes when:

- A new substrate file is added to the seat (with a non-trivial architectural reason)
- The attribution contract invariants change
- The operational modes vocabulary is extended
- The calibration loop's inputs or cadence change structurally

It does not change when:

- An ADR adjusts implementation details within the specified substrate
- A new occupant class is added (the occupant taxonomy is extension-friendly; new classes are noted in-line without revising this doc)
- Principles, modes, or calibration content evolve (that is the seat's normal operation, not doc evolution)
