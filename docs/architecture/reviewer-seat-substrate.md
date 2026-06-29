# Reviewer Seat Substrate

> **Status**: Canonical
> **Date**: 2026-04-24 (split from `reviewer-substrate.md` per ADR-315 D5, 2026-06-04)
> **Authors**: KVK, Claude
> **Scope**: The **kernel/seat** half of the Reviewer canon — the filesystem substrate that *is* the seat, independent of whoever occupies it. Seat files, occupant declaration + rotation protocol, calibration trail semantics, delegation vocabulary, and the prospective-attribution contract with chat surfaces. The *occupant* (the AI agent that fills the seat) is documented separately in [reviewer-occupant.md](reviewer-occupant.md); the named seam between them is [reviewer-occupant-contract.md](reviewer-occupant-contract.md).
> **Upstream**: [THESIS.md](THESIS.md) §"Independent judgment" (the Reviewer is the second architectural commitment). [FOUNDATIONS.md](FOUNDATIONS.md) Axiom 2 (Agents vs Orchestration — the Reviewer is an Agent). [LAYER-MAPPING.md](LAYER-MAPPING.md) (authoritative Agent/Orchestration taxonomy). Derived Principle 14 (Agent seats persist; occupants rotate).
> **Implementation**: [ADR-194 v2](../adr/ADR-194-pluggable-reviewer-and-impersonation.md) (Phases 1–4). [ADR-217](../adr/ADR-217-workspace-autonomy-substrate.md) (autonomy moved from seat-owned `modes.md` to shared `_shared/AUTONOMY.md`). [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) (seat ≠ occupant — the seat stays substrate; the occupant is carved into a contract-bounded module).

---

## Purpose

This document is the technical canon for the **Reviewer seat** — the systemic Agent role (one per workspace) that occupies the independent judgment seat. It specifies what the Reviewer's substrate *is*, independent of the current occupant, so that future occupants (human operator, YARNNN-internal AI, external AI service) and future implementations can be evaluated against a stable specification.

The seat≠occupant distinction (ratified by [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md)): **the seat is substrate; the occupant is a module.** This document is the seat. [reviewer-occupant.md](reviewer-occupant.md) is the occupant.

Sibling to [authored-substrate.md](authored-substrate.md): where `authored-substrate.md` is the canon for how files are written with attribution, this document is the canon for the files the Reviewer seat reads and writes.

Sibling to [orchestration.md](orchestration.md): where `orchestration.md` is the canon for production machinery (task pipeline, capability bundles, dispatch routing), this document is the canon for one of the Agent seats the Orchestrator serves. The Reviewer Agent uses orchestration machinery (to read proposals, dispatch calibration rebuilds) but is not itself orchestration.

---

## The claim

**The Reviewer is an Agent** — a judgment-bearing entity that reads the operator's declared intent, the accumulated track record, and a proposed action; renders a verdict with reasoning; and maintains a durable trail of judgment that calibrates over time.

