# ADR-138: Workspace → Agents → Tasks — Project Layer Collapse

> **⚠ Superseded by [ADR-231](ADR-231-task-abstraction-sunset.md) (2026-04-29).** Tasks-as-work-units framing dissolves. Agents survive as Identity layer per FOUNDATIONS Axiom 2 + Axiom 9; work units dissolve into invocations. The Workspace → Agents → Tasks hierarchy collapses to Workspace → Agents → Recurrence Declarations (YAML legibility wrappers at natural-home paths) → Invocations. The `tasks` DB table survives as a thin scheduling index per ADR-231 D4 Path B; the `/tasks/{slug}/` filesystem tree, `task_pipeline.py` dispatch path, and `ManageTask` primitive are all DELETED in ADR-231 Phase 3.7.
>
> **Status**: Proposed (v3.1 — filesystem-first, no join tables)
> **Date**: 2026-03-25
> **Authors**: KVK, Claude
> **Supersedes**: ADR-120 (PM/Project Execution), ADR-121 (PM Intelligence Director), ADR-122 (Project Type Registry), ADR-123 (Project Objective & Ownership), ADR-124 (Meeting Room), ADR-125 (Project-Native Sessions), ADR-128 (Multi-Agent Coherence — PM portions), ADR-129 (Activity Scoping — project tier), ADR-132 (Onboarding — project scaffolding), ADR-133 (PM Phase Dispatch), ADR-134 (Output-First Project Surface), ADR-136 (Charter File Split), ADR-137 (Pipeline Execution)
> **Evolves**: ADR-106 (Workspace), ADR-109 (Agent Framework), ADR-111 (Composer → thins), ADR-126 (Pulse — simplifies), ADR-130 (Type Registry → archetypes)
> **Preserves**: ADR-117 (Feedback distillation), ADR-118 (Output gateway/skills), ADR-119 (Workspace filesystem conventions), ADR-128 (Self-assessment — agent portions), ADR-130 (Compose engine, capability/runtime registries)
> **Requires update**: FOUNDATIONS.md (Axioms 1, 5, 6), ESSENCE.md (System Shape, User Experience Loop), NARRATIVE.md (references to projects), workspace-conventions.md, agent-framework.md, CLAUDE.md

---

## Context

### What we built

Over ADRs 120-137, we built a three-layer system: **Workspace → Projects → Agents**. Projects contain agents, each project has a PM agent that coordinates, and agents are workers within a project container. The PM layer alone is ~3,100 lines of code across 7 files with 8 decision actions, 6 workspace files, a dedicated coordination pulse (Tier 3), and a 477-line prompt.

### Why it's wrong

1. **Most work needs 1 agent, not 3.** A competitive intel task doesn't need scout + analyst + writer — one agent handles the full thinking chain (sense → reason → produce) like Claude Code handles a task in one session with multiple tool rounds. Context stays unified. Output is better.

2. **The project layer duplicates the agent layer.** A "Competitive Intel Project" with one "Competitive Intel Agent" is redundant naming. PROJECT.md + TEAM.md + PROCESS.md + AGENT.md is 4 files for what should be 1. `scaffold_project()` creates a PM, contributors, charter files, cognitive files — all infrastructure for the common case of 1 agent doing 1 job.

3. **We're stuck in the middle.** We built project infrastructure but keep trying to collapse toward simpler models. Every session adds project complexity; the next session proposes simplifying it. This oscillation wastes effort.

4. **PM overhead without proportional value.** PM costs $0.05/cycle for coordination that a single agent doesn't need. For multi-agent work, TP can orchestrate directly — it already has full workspace visibility.

5. **The user model is wrong for solo founders.** A solo founder thinks "I need competitive intel weekly" — that's a task, not a project. They think "I want an agent handling my market research" — that's a domain expert, not a skill-typed contributor within a project.

### The insight: separate WHO from WHAT

The current architecture conflates agent identity (who) with work definition (what) inside project containers (where). The clean separation is:

- **Agent** = WHO — persistent domain expert with identity, capabilities, memory
- **Task** = WHAT — a defined unit of work with objective, cadence, delivery, criteria
- **Workfloor** = WHERE — shared filesystem, knowledge base, platform connections

An agent can work on multiple tasks. A task can involve multiple agents. The workfloor is the shared substrate they all operate on. No project container needed.

### The Claude Code analogy

Claude Code doesn't decompose "research competitors" into sub-agents. It uses one agent with multiple tools and reasoning rounds. When it needs parallel work, it spawns sub-agents from **one orchestrator**. There's no PM layer — the orchestrator IS the coordinator.

