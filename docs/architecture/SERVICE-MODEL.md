# YARNNN Service Model

> **Status**: Canonical
> **Date**: 2026-03-29
> **Scope**: End-to-end service model — how the system works, from user intent to delivered output.
> **Rule**: This is the single document that describes the complete system. Deep-dive docs are linked, not duplicated.

---

## What YARNNN Is

YARNNN is an **autonomous agent platform for recurring knowledge work**. Users describe their work, AI agents are assigned to tasks, and the system produces deliverables on schedule. Over time, each agent accumulates domain knowledge — a tenured agent produces better output than a fresh one.

**The product thesis**: Accumulated attention compounds. Each execution cycle benefits from prior outputs, user feedback, and learned preferences. The system gets smarter the longer it runs.

---

## Entity Model

Three entities, one workspace:

```
WORKSPACE (per user)
├── /workspace/           User context: identity, brand, documents
├── /platforms/           Distilled Slack/Notion content
├── /agents/{slug}/       Agent identity + memory + outputs
└── /tasks/{slug}/        Task definition + outputs + run log
```

### Agents (WHO)

Persistent domain experts with three independent axes:

| Axis | What | Mutability |
|------|------|------------|
| **Identity** | AGENT.md — name, domain, persona | Evolves with use |
| **Capabilities** | Type registry — tools and runtimes available | Fixed at creation |
| **Tasks** | TASK.md assignments — what work to do | Come and go |

**Pre-scaffolded roster** (ADR-140): Every user gets 6 agents at sign-up:
- 4 domain agents: Research, Content, Marketing, CRM
- 2 platform bots: Slack Bot, Notion Bot

Agent types determine capabilities. Development is knowledge depth (accumulated memory, preferences, observations), not capability breadth. See [agent-framework.md](agent-framework.md).

### Tasks (WHAT)

Defined work units with an objective, schedule, and delivery target.

| Field | Purpose |
|-------|---------|
| `objective` | What to produce (deliverable, audience, format, purpose) |
| `mode` | Temporal behavior: `recurring` (indefinite cadence), `goal` (bounded, completes), `reactive` (on-demand/event) |
| `schedule` | When to run: daily, weekly, biweekly, monthly, on-demand |
| `delivery` | Where to send: email, Slack channel, Notion page |
| `process` | Multi-step agent sequence (from task type registry, if applicable) |

Mode is a property of the task, not the agent. A Research Agent can simultaneously have a recurring weekly briefing and a goal-based one-off investigation.

**Task types** (ADR-145): Pre-meditated deliverable definitions. Users select an outcome ("Competitive Intelligence Brief"), and the system resolves it into a deterministic sequence of agent steps. See [task-type-orchestration.md](task-type-orchestration.md).

### Workspace (WHERE)

Virtual filesystem over Postgres (`workspace_files` table). Path conventions are the schema — new capabilities extend paths, not database tables. See [workspace-conventions.md](workspace-conventions.md).

---

## Two Layers of Intelligence

| Layer | Entity | Role | Develops |
|-------|--------|------|----------|
| **Meta-cognitive** | TP (Thinking Partner) | Creates agents, assigns tasks, monitors health, orchestrates | Upward — better judgment about attention allocation |
| **Domain-cognitive** | Agents | Execute tasks, accumulate domain expertise | Inward — deeper knowledge in their domain |

**TP** is the singular orchestrator. It mediates user conversation, creates/adjusts/dissolves agents and tasks, and supervises the workforce. TP is the control plane.

**Agents** are the data plane. They accumulate domain knowledge TP doesn't have. A mature Slack agent understands team communication patterns; TP orchestrates based on what agents know. See [FOUNDATIONS.md](FOUNDATIONS.md) Axiom 1.

---

## Execution Flow

### How Work Gets Created

```
User intent (chat or UI)
  → TP decomposes into task definition
  → CreateTask primitive writes TASK.md + tasks DB row
  → next_run_at calculated from schedule
```

### How Work Gets Executed

Three layers, strictly separated (ADR-141):

**Layer 1 — Mechanical Scheduling** (zero LLM cost)
- Unified scheduler cron runs every 5 minutes
- SQL query: `tasks WHERE next_run_at <= NOW()`
- For each due task: calls `execute_task()`

**Layer 2 — Task Execution** (Sonnet per task, then mechanical render + compose)
```
execute_task(slug)
  → Read TASK.md from workspace
  → Resolve assigned agent(s) from process definition
  → Check work credits (budget gate)
  → Gather context (task-aware KB search by objective)
  → GENERATE: headless agent produces prose + inline data tables + mermaid diagrams
  → RENDER: extract data tables → charts, mermaid → SVGs (mechanical, zero LLM)
  → COMPOSE: enriched markdown + assets → styled HTML per composition mode
  → Save output to /tasks/{slug}/outputs/{date}/
  → Deliver to destination (email/Slack/Notion)
  → Update agent memory (self-assessment, observations)
  → Advance next_run_at
```

**Multi-step process** (task types with `process` field defining multiple agent steps):
```
For each step in process:
  → Resolve agent by type from user's roster
  → Inject prior step output as context (handoff)
  → Generate → save step output
  → Final step = deliverable → deliver
```