The **seat** (the Reviewer Agent's architectural role) is interchangeable between occupant classes — human, YARNNN-internal AI, external AI service — without architectural change. The architectural value compounds in the **seat's substrate** (what it reads and writes) and the **accumulated calibration** over tenure, not in the **occupant** (who happens to be rendering verdicts this cycle). This is Derived Principle 14 ("Agent seats persist; occupants rotate") applied to its canonical case.

The Reviewer is the **sole systemic persona-bearing Agent in YARNNN today** (see [LAYER-MAPPING.md](LAYER-MAPPING.md) + [FOUNDATIONS.md](FOUNDATIONS.md) Axiom 2). YARNNN itself is the orchestration chat surface, not a persona-bearing Agent. The seat lives at `/workspace/persona/` (ADR-320 re-rooting).

> **Seat-canon generalization (ADR-381 D4, 2026-06-29 — supersedes ADR-320 D9's "one judgment seat per workspace").** The two-order model splits the single seat into **two seat *classes*** along the management/judgment seam:
> - **One management seat** (Rung 1) — occupied by **Freddie**, the named Rung-1 substrate steward (systemic, one per workspace, the substrate + the system). This is today's `/workspace/persona/` six-file seat, re-labeled the *management* seat. Freddie's domain is substrate management, derive-and-cite, placement, multi-principal arbitration, and CRUD + governance over the judgment seats. **No operator-authored persona, no capital/consequential judgment** (Rung 2's, the persona agents). Reversible substrate-internal mutations.
> - **N judgment seats** (Rung 2) — occupied by **persona agents** (operator-opted-in, zero-to-many, bounded judgment within a mandate, consequential external action under Freddie-set authority).
>
> The **seat≠occupant model (ADR-315) is the inheritance vehicle for both classes** — a seat is substrate, an occupant is a module/identity, rotation is a file write. ADR-381 names the split + Freddie's governing authority (D4 + D5) from Freddie's side; **the per-judgment-seat substrate shape (how much of the six files below each persona agent gets), its lifecycle, and its trust model are deferred to [ADR-382](../adr/ADR-382-persona-agent-seats-the-rung-2-judgment-layer.md)** (the governed side). The six files below describe the **management seat** (Freddie's). See [ADR-381](../adr/ADR-381-freddie-the-rung-1-substrate-steward.md) + the [two-order direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md).
>
> **Naming**: "Freddie" is the operator-facing label for the *occupant* of the management seat (ADR-381 D1, a relabel-keep-slug per ADR-251). The internal `reviewer` slug + `reviewer:` attribution prefix + `/workspace/persona/` path are unchanged. Where this doc says "the Reviewer seat" / "the seat," read it as the management seat's *role*; where it names today's hardened occupant, that occupant is Freddie. Future systemic management-class Agents (Auditor, Advocate, etc.) remain deferred.

---

## The six seat files

The Reviewer seat is expressed as a filesystem subtree at `/workspace/persona/` (re-rooted from `/workspace/review/` by ADR-320 — the directory `persona/` names the detached judge regardless of what the entity is eventually called). The substrate is the seat: there is no in-memory abstraction that persists between verdicts, no parallel config table, no reviewer ABC. Every aspect of the seat — who occupies it, what principles it judges by, how it has calibrated, what it has decided — lives in files. Delegation authority is read alongside the seat from `/workspace/governance/AUTONOMY.md`, but it is **not** a seat-owned file (`governance/` is the operator-only ceiling root the seat runs under but cannot set).

### `IDENTITY.md` — who the seat is

Persona-agnostic statement of the role. What the seat is for, what its scope is, what its reasoning posture is. This file describes the *role*, not the occupant. It is largely static after scaffolding and edited rarely. Per ADR-320 D2b the legacy operator-identity file (the operator's operating posture) collapsed into this one — the operator's reasoning-character and the embodied judge persona are the same reasoning-character described twice, so there is no separate `context/_shared/IDENTITY.md`; `persona/IDENTITY.md` is the singular home for "how this operator's judgment reasons."

*Written by*: operator (at scaffold time and on rare revisions).

### `OCCUPANT.md` — who currently fills the seat

Declares the current occupant of the seat. One of:

- `human:<user_id>` — the operator themselves, filling the seat via approval UX
- `ai:<model>-<version>` — a YARNNN-internal AI reviewer (e.g., `ai:sonnet-v2`)
- `external:<service>-<identifier>` — an external AI service filling the seat via adapter
- `impersonated:<admin_user_id>-as-<persona_slug>` — admin alpha-stress-testing mode

The file also declares occupant-level configuration that is not architecturally universal: for AI occupants, the confidence threshold at which the occupant auto-acts vs. defers; for human occupants, availability expectations (if any); for external occupants, the adapter contract.

When the occupant rotates, `OCCUPANT.md` is overwritten and a handoff entry appends to `handoffs.md` (below). The occupant classes and how the AI occupant reads this file are detailed in [reviewer-occupant.md](reviewer-occupant.md).

*Written by*: operator (rotation is operator-initiated) or system (when a rotation trigger fires, e.g., human unavailable for > threshold).

### `principles.md` — operator-declared judgment framework

The rule-set the persona applies — *what rules of judgment* the Reviewer evaluates substrate against. Seeded with sensible defaults at scaffold. Operator-editable at any time via Context surface or chat with YARNNN. Independent of the occupant class.

> **Partition-discipline canon is at [`agent-composition.md`](agent-composition.md) §3.2.1 — the singular enforcement home for the content boundary between `principles.md` (rule-set) and the persona-frame `_compute_*` sections in `api/agents/reviewer_agent.py` (reasoning posture).** That section names: the four-field rule shape every `principles.md` entry must take (name + substrate-read + pass-condition + verdict-on-fail), the bright-line list of content that does NOT belong in `principles.md` (self-amendment discipline, anti-patterns, fiduciary principle, posture taxonomy, standing-intent contract, cadence-trifecta, wake-context discipline, write authority, voice/narration — all in persona-frame), the conflict-resolution rule (PRECEDENT > principles; persona-frame > principles for reasoning-posture content; AUTONOMY ceiling > principles for delegation widening), and a diagnostic test for uncertain content. **Future ADRs that reshape principles.md content must update §3.2.1 in the same commit.** This document describes the substrate file's role in the seat; §3.2.1 describes the content boundary within it; [reviewer-occupant.md](reviewer-occupant.md) describes the persona-frame side of the partition.

Examples of rules that fit the four-field shape (illustrative, per-program tuning in bundle templates):
- Capital horizons that matter (daily / weekly / quarterly / multi-year) — substrate-anchor: `_money_truth.md`-derived rolling window.
- Reversibility thresholds and framework-level defer rules — substrate-anchor: proposal `reversibility` field × declared threshold.
- Ambiguity resolution posture (prefer defer / reject / approve-with-note) as the verdict-on-fail shape per rule.
- Narrowing conditions that add defer conditions on top of AUTONOMY.md's raw delegation ceiling (never widen — ADR-217 D4).

Numeric thresholds per program live in `_principles.yaml` (ADR-254 machine-parsed sibling); prose declarations of the *categories* may live here.

*Written by*: operator.

### Read alongside the seat: `/workspace/governance/AUTONOMY.md`

Autonomy declaration is no longer owned by the Reviewer seat. ADR-217 moved it to shared operator-intent substrate; ADR-320 re-rooted it to the `governance/` ceiling root:

- **Prose path**: `/workspace/governance/AUTONOMY.md` (LLM/human reading only)
- **Machine config path**: `/workspace/governance/_autonomy.yaml` (ADR-254 + Commit F)
- **Author**: operator only (or YARNNN on explicit operator instruction)
- **Meaning**: workspace-scoped delegation ceiling, with `default` + per-domain overrides. Field `delegation` ∈ `{manual, bounded, autonomous}` (Commit F 2026-05-11 — 3-value canonical enum) plus optional `ceiling_cents` (required when `bounded`) and `never_auto`

The Reviewer dispatcher reads AUTONOMY.md at the start of every verdict rendering. `principles.md` can **narrow** that delegation with additional defer conditions, but never widen it. This is the servant-can-be-more-conservative-than-the-master-permits rule ratified by ADR-217.

AUTONOMY.md sits outside the six seat files because seat rotation must not touch it; delegation is operator-to-role, not operator-to-occupant.

### Read alongside the seat: `/workspace/constitution/MANDATE.md` (the agent's purpose — ADR-383)

The seat's six files express *how the agent reasons + its trail*; `MANDATE.md` (read alongside, in `constitution/`) expresses *why the agent exists* — its purpose. Per [ADR-383](../adr/ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md), **the seat's file-structure is the agent-universal shape**: every agent over this substrate is constituted by these files + MANDATE + governance, differing only in *content*. Two consequences for the seat:

- **MANDATE is every agent's purpose, populated for every agent.** ADR-383 reframes ADR-207's "MANDATE declares the Primary Action" → "MANDATE declares the agent's *purpose*; the Primary Action is the operation-instance of purpose." The **system agent (Freddie)** that fills the seat in a bare workspace carries the kernel-default **steward-mandate** ("steward this substrate" — names no value-moving Primary Action); a program activation overwrites it with the operation's mandate (bundle-fork, ADR-226). So MANDATE is never empty, and a bare workspace is a *constituted steward*, not "unconfigured" (ADR-383 §3 D3).
- **The systemic occupant's self-model is steward-first.** The persona-frame (`_compute_minimal_frame`) leads with the steward self-model (the system agent), routing to judgment when the MANDATE/principles.md declare an operation — FOUNDATIONS DP21's two-order amendment. The seat's *structure* (the Variant-F seven claims) is occupant-agnostic and describes both the steward and the judgment occupant; the *self-model* the frame carries is steward-first (ADR-381/383). The judgment posture (standing-obligation, aperture/floor) lives in each agent's `principles.md`, not the frame (`agent-composition.md` §3.2.1 + §4.4 ADR-383 amendment).

### `standing_intent.md` — forward-looking working state (ADR-284, 2026-05-17)

The Reviewer's forward-looking judgment substrate. *What is the Reviewer watching for?* *What would change its next move?* *What open questions would it surface to the operator?* Read at every wake (kernel-universal envelope addition per ADR-284 + ADR-285). Updated at every judgment-mode cycle — including no-fire cycles, because the substrate counterpart to a no-fire judgment is an updated standing_intent.md.

Schema is instance-agnostic (frontmatter + three section headings: *What I'm watching for* / *What would change my next move* / *Open questions to the operator*); content varies per program. Single-writer (the Reviewer itself). Overwritable per cycle; the revision chain (ADR-209) preserves history of what the seat was watching for across cycles, queryable via `ListRevisions` + `ReadRevision` + `DiffRevisions`.

`reviewer-workbench` role per ADR-281 §3 six-role taxonomy — peer to `notes.md` and `working/`. **Not** `system-ledger` (that role is single-writer infrastructure-rendered append-only; standing_intent is Reviewer-authored and overwritable).

This file closes the load-bearing canon gap that pre-ADR-284 declared the Reviewer "holds standing intent on behalf of a principal" (Axiom 2) without giving standing intent a substrate home. Same canon applies to future systemic Agents (Auditor at `/workspace/auditor/standing_intent.md`, etc.) and to user-authored domain Agents (`/agents/{slug}/standing_intent.md`, deferred per ADR-284 D10).

*Written by*: the occupant currently filling the seat, at every judgment cycle.

### `judgment_log.md` — append-only verdict + material-outcome lineage (post-ADR-281 §5)

> **Vocabulary note (ADR-281, 2026-05-15)**: `decisions.md` was renamed to `judgment_log.md` and tightened to a single-writer contract gated by the 5-condition material-outcome gate. The rest of this section's prose still refers to `decisions.md` in places where ADR-281's cascade pass didn't reach; substitute `judgment_log.md` everywhere. Targeted prose cleanup is a separate scope-discipline commit.

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

### `reflection.md` — the seat's interpreted learning from how its judgments turned out (ADR-364, supersedes `calibration.md`)

The reflection trail — the agent's *own interpretation* of the closed intent→outcome loop. **Reviewer-authored** (not machine-rebuilt) from the wake envelope's **gap-fact**: each recent material verdict in `judgment_log.md` joined to its ground-truth outcome (value + ADR-330 attestation) by `proposal_id` — the keystone FK ADR-364 D1 persists. The seat reads that presented gap and writes here what it learned.

The two-layer split is what makes this honest:
- **The gap (a fact, not a file)** — a DP19-clean bounded read-and-present in the envelope (`reviewer_envelope.py::_reflection_gap_fact`). The kernel *presents* the join (decision → attested outcome); it does NOT label matched/diverged. Derived-not-stored per Axiom 1.
- **The reflection (the file)** — the agent's interpretation: did my call work, what would I watch for or decide differently. The agent reflects over an outcome it *cannot edit* (attested), so development-over-tenure has an honest substrate.

Reflection captures (the agent's own words, prose):
- Which verdict patterns the agent now trusts vs distrusts, given how they paid off
- What it has stopped watching for (a watch that never produced) or started watching for (a divergence the outcomes revealed)
- The "I'd decide differently next time" learning that compounds across tenure

Read by the operator when evaluating whether to rotate the occupant, tune `AUTONOMY.md`, or review `principles.md`; read by AI occupants as prior context. It closes the ground-truth → future-judgment loop per FOUNDATIONS Axiom 7 (Recursion) — and it is what makes the development-axis claim (FOUNDATIONS Axiom 2: "Reviewer develops through reflection") *real* rather than aspirational.

*Written by*: the Reviewer (seat occupant), from the envelope gap-fact. **No system-writer** — this retires `calibration.md`'s back-office reconciliation writer and the single-writer cross-class exception that came with it (a topology simplification per ADR-364 D4). *(The legacy aggregate-windows `calibration.md` — per-occupant × verdict rolling windows, machine-rebuilt — is superseded; its `back-office-reviewer-calibration` task retirement is a scoped follow-up.)*

---

## The prospective-attribution contract

Retrospective attribution exists in `decisions.md`. Prospective attribution is a contract with the chat and cockpit surfaces: **the operator must be able to see who currently occupies the seat before they rely on a pending verdict.**

The contract, stated as invariants:

- **I1**: Any surface that displays a pending proposal displays the current occupant identity (from `OCCUPANT.md`) alongside it.
- **I2**: When a verdict renders, the verdict card displays the occupant identity inline with the verdict — not only in the audit trail.
- **I3**: When `OCCUPANT.md` changes (seat rotation), the chat surface emits a handoff event that is legible to the operator in real time.
- **I4**: The operator has a single command path in chat to inspect `OCCUPANT.md`, shared `AUTONOMY.md`, and recent `handoffs.md` entries without leaving the conversation.

Why this matters architecturally: Principle 14 says the seat is interchangeable. Interchangeability that is invisible to the operator is not interchangeability — it is opacity. The substrate makes the seat knowable; the attribution contract makes the seat knowable *in the moment of relying on its verdicts*.

---

## Delegation vocabulary

The delegation settings in AUTONOMY.md deserve named vocabulary so that operator-facing surfaces and prompts can refer to them consistently.

**Delegation** (per Commit F 2026-05-11 — canonical 3-value enum) — positions along the continuum:

- `manual` — every verdict deferred to human, regardless of reversibility or stakes
- `bounded` — AI occupant auto-acts below declared thresholds; defers above
- `autonomous` — AI occupant auto-acts on all verdicts within the seat's scope; escalates only on declared exception conditions (still respects `never_auto` and the irreversibility gate)

These are not modes the seat *is in globally* — they are workspace-scoped defaults and per-domain overrides in `_autonomy.yaml` (ADR-254 — machine-parsed sibling of AUTONOMY.md).

**Thresholds** — for `bounded`, `ceiling_cents` is required; `never_auto` lists action-type substrings that always defer regardless of the ceiling.

**Naming history** — pre-Commit-F the field was `level` and the value space included `assisted` + `bounded_autonomous`. The mismatch silently treated every workspace as `manual` because the FE wrote `level` while the backend read `delegation`. Migration 172 + Commit F unified the schema; the legacy fields no longer exist on disk.

**Framework narrowing** — `principles.md` may add defer conditions beyond AUTONOMY.md. This preserves the separation between operator delegation and the persona's applied framework.

---

## The reflection loop (ADR-364, supersedes the calibration loop)

The Reviewer seat gains value over tenure via the reflection loop:

1. Verdict renders → `judgment_log.md` (carrying `proposal_id` on decision blocks)
2. Proposal executes (if approved) → outcome lands in platform → ADR-195/ADR-330 reconciliation detects outcome → ground-truth file (`_money_truth.md` / `_signal.md`) updates, **carrying `proposal_id` on the event** (the ADR-364 D1 keystone — the join key that was previously dropped)
3. The wake envelope **presents the gap** — each verdict joined to its attested outcome by `proposal_id` (a fact, DP19-clean; the kernel presents, it does not judge)
4. The Reviewer **reads the gap and authors `reflection.md`** — its interpretation of which calls worked, what it learned, what it'd watch for or decide differently (the agent reflects over an outcome it cannot fake)
5. Future verdicts read `reflection.md` as prior; occupant rotation + delegation/framework tuning reference it (was the AI occupant over-confident, per its own reflected record vs ground truth? → tighten `AUTONOMY.md`, add narrowing in `principles.md`, or rotate)

This loop is the ground on which the seat's judgment improves — and the keystone (step 2's preserved FK) is what makes it *closeable* at all; before ADR-364 the join key was dropped and the loop stayed open (the symptom: "reflection verdicts accumulate without changes; surface looks stagnant"). It is also the mechanism by which seat rotation is evidence-based rather than speculative: an AI occupant's suitability is not asserted but measured against attested outcomes.

---

## Review orchestration vs. reviewer entity — the split

Two structurally distinct things live inside what we call "the Reviewer." Conflating them is the first source of confusion for anyone encountering the architecture, and making the split explicit is canon. (This is the seat-side framing of the same boundary ADR-315 draws between seat-substrate and occupant: orchestration is plumbing the kernel owns; the entity is the occupant — see [reviewer-occupant.md](reviewer-occupant.md).)

### Review orchestration (the mechanics)

The **review orchestration** is the runtime coordination that moves a proposal from creation to verdict to execution or rejection:

- `ProposeAction` creates a proposal → status `pending`
- Reactive trigger fires the wake gateway (`services/wake.py`)
- The wake gateway dispatches to the current occupant declared in `OCCUPANT.md`
- Occupant reads inputs (proposal, `_money_truth.md`, principles, shared AUTONOMY declaration, calibration), reasons, renders verdict
- Verdict writes to `decisions.md` with proper `authored_by` attribution
- On approve: verdict triggers `ExecuteProposal` callback
- On reject: verdict triggers `RejectProposal` callback
- On defer: proposal remains pending with annotation

This is **orchestration machinery** — runtime coordination, dispatch, callbacks. It is implemented in `review_proposal_dispatch.py`, `reviewer_audit.py`, `services/wake.py`. It is part of the orchestration framework (in the philosophical sense). **This machinery is not where agency lives.** It is plumbing.

### The reviewer entity (the agent-in-the-strict-sense)

The **reviewer entity** is the persona/occupant that applies judgment. When a human occupies the seat, the operator is the entity. When an AI occupies the seat, the AI occupant is the entity. In either case, the entity:

- Holds standing intent (the operator's declared principles, which live in the seat's substrate)
- Reasons from that intent against track record and proposal
- Renders a verdict on behalf of the operator's declared judgment framework

This is **agency in the strict principal-agent sense** (see [THESIS.md](THESIS.md) "Vocabulary: production layers vs. judgment layers"). The reviewer entity is the fiduciary representative of the operator's judgment. The occupant's implementation is documented in [reviewer-occupant.md](reviewer-occupant.md).

### Why the split matters

- **The orchestration is interchangeable and low-novelty.** Another system could implement the same dispatch-and-callback pattern; the interesting thing isn't the mechanics.
- **The reviewer entity is where YARNNN's architectural differentiation concentrates.** A judgment-bearing, intent-holding, principal-representing seat is the thing most "agentic frameworks" lack.
- **Implementation going forward should respect the split.** Code that touches review orchestration (dispatch, callbacks, audit) is plumbing and should be named/structured accordingly. Code and substrate that touches the reviewer *entity* (IDENTITY, OCCUPANT, principles, calibration, judgment logic) is where agency is expressed and should be treated as first-class architectural concern. ADR-315 made this structural: the kernel/harness depends on the published contract ([reviewer-occupant-contract.md](reviewer-occupant-contract.md)), never on the occupant implementation.

### Implementation alignment going forward

From 2026-04-23 onward, every design decision that touches the Reviewer should explicitly answer: *"is this orchestration (mechanical runtime coordination) or entity (judgment, persona, principles)?"*

Examples:
- Prospective-attribution contract (invariants I1–I4 above) is **entity** — it surfaces who is occupying the seat, which is about agency legibility.
- Dispatch routing from `ProposeAction` to occupant is **orchestration** — pure runtime plumbing.
- Calibration loop feedback into future verdicts is **entity** — it shapes how the entity judges.
- `decisions.md` write discipline is **both** — the write path is orchestration (how the entry lands); the content of the entry (the reasoning) is entity-output.

---

## What the Reviewer seat is not

- **Not a safety layer.** Safety layers reject bad things. The Reviewer layer makes *judgments* — approve, reject, defer — against declared principles. Safety is one of many possible framings of what a judgment evaluates; the seat is general over all of them.
- **Not coupled to proposal review exclusively.** Today the seat's primary action is rendering verdicts on `action_proposals`. The substrate supports the seat taking a broader judgment role (evaluating accumulated context for stale entries, flagging drift in domain principles, etc.) without architectural change. The proposal-review action is the first use case, not the only one.
- **Not a human-in-the-loop feature.** Human-in-the-loop frames AI as primary and human as safety net. The Reviewer seat is primary; the occupant (human or AI) fills it. The loop is not about human oversight — it is about independent judgment with occupant-interchangeable rendering.
- **Not an ABC, interface, or pluggable abstraction in code.** Per ADR-194 v2 retraction of v1 (preserved by ADR-315 D1), the seat is substrate — the files at `/workspace/persona/` — not an in-memory abstraction. Occupant rotation is a file write, not a dependency injection. (The *occupant* is a contract-bounded module per ADR-315 D2, but the boundary is a *data* contract over substrate, not an OO abstraction over the seat.)
- **Not identical with review orchestration.** The orchestration is plumbing; the reviewer entity is where agency lives. See "Review orchestration vs. reviewer entity — the split" above.

---

## Relationship to other canons

- [reviewer-occupant.md](reviewer-occupant.md) — the AI occupant that fills this seat (impl structure, model-by-trigger, persona-frame discipline, occupant classes).
- [reviewer-occupant-contract.md](reviewer-occupant-contract.md) — the published ABI between this seat (substrate) and the occupant (module): `ReviewerContext` / `ReviewerOutput` / `invoke_reviewer` / the kernel-side envelope assembler.
- [THESIS.md](THESIS.md) — second architectural commitment ("Independent judgment — the reviewer is a durable role, not a safety feature") states the philosophical claim. This document specifies the substrate expression of that claim.
- [FOUNDATIONS.md](FOUNDATIONS.md) — Axiom 1 (Substrate) requires the seat be filesystem-expressed; Axiom 2 (Identity) establishes Reviewer as the fourth cognitive layer; Derived Principle 14 ("Roles persist; occupants rotate") makes occupant-interchangeability structurally enforceable.
- [authored-substrate.md](authored-substrate.md) — every write to `/workspace/persona/` (including `judgment_log.md` append, `OCCUPANT.md` rotation, `handoffs.md` entry) flows through the Authored Substrate with required `authored_by` attribution.
- [ADR-194 v2](../adr/ADR-194-pluggable-reviewer-and-impersonation.md) — current implementation. Phases 1 + 2a + 2b + 3 shipped.
- [ADR-195 v2](../adr/ADR-195-outcome-attribution-substrate.md) — money-truth substrate that calibration.md reads from.
- [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) — seat ≠ occupant; the carve that produced this document split.

---

## Revision discipline

This document changes when:

- A new substrate file is added to the seat (with a non-trivial architectural reason)
- The attribution contract invariants change
- The delegation vocabulary is extended
- The calibration loop's inputs or cadence change structurally

It does not change when:

- An ADR adjusts implementation details within the specified substrate
- A new occupant class is added (the occupant taxonomy is extension-friendly; new classes are noted in [reviewer-occupant.md](reviewer-occupant.md))
- Principles, modes, or calibration content evolve (that is the seat's normal operation, not doc evolution)
- The occupant implementation changes (that is documented in [reviewer-occupant.md](reviewer-occupant.md))