TP should work the same way: it creates agents, assigns tasks, and orchestrates complex multi-agent work directly.

### Clean-slate decision

This is a pre-launch system with only test data (2 user IDs). Rather than migrate, we delete the entire project layer — code, DB, routes, frontend, workspace files. No legacy, no dormant code, no dual approaches.

---

## Decision

### The definitive hierarchy

```
Workspace (1 per user, implicit)
├── Workfloor (shared substrate)
│   ├── /workspace/ (IDENTITY.md, BRAND.md)
│   ├── /knowledge/ (accumulated content corpus)
│   ├── /memory/ (TP-extracted notes)
│   └── Platform Connections (Slack, Notion)
│
├── TP (Orchestrator)
│   ├── Chat — user's conversational interface
│   ├── Create — spins up agents and tasks
│   ├── Monitor — periodic workforce health check (absorbs Composer)
│   ├── Orchestrate — coordinates multi-agent tasks (absorbs PM)
│   ├── Assemble — combines agent outputs on demand
│   └── Adjust — modifies agents/tasks via chat or autonomously
│
├── Agents (WHO — persistent domain identities)
│   ├── Agent: "Market Intelligence"
│   │   ├── AGENT.md (identity, expertise, capabilities)
│   │   ├── memory/ (accumulated domain knowledge)
│   │   └── Assigned to: Task A, Task C
│   │
│   ├── Agent: "Content Writer"
│   │   ├── AGENT.md
│   │   ├── memory/
│   │   └── Assigned to: Task B, Task C
│   │
│   └── Agent: "Team Observer"
│       ├── AGENT.md
│       ├── memory/
│       └── Assigned to: Task D
│
└── Tasks (WHAT — defined work units)
    ├── Task A: "Weekly Competitive Briefing"
    │   ├── TASK.md (objective, cadence, delivery, output spec, criteria)
    │   ├── outputs/ (delivery history)
    │   └── Agent: Market Intelligence (sole worker)
    │
    ├── Task B: "Daily Slack Recap"
    │   ├── TASK.md
    │   ├── outputs/
    │   └── Agent: Team Observer (sole worker)
    │
    ├── Task C: "Q1 Board Review" (multi-agent)
    │   ├── TASK.md (includes process: who does what)
    │   ├── outputs/
    │   └── Agents: Market Intelligence (research), Content Writer (compose)
    │
    └── Task D: "Competitor Pricing Alert"
        ├── TASK.md
        ├── outputs/
        └── Agent: Market Intelligence (same agent, different task!)
```

### Key separations

**Agent = WHO (persistent identity)**
- AGENT.md: identity, domain expertise description, capabilities, personality
- memory/: accumulated domain knowledge, observations, preferences, self-assessment
- An agent persists across tasks — its domain knowledge compounds regardless of which task triggered a run
- An agent can be assigned to multiple concurrent tasks
- Archetype determines default capabilities (monitor, researcher, producer, operator)

**Task = WHAT (work definition)**
- TASK.md: objective (deliverable, audience, purpose, format), cadence, delivery, output spec, success criteria
- outputs/: delivery history with manifest.json per run
- A task is lightweight — a definition of work to be done, not an organizational container
- Simple tasks: 1 agent. Complex tasks: multiple agents with a process spec.
- Task `mode` determines temporal behavior: `recurring` (indefinite cadence), `goal` (bounded, completes when criteria met), `reactive` (event-triggered or on-demand)

**Workfloor = WHERE (shared substrate)**
- /workspace/: user identity (IDENTITY.md, BRAND.md)
- /knowledge/: shared content corpus from platform sync + agent outputs
- /memory/: TP-extracted notes
- Platform connections: Slack, Notion
- This is what all agents and tasks share — the operating substrate

### TP absorbs PM and Composer coordination

| PM/Project Responsibility | New Home | Mechanism |
|---|---|---|
| Create agents | TP primitive | `ManageAgent` with AGENT.md |
| Create tasks | TP primitive | `CreateTask` with TASK.md, assigns agent(s) |
| Agent health monitoring | Composer cron | Periodic workforce health check (existing, thins to health-only) |
| Quality assessment | Agent self-check | Haiku post-generation eval against TASK.md criteria |
| Work steering | TP chat / TASK.md update | User says "focus on pricing" → TP updates TASK.md or AGENT.md |
| Task decomposition | Inference at creation | TP infers task structure from user intent |
| Multi-agent coordination | TP orchestration | TP triggers agents sequentially with cross-agent context |
| Assembly | TP primitive | `AssembleOutputs` — read multiple agent outputs, compose |
| Cadence enforcement | Scheduler + DB | `tasks.schedule` + `tasks.next_run_at` |
| Delivery | Per-task | Each task delivers its output per TASK.md config |
| Budget enforcement | Scheduler | `check_work_budget()` (existing, per-user) |
| Decision log | TP chat history | Chat IS the decision log |
| Phase sequencing | **Deleted** | Single-agent tasks: agent handles full chain. Multi-agent: TP orchestrates. |

