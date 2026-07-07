# Reviewer Substrate — Index

> **Status**: Canonical (index)
> **Date**: 2026-04-24, split into three domain docs 2026-06-04 (ADR-315 D5)
> **Authors**: KVK, Claude

> **⚠ ADR-414 banner (2026-07-07 — the pure workspace):** these three docs describe the **one-judgment-seat world** and are superseded in direction: the steward's constitution moves to **kernel constants** (no seeded `persona/` files — [ADR-414](../adr/ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md) D2), judgment seats become **hired-agent homes** at `agents/{slug}/` recorded as grant rows (D5/D6), and the ADR-216 orchestration-surface seam collapses (D3 — one system agent, the rail is its voice). The seat≠occupant model (ADR-315) and the contract ABI survive; the seat's *substrate form* changes per the ADR-414 phases. Prose below that reads "the Reviewer's capital judgment" describes the Altitude-3 layer (ADR-408 D2), not the steward.

This document was the single technical canon for the Reviewer Agent. Per [ADR-315](../adr/ADR-315-reviewer-occupant-contract.md) D5 — which carved the Reviewer **occupant** out of the Reviewer **seat** — it is now a one-screen index to three domain-scoped docs. The seat≠occupant distinction is the organizing principle: **the seat is substrate (kernel-owned); the occupant is a module (swappable); the contract is the named seam between them.**

| Read this | For |
|---|---|
| **[reviewer-seat-substrate.md](reviewer-seat-substrate.md)** | The **kernel/seat** — the six seat files at `/workspace/review/`, occupant-rotation protocol (`OCCUPANT.md` + `handoffs.md`), the calibration trail, the delegation vocabulary, the prospective-attribution contract with chat surfaces, and "what the seat is not." This is substrate. |
| **[reviewer-occupant.md](reviewer-occupant.md)** | The **personification** — the AI agent (`freddie_agent.py`) that fills the seat: occupant classes, `invoke_freddie`, model selection by trigger, the persona-frame discipline (→ [agent-composition.md](agent-composition.md) §3.2.1 + §3.2.2), and how the occupant consumes the contract. |
| **[reviewer-occupant-contract.md](reviewer-occupant-contract.md)** | The **published ABI** — `FreddieContext` / `FreddieOutput` / `FREDDIE_MODEL_IDENTITY` / `invoke_freddie` / the kernel-side envelope assembler. The named seam every kernel caller depends on and every occupant implements. Defined in `api/agents/occupant_contract.py`. |

### The one-line frame

- **The seat is substrate** (no ABC — ADR-194 v2, preserved by ADR-315 D1). Files at `/workspace/review/`. Rotating the occupant is a file write.
- **The occupant is a module** (ADR-315 D2). `freddie_agent.py` implements today's `ai:freddie-sonnet-v8`. Human occupants bypass it; external occupants are deferred (ADR-315 D6).
- **The contract is the seam** (ADR-315 D3). The kernel depends on the contract, never on the occupant implementation. `occupant_contract.py` is pure data — it imports with no LLM runtime, the standing proof the ABI is decoupled.

### Partition discipline pointer

The content boundary between `principles.md` (operator-authored rule-set) and the persona-frame (system-authored reasoning posture) is enforced at **[agent-composition.md](agent-composition.md) §3.2.1** (partition) + **§3.2.2** (composed coherence) — the singular enforcement home. Future ADRs that reshape `principles.md` content or any persona-frame section must update §3.2.x in the same commit.

The one-line statement (canonized at agent-composition.md §4.2 + §3.2.1): *persona is how to reason; mandate is why we exist; autonomy is how far decisions bind; principles is what the rules of judgment are.*
