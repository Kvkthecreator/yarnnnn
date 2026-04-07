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
│   └── /workspace/context/  Accumulated context domains (competitors, market, relationships, etc.)
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

Defined work units with an objective, schedule, and delivery target. Two charter files:

- **TASK.md** — operational charter: objective, mode, schedule, delivery, process steps.
- **DELIVERABLE.md** — output specification: what the final artifact should look like (format, structure, quality criteria, audience). The north star for generation and evaluation.

| Field | Purpose |
|-------|---------|
| `objective` | What to produce (deliverable, audience, format, purpose) |
| `mode` | Temporal behavior: `recurring` (indefinite cadence), `goal` (bounded, completes), `reactive` (on-demand/event) |
| `schedule` | When to run: daily, weekly, biweekly, monthly, on-demand |
| `delivery` | Where to send: email, Slack channel, Notion page |
| `process` | Multi-step agent sequence (from task type registry, if applicable) |

Mode is a property of the task, not the agent. A Research Agent can simultaneously have a recurring weekly briefing and a goal-based one-off investigation. Mode also signals TP's management posture — recurring tasks get periodic review, goal tasks get completion tracking, reactive tasks get trigger monitoring.

**Task types** (ADR-145): Pre-meditated deliverable definitions. Users select an outcome ("Competitive Intelligence Brief"), and the system resolves it into a deterministic sequence of agent steps. See [task-type-orchestration.md](task-type-orchestration.md).

### Workspace (WHERE)

Virtual filesystem over Postgres (`workspace_files` table). Three content areas: identity, brand, and accumulated context domains (`/workspace/context/` — competitors, market, relationships, etc. per ADR-151). Path conventions are the schema — new capabilities extend paths, not database tables. See [workspace-conventions.md](workspace-conventions.md).

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
  → Read TASK.md + DELIVERABLE.md + steering.md + feedback.md from workspace
  → Resolve assigned agent(s) from process definition
  → Check work credits (budget gate)
  → Gather context (task-aware KB search by objective)
  → GENERATE: headless agent produces prose + inline data tables + mermaid diagrams
  → RENDER: extract data tables → charts, mermaid → SVGs (mechanical, zero LLM)
  → COMPOSE: enriched markdown + assets → styled HTML per composition mode
  → Save output to /tasks/{slug}/outputs/{date}/
  → Deliver to destination (email/Slack/Notion)
  → Update agent memory (agent reflection, observations)
  → TP evaluates task output quality against DELIVERABLE.md (evaluation loop)
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

### The Heartbeat Artifact (ADR-161)

Every workspace is scaffolded at signup with exactly one default task: `daily-update`. This task is **essential** — it cannot be archived, cannot be auto-paused, and exists from day one regardless of user engagement.

The daily-update is the **user-facing manifestation of the system being alive**. It is the only task that arrives in the user's inbox by default. It runs every morning at 09:00 UTC. Its content scales with workspace maturity:

- **Empty workspace** (no other active tasks, no context entities): a deterministic template (no LLM cost) — "Your workforce is here. Tell me what matters to start." with a CTA back to chat. ~$0/run.
- **Sparse workspace** (some context, few runs): a "quiet day" digest framing what little there is. ~$0.03/run.
- **Active workspace**: a full operational digest reading run logs across all active tasks. ~$0.05–0.15/run.

Three layers of heartbeat exist:

| Layer | Mechanism | What it does | Independence |
|---|---|---|---|
| **Infrastructure** | Render cron, every 5 min | Polls tasks, fires due ones | Plumbing — user never sees |
| **Daily-update task** | One row in tasks, daily cadence | Produces user-facing artifact | Standard task in standard pipeline |
| **User experiential** | Email landing at 9am | The user knows the system is alive | Emergent from above |

These are technically independent but conceptually fused. The daily-update is *not* a special code path — it executes through `task_pipeline.execute_task()` like any other task. It is special only in metadata (`essential=true`) and in having an empty-state branch that short-circuits the LLM call when there is genuinely nothing to summarize.

This is the floor that prevents dormant signups from going silent. See ADR-161 for the full rationale.

### How Output Gets Displayed and Delivered

**Singular rendering path** (ADR-148): every task output is composed HTML. No branching based on agent type, no fallback renderers.

- **Task page**: Always shows `output.html` via sandboxed iframe
- **Email**: Always sends composed HTML via Resend API
- **Slack**: Posts condensed summary + link to full output
- **Notion**: Writes structured page via Notion API
- **PDF/XLSX**: Mechanical exports derived from composed HTML (future)

Agents produce structured markdown with inline data tables and mermaid diagrams. The platform renders assets and composes HTML. Delivery transports the composed output to external destinations.

---

## Deployed Services

5 services on Render.com (Singapore region):