### AGENT.md (identity — WHO)

```markdown
# Market Intelligence

## Identity
Domain expert in competitive intelligence and market analysis for AI agent platforms.

## Expertise
- AI agent platform landscape (CrewAI, AutoGen, LangGraph, Claude Agent SDK)
- Competitive positioning and pricing analysis
- Market trend identification and strategic implications

## Capabilities
- web_search, read_platforms, chart, compose_html

## Coherence Protocol
Self-assessment on each run. Feedback distillation from user edits.
```

### TASK.md (work definition — WHAT)

```markdown
# Weekly Competitive Briefing

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
- **Mode**: recurring
- **Agents**: market-intelligence
- **Cadence**: weekly
- **Delivery**: email → kvkthecreator@gmail.com

## Output Specification
- Executive summary (key changes this week)
- Competitor-by-competitor analysis
- Pricing comparison chart
- Strategic recommendations
```

### Goal task example (bounded, completes when done)

```markdown
# Acquisition Due Diligence: Acme Corp

## Objective
- **Deliverable**: Comprehensive due diligence report on Acme Corp acquisition target
- **Audience**: Founder
- **Purpose**: Inform acquisition decision
- **Format**: Document with data tables and risk assessment

## Success Criteria
- Financial analysis of last 3 years
- Technology stack assessment
- Team and culture evaluation
- Risk matrix with mitigation strategies
- Go/no-go recommendation with rationale

## Process
- **Mode**: goal
- **Agents**: market-intelligence
- **Cadence**: daily (until complete)
- **Delivery**: none (review in-app)

## Output Specification
- Executive summary with recommendation
- Financial deep dive
- Technology assessment
- Team analysis
- Risk matrix
- Appendix: data sources
```

### Multi-agent TASK.md example

```markdown
# Q1 Board Review

## Objective
- **Deliverable**: Quarterly board deck with market + product analysis
- **Audience**: Board of Directors
- **Purpose**: Quarterly business review
- **Format**: Presentation with charts and data

## Success Criteria
- Market section with competitive landscape
- Product section with key metrics
- Financial summary with projections
- Strategic recommendations

## Process
- **Mode**: recurring
- **Agents**: market-intelligence, content-writer
- **Sequence**:
  1. market-intelligence: Research competitive landscape, produce analysis
  2. content-writer: Compose board deck from market analysis + workspace context
- **Cadence**: quarterly
- **Delivery**: email → kvkthecreator@gmail.com

## Output Specification
- Market landscape overview (chart)
- Competitive positioning matrix
- Product metrics dashboard
- Strategic recommendations
- Financial summary
```

For multi-agent tasks, TP reads the process spec and orchestrates: triggers Agent A, waits for output, feeds output to Agent B as context, delivers final result.

### Agent archetypes (simplified)

| Archetype | Domain Pattern | Default Capabilities | Examples |
|---|---|---|---|
| **monitor** | Watches a domain, alerts on changes | read_platforms, web_search | Slack Recap, Competitor Watch |
| **researcher** | Deep investigation, analysis | web_search, read_workspace, chart | Market Research, Due Diligence |
| **producer** | Creates deliverables from context | read_workspace, chart, compose_html | Investor Update, Board Deck |
| **operator** | Takes actions on platforms (future) | write_slack, write_notion | Social Posts, CRM Updates |

Each archetype handles the FULL thinking chain: sense → reason → produce. Not decomposed into sub-agents. Archetype determines default tool access and prompt framing. All agents can use any tool.

Legacy v2 types: `briefer`→`monitor`, `scout`→`monitor`, `analyst`→`researcher`, `drafter`→`producer`, `writer`→`producer`, `planner`→`producer`. `pm`→**deleted**.

### Session model (simplified)

| Scope | Boundary | Surface | Purpose |
|---|---|---|---|
| Global TP | 4h inactivity | `/orchestrator` | Workspace-level: create agents, create tasks, monitor, orchestrate |
| Agent 1:1 | 4h inactivity | `/agents/{slug}` | Domain-level: steer agent, review work, adjust expertise |

No project sessions. No meeting rooms. No `thread_agent_id`. User talks to TP (about the workspace) or to an agent (about its domain). Each agent session has its own compaction budget — no cross-contamination.

