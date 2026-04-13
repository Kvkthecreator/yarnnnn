# Agent And Task Surface Patterns

**Date:** 2026-04-09  
**Status:** Active  
**Related:**
- [SURFACE-ARCHITECTURE.md](./SURFACE-ARCHITECTURE.md) — canonical route and surface model
- [TASK-OUTPUT-SURFACE-CONTRACT.md](./TASK-OUTPUT-SURFACE-CONTRACT.md) — proposed run-level API contract for `/work`
- [AGENT-PRESENTATION-PRINCIPLES.md](./AGENT-PRESENTATION-PRINCIPLES.md) — historical framing and prior agent-surface principles
- [../features/task-types.md](../features/task-types.md) — task registry grouped by `output_kind`
- [ADR-140](../adr/ADR-140-agent-workforce-model.md) — workforce classes
- [ADR-164](../adr/ADR-164-back-office-tasks-tp-as-agent.md) — Thinking Partner as meta-cognitive agent
- [ADR-167](../adr/ADR-167-list-detail-surfaces.md) — canonical `/agents` list/detail surface

## Purpose

Define the scalable presentation rules for agent and task detail surfaces.

This doc is broader than the current implementation pass. It covers:

- how agent detail should vary by class without exploding into per-agent pages
- how task detail should vary by `output_kind` without exploding into per-task-type pages
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

## Task-Side Counterpart On `/work`

The same anti-fragmentation rule applies on the work surface, but the top-level
cut is different.

**Do not build one page per task type.**

The right layering for task detail is:

1. **`output_kind` chooses the primary `/work` shell**
2. **registry metadata chooses optional secondary modules**
3. **`type_key` only specializes bounded copy, labels, and a small number of modules**

That means the task-side equivalent of `agent_class` is **not** `type_key`.
It is `output_kind`.

### Why `output_kind` is the right shell boundary

The four task shapes represent materially different user questions:

| `output_kind` | User question | Primary shell emphasis |
|---|---|---|
| `accumulates_context` | "What knowledge is this task keeping fresh?" | Domain coverage, freshness, changelog, context growth |
| `produces_deliverable` | "What artifact did this task produce?" | Latest deliverable, exportability, audience, quality contract |
| `external_action` | "What did this task send, where, and did it land?" | Target surface, payload, delivery result, action history |
| `system_maintenance` | "What upkeep happened and can I trust it?" | Policy, thresholds, hygiene log, deterministic run history |

If two task types answer the same user question with the same primary data
shape, they should share the shell even if the copy differs.

### What registry metadata should specialize

Once the shell is chosen by `output_kind`, small secondary modules can come
from registry metadata when the data genuinely differs:

- `layout_mode` can distinguish document-style deliverables from email-like digests
- `requires_platform` can add connection or target-surface panels
- `bootstrap` can add tracker setup/progress modules
- `default_deliverable` or quality metadata can shape expectation blocks

This is the correct place for variation. It avoids forking the whole page just
because one task type has a different framing detail.

### Surface-Ready Output Principle

Task outputs should be **surface-ready**, but that does not mean every task can
collapse into a single generic "Latest output" section.

There are two different concepts:

- **surface-ready artifact** — a report, digest, message body, or log block that
  is ready to render directly
- **surface-ready task view** — the full user-facing explanation of what the task
  did, including status, provenance, targets, history, and operational context

For `produces_deliverable`, the artifact is often close to the whole story.
For the other three `output_kind`s, the artifact is only one component of the
page. A good task detail still needs kind-specific context around it.

Every run should emit enough structure for the UI to render without guesswork:

- primary artifact or latest payload
- summary
- status
- timestamp
- provenance
- delivery/result metadata
- links or exports
- optional typed extras by `output_kind`

### Recommended Frontend Shape For Task Detail

```text
WorkDetail
├── SurfaceIdentityHeader
├── TaskShellRegistry[output_kind]
│   ├── kind-aware primary block
│   └── kind-aware operational block
├── TaskTypeAddonRegistry[task_family or capability]
├── Instructions / Objective / Feedback blocks
└── Assigned agent + task stats / run history
```

Use `TaskTypeAddonRegistry` only for bounded add-ons, not as a back door to one
page per task type.

## Rendering Axes

### 1. `agent_class` owns the shell

The four classes get distinct top-of-page interpretation:

| Class | User question | Shell emphasis |
|---|---|---|
| `specialist` (Researcher, Analyst, Writer, Tracker, Designer) | "What work is this specialist assigned to, and how do they contribute?" | Active tasks, capability summary, recent output quality |
| `platform-bot` | "Is this platform connected, what sources are selected, and what work runs on top of them?" | Connection state, source selection, connect/manage path, platform task setup |
| `meta-cognitive` (TP) | "What system-level responsibility does TP own?" | Orchestration role, back-office tasks, essential maintenance |

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
  Add connection/source-selection or platform-specific activity modules. When disconnected, the UI should say so directly and route to Settings > Connectors. Source selection belongs on the bot's agent detail surface, not under `/context`.
- `analyst`, `writer`
  Add upstream-readiness modules showing which context domains they read from.
- `thinking_partner`
  Add workforce-health and essential-task modules.
- `researcher`, `tracker`
  Add active-domain blocks showing which context domains they currently write to across their assigned tasks.

## No-Task States Must Differ By Class

Generic "No tasks assigned yet" copy is not sufficient. The absence of tasks means different things for different agent classes, but the card itself should stay minimal.

Use one shared pattern:

- short title
- one sentence only
- no step list inside the card
- one common header CTA: `Create Task`
- keep local operational links only when the agent has a real setup dependency, such as `Connect platform`

### Specialists (Researcher, Analyst, Writer, Tracker, Designer)

No tasks means the specialist is available but has no active work assignments.

The empty state should describe what this specialist does in one sentence and suggest creating a task that would use them.

### Writer / Analyst (cross-domain readers)

No tasks means these agents have nothing to read from or synthesize into deliverables.

The empty state should name the missing report task in plain language.

### Integration Bots (`platform-bot`)

No tasks does **not** necessarily mean "idle worker." It may mean the integration exists but no observation or write-back flow has been defined yet.

The empty state should stay short and defer setup detail to the dedicated connection and source-selection modules above it.

### Thinking Partner (`meta-cognitive`)

No tasks is usually a coherence/scaffold problem, not a neutral empty state.

The empty state should name the missing maintenance responsibility in plain language.

## Dedicated Components: When They Are Warranted

Create a dedicated component when one of these is true:

1. The **empty state logic** differs materially
2. The **primary data** differs, not just the copy
3. The **operational CTA** differs
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
│   └── class-aware add-on block
├── DomainOwnershipBlock (for specialists)
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

- class-specific top shell / role blocks
- class-specific no-task states
- one shared header CTA for task creation
- no second route or second agent detail page

This session does **not** add new API data or platform-connection health models. Richer role-specific modules can follow later once the required data is available on the canonical agent payload.
