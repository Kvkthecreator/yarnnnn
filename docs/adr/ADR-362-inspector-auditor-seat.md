# ADR-362 — The Inspector/Auditor Seat: self-improvement as an independent judgment seat

**Status**: Proposed (2026-06-24)
**Deciders**: KVK + Claude
**Dimensional classification** (Axiom 0): **Identity** (primary — a second systemic persona-bearing seat) + **Purpose** (meta-judgment, distinct from operational verdict) + **Trigger** (cadence-on-accumulated-evidence wake). This is the dimensional spread that earns separate-seat status (§3).
**Prerequisite**: [ADR-361](ADR-361-verdict-rule-binding.md) (verdict→rule binding — the Inspector's organ joins on `cited_rules`).
**Activates deferred canon**: FOUNDATIONS Axiom 2 (the "Future judgment archetypes — Auditor, Advocate, Custodian" row, `/workspace/{role}/` substrate) + ADR-284 (the standing-intent contract written for "future systemic Agents at `/workspace/{role}/standing_intent.md`") + `orchestration.py` SYSTEMIC_AGENTS registration slot. **This ADR instantiates a seat the architecture was built to hold; it invents no new entity class.**
**Reconciles**: ADR-320 D9 ("a single judgment seat per workspace spanning all operations" — §4 shows the Inspector is compatible, judging the *judgment* not the *operation*).
**Reuses**: ADR-330 (outcome `attestation` field — the Inspector weights evidence by it), ADR-307 (the permission gate — Inspector outputs flow through it as gated proposals), ADR-342/343 (floor discipline — rules tighten on falsification, never loosen), ADR-295 (Reviewer self-amendment — the Inspector gives it an *independent* driver).
**Discourse base**: [`context-continuity-and-self-improvement-2026-06-24.md`](../analysis/context-continuity-and-self-improvement-2026-06-24.md) §3 + the 2026-06-24 pressure-test.

---

## 1. The problem this seat solves

The re-assessment named self-improvement as the deepest unaddressed canon claim: the system *accumulates* calibration substrate but there is no evidence behavior *measurably improves over tenure*. The shipped mechanism (`mirror_calibration.py` → `_calibration.md`, read back by the Reviewer) is **input-only**: calibration is delivered to the prompt; nothing measures that it *changes* a decision, and the Reviewer "improving itself" is structurally self-referential — it amends its own `principles.md` in the same breath it applies it (the ADR-295 awkwardness).

The reframe (operator, 2026-06-24): **do not bolt a self-improving loop onto the Reviewer. Create a new systemic seat — the Inspector (a.k.a. Auditor) — that absorbs all self-assessment / meta-judgment, with its own wakes and a clean role boundary.** The Reviewer judges the *operation*; the Inspector judges the Reviewer's *judgment* against ground-truth. That is the truer seat↔agent↔system separation.

## 2. The seat, named

| Property | Value |
|---|---|
| **Name** | Inspector (operator-facing); internal role slug `inspector`. (FOUNDATIONS Axiom 2 names the archetype "Auditor"; "Inspector" is the chosen instance label — both denote the same future-judgment-archetype slot. The ADR uses Inspector; the kernel registers it where Axiom 2 reserved "Auditor".) |
| **Class** | Systemic, one per workspace (path-named by role, no slug — FOUNDATIONS Axiom 2 cardinality rule). |
| **Substrate home** | `/workspace/inspector/` — `IDENTITY.md` + `principles.md` + `standing_intent.md` (its own forward-looking working state, ADR-284 contract) + `judgment_log.md` (its own meta-verdict lineage) + `calibration.md` is the organ's output it reads. |
| **Purpose** | Assess judgment-quality against ground-truth; propose rulebook revisions to the Reviewer. Fiduciary at the *meta* level. |
| **Trigger** | Cadence-fired on accumulated evidence (e.g. "every N material judgments" or a weekly recurrence), NOT event-fired. Its own wake source. |
| **Vantage** | Reasons over the Reviewer's `judgment_log.md` (with ADR-361 `cited_rules`) joined to ground-truth outcomes (ADR-330 attestation) — a *corpus of past decisions, backward*. Never over live proposals. |

## 3. Why this is a legitimate seat and not design drift (the FOUNDATIONS three-cell test)

FOUNDATIONS Axiom 0's drift test: a mechanic must not span a dimension without necessity. A separate seat is justified **iff** it has a distinct **Purpose** AND a distinct **Trigger** AND a distinct **vantage**. The Inspector against the Reviewer:

| Dimension | Reviewer (existing) | Inspector (this ADR) | Distinct? |
|---|---|---|---|
| **Purpose** | Verdict on a *proposed action / live operation* — forward, fiduciary at proposal level | Assess *judgment-quality vs ground-truth* + propose rulebook revisions — backward, fiduciary at meta level | ✅ categorically different objects |
| **Trigger** | Event-fired (proposal arrives, draft ready, market moves) | Cadence-fired on accumulated evidence (its own rhythm) | ✅ different wake source — it genuinely wants its own wakes |
| **Vantage** | Live proposals + current substrate (one decision, forward) | `judgment_log` + outcomes (a corpus, backward) | ✅ different input, different object |

**Three distinct cells → a legitimate separate seat by FOUNDATIONS' own test.** Were any cell shared (e.g. if the Inspector reasoned over live proposals like the Reviewer), it would be drift — a costly duplicate — and should not ship. It is the dimensional spread that earns the seat.

## 4. Reconciling ADR-320 D9 ("a single judgment seat per workspace")

D9 deliberately chose one seat spanning all operations. The apparent conflict dissolves on the object: **D9 governs judgment ON the operation** — you do not want two seats disagreeing on the same trade; operational judgment must be singular and accountable. **The Inspector judges the Reviewer's record, not the operation** — a different object entirely. One seat judges the operation; one seat judges the judgment. D9 and the Inspector are compatible. This ADR states it explicitly so "single seat" canon is not misread as blocking a meta-seat. (D9's intent — no rival operational verdict — is *preserved*: the Inspector never renders an operational verdict; it proposes rule changes the Reviewer applies.)