Task-level discussion happens naturally: user goes to the agent assigned to the task and discusses the work. If a task has multiple agents, user talks to each, or asks TP to coordinate.

### Backend execution (post-collapse)

```
Unified Scheduler (cron, every 1 min)
│
├── Task Pulse Loop
│   └── For each task where next_run_at <= now:
│       ├── Tier 1 (deterministic): cooldown? budget? fresh content?
│       ├── Single-agent task:
│       │   └── Trigger agent → gather → generate → self-check → deliver
│       ├── Multi-agent task:
│       │   └── TP orchestrates sequence per TASK.md process spec
│       └── Update next_run_at per TASK.md cadence
│
├── Composer Heartbeat (every 6h)
│   ├── Are any agents unhealthy? (no task runs, errors)
│   ├── Are any tasks stale? (missed cadence)
│   ├── Should new agents/tasks be suggested?
│   └── Surface findings to TP
│
├── Platform Sync (existing, unchanged)
│
└── Workspace Cleanup (/working/ 24h, ephemeral 30d)
```

No PM pulse (Tier 3 deleted). No pipeline executor. No phase dispatch. The scheduler pulses tasks, not agents. Agents run when a task needs them.

### Workspace filesystem (post-collapse)

```
/workspace/
  ├── IDENTITY.md         (user profile)
  └── BRAND.md            (output identity)

/agents/{slug}/
  ├── AGENT.md            (identity — WHO)
  ├── memory/
  │   ├── observations.md
  │   ├── preferences.md  (feedback-distilled)
  │   ├── self_assessment.md
  │   └── directives.md   (user guidance from chat)
  ├── working/            (ephemeral scratch, 24h TTL)
  └── history/            (version history)

/tasks/{slug}/
  ├── TASK.md             (work definition — WHAT)
  ├── memory/
  │   └── run_log.md      (append-only: date, outcome, observations per run)
  └── outputs/{date}/
      ├── output.md
      ├── output.html     (composed)
      └── manifest.json

/knowledge/
  ├── digests/
  ├── analyses/
  ├── briefs/
  ├── research/
  └── insights/

/memory/
  └── notes.md            (TP-extracted)
```

Key changes:
- Agent workspace has NO outputs — outputs belong to tasks. Agent workspace is pure identity + domain memory.
- Task workspace has TASK.md (definition) + `memory/run_log.md` (task-level continuity) + `outputs/` (delivery history).
- `memory/run_log.md` is append-only, written by post-run self-check: date, outcome, observations. Agent self-assessment is domain growth; run_log is task-specific learning ("this week's briefing missed pricing data because Notion sync was stale").
- Multi-agent handoff: intermediate outputs go to `/tasks/{slug}/outputs/{date}/step-{N}-{agent-slug}.md`. Final composed output is `output.md`. All in the same dated folder.
- Knowledge base writes still happen: agent output → `/knowledge/` for workspace-level accumulation.

### Onboarding (post-collapse)

```
1. User signs up
2. "What kind of work do you need help with?"
   → "Competitive intelligence" → infer: researcher agent + weekly briefing task
   → "Slack recap" → infer: monitor agent + daily recap task
   → "Investor updates" → infer: producer agent + monthly update task
3. User connects platforms (Slack, Notion)
4. Platform content enriches /knowledge/
5. Agents pulse on task cadence
6. First outputs delivered
```

`scaffold_project()` → `create_agent()` + `create_task()`. No PM. No project. Just agents and tasks.

### Frontend surfaces (post-collapse)

```
/orchestrator          — TP chat (workspace-level orchestration)
/agents                — Agent list (your workforce — WHO)
/agents/{slug}         — Agent detail: identity, memory, chat, assigned tasks
/tasks                 — Task list (your work — WHAT)
/tasks/{slug}          — Task detail: objective, latest output, delivery history
/context               — Platform source curation
/activity              — Global activity log
/integrations          — Platform connections
```

Agent list = "your team." Task list = "your work." TP chat = "your office."

---

## Schema changes

### Design principle: filesystem-first, DB as scheduling index

Consistent with the existing workspace architecture (ADR-106, ADR-119), all rich metadata lives in workspace files. The DB stores only what the scheduler needs for time-based queries. Agent-task relationships live in TASK.md (authoritative, names agent slugs) and agent's `memory/tasks.json` (denormalized reverse index). **No join tables.**

### New: `tasks` table (thin scheduling index)

```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  slug TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'recurring' CHECK (mode IN ('recurring', 'goal', 'reactive')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
  schedule TEXT,             -- cron or human-readable cadence
  next_run_at TIMESTAMPTZ,
  last_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, slug)
);
```

