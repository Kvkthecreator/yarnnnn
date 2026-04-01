# ADR-136: Project Charter Architecture — Separated Concerns

> **Status**: Phases 1-4 Implemented
> **Superseded by**: [ADR-138](ADR-138-agents-as-work-units.md) — Project layer collapsed. PM dissolved. Tasks replace projects.
> **Date**: 2026-03-24
> **Authors**: KVK, Claude
> **Supersedes**: Single PROJECT.md model (ADR-119, ADR-122, ADR-123)
> **Evolves**: ADR-133 (phase dispatch), ADR-134 (project surface), ADR-135 (chat coordination)
> **Extends**: ADR-130 (type registry → TEAM.md capability vocabulary)

---

## Context

The current `PROJECT.md` is a single file carrying too many concerns: objective, team roster, assembly spec, delivery config, and implicitly cadence. This causes:

1. **Runaway execution loops** — no cadence enforcement because cadence isn't in the charter. Agents run whenever their pulse fires, producing duplicate outputs.
2. **PM can't reason about composition** — no output specification telling PM what the final deliverable should look like (format, components, quality bar).
3. **No definition of done** — agents produce outputs but nothing says "this is what good looks like" or "we need 3 charts and a comparison table."
4. **Charter/memory confusion** — `memory/work_plan.md` tried to be both charter (what we intend) and memory (what PM decided). PM's working state mixed with project constitution.

### The filesystem IS the architecture

YARNNN's workspace filesystem is the agent framework. How files are organized determines how agents reason. A single PROJECT.md means agents see the project as one undifferentiated blob. Separated files mean agents can focus on their concern:
- PM reads PROCESS.md for cadence and output spec
- Contributors read PROJECT.md for objective and success criteria
- Assembly reads PROCESS.md for output spec and component list
- Tier 1 reads PROCESS.md for cadence enforcement

---

## Decision

### Three charter files, separated by concern

```
/projects/{slug}/
├── PROJECT.md      ← WHAT: objective, success criteria, audience
├── TEAM.md         ← WHO: contributors, types, capabilities, sources
├── PROCESS.md      ← HOW: output spec, cadence, delivery, phases
```

### Charter vs. Memory: strict separation

**Charter files** (top-level): what the project IS. Defined at creation, refined by user/TP. The constitution. Append-to-top versioning — changes prepend, history preserved in-file.

**Memory files** (`memory/`): what the project has LEARNED. Accumulated by agents during execution. Working state.

| File | Type | Who Writes | Who Reads |
|------|------|-----------|-----------|
| `PROJECT.md` | Charter | User, TP, Composer | All agents, PM, frontend |
| `TEAM.md` | Charter | scaffold_project(), Composer | PM, frontend |
| `PROCESS.md` | Charter | scaffold_project(), user, PM | PM, Tier 1, assembly, frontend |
| `memory/pm_log.md` | Memory | PM | PM (continuity) |
| `memory/project_assessment.md` | Memory | PM | Contributors, PM, frontend |
| `memory/quality_assessment.md` | Memory | PM | PM, assembly |
| `memory/phase_state.json` | Memory | PM Tier 3 | PM, frontend |
| `memory/decisions.md` | Memory | Chat PM | PM, contributors |

No overlap. Charter = constitution. Memory = working state.

### PROJECT.md — The Objective

```markdown
# Competitive Watch

## Objective (updated 2026-03-24)
- **Deliverable**: Weekly competitive intelligence briefing
- **Audience**: Founder (you)
- **Purpose**: Track competitor moves, pricing changes, market shifts
- **Format**: Document with comparison charts

## Success Criteria
- Covers top 3 competitors by name
- Includes at least 1 external source per competitor
- Each finding has "so what" implication for positioning
- Actionable recommendations section

---
## Objective (created 2026-03-22)
- **Deliverable**: Competitive Watch update
...
```

Append-to-top versioning: changes prepend with date header, history preserved below divider. Agents read the latest (top) section.

### TEAM.md — The Roster

```markdown
# Team

## competitive-watch-scout
- **Type**: scout
- **Capabilities**: web_search, chart, image, compose_html
- **Role in project**: External monitoring — competitors, market, pricing
- **Sources**: web search (no platform sources)

## Project Manager
- **Coordinates**: assembly + delivery
- **Capabilities**: read_workspace, steer_contributors, trigger_assembly
```

Maps directly to `AGENT_TYPES` registry. PM can reason: "objective needs charts, scout has chart capability — covered."

