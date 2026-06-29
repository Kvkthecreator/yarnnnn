# Open Scoping — Phase-1 Packaging, and ADR-334 as the Rung-2 Pricing Model

**Date**: 2026-06-29
**Hat**: A (system canon — a scoping note; surfaces an open item, decides no pricing).
**Status**: **Open scoping item.** This note does **not** decide Phase-1 pricing — per [ADR-380](../adr/ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md) §6, that decision is deliberately not made. It records the gap so it is not lost, and marks the existing pricing ADR as belonging to a different rung.
**Trigger**: ADR-380 §6 — *"[ADR-334](../adr/ADR-334-per-operation-pricing.md) prices the autonomy/delegation dial — a Rung-2 axis. With Rung 2 deferred, the launch needs its own pricing thesis, and ADR-334 should be marked the Phase-2 (Rung-2) model. Out of scope here; named so it is not lost."*

---

## 1. The finding (one sentence)

**The only pricing canon YARNNN has — [ADR-334](../adr/ADR-334-per-operation-pricing.md) (per-operation / delegation-tiered seats: Supervised/Delegated/Autonomous $149/$299/$499, where the AUTONOMY dial IS the pricing axis) — prices a Rung-2 capability that the launch defers; so the Phase-1 launch (Rungs 0–1) has no pricing thesis, and that is an open scoping item, not a decided one.**

## 2. Why ADR-334 is a Rung-2 model (the rung mapping)

ADR-334's pricing axis is the **autonomy/delegation dial** — Supervised → Delegated → Autonomous. Per the [activation ladder](../adr/ADR-380-the-activation-ladder-and-the-judgment-deferral-line.md):

- The autonomy dial only has stakes to price at **Rung 2** (2nd-order persona agents taking consequential external action under an autonomy grant). This is exactly the axis ADR-380 D3 calls *degenerate at Rung 1* — Freddie has no consequential external write, so an autonomy tier over Freddie prices nothing.
- Therefore **ADR-334 is the Rung-2 (Phase-2) pricing model.** It prices the thing the launch defers.

**Recommended (not done here — a one-line status note on ADR-334 when a session touches it):** mark ADR-334 as *"the Rung-2 / Phase-2 (delegation) pricing model; not the Phase-1 launch pricing — see this note."* (Not edited in this pass to avoid scope-creeping a pricing decision into a cascade-hygiene session.)

## 3. The gap (Phase-1 has no pricing thesis)

The Phase-1 launch is Rungs 0–1: the substrate wedge (`remember`/`recall`/`trace` + connectors + files) + Freddie the substrate steward. What does the operator pay for *there*?

- It is **not** an autonomy tier (no consequential autonomy ships — Rung 2 deferred).
- It is some function of: substrate value (portable, attributed, judged context), interop reach (N LLM hosts — ADR-379), Freddie's substrate-management work (token cost — ADR-327 budget), connector/perception breadth.
- **What that function IS is undecided.** Seat/subscription? Usage over the ADR-327 cost ledger? A substrate tier + an interop tier? **Open.**

This note deliberately does **not** propose an answer — ADR-380 §6 named it out of scope, and inventing Phase-1 pricing in a doc-cascade pass would violate the doc-first / confirm-before-deciding discipline. It is surfaced as an **owed scoping item** for its own session.

## 4. Disposition

- **ADR-334** → recommended re-label as the Rung-2/Phase-2 pricing model (one-line status note, when a session next touches it). Not edited here.
- **Phase-1 packaging thesis** → **OPEN.** Owed its own scoping discourse. Inputs: ADR-327 (the cost ledger the launch already has), ADR-379 (interop reach), the ADR-375 substrate-wedge value, the ADR-380 §5 *open* vision/moat items (which shape whether Phase-1 pre-sells Rung 2).
- **Coupling to the open vision boundary (ADR-380 §5)**: whether Phase-1 packaging *pre-sells* the Rung-2 judgment layer depends on the still-open vision-boundary decision. So the packaging thesis cannot fully close until the vision boundary does. Named, not resolved.

## 5. What this note does NOT do

- Does not decide Phase-1 pricing (ADR-380 §6 — out of scope by instruction).
- Does not edit ADR-334 (recommends a status note for a future session).
- Does not close ADR-380 §5's vision/moat open items (it depends on them).
- Implies no code.