`mode` is on tasks, not agents — it describes temporal behavior of the work, not identity of the worker. A Research Agent can simultaneously have a `recurring` task (weekly briefing) and a `goal` task (investigate this acquisition). All rich metadata (title, objective, delivery, output spec, success criteria, agent assignments, process) lives in `/tasks/{slug}/TASK.md`. The DB is the scheduler's index only.

### No `task_agents` join table

Agent-task relationships are filesystem-based:
- **TASK.md** (authoritative): `## Process` section names agent slug(s) and sequence
- **Agent `memory/tasks.json`** (reverse index): written at task creation/update, lists assigned task slugs
- **Reverse lookup**: query workspace_files or read agent's `memory/tasks.json`

This is consistent with how project-agent relationships worked (via `type_config.project_slug` + `memory/projects.json`), but cleaner.

### Modified: `agents` table

- **Remove**: `schedule`, `next_pulse_at`, `destination` — scheduling moves to tasks table
- **Remove**: `type_config.project_slug` — no projects
- **Remove**: `mode` — temporal behavior (recurring/goal/reactive) is a property of WHAT (task), not WHO (agent). A Research Agent can simultaneously have a recurring task and a goal task. Mode moves to `tasks` table.
- **Keep**: `id`, `user_id`, `title`, `slug`, `role` (archetype), `scope`, `status`, `type_config` (agent-level config)
- **Role CHECK**: remove `pm`, keep/add `monitor`, `researcher`, `producer`, `operator` + legacy values with migration map

### Deleted: project-related

- All `workspace_files` rows where `path LIKE '/projects/%'`
- All `agents` rows where `role = 'pm'`
- `chat_sessions.project_slug` column (drop — clean slate)
- `session_messages.thread_agent_id` column (drop — clean slate)

### Clean wipe

Since all data is test data, execute full cleanup:
- TRUNCATE workspace_files, agents, agent_runs, chat_sessions, session_messages, activity_log CASCADE
- Recreate with new schema

---

## What gets DELETED (complete inventory)

### Files to delete entirely
- `api/services/pm_coordination.py`
- `api/services/pipeline_executor.py`
- `api/services/project_registry.py`
- `api/routes/projects.py`
- `web/app/(authenticated)/projects/` (entire directory)

### Code to delete from existing files
- `api/services/agent_pulse.py` — Tier 3 PM coordination (~330 lines)
- `api/services/agent_execution.py` — PM decision interpreter, assembly execution, `_write_contribution_to_projects()`, `_maybe_trigger_project_heartbeat()` (~500 lines)
- `api/services/agent_pipeline.py` — PM prompt v6.0 (~200 lines), PM-specific context loading
- `api/services/agent_creation.py` — PM-specific seeding paths
- `api/services/workspace.py` — `ProjectWorkspace` class (~400 lines)
- `api/services/composer.py` — `_execute_create_project()`, project-related Composer actions
- `api/services/onboarding_bootstrap.py` — `maybe_bootstrap_project()` (rewrite to create agents + tasks)
- `api/jobs/unified_scheduler.py` — pipeline execution path, PM pulse routing

### Workspace files to delete
- `/projects/` namespace — everything
- `memory/projects.json` in agent workspaces
- `contributions/` folders
- `memory/work_plan.md`, `memory/phase_state.json`, `memory/pm_log.md`
- `memory/project_assessment.md`, `memory/supervisor-notes.md`

### Concepts to delete
- PM agent type, PM prompts, PM modes, PM coordination pulse (Tier 3)
- Phase dispatch, phase sequencing, phase_state.json
- Pipeline executor, pipeline_state.json
- Project charter files (PROJECT.md, TEAM.md, PROCESS.md)
- Contribution briefs
- Project-scoped sessions, meeting rooms
- Assembly as PM-triggered concept (becomes TP-triggered)

---

## What STAYS (preserved infrastructure)

- **Agent pulse** — Tier 1 + Tier 2 (Tier 3 deleted). Pulse triggers moved to task level.
- **Agent workspace** — `/agents/{slug}/` with AGENT.md (identity), memory/ (domain knowledge)
- **KnowledgeBase** — `/knowledge/` shared corpus
- **UserMemory** — `/workspace/` identity files
- **Compose engine** — per-task output rendering (ADR-130)
- **Feedback distillation** — edits → preferences.md (ADR-117)
- **Self-assessment** — per-agent cognitive files (ADR-128, simplified)
- **Delivery service** — `deliver_from_output_folder()` per task
- **Output gateway** — render service, skills, RuntimeDispatch
- **Platform sync** — unchanged
- **Workspace cleanup cron** — unchanged
- **Agent chat** — user talks to agents 1:1
- **TP/Orchestrator** — chat, primitives, enriched with task management
- **Composer** — workforce health check only (thins significantly)
- **Capability/Runtime registries** — from ADR-130, unchanged