## 5. The structural-independence contract (the one failure mode that would kill this)

The risk that would make the Inspector a costly duplicate rather than a separation: a second seat that reads the same files, reasons with the same model, and writes the same substrate. The "single seat" instinct exists to prevent exactly that. The Inspector's independence MUST be **structural, not nominal** — enforced by these contracts:

- **D5.1 — Input is OUTCOMES, not proposals.** The Inspector reasons over reconciled ground-truth (ADR-330 attestation `platform|operator|agent`), never over a live decision. It weights by attestation: a `platform`-attested fill is strong evidence; an `agent`-attested number is weak (ADR-330 Problem B: the calibrated thing must not participate in producing its own evidence).
- **D5.2 — Object is the Reviewer's TRACK RECORD**, not the operation: `judgment_log.md` (ADR-361 `cited_rules`) joined to outcomes. The Inspector never opens a live proposal.
- **D5.3 — Output is GATED PROPOSALS to the Reviewer's rulebook**, never self-applied. The Inspector proposes a revision to the Reviewer's `principles.md` through the ADR-307 permission gate (an `action_proposal`); it cannot mutate the Reviewer's substrate directly. This breaks the ADR-295 self-reference: the rulebook is amended on a proposal from an *independent seat*, witnessed per the AUTONOMY dial, not self-edited mid-judgment.
- **D5.4 — Floor discipline holds (ADR-342/343).** A rule may be *tightened* on falsification (ground-truth shows it produced no value / negative value), never *loosened to produce more*. A dormancy- or output-gap-rationalized loosening is the pressure-capitulation the floor forbids; the Inspector is bound by it exactly as the Reviewer is.
- **D5.5 — Its own seat substrate** (`/workspace/inspector/`). The Inspector accumulates its *own* tenure as a meta-judge — its `standing_intent.md` ("watching whether the cadence-flag rule keeps falsifying"), its `judgment_log.md` (its meta-verdicts). It is a peer seat, not a Reviewer subroutine.