**Layer 3 — TP Intelligence** (user-driven)
- Chat mode: responds to user, creates/adjusts tasks
- Composer heartbeat: periodic workforce assessment
- The only component that "thinks about" the system

### How Work Gets Delivered

Delivery targets live in TASK.md. Exporters in `api/integrations/exporters/`:
- **Email**: via Resend API (HTML + optional attachments)
- **Slack**: post to channel via Slack API
- **Notion**: write to page via Notion API

Output is HTML-native (ADR-130). Agents produce structured content, the platform renders visually, PDF/XLSX are mechanical exports.

---

## Deployed Services

5 services on Render.com (Singapore region):

| Service | Type | What It Does |
|---------|------|-------------|
| **yarnnn-api** | Web (FastAPI) | API endpoints, TP chat, OAuth, all user-facing operations |
| **yarnnn-unified-scheduler** | Cron (*/5 min) | Task execution, workspace cleanup, memory extraction, Composer heartbeat |
| **yarnnn-platform-sync** | Cron (*/5 min) | Slack/Notion content sync (tier-gated frequency) |
| **yarnnn-mcp-server** | Web (FastAPI) | MCP protocol for Claude Desktop/Code access |
| **yarnnn-render** | Web (Docker) | Output gateway — PDF, chart, mermaid, xlsx, image rendering |

**Critical shared state**: All services share Supabase (Postgres). `INTEGRATION_ENCRYPTION_KEY` must be on API + both crons. See [CLAUDE.md](/CLAUDE.md) "Render Service Parity" section for full env var matrix.

**Frontend**: Next.js 14 on Vercel. Supabase auth. Communicates exclusively via `/api/*` endpoints.

---

## Primitives (Agent Tools)

Primitives are the operations available to agents. Two explicit registries (ADR-146):

**Chat mode** (14 tools — TP in conversation):
- Discovery: Read, List, Search, Edit, GetSystemState
- External: RefreshPlatformContent, WebSearch, ListIntegrations
- Context: UpdateContext (unified — identity, brand, memory, agent feedback, task feedback)
- Lifecycle: CreateAgent, CreateTask, ManageTask (trigger/update/pause/resume)
- Execution: Execute
- Interaction: Clarify

**Headless mode** (17 tools — background agent execution):
- Discovery: Read, List, Search, GetSystemState
- External: RefreshPlatformContent, WebSearch
- Workspace: ReadWorkspace, WriteWorkspace, SearchWorkspace, QueryKnowledge, ListWorkspace
- Inter-agent: DiscoverAgents, ReadAgentContext
- Lifecycle: CreateAgent, CreateTask, ManageTask
- Output: RuntimeDispatch

See `api/services/primitives/registry.py` for the canonical source.

---

## Perception Model

Four layers of perception feed agent execution (FOUNDATIONS Axiom 2):

1. **External** — Platform sync fills `/platforms/` from Slack and Notion. TTL-based (Slack 14d, Notion 90d).
2. **User-contributed** — Uploaded documents in `/workspace/documents/`. Permanent reference material.
3. **Internal** — Prior task outputs in `/tasks/{slug}/outputs/`. Each run's output feeds the next run's context.
4. **Reflexive** — User feedback (edits, approvals), TP observations (`/workspace/notes.md`, `/workspace/preferences.md`).

The recursive property: external data → agent output → next cycle's context → better output. Accumulated attention compounds.

---

## Revenue Model

- **Chat is free** — TP conversation is the onramp
- **Work is metered** — autonomous task runs consume credits
- **Two tiers**: Free (limited runs/month) and Pro ($19/mo, generous allocation)
- **Two platforms**: Slack and Notion (Gmail/Calendar sunset per ADR-131)

---

## Key Files

| Concern | File |
|---------|------|
| TP (orchestrator) | `api/agents/thinking_partner.py` |
| Task execution | `api/services/task_pipeline.py` |
| Agent types & capabilities | `api/services/agent_framework.py` |
| Task type registry | `api/services/task_types.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| Workspace abstraction | `api/services/workspace.py` |
| Working memory (TP context) | `api/services/working_memory.py` |
| Delivery | `api/services/delivery.py` |
| Scheduler | `api/jobs/unified_scheduler.py` |
| Platform sync | `api/jobs/platform_sync_scheduler.py` |
| Composer (TP workforce assessment) | `api/services/composer.py` |

---

## Deep-Dive References

| Topic | Document |
|-------|----------|
| First principles & axioms | [FOUNDATIONS.md](FOUNDATIONS.md) |
| Agent taxonomy & type registry | [agent-framework.md](agent-framework.md) |
| Execution model & trigger taxonomy | [agent-execution-model.md](agent-execution-model.md) |
| Task type orchestration | [task-type-orchestration.md](task-type-orchestration.md) |
| Workspace filesystem conventions | [workspace-conventions.md](workspace-conventions.md) |
| Output substrate & capabilities | [output-substrate.md](output-substrate.md) |
| Product narrative | [NARRATIVE.md](../NARRATIVE.md) |
| Core identity | [ESSENCE.md](../ESSENCE.md) |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-29 | v1 — Initial creation. Consolidates service topology from CLAUDE.md, execution model from agent-execution-model.md, entity model from FOUNDATIONS.md/ADR-138/ADR-140, primitives from registry.py. Establishes single canonical service description. |