---

## FOUNDATIONS.md changes required

### Axiom 1: Two Layers of Intelligence — revision

Remove PM as domain-cognitive agent example. TP absorbs coordination. Agents are domain experts; tasks are work units. The two layers remain (TP meta-cognitive + Agent domain-cognitive), but the PM sub-layer dissolves.

### Axiom 5: TP's Compositional Capability — revision

Composer/PM separation table deleted. TP directly handles: create agents, create tasks, monitor health, orchestrate multi-agent work, assemble outputs. Composer thins to periodic health-check cron. No PM delegation.

### Axiom 6: Autonomy Is the Product Direction — revision

Autonomous flow updated:
```
1. User describes work → TP creates agent(s) + task(s)
2. Task pulses on cadence → agent gathers context → generates → self-checks → delivers
3. User feedback refines agent expertise + task definition
4. Recursive: each cycle benefits from accumulated agent memory
```

Remove: "Every project gets a PM. No exceptions." Remove: "Agents produce, projects deliver."
Replace with: "Agents are persistent domain experts. Tasks define what work gets done. TP orchestrates."

### Derived Principle 3: Agents are the write path — preserved

Still true. All workspace writes flow through agent execution, not direct user manipulation.

---

## ESSENCE.md changes required

### System Shape — revision

```
1. TP: The Meta-Cognitive Layer (unchanged, absorbs PM/Composer coordination)
2. Agents: The Domain-Cognitive Layer (persistent domain specialists)
3. Tasks: The Work Definition Layer (NEW — objective, cadence, delivery, criteria)
4. Workspace: The Shared Operating Substrate (unchanged)
5. Output Skills: The Execution Layer (unchanged)
```

### User Experience Loop — revision

```
1. Describe your work — connect tools to enrich it
2. System scaffolds the right agents and tasks
3. Tasks run on cadence, agents produce, outputs deliver
4. User reviews, refines, or redirects
5. Agent memory, preferences, and domain knowledge compound
6. Future supervision gets lighter
```

---

## Implementation sequence

### Execution disciplines (enforced throughout)

1. **SINGULAR IMPLEMENTATION** — Delete legacy code when replacing. No dual approaches. No backwards-compat shims. No dormant code. When PM code is removed, it is deleted, not commented out.
2. **DOCS ALONGSIDE CODE** — Every phase updates relevant docs. No phase is "done" until docs match code.
3. **FILESYSTEM IS SOURCE OF TRUTH** — Rich metadata in workspace files (AGENT.md, TASK.md). DB is scheduling index only. No join tables for relationships that can live in files.
4. **CLEAN SLATE** — All existing test data wiped. No migration compatibility needed. Schema can break.
5. **COMMIT PER PHASE** — Each phase produces a working (or at least non-crashing) state. Commit and push after each phase. Conventional commit style with ADR-138 ref.
6. **PROGRESS TRACKING** — TodoWrite updated at start of each phase with sub-tasks. Todos marked complete immediately on finish.
7. **PROMPT CHANGES LOGGED** — Any TP/agent prompt modification gets a CHANGELOG.md entry.
8. **VERIFY AFTER DELETE** — After deleting code, verify imports resolve and the app starts. Don't leave dangling references.

### Phase 1: Clean slate + schema migration
**Goal**: Empty database with new schema. No test data. Tasks table exists.

Steps:
1. Write SQL migration that:
   - TRUNCATEs all data tables (workspace_files, agents, agent_runs, chat_sessions, session_messages, activity_log, render_usage)
   - Creates `tasks` table (thin: id, user_id, slug, mode, status, schedule, next_run_at, last_run_at, timestamps)
   - Drops `schedule`, `next_pulse_at`, `destination`, `mode` columns from `agents` (mode moves to tasks)
   - Updates `agents.role` CHECK constraint (remove `pm`, add `monitor`, `researcher`, `producer`, `operator`)
   - Drops `chat_sessions.project_slug` column
   - Drops `session_messages.thread_agent_id` column
2. Run migration against Supabase
3. Verify schema via psql

**Commit**: `feat(ADR-138): Phase 1 — clean slate + tasks schema`

### Phase 2: Delete project layer (code)
**Goal**: All project/PM code removed. App compiles without project references.