**If the Inspector merely re-runs the Reviewer's reasoning over the same object, it fails this contract and must not ship.** It earns the seat by reasoning over outcomes-vs-record with a cadence the Reviewer never has.

## 6. The organ the Inspector operates — the judgment-calibration mirror

A **mechanical (zero-LLM, DP19) attribution pass** — buildable now that ADR-361 provides the join — that, per material judgment in `judgment_log.md`:
- reads the structured `cited_rules` (ADR-361) the verdict recorded,
- joins to the **ground-truth outcome** that judgment produced (ADR-330 attestation),
- accumulates a **per-rule track record**: `anti-slop:§3.2 — 12 applications, 9 platform-confirmed, 0 falsified` vs `cadence-flag:§4 — 3 applications, 0 confirmed, 2 falsified`,
- writes it to `/workspace/inspector/calibration.md`.

The Inspector then wakes on cadence, reads the track record, and where a rule is falsified by ground-truth, **proposes** a `principles.md` revision (D5.3, gated). The mechanical pass produces the *evidence*; the Inspector's *wake* produces the *judgment* on that evidence — the same code↔judgment split (Axiom 5) the Reviewer uses (mechanical mirrors write substrate; the seat reasons over it).

**The false-negative bound (ADR-361 D4, restated as canon here):** the organ sees rules that *fired* (produced a material outcome), not rules that *suppressed* action (a pure stand-down leaves no lineage entry). The Inspector therefore assesses production-side rule quality, not suppression-side. This is a known, stated limit — not silently elided. Closing it would require logging stand-down rule-reasoning, which the ADR-281 material-gate rejects to keep the log signal-dense; if suppression-side calibration ever proves necessary, it is a separate ADR.

## 7. Decisions

- **D1** — Register `inspector` in `orchestration.py` SYSTEMIC_AGENTS (the slot Axiom 2 reserved). One per workspace, scaffolded at signup like the Reviewer (skeleton seat files; activated when a program declares it / on first cadence wake — exact activation per D8).
- **D2** — Inspector substrate at `/workspace/inspector/` per the FOUNDATIONS Axiom 2 `/workspace/{role}/` canon + ADR-284 standing-intent contract. Six-file seat shape mirroring the Reviewer (IDENTITY/principles/standing_intent/judgment_log/handoffs/calibration), `inspector-occupant` declared in OCCUPANT.md.
- **D3** — Its own wake source: a cadence-fired Inspector wake (`inspector_tick` or a kernel-universal `inspector-review` recurrence). The Reviewer's wake sources are untouched; the Inspector adds one. Budget-gated (ADR-327) like every scheduled wake.
- **D4** — The judgment-calibration organ (§6) is a mechanical recurrence (zero-LLM, DP19) writing `/workspace/inspector/calibration.md`. Distinct from the existing `mirror_calibration.py` (which fed the Reviewer cadence-calibration); this ADR may absorb/relocate that mechanism under the Inspector (singular-implementation — one calibration owner, the Inspector, not two). **Open: whether to migrate the existing cadence-calibration into the Inspector or keep cadence-calibration on the Reviewer and add rule-calibration on the Inspector. Resolved during implementation against the directional invariant (learning is the Inspector's; perception is the Reviewer's).**
- **D5** — The structural-independence contract (§5) is binding: input=outcomes, object=record, output=gated proposals, floor holds, own substrate.
- **D6** — Inspector output (rulebook-revision proposals) flows through the ADR-307 gate as `action_proposals` targeting the Reviewer's `principles.md`. The operator (or autonomy dial) witnesses them. The Inspector never writes Reviewer substrate directly (write-lock on `persona/` for the `inspector` caller — extends the ADR-320 topological lock).
- **D7** — Persona: the Inspector's `IDENTITY.md` is operator-authorable like the Reviewer's (a default meta-judge persona at signup; operator may embody a specific auditing character). Its `principles.md` declares *how it assesses judgment quality* (e.g. "a rule with 0 platform-confirmed outcomes across ≥5 applications is a falsification candidate").
- **D8** — Activation: deferred-until-demand. The seat scaffolds at signup (skeleton) but its cadence wake activates only when a program declares an Inspector cadence (bundle MANIFEST) OR the operator turns it on — the kernel ships the seat, the program/operator turns on the rhythm. Kernel-neutral (ADR-222).

