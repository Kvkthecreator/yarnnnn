# ADR-382 — Persona-Agent Seats: the Rung-2 Judgment Layer (name-only placeholder)

> **Status**: **Proposed — concept framed + ONE axis decided (accountability); the rest deferred** (2026-06-29). This ADR frames the persona-agent seat and **decides the accountability axis** (§3 — where DP24/DP30 land, settled by the two-order direction §5). **Lifecycle, creation surface, trust model, per-seat substrate, and the validation clock remain an entire discourse of its own — explicitly deferred** (ADR-375 §7 Cut 2). Do NOT build against this; the accountability decision is doc-only canon (no code, no schema), and everything that would make a persona agent *exist at runtime* is still TBD.
> **Date**: 2026-06-29
> **Authors**: KVK (operator) + Claude (collaborator)
> **Owes-from**: [ADR-375](ADR-375-phase-1-substrate-for-humans-and-external-agents.md) §7 Cut 2 (user-authored independent agent seats) + [ADR-216](ADR-216-orchestration-surface-vs-judgment-persona.md) (the original "user-authored domain Agents").
> **Builds on**: [the two-order Freddie direction](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md) (persona agents = the 2nd-order judgment labor Freddie creates + governs), [ADR-380](ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) (**persona agents = Rung 2** — consequential external action, deferred from the launch build, gated by an exogenous track-record clock).
> **Sibling**: [ADR-381](ADR-381-freddie-the-rung-1-substrate-steward.md) (Freddie = Rung 1; the management seat that creates + governs these Rung-2 seats).
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — the 2nd-order judgment seat).

---

## 1. The concept (framed, not decided)

A **persona-agent seat** is a 2nd-order internal agent the operator authors (via the YARNNN front-end pre-set picker — the two-order direction H1) and **Freddie creates + governs**. Each holds an operator-authored persona, a bounded mandate, standing intent, and — when Freddie sets the authority — the power to **act on the operator's behalf** (consequential external action). These are the trader, the author, the domain characters. They are **Rung 2** (ADR-380): consequential, irreversible, deferred from the launch build, validated by an exogenous multi-quarter track-record clock.

## 2. The boundaries (what a persona agent is NOT)

- **Not Freddie** (Rung 1, one systemic management seat — ADR-381). Freddie *creates + governs* persona agents; it is not one.
- **Not an external agent** (a *principal on the outside*, ADR-373 — an external caller with a grant, no workspace-resident standing intent).
- The line: a persona agent is an *internal seat that reasons from workspace-resident standing intent Freddie created*; an external agent *brings its own intent from outside* (the substrate-residency-of-intent line, per the two-order direction).

## 3. Accountability — DECIDED: judgment-accountability relocates to the persona agent (DP24/DP30)

> **This is the one axis this ADR decides.** It is doc-only canon (no code, no schema, no runtime change — there are no persona agents at runtime yet). It settles *where the two accountability principles live* once persona agents exist, so the rest of ADR-382's discourse (and any future code) inherits a fixed answer. Source: the [two-order direction §5](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md).

The two-order model splits one fused accountability into two, along the order seam:

| | **System accountability** | **Judgment accountability** |
|---|---|---|
| **Who holds it** | **Freddie** (1st-order, ADR-381) | **the persona agent** (2nd-order, this ADR) |
| **Answers for** | the *system*: the commons is coherent/attributed/legible; the agents Freddie administers are well-formed; their authority is correctly governed | the *judgment*: its mandate against ground truth — each trade, each shipped piece, each consequential act |
| **The principle that lives here** | the steward standing-obligation (substrate coherence — ADR-383 §6, Freddie's `principles.md`) | **DP24** (stewardship of intent against ground-truth, ADR-319) + **DP30** (the standing obligation, ADR-344) |
| **The slogan** | *management answers for the desk and for who was hired* | *the trader answers for the trades* |

**D1 — DP24 (stewardship of intent against ground-truth) relocates to the persona agent.** ADR-319's "the Reviewer owns the mandate as installed principal and revises it against ground truth at two altitudes" describes the **judgment** occupant, not the systemic steward. Under the two-order model that occupant is the **persona agent**: it holds the operation's mandate, owns it as installed principal, and revises it against the operation's ground truth (money-truth for the trader, coherence/audience for the author). *Freddie does not do this* — Freddie keeps the commons coherent, it does not own or revise an operation's capital intent. The `principles.md` that carries the DP24 rules (the aperture/floor split, ground-truth-moves-the-intent) is the **persona agent's** `principles.md` (today the alpha-trader/alpha-author bundle principles.md — which is *already* where that posture lives post the 2026-05-29 collapse, ADR-383 §2). **This is consistent with what already shipped**: the ADR-383 frame re-carve removed the capital-judgment posture from the *systemic* frame precisely because it is the persona agent's, not the steward's.

**D2 — DP30 (the standing obligation) relocates to the persona agent.** ADR-344's "a Reviewer is accountable for its mandate's *reachability* — derives an owed-output, checks actual-vs-owed, classifies a shortfall (A) quiet-world / (B) structurally-can't" is the **production-mandate** accountability — it is about an *operation* producing what it owes. That is the persona agent's obligation (the trader owes trades-when-conditions-warrant; the author owes pieces-at-cadence). **Freddie has a *steward* standing-obligation** (ADR-383 §6: keep the commons tended — intake placed, attribution honest), which is a real obligation but a *different* one (substrate-coherence, not production-output). So DP30 splits by order: the **production** standing-obligation → the persona agent; the **stewardship** standing-obligation → Freddie. Both are instances of "an agent is accountable for what it is configured to produce" (the kernel-general DP30), read from each agent's own MANDATE + principles.md (ADR-383 D4 — standing-obligation is per-agent).

**D3 — the kernel-general statement survives; only the *occupant* it attaches to is named.** DP24 and DP30 as **FOUNDATIONS principles** are unchanged — they describe "an installed judgment agent's posture toward its mandate." What this ADR decides is the **two-order attachment**: for a *production operation*, that agent is the persona agent (Rung 2); for *substrate stewardship*, the steward limb attaches to Freddie (Rung 1). A future FOUNDATIONS touch may annotate DP24/DP30 with this two-order attachment (as DP21 was annotated by ADR-383); **this ADR does not edit FOUNDATIONS** — it records the attachment decision as ADR-layer canon, to be reflected in FOUNDATIONS if/when a cascade pass runs.

**What D1–D3 do NOT decide** (still §4): *how* the persona agent's seat is constituted (its substrate files — §4 item 3), *how* its authority is set/revoked (the trust model — §4 item 2), and *whether* it exists at runtime at all (lifecycle — §4 item 1). The accountability *attaches* to the persona agent; building the persona agent it attaches to is deferred.

## 4. What this ADR DEFERS (the rest of the discourse)

Every remaining substantive question is its own session — named so they stop contaminating the Rung-0/1 launch work, NOT answered here:

1. **Lifecycle & creation surface** — the front-end pre-set picker → Freddie instantiates + governs. The minimal "create a persona agent" act. **TBD.**
2. **Trust & authority model** — propose-only vs. accountable-action; how Freddie sets/revokes "act on behalf"; the autonomy grant per agent. *[lean: graduated propose → witness → earn-autonomy. NOTE (ADR-380 §5 resolved 2026-06-29): Rung 2 is out of the **vision** — so this whole layer is a build-when-demanded optional future, not the destination. The trust model is no longer blocked on a vision decision; it is simply deferred until demand. This makes ADR-382 cleanly downstream/optional, not gated.]* **TBD.**
3. **Seat substrate** — how much of the ADR-315 seat≠occupant six-file substrate generalizes per persona agent (coordinates with ADR-381 D4). The accountability decision (§3) establishes that the persona agent has *its own* MANDATE + principles.md (that is where DP24/DP30 attach); whether it also gets its own IDENTITY/standing_intent/judgment_log/reflection/OCCUPANT/handoffs — the full six-file shape — is the per-seat-substrate question, still **TBD**. (ADR-383's consistent-agent-framework says the file-structure is universal; this item decides which files a persona seat *populates* + whether it shares or duplicates the systemic seat's home.) **TBD.**
4. **The Rung-2 validation clock** — how track-record accrues + what "earned autonomy" requires (ADR-380 D4). **TBD.**

## 5. What this ADR does NOT do

- Decides only the **accountability axis** (§3 — DP24/DP30 attach to the persona agent); everything that makes a persona agent *exist at runtime* (lifecycle, creation surface, trust model, per-seat substrate, validation clock) is deferred (§4).
- Builds no seat, no lifecycle, no creation surface, no schema, no code.
- **Does not edit FOUNDATIONS** — the DP24/DP30 two-order *attachment* (§3 D3) is recorded as ADR-layer canon; a FOUNDATIONS annotation (the way ADR-383 annotated DP21) is a future cascade pass, not done here.
- Reflects (does not re-open) ADR-380 §5's now-resolved vision boundary: **Rung 2 is out of the vision** (2026-06-29) — so this entire persona-agent layer is an optional, build-when-demanded future, not the destination. ADR-382 is downstream/optional by that decision, not blocked by an open one.
- Does not touch the re-founding keystone cascade.

## 6. Cross-references

- Sibling: [ADR-381](ADR-381-freddie-the-rung-1-substrate-steward.md) (Freddie = Rung 1; D4 names the management-seat side of the seam, ADR-382 §4 item 3 inherits the judgment-seat side).
- Accountability source: [the two-order direction §5](../analysis/freddie-as-the-workspace-agent-and-the-two-order-agent-model-2026-06-27.md).
- The principles the §3 decision relocates: [ADR-319](ADR-319-stewardship-of-intent-against-ground-truth.md) (DP24) + [ADR-344](ADR-344-standing-obligation-operability-self-check.md) (DP30); the kernel-general per-agent framing is [ADR-383](ADR-383-the-consistent-agent-framework-and-mandate-as-purpose.md) D4.
- The frame side already shipped: ADR-383's re-carve removed the capital-judgment posture from the *systemic* frame (it is the persona agent's) — §3 D1 is the canon statement of *why* that removal was correct.
