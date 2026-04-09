# Agent Surface Patterns

**Date:** 2026-04-09  
**Status:** Active  
**Related:**
- [SURFACE-ARCHITECTURE.md](./SURFACE-ARCHITECTURE.md) — canonical route and surface model
- [AGENT-PRESENTATION-PRINCIPLES.md](./AGENT-PRESENTATION-PRINCIPLES.md) — historical framing and prior agent-surface principles
- [ADR-140](../adr/ADR-140-agent-workforce-model.md) — workforce classes
- [ADR-164](../adr/ADR-164-back-office-tasks-tp-as-agent.md) — Thinking Partner as meta-cognitive agent
- [ADR-167](../adr/ADR-167-list-detail-surfaces.md) — canonical `/agents` list/detail surface

## Purpose

Define the scalable presentation rules for agent surfaces.

This doc is broader than the current implementation pass. It covers:

- how agent detail should vary by class without exploding into per-agent pages
- how no-task states should differ by agent class
- when to create role-specific add-on modules
- which presentation concerns belong to `agent_class`, `role`, or `task.output_kind`

## Core Rule

**Do not build one page per agent type.**

The right layering is:

1. **`agent_class` chooses the shell**
2. **`task.output_kind` chooses assigned-work card rendering**
3. **`role` can add small specialized modules when the data genuinely differs**

This prevents a combinatorial explosion as the roster evolves.

## Rendering Axes

### 1. `agent_class` owns the shell

The four classes get distinct top-of-page interpretation:

| Class | User question | Shell emphasis |
|---|---|---|
| `domain-steward` | "What domain does this specialist own, and how fresh is it?" | Owned domain, tracking posture, downstream deliverable posture |
| `synthesizer` | "What cross-domain outputs is this reporter responsible for?" | Upstream domain inputs, synthesis posture, reporting cadence |
| `platform-bot` | "What platform does this integration cover, and is it observing or acting?" | Platform bridge status, observation vs write-back posture |
| `meta-cognitive` | "How is TP keeping the workforce coherent?" | Orchestration posture, back-office tasks, essential maintenance |

### 2. `task.output_kind` owns assigned-work cards

Assigned work should remain shared and registry-driven:

| `output_kind` | What the card explains |
|---|---|
| `accumulates_context` | Which context it reads/writes, what is being kept fresh |
| `produces_deliverable` | What artifact it produces, for whom, and why |
| `external_action` | Which platform it acts on and what action it takes |
| `system_maintenance` | What system-level maintenance it performs |

### 3. `role` owns optional add-ons, not the page itself

Role-specific UI should only exist when the primary data model differs enough to justify it.

Examples:

- `slack_bot`, `notion_bot`, `github_bot`
  Add connection/source-selection or platform-specific activity modules.
- `executive`
  Add upstream-readiness and cross-domain input modules.
- `thinking_partner`
  Add workforce-health and essential-task modules.

## No-Task States Must Differ By Class

Generic "No tasks assigned yet" copy is not sufficient. The absence of tasks means different things for different agent classes.

### Specialists (`domain-steward`)

No tasks means the specialist has an owned domain but no active work keeping it fresh.

The empty state should:

- remind the user which domain this agent owns
- suggest starting with a tracking task
- suggest adding deliverable tasks only after context begins to accumulate

### Reporting (`synthesizer`)

No tasks means the reporting agent has nothing synthesizing cross-domain work.

The empty state should:

- explain that reporting depends on upstream specialist context
- suggest creating a daily update or stakeholder report
- remind the user that reporting quality depends on active upstream tracking

### Integration Bots (`platform-bot`)

No tasks does **not** necessarily mean "idle worker." It may mean the integration exists but no observation or write-back flow has been defined yet.

The empty state should:

- explain which platform this bot bridges
- distinguish observation work from outbound actions
- suggest starting with a digest/observation task before write-back

### Thinking Partner (`meta-cognitive`)

No tasks is usually a coherence/scaffold problem, not a neutral empty state.

The empty state should:

- explain that TP owns orchestration and back-office maintenance
- distinguish workforce upkeep from domain production
- suggest restoring essential maintenance tasks if they are missing

## Dedicated Components: When They Are Warranted

Create a dedicated component when one of these is true:

1. The **empty state logic** differs materially
2. The **primary data** differs, not just the copy
3. The **main CTA** differs
4. The **health/readiness model** differs

Using that rule:

- **Yes**: class-specific shells
- **Yes**: class-specific empty states
- **Yes**: a few role-specific add-on modules
- **No**: one full-page component per specific agent type

## Recommended Frontend Shape

```text
AgentContentView
├── SurfaceIdentityHeader
├── AgentShellRegistry[agent_class]
│   ├── class-aware top block
│   └── class-aware posture/add-on block
├── AssignedWork
│   ├── if tasks.length === 0 → AgentEmptyStateRegistry[agent_class]
│   └── else TaskCardRegistry[output_kind]
├── LearnedBlock
├── InstructionsBlock
└── StatsStrip
```

Optional future extension:

```text
AgentRoleAddonRegistry[role]
```

Use this only for bounded role-specific modules, not to replace class-based shells.

## Session Scope

This session implements only what the current surface and data already support cleanly:

- class-specific top shell/posture blocks
- class-specific no-task states
- no second route or second agent detail page

This session does **not** add new API data or platform-connection health models. Richer role-specific modules can follow later once the required data is available on the canonical agent payload.
