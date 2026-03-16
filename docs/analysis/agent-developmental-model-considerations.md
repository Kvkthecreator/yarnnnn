# Agent Developmental Model — Considerations

> **Status**: Analysis (pre-decision)
> **Date**: 2026-03-16
> **Context**: Emerged from FOUNDATIONS.md v2 audit. Parked here pending TP Composer architecture clarity.
> **Dependency**: TP Composer autonomy must be defined first — agent developmental trajectory is downstream of TP's supervisory/compositional role.

---

## Why This Is Parked

The agent developmental model (Axiom 3 in FOUNDATIONS.md) describes how agents evolve over time — intentions, capabilities, autonomy. But **who steers that evolution** is TP (Axiom 1). Until TP's Composer capability is architecturally clear, designing agent-side developmental mechanics risks:

1. Building agent autonomy that conflicts with TP's supervisory authority
2. Duplicating decision-making between TP and agents
3. Evaluating qualitative progression without a clear control surface

The sequencing principle: **TP Composer autonomy first → agent developmental model second.**

---

## Insights to Preserve

### Agent Lifecycle Phases (from FOUNDATIONS.md Axiom 3)

```
Creation → Early Tenure → Developing → Mature → [Evolved | Dissolved]
```

### Three Dimensions of Agent Development

1. **Intentions** — dynamic, multiple per agent. Not static triggers but evolving understanding of what the domain requires. Types: recurring, goal-driven, reactive.
2. **Capabilities** — earned through feedback: read → analyze → write-back → act.
3. **Autonomy** — graduated per-capability: supervised → semi-autonomous → autonomous → trusted.

### Key Reframes from Discussion

- **Trigger is a property of the intention, not the agent** — a mature agent holds multiple intentions with different triggers simultaneously.
- **Multi-step, multi-skill execution** — e.g., a Slack agent that digests, writes back, monitors reactions, adjusts. Not a single-skill executor.
- **Scope × Skill × Trigger (ADR-109) describes initial configuration**, not steady state. It's a starting point that developmental trajectory evolves beyond.

### Where Intentions Likely Live

Workspace (`/agents/{slug}/intentions/*.md`) per ADR-106 path conventions. TP creates/retires intentions; agents can propose new ones via workspace writes.

### Capability Gating Signal

`agent_runs` already tracks output history + user edits. Capability level derivable from feedback history (edit rate, approval rate) — dynamic, not a static column.

### Open Questions (to resolve after TP Composer is clear)

1. How are intentions represented and who manages their lifecycle?
2. What constitutes "enough feedback" to graduate capabilities?
3. When an agent's domain expands, new agent or scope expansion?
4. Multi-intention scheduling mechanics
5. How does TP's supervisory review interact with an agent's earned autonomy?

---

## Audit Findings (Agent-Side)

These are the codebase gaps identified during the FOUNDATIONS v2 audit. They remain valid but are **deferred** until TP Composer is defined:

| Finding | Location | Status |
|---------|----------|--------|
| Zero schema for intentions, capabilities, autonomy_level | DB schema | Deferred |
| `agent-framework.md` describes static taxonomy only | `docs/architecture/` | Deferred — rewrite after TP Composer |
| `agents.md` lists fixed agent types, no lifecycle | `docs/architecture/` | Deferred |
| ADR-109 partially superseded by developmental model | `docs/adr/` | Deferred |
| Proactive/coordinator as agent modes vs TP capabilities | `proactive_review.py`, ADR-092 | **Blocked on TP Composer architecture** |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-16 | Initial — parked insights from FOUNDATIONS v2 audit, pending TP Composer clarity |
