# ADR-138: Agents as Work Units — Project Layer Collapse

> **Status**: Proposed — next session implementation
> **Date**: 2026-03-25
> **Authors**: KVK, Claude
> **Supersedes**: ADR-122 (Project Type Registry), ADR-133 (PM Dispatch), ADR-136 (Charter File Split), ADR-137 (Pipeline Execution)
> **Evolves**: ADR-130 (Type Registry → archetype simplification), ADR-132 (Onboarding → creates agents not projects)
> **Preserves**: ADR-135 (Chat coordination), ADR-130 (Compose engine, capabilities)

---

## Context

The system has three layers: Workspace → Projects → Agents. Projects were introduced as containers for multi-agent coordination with PM agents managing execution. In practice:

1. **Most projects need 1 agent, not 3.** A competitive intel project doesn't need scout + analyst + writer — one agent handles the full thinking chain (sense → reason → produce) like Claude Code handles a task in one session with multiple tool rounds.

2. **PM agents add overhead without value for simple projects.** PM pulses, coordinates, dispatches — but for a 1-agent project, PM is just a passthrough that costs $0.05/cycle for no benefit.

3. **Projects and agents are conceptually the same thing.** A "Competitive Intel Project" with one "Competitive Intel Agent" is redundant naming. The agent IS the work unit.

4. **The project layer creates naming confusion.** PROJECT.md vs AGENT.md, scaffold_project() vs create_agent(), project_slug vs agent_slug. Two names for the same concept.

5. **Context is lost in multi-agent handoffs.** When scout passes to analyst, the analyst only sees the output text — not the scout's reasoning, failed searches, or judgment calls. One agent with multiple tool rounds retains full context.

### The Claude Code analogy

Claude Code doesn't decompose "research competitors" into separate research/analyze/write agents. It uses one agent with multiple tools (Read, WebSearch, Write) and multiple reasoning rounds. The context stays unified. The output is better because reasoning is continuous.

Our agents should work the same way — one agent per domain, full tool access, multiple rounds, continuous reasoning.

---

## Decision

### Collapse projects into agents

Each agent IS a work unit. It has its own:
- **Objective** (what to produce)
- **Cadence** (when to run)
- **Delivery** (where to send)
- **Output specification** (what good looks like)
- **Success criteria** (definition of done)
- **Memory** (accumulated knowledge)
- **Output history** (versions delivered)

No separate project container needed for single-agent work.

### Hierarchy

```
Workspace (user level)
├── Brand, Identity, Memory
├── Platform Connections
│
├── Agent: Competitive Intelligence
│   ├── AGENT.md (objective + criteria + process + output spec)
│   ├── memory/ (accumulated knowledge)
│   ├── outputs/ (delivery history)
│   └── Runs autonomously: sense → reason → produce → deliver
│
├── Agent: Slack Team Recap
│   ├── AGENT.md
│   ├── memory/
│   ├── outputs/
│   └── Runs daily: read Slack → summarize → deliver
│
└── Assembly (rare, cross-agent)
    └── Quarterly Board Review
        ├── Combines outputs from multiple agents
        └── Orchestrator-coordinated, not PM-coordinated
```

### Agent types become archetypes

| Archetype | Domain Pattern | Tools | Example |
|-----------|---------------|-------|---------|
| **Monitor** | Watches a domain, alerts on changes | read_platforms, web_search | Slack Recap, Competitor Watch |
| **Researcher** | Deep investigation, produces analysis | web_search, read_workspace, chart | Market Research, Due Diligence |
| **Producer** | Creates deliverables from context | read_workspace, chart, compose | Investor Update, Weekly Report |
| **Operator** | Takes actions on platforms (future) | write_slack, write_notion | Social Posts, CRM Updates |

Each archetype handles the FULL thinking chain within its domain. Not decomposed into sub-agents.

### PM role dissolves

PM responsibilities move to:
- **Orchestrator (TP)**: creates agents, monitors health, adjusts objectives, handles cross-agent assembly
- **Agent self-governance**: each agent has its own cadence, quality self-check, delivery
- **Composer**: workforce-level assessment (existing)

No PM agent type. No PM prompts. No PM coordination pulses.

### AGENT.md becomes the charter

```markdown
# Competitive Intelligence

## Objective
- **Deliverable**: Weekly AI competitive intelligence briefing
- **Audience**: Founder
- **Purpose**: Track competitor moves to inform strategic positioning
- **Format**: Document with comparison charts

## Success Criteria
- Cover CrewAI, AutoGen, LangGraph, Claude Agent SDK
- Include pricing and feature comparisons
- Each finding has positioning implication
- Actionable recommendations section

## Process
- **Cadence**: weekly
- **Delivery**: email → kvkthecreator@gmail.com
- **Tools**: web_search, chart, compose_html

## Output Specification
- Executive summary (key changes this week)
- Competitor-by-competitor analysis
- Pricing comparison chart
- Strategic recommendations

## Memory
(accumulated by agent across runs)
```

This is PROJECT.md + TEAM.md + PROCESS.md + AGENT.md collapsed into one file.

### Cross-agent assembly (rare case)

For genuinely multi-domain work (quarterly board review = market + product + finance), the Orchestrator coordinates:

1. User requests: "Create a quarterly board review combining market intel and product updates"
2. Orchestrator identifies existing agents whose outputs are relevant
3. Orchestrator triggers an assembly: reads recent outputs from selected agents → composes into unified deliverable
4. No PM agent needed — Orchestrator IS the coordinator

This uses existing `compose_html` + delivery infrastructure.

---

## What changes