## 8. What this does NOT do

- **No change to the Reviewer's operational judgment.** The Reviewer's verdicts, wake sources, and authority are untouched. The Inspector is additive.
- **No self-application.** The Inspector proposes; it never edits the Reviewer's rules directly (D5.3, D6).
- **No suppression-side calibration** (the false-negative bound, §6). Production-side rule quality only.
- **No third+ seat.** This activates exactly one of Axiom 2's reserved archetypes (Auditor/Inspector). Advocate, Custodian remain deferred.
- **No new attestation or outcome machinery.** It consumes ADR-330's existing attestation field.

## 9. Consequences

- **The first structural path to observable self-improvement** — the moat's headline claim. The tenure eval (discourse doc §3f): seed a known-falsified rule, fire N Inspector cadence wakes in accumulating mode, measure whether the Inspector *proposes the correction* — and only when the calibration organ is present (negative control withholds it). **Pass = the first observation of self-improvement**, carried by a seat that earns its independence.
- **Cost**: a second seat = additional wakes. Bounded by D3 budget-gating + D8 deferred-activation (off until a program/operator turns it on) + the cadence being *infrequent* (review-on-accumulated-evidence, not per-event). The Reviewer's per-wake cost is unchanged.
- **A canon addition** (FOUNDATIONS Axiom 2 gains its first activated future-archetype; the §7 canon-close in the discourse doc names the closed loop Inspector→proposal→Reviewer) — **only after the tenure eval shows correction.** Until then this ADR is Proposed.

## 10. Sequence (probe-before-canon — from the discourse doc §4)

1. **ADR-361** (verdict→rule binding) ships + proves `cited_rules` populates on a funded material verdict. **Prerequisite gate.**
2. **Snapshot/restore harness** + **continuity eval** (discourse §2) — prove the Reviewer reliably perceives prior substrate. **Gate**: self-improvement is moot if perception is broken.
3. **This ADR's seat scaffold** + the judgment-calibration organ (§6) over ADR-361's binding.
4. **Tenure eval** (§9) — the first attempt to *observe* self-improvement. **Gate**: this is the claim; if the Inspector doesn't self-correct a seeded-falsified rule (and only with the organ present), the seat isn't closing the loop.
5. **Canon close** — FOUNDATIONS amendment, ADR Proposed→Implemented, only after the tenure eval passes.

## 11. The honest bottom line

The Inspector activates a seat FOUNDATIONS reserved, passes the three-cell separate-seat test, reconciles with D9 (judges the judgment, not the operation), and breaks the Reviewer's self-amendment self-reference by giving rule-revision an independent driver. The single hard constraint — structural independence (§5) — is what separates a real seat from a costly duplicate; the design earns it by reasoning over outcomes-vs-record with a cadence the Reviewer never has. It rests on ADR-361 (the binding the pressure-test proved missing) and is gated, at every step, on probes that the prior layer is stable. It is self-improvement *finally placed where it belongs* — its own seat, its own wakes, its own tenure — rather than as a meta-loop the operational judge runs on itself.