Steps:
1. Delete entire files:
   - `api/services/pm_coordination.py`
   - `api/services/pipeline_executor.py`
   - `api/services/project_registry.py`
   - `api/routes/projects.py`
2. Delete from existing files:
   - `api/services/workspace.py` — delete `ProjectWorkspace` class entirely
   - `api/services/agent_pulse.py` — delete Tier 3 PM coordination
   - `api/services/agent_execution.py` — delete PM decision interpreter, assembly execution, `_write_contribution_to_projects()`, `_maybe_trigger_project_heartbeat()`
   - `api/services/agent_pipeline.py` — delete PM prompt, PM context loading, PM-specific DEFAULT_INSTRUCTIONS
   - `api/services/agent_creation.py` — delete PM-specific seeding paths
   - `api/services/composer.py` — delete `_execute_create_project()`, project Composer actions
   - `api/services/onboarding_bootstrap.py` — gut `maybe_bootstrap_project()` (stub for Phase 3)
   - `api/jobs/unified_scheduler.py` — delete pipeline execution path, PM pulse routing
   - `api/services/agent_framework.py` — delete `pm` from AGENT_TYPES, simplify to 4 archetypes + legacy map
3. Fix all broken imports and references across codebase
4. Delete frontend project files:
   - `web/app/(authenticated)/projects/` — entire directory
   - Remove project imports/references from navigation, API client, types
5. Verify app starts: `cd api && python -c "from main import app"` (or equivalent)
6. Verify frontend compiles: `cd web && pnpm build` (or `pnpm tsc --noEmit`)

**Commit**: `feat(ADR-138): Phase 2 — delete project/PM layer (~5000 lines)`

### Phase 3: Task + Agent infrastructure (backend)
**Goal**: Agents are identity-only. Tasks are work units. Creation and execution work.

Steps:
1. Create `api/services/task_workspace.py` — `TaskWorkspace` class (read/write/list for `/tasks/{slug}/`)
2. Create `api/routes/tasks.py` — CRUD routes (list, get, create, update, delete)
3. Write AGENT.md v2 template (identity-focused: identity, expertise, capabilities, coherence)
4. Write TASK.md v2 template (work-focused: objective, criteria, process with agent slug(s), output spec)
5. Update `api/services/agent_creation.py`:
   - `create_agent()` writes identity-focused AGENT.md (no schedule, no delivery)
   - Seeds `memory/tasks.json` (empty initially)
6. Create `api/services/task_creation.py`:
   - `create_task()` writes TASK.md, creates DB row, updates agent's `memory/tasks.json`
7. Update `api/services/agent_execution.py`:
   - Execution reads objective + criteria from TASK.md (not AGENT.md)
   - Output writes to `/tasks/{slug}/outputs/{date}/` (not `/agents/{slug}/outputs/`)
   - Agent's domain memory still read from `/agents/{slug}/memory/`
8. Update `api/jobs/unified_scheduler.py`:
   - Scheduler queries `tasks` table for `next_run_at <= now`
   - Reads TASK.md to resolve agent slug(s)
   - For single-agent: triggers agent execution with task context
   - For multi-agent: TP imperative orchestration (future, stub for now)
9. Update `api/services/agent_pulse.py`:
   - Tier 1 checks move to task level (cooldown, budget, fresh content)
   - Tier 2 agent self-assessment still agent-level
10. Update delivery: `deliver_from_output_folder()` reads from `/tasks/{slug}/outputs/`

**Commit**: `feat(ADR-138): Phase 3 — task infrastructure + agent identity separation`

### Phase 4: TP enrichment (primitives + prompt)
**Goal**: TP can create agents, create tasks, trigger tasks, and manage the workforce.

Steps:
1. Update `ManageAgent` primitive — writes identity-focused AGENT.md
2. Create `CreateTask` primitive — writes TASK.md, creates DB row, assigns agent
3. Create `TriggerTask` primitive — run a task now with optional injected context
4. Create `AssembleOutputs` primitive — read outputs from multiple tasks, compose unified deliverable
5. Update TP system prompt:
   - Remove project/PM language
   - Add task management language
   - Absorb workforce monitoring (from Composer)
   - Add "agent = who, task = what" framing
6. Update Composer:
   - Remove project creation actions
   - Thin to health-check only (agent health, task staleness)
7. Log all prompt changes in `api/prompts/CHANGELOG.md`

**Commit**: `feat(ADR-138): Phase 4 — TP primitives + prompt (absorbs PM coordination)`

### Phase 5: Frontend
**Goal**: User sees agents (team) and tasks (work). No project references anywhere.

