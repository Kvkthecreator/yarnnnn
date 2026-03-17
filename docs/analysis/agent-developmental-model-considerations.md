# Agent Developmental Model — Considerations

> **Status**: **Formalized** — insights in this doc are now captured in [ADR-117: Agent Feedback Substrate & Developmental Model](../adr/ADR-117-agent-feedback-substrate-developmental-model.md)
> **Date**: 2026-03-16 (formalized 2026-03-17)
> **Context**: Emerged from FOUNDATIONS.md v2 audit. Was parked pending TP Composer architecture clarity.
> **Dependency resolution**: TP Composer is now architecturally defined (ADR-111 Phases 1-5 implemented, ADR-114/115 substrate awareness and density model shipped). The sequencing principle is satisfied.

---

## Status: UNPARKED

The blocking dependency — TP Composer autonomy — is resolved:
- **ADR-111** (Agent Composer): Implemented Phases 1-5. Composer is TP's meta-cognitive layer with bootstrap, heartbeat, assessment, creation, and lifecycle capabilities.
- **ADR-114** (Substrate-Aware Assessment): Composer reasons over knowledge corpus, not just platform metadata.
- **ADR-115** (Workspace Density Model): Composer eagerness calibrated to workspace maturity.

The insights below are now formalized in **ADR-117**, which defines:
- Phase 1: Unified feedback distillation for all agent types (not just analyst)
- Phase 2: Agent self-reflection (post-generation observations)
- Phase 3: Intentions architecture (multi-skill within one agent identity)

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