| Service | Type | What It Does |
|---------|------|-------------|
| **yarnnn-api** | Web (FastAPI) | API endpoints, TP chat, OAuth, all user-facing operations |
| **yarnnn-unified-scheduler** | Cron (*/5 min) | Task execution, workspace cleanup, memory extraction, Composer heartbeat |
| **yarnnn-platform-sync** | Cron (*/5 min) | Platform connection health checks, OAuth token refresh (ADR-153: bulk content sync sunset) |
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
- Lifecycle: ManageAgent (create/update/pause/resume/archive), CreateTask, ManageTask (trigger/update/pause/resume/evaluate/steer/complete), ManageDomains (scaffold/add/remove/list)
- Execution: Execute
- Interaction: Clarify

**Headless mode** (17 tools — background agent execution):
- Discovery: Read, List, Search, GetSystemState
- External: WebSearch
- Workspace: ReadWorkspace, WriteWorkspace, SearchWorkspace, QueryKnowledge, ListWorkspace
- Inter-agent: DiscoverAgents, ReadAgentContext
- Lifecycle: ManageAgent, CreateTask, ManageTask, ManageDomains

See `api/services/primitives/registry.py` for the canonical source.

---

## Perception Model

Four layers of perception feed agent execution (FOUNDATIONS Axiom 2):

1. **External** — Agents call platform APIs (Slack, Notion, GitHub) live during task execution. Signals flow into `/workspace/context/` domains. Platform connections provide auth infrastructure; there is no intermediate staging table (ADR-153).
2. **User-contributed** — Uploaded documents in `/workspace/uploads/`. Permanent reference material.
3. **Internal** — Prior task outputs in `/tasks/{slug}/outputs/` + accumulated context in `/workspace/context/`. Each run's output feeds the next run's context.
4. **Reflexive** — User feedback (edits, approvals), TP observations (`/workspace/notes.md`, `/workspace/style.md`).

The recursive property: external data → agent output → next cycle's context → better output. Accumulated attention compounds.

### Inference Hardening (ADR-162)

Inference is the upstream lever for everything downstream — bad inference at IDENTITY.md cascades into wrong domain entities, expensive bootstrap research, and mediocre outputs. ADR-162 makes inference **measurable**, **iterative**, **proactive on uploads**, and **traceable**:

- **Measurable**: `api/eval/run_inference_eval.py` runs a fixture set (10 fixtures) through `infer_shared_context()` and scores entity recall, section completeness, anti-fabrication, length, and richness. Run before any prompt change to detect regressions. See [inference-evaluation.md](inference-evaluation.md).

- **Iterative**: After every successful inference, `detect_inference_gaps()` (pure-Python, zero LLM cost) examines the output for missing-but-load-bearing fields. The structured gap report is returned to TP, which issues at most one targeted Clarify per inference cycle when the most important gap is high-severity. Deterministic by design — no shadow LLM judgment, preserves single-intelligence-layer (ADR-156).

- **Proactive on uploads**: `working_memory.py` surfaces documents uploaded in the last 7 days as a "Recent uploads" entry in TP's compact index. TP sees this on every chat turn and proactively offers to process the upload via `UpdateContext`, with user consent. Filesystem-as-notification — no separate notification table.

- **Traceable**: Every inference output ends with a `<!-- inference-meta: {...} -->` HTML comment recording target, timestamp, and source provenance (chat text, document filenames, URLs). Frontend can parse this to show "Last updated from: 2 documents + 1 URL · 2h ago" captions on the Identity/Brand surfaces.

These four pieces compound: measurement validates that gap detection is helping; gap detection makes thin inference recoverable; upload surfacing puts the richest source material in front of TP automatically; traceability lets users see and trust the result.

---

## Feedback, Evaluation, and Reflection (ADR-149)

Three distinct mechanisms drive agent development:

- **Feedback** — User corrections (edits, comments) routed by TP to the appropriate scope: workspace-level (`/workspace/style.md`), agent-level (`/agents/{slug}/memory/`), or task-level (`/tasks/{slug}/feedback.md`).
- **Evaluation** — TP judges task output quality against the DELIVERABLE.md specification. Produces steering directives (`/tasks/{slug}/steering.md`) that guide the next execution cycle.
- **Reflection** — Agent self-assesses fitness and confidence post-run, written to `/agents/{slug}/memory/reflections.md`. Formerly "contributor assessment." Gives the agent a developmental voice independent of external judgment.

---

## Revenue Model

- **Chat is free** — TP conversation is the onramp
- **Work is metered** — autonomous task runs consume credits
- **Two tiers**: Free (limited runs/month) and Pro ($19/mo, generous allocation)
- **Three platforms**: Slack, Notion, and GitHub (Gmail/Calendar sunset per ADR-131, GitHub added per ADR-147)

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
| 2026-03-31 | v1.1 — ADR-153 platform_content sunset. Perception model updated: agents call platform APIs live, no intermediate staging. /platforms/ removed from entity model. Platform sync cron role updated. |