> **Detailed specification**: [ADR-139](ADR-139-workfloor-task-surface-architecture.md) + [SURFACE-ARCHITECTURE.md](../design/SURFACE-ARCHITECTURE.md)

**Three surfaces** (ADR-139 v2):
- `/workfloor` — Home. Output feed (left hero) + Agent roster grid (right). Chat as drawer. Replaces `/orchestrator`.
- `/tasks/{slug}` — Task working page. Latest output (left hero) + Task meta + run trajectory (right). Chat as drawer (task-scoped).
- `/agents/{slug}` — Agent identity page. AGENT.md + memory browser (left) + assigned tasks + actions (right). Read-only reference, no chat.

Steps:
1. Create `/workfloor` page — output feed (left), agent roster 2×3 grid + Tasks/Workspace tabs (right), chat drawer component
2. Create `/tasks/[slug]` page — latest output hero (left), task meta + trajectory + criteria (right), chat drawer (task-scoped)
3. Update `/agents/[slug]` page — identity display, memory browser, assigned tasks, no chat
4. Add `task_slug` column to `chat_sessions` (migration) for task-scoped sessions
5. Update `chat.py` session routing — task-scoped sessions via `surface_context.taskSlug`
6. Update `load_surface_content()` for workfloor, task-detail, agent-identity surface types
7. Update navigation sidebar — Workfloor (home), Activity, Integrations, Settings
8. Fold `/context` into workfloor Workspace tab
9. Update API client (`web/lib/api/client.ts`) — add tasks endpoints, remove projects
10. Update `HOME_ROUTE` in `routes.ts` to `/workfloor`, redirect `/orchestrator` → `/workfloor`
11. Delete `ChatAgent` class and agent_chat mode (dormant, never wired into routing)
12. Verify all routes and links work

**Commit**: `feat(ADR-138): Phase 5 — frontend (workfloor + task surfaces, ADR-139)`

### Phase 6: Documentation alignment
**Goal**: All docs reflect the new architecture. No stale project references.

Steps:
1. **FOUNDATIONS.md v4.0**:
   - Axiom 1: Remove PM as domain-cognitive example. TP absorbs coordination.
   - Axiom 3: Agent identity = archetype + instructions. Remove PM cognitive state.
   - Axiom 5: Delete Composer/PM separation table. TP directly orchestrates.
   - Axiom 6: New autonomous flow (agent + task, no PM). Remove "every project gets PM."
   - Derived principles: update all project references.
2. **ESSENCE.md v11.0**:
   - System Shape: 5 layers (TP, Agents, Tasks, Workspace, Skills)
   - UX Loop: describe work → agents + tasks → deliver → refine → compound
   - Remove all project references
3. **NARRATIVE.md**: Remove project references in product description
4. **workspace-conventions.md v3**: New filesystem layout with `/tasks/{slug}/`
5. **agent-framework.md**: 4 archetypes, remove PM, update taxonomy
6. **api/prompts/CHANGELOG.md**: Document all prompt changes from Phase 4
7. **CLAUDE.md**: Comprehensive update — remove project references, add task model, update file locations, update terminology
8. **Mark superseded ADRs**: Add superseded-by notes to ADRs 120-125, 128-129, 132-137
9. **docs/database/ACCESS.md**: Update schema documentation

**Commit**: `docs(ADR-138): Phase 6 — documentation alignment (FOUNDATIONS v4, ESSENCE v11, CLAUDE.md)`

---

## Cost impact

| Current (project: 3 agents + PM) | Proposed (1 agent + 1 task) |
|---|---|
| Scout: $0.05 | Agent: $0.06 (more tool rounds) |
| Analyst: $0.04 | — |
| Writer: $0.03 | — |
| PM evaluate: $0.001 | Self-check: $0.001 |
| PM compose: $0.05 | Delivery: $0 (direct) |
| **Total: ~$0.17/cycle** | **Total: ~$0.06/cycle** |

65% cost reduction. Better output quality (unified reasoning context). Simpler architecture.

---

## Future considerations

### Multi-workspace (not this ADR)
When the product scales beyond solo founders, the natural extension is multiple workspaces per user ("my consulting firm" vs "my startup"). Each workspace has its own agents, tasks, knowledge base, platform connections. This is the scaling axis — not more agents per task.

### Declarative task chains (not this ADR)
"When Task A completes, trigger Task B with A's output." Stored as task metadata, evaluated by scheduler. Build when a user actually needs recurring chains. For now, TP imperative orchestration is sufficient.

### Agent marketplace (not this ADR)
Pre-configured agent identities that users can "hire." Monitor agents, researcher agents, producer agents — with domain-specific AGENT.md templates. The archetype system makes this natural.