### Database / Schema
- `agents` table: add `objective` JSONB, `cadence` TEXT, `delivery` JSONB, `output_spec` JSONB columns. Or keep in AGENT.md (workspace file).
- `agents.role`: archetype values (monitor, researcher, producer, operator) replace current v2 types
- PM agents: archive existing, stop creating new ones

### API Routes
- `/api/projects/*` routes: deprecate or redirect to `/api/agents/*`
- `/api/agents/{id}` enriched with objective, cadence, delivery, output history
- Agent detail page becomes the primary work surface (not project page)

### Frontend
- Project pages → Agent pages (same layout: chat + workfloor panel)
- Project list → Agent list (already exists at `/agents`)
- Orchestrator panel: shows agents, not projects
- Agent page: objective + output + activity (same as current project workfloor)

### Workspace Files
- `/projects/{slug}/` → contents move to `/agents/{slug}/`
- `/agents/{slug}/AGENT.md` absorbs objective, process, output spec
- `/agents/{slug}/outputs/` (already exists)
- `/agents/{slug}/memory/` (already exists)
- Assembly outputs: `/assemblies/{name}/` at workspace level (rare)

### Execution
- Each agent runs autonomously on its cadence (existing pulse system)
- No pipeline executor needed for single-agent work
- Agent gets all tools for its archetype (5-8 tool rounds like Claude Code)
- Quality self-check: agent evaluates own output against success criteria
- Delivery: agent delivers its own output (no PM passthrough)

### Inference
- Onboarding produces agent specs, not project specs
- Each scope → 1 agent with rich AGENT.md
- Multi-agent assembly only when genuinely needed

---

## What stays unchanged

- Compose engine (ADR-130) — per-agent output rendering
- Chat coordination (ADR-135) — user talks to agents
- Type registry structure — archetypes replace v2 types
- Workspace filesystem — `/agents/` namespace already canonical
- Feedback distillation — per-agent learning
- Cadence enforcement — per-agent (moves from PROCESS.md to AGENT.md)
- Export pipeline — per-agent output

## What gets deleted

- PM agent type
- PM prompts, PM modes, PM coordination
- `/projects/` namespace (or deprecated)
- scaffold_project() (replaced by enriched create_agent())
- Pipeline executor (agents are autonomous, not pipelined)
- PROJECT.md, TEAM.md, PROCESS.md (absorbed into AGENT.md)
- pm_coordination.py
- pipeline_executor.py

---

## Migration

### Existing projects → agents
For each existing project with 1 contributor:
1. Merge PROJECT.md objective + PROCESS.md cadence into contributor's AGENT.md
2. Move `/projects/{slug}/outputs/` to `/agents/{contributor-slug}/outputs/`
3. Set delivery config on the agent
4. Archive PM agent
5. Archive project workspace files

For multi-contributor projects (rare):
1. Keep primary contributor as the agent
2. Archive secondary contributors (or convert to standalone agents)
3. Cross-agent assembly handled by Orchestrator on-demand

### Database migration
- Add columns to `agents` table (or keep in AGENT.md — simpler, no migration)
- Archive PM agents: `UPDATE agents SET status = 'archived' WHERE role = 'pm'`

---

## Naming alignment

| Current | Proposed |
|---------|----------|
| Project | Agent (or "Work Unit" in user-facing copy) |
| scaffold_project() | create_agent() (enriched) |
| PROJECT.md | AGENT.md (expanded) |
| TEAM.md | (deleted — one agent per work unit) |
| PROCESS.md | (absorbed into AGENT.md ## Process) |
| PM agent | (deleted — Orchestrator handles coordination) |
| /projects/{slug}/ | /agents/{slug}/ |
| Project page | Agent page |
| project_slug | agent_slug (already exists) |

---

## Cost impact

| Current (3 agents + PM) | Proposed (1 agent) |
|--------------------------|-------------------|
| Scout: $0.05 | Agent: $0.06 (more tool rounds) |
| Analyst: $0.04 | — |
| Writer: $0.03 | — |
| PM evaluate: $0.001 | Self-check: $0.001 |
| PM compose: $0.05 | Delivery: $0 (direct) |
| **Total: $0.17/cycle** | **Total: $0.06/cycle** |

**65% cost reduction** with better output (unified reasoning context).

---

## Implementation sequence (next session)

### Phase 1: AGENT.md expansion
- Expand AGENT.md to include objective, cadence, delivery, output spec, success criteria
- Update create_agent() to write enriched AGENT.md
- Update agent execution to read objective + criteria from AGENT.md

### Phase 2: Agent self-governance
- Agent evaluates own output against success criteria (Haiku self-check)
- Agent delivers its own output (no PM passthrough)
- Cadence enforcement on agent (from AGENT.md, not PROCESS.md)

### Phase 3: PM dissolution
- Archive PM agents
- Move PM assembly → Orchestrator-triggered cross-agent assembly (rare)
- Delete PM prompts, modes, coordination code

### Phase 4: Frontend
- Project pages → Agent pages
- Agent list replaces project list as primary navigation
- Agent page: chat + objective + outputs + activity

### Phase 5: Cleanup
- Delete /projects/ namespace (or archive)
- Delete scaffold_project(), pipeline_executor.py, pm_coordination.py
- Update inference to produce agent specs
- Update onboarding to create agents directly

---

## Hooks discipline reminder (next session)

1. Singular implementation — delete project layer, not dual approach
2. Docs alongside code — update FOUNDATIONS, workspace-conventions, CLAUDE.md
3. Check ADRs — this supersedes 122, 133, 136, 137
4. Database — AGENT.md expansion preferred over schema changes
5. Quality checks — verify agent routes match frontend calls
6. Prompt changes — agent prompts read from enriched AGENT.md, CHANGELOG entries
7. Git — commit per phase