### PROCESS.md — The Operating Model

```markdown
# Process

## Output Specification
- **Layout mode**: document
- **Components**:
  - Competitive landscape section with comparison chart (scout)
  - Positioning recommendations (PM synthesis)
- **Quality bar**:
  - Minimum 3 named competitors
  - At least 1 external source per finding
- **Export formats**: PDF, email body

## Cadence
- **Contributor runs**: weekly (Monday)
- **Assembly**: weekly (Monday, after contributors)
- **Delivery**: weekly (Monday, after assembly)

## Delivery
- **Channel**: email
- **Recipient**: kvkthecreator@gmail.com

## Phases
### Phase 1: Research
- competitive-watch-scout: external scanning

### Phase 2: Assembly + Delivery
- pm: compose output per spec, deliver
```

This is what Tier 1 reads for cadence enforcement. PM reads for composition orchestration. Assembly reads for output specification.

---

## PM Agent = Project Workspace

PM has no separate `/agents/pm-slug/` directory. PM's workspace IS the project workspace. PM's memory IS `memory/`. PM's identity IS "manage this project."

Contributors keep their own `/agents/{slug}/` workspace with AGENT.md, thesis.md, self_assessment.md, preferences.md.

---

## Cadence Enforcement (Tier 1)

New Tier 1 gate: read `PROCESS.md` cadence, check if project has already delivered in the current cadence window.

```python
# Tier 1 Gate: Cadence window
cadence = read_cadence_from_process_md(project_slug)  # "weekly"
last_delivery = get_last_delivery_time(project_slug)
if cadence == "weekly" and last_delivery > start_of_current_week:
    return wait("Already delivered this week")
```

This prevents the runaway loop: once the project delivers for the week, all agents wait until the next cadence window opens.

---

## Composition Orchestration

The output spec in PROCESS.md tells PM what the final deliverable should look like. PM's assembly decision becomes:

1. Read output spec: "document with comparison chart + recommendations"
2. Check contributions: does scout output have a chart? does it cover 3 competitors?
3. Identify gaps: "no chart produced — scout should include chart next run"
4. Compose: arrange components per spec, apply layout mode
5. Quality check: compare against success criteria from PROJECT.md
6. Deliver: per PROCESS.md delivery config

This is **composition intelligence** — PM reasons about what the output should look like, not just whether contributors have produced.

---

## Frontend Mapping

| Tab | Files | Surface |
|-----|-------|---------|
| Workfloor | PROJECT.md + TEAM.md + memory/ | Objective (editable) + agent roster + PM state |
| Outputs | assemblies/ + PROCESS.md output spec | Rendered HTML + version history + export |
| Brand | User-scoped brand file | Brand identity editing |
| Settings | PROCESS.md cadence/delivery | Cadence, delivery config, archive |

---

## Impact on Pricing / LLM Optimization

This architecture enables more **deterministic execution**:
- Cadence enforcement means agents run N times per period, not unbounded
- Output spec means PM can evaluate without running contributors again
- Phase structure means sequential execution, not parallel chaos
- Success criteria means PM can gate quality before delivery

Predictable execution = predictable cost. For a weekly project with 1 scout + 1 PM:
- Scout: 1 Sonnet call/week (~$0.03)
- PM: 1 Sonnet call/week for assessment + assembly (~$0.05)
- PM Tier 3: ~30 Haiku calls/week for coordination (~$0.03)
- Total: ~$0.11/week per project, ~$0.50/month

User feedback is optional supervision, not required for execution. Agents reason against the charter + success criteria autonomously.

---

## Phases

### Phase 1: Charter file split
- Split PROJECT.md → PROJECT.md + TEAM.md + PROCESS.md
- Update scaffold_project() to write three files
- Update read_project() to read and merge three files
- PM workspace = project workspace (no separate /agents/pm-slug/)

### Phase 2: Cadence enforcement
- Add PROCESS.md cadence parsing
- Tier 1 gate: cadence window check
- PM reads cadence for assembly timing

### Phase 3: Composition intelligence
- PM reads PROCESS.md output spec
- Assembly uses output spec for component arrangement
- PM quality gates against PROJECT.md success criteria
- Layout mode from output spec → compose engine

### Phase 4: Frontend alignment
- Workfloor: PROJECT.md + TEAM.md rendering
- Settings: PROCESS.md cadence/delivery editing
- Outputs: output spec header + assembly rendering
