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

**Universal roles, contextual application** (ADR-176 + ADR-164 + ADR-188): The role taxonomy is a fixed framework primitive — six universal specialist roles (Researcher, Analyst, Writer, Tracker, Designer) + Thinking Partner + platform bots (Slack, Notion, GitHub, Commerce, Trading — activated on platform connection). Which specialists are instantiated and what domains they serve is contextual, determined by TP based on the user's work description. A default roster is scaffolded at signup; TP customizes it during onboarding.

Capability split (ADR-176): accumulation agents (Researcher, Analyst, Writer, Tracker) accumulate knowledge and produce markdown. Production agent (Designer) generates visual assets via RuntimeDispatch. TP orchestrates. No domain ownership baked into agent identity — specialists are assigned to tasks by TP, and tasks read/write context domains.

TP is an agent (ADR-164). It has the same structural shape as specialist agents — row in the agents table, slug (`thinking-partner`), workspace folder (`/agents/thinking-partner/`), can own tasks. What distinguishes TP is its class (`meta-cognitive`) and domain (orchestration itself, no context domain). TP's tasks are back office tasks: agent hygiene, workspace cleanup, future task-freshness review.

Agent roles determine capabilities. Development is knowledge depth (accumulated memory, preferences, observations), not capability breadth. See [agent-framework.md](agent-framework.md).

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

**Task types** (ADR-145, ADR-188): A curated template library of deliverable definitions. TP can select from the library ("Competitive Intelligence Brief") or compose novel task definitions from the user's work description. The template library encodes domain-specific patterns (step instructions, context domain mappings, process configurations); TP can draw from it or compose beyond it. At execution time, the pipeline reads TASK.md — not the registry. See [task-type-orchestration.md](task-type-orchestration.md).

### Workspace (WHERE)

Virtual filesystem over Postgres (`workspace_files` table). Three content areas: identity, brand, and accumulated context domains (`/workspace/context/` — extensible per ADR-151, ADR-188). The directory registry provides curated domain templates (e.g., competitors, market, customers, trading); TP can scaffold these or compose novel domains with custom entity structures from the user's work description. Path conventions are the schema — new capabilities extend paths, not database tables. See [workspace-conventions.md](workspace-conventions.md).

---

## Two Layers of Intelligence, One Agent Substrate (ADR-164)

| Layer | Agent class | Role | Develops |
|-------|-------------|------|----------|
| **Meta-cognitive** | TP (Thinking Partner) — `meta-cognitive` | Creates tasks, assigns teams, monitors health, orchestrates; owns back office tasks | Upward — better judgment about attention allocation |
| **Domain-cognitive** | Specialists (Researcher, Analyst, Writer, Tracker, Designer) + platform bots | Execute tasks, accumulate domain expertise | Inward — deeper knowledge through accumulated work |

**Both layers are expressed through the same agent substrate.** TP is an agent (ADR-164) — same DB row, same task ownership, same pipeline. What distinguishes TP from domain agents is its *class* and *domain* (meta-cognitive, orchestration itself) rather than being "not an agent."

TP has two runtime modes that share one identity:
- **Chat runtime**: user-present conversation via `ThinkingPartnerAgent` class in `api/agents/thinking_partner.py`
- **Task runtime**: scheduler-triggered back office task execution via `task_pipeline._execute_tp_task()`

Domain agents accumulate domain knowledge TP doesn't have. A mature Slack Bot understands team communication patterns; TP orchestrates based on what agents know. See [FOUNDATIONS.md](FOUNDATIONS.md) Axiom 1.

### Back Office Tasks (ADR-164)

Back office tasks are tasks owned by TP. They are scaffolded at workspace init as essential tasks alongside the daily-update heartbeat (ADR-161):

| Task | Executor | Purpose |
|---|---|---|
| `back-office-agent-hygiene` | `services.back_office.agent_hygiene` | Daily: pause underperforming agents (migrated from ADR-156) |
| `back-office-workspace-cleanup` | `services.back_office.workspace_cleanup` | Daily: delete expired ephemeral files (migrated from ADR-119/127) |

Back office tasks run through the same `execute_task()` pipeline as user work. The pipeline dispatches on `agent.role`: if the resolved agent is `thinking_partner`, it hands off to `_execute_tp_task()` which reads the `executor:` directive from the TASK.md process step, imports the module, calls its `run(client, user_id, task_slug)` function, and writes the returned output to the standard outputs folder. Zero LLM cost for deterministic executors. Same substrate as user tasks: TASK.md, run log, output manifest, all visible on `/work`.

No hidden flag. No `task_kind` column. Task ownership (agent.role) is the only distinguisher. Users can see back office tasks alongside user tasks on `/work` and can filter by agent if they want just one or the other.

---

## Execution Flow

### How Work Gets Created

```
User intent (chat or UI)
  → TP decomposes into task definition (from template library or composed novel)
  → ManageTask(action="create", ...) writes TASK.md + tasks DB row
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
  → Read TASK.md + DELIVERABLE.md + steering.md + feedback.md
  → Read task type's page_structure + surface_type from registry
  → Resolve assigned agent(s) from process definition
  → Check work credits (budget gate)
  → SCAFFOLD (first run): resolve structural plan from page_structure
  → ASSEMBLE (pre-gen): query filesystem for scoped directories, discover assets,
      enumerate entities, flag stale sections, build generation brief
  → GENERATE: headless agent produces prose guided by assembly brief
  → ASSEMBLE (post-gen): parse LLM output into section partials,
      resolve asset refs, render section kinds per surface type, compose index.html
  → RENDER: derivative assets — data tables → charts, mermaid → SVGs (mechanical, zero LLM)
  → COMPOSE: apply surface-type arrangement + final HTML styling
  → Save output folder to /tasks/{slug}/outputs/{date}/
  → Deliver to destination (email/Slack/Notion) with delivery channel transform
  → Update agent memory (agent reflection, observations)
  → TP evaluates task output quality against DELIVERABLE.md (evaluation loop)
  → Advance next_run_at
```

The SCAFFOLD → ASSEMBLE → GENERATE → ASSEMBLE → RENDER → COMPOSE chain is the **compose substrate** (ADR-170) — the binding layer between the accumulating filesystem and rendered output. Assembly and revision routing are deterministic Python (zero LLM cost). The compose substrate reads the task type's **surface type** (visual paradigm: report, deck, dashboard, digest, workbook, preview, video) and **section kinds** (typed components: narrative, metric-cards, entity-grid, etc.) to arrange output structurally. See [compose-substrate.md](compose-substrate.md) for the function, [output-surfaces.md](output-surfaces.md) for the vocabulary.

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

**Singular rendering path** (ADR-148, extended by ADR-170): every task output is an HTML output folder. Surface type determines the visual paradigm; export to file formats is derivative. No branching based on agent type, no fallback renderers.

- **Task page**: Shows `index.html` from output folder via sandboxed iframe
- **Email**: Sends HTML with delivery channel transform (inline CSS, 600px max, CID images)
- **Slack**: Posts condensed summary + link to web view
- **Notion**: Writes structured blocks via Notion API
- **Export**: Mechanical conversion — HTML → PDF/PPTX/XLSX/DOCX/MP4 via `yarnnn-render` (on-demand)

Agents produce structured markdown with inline data tables and mermaid diagrams. The compose substrate structures the output per surface type and section kinds. The render service produces derivative assets. Delivery transports the composed output to external destinations with channel-appropriate transforms. See [output-surfaces.md](output-surfaces.md).

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

Primitives are the operations available to agents. Two explicit registries (ADR-146, ADR-168): `CHAT_PRIMITIVES` and `HEADLESS_PRIMITIVES` in `api/services/primitives/registry.py`.

**Canonical reference:** [primitives-matrix.md](primitives-matrix.md) — the full substrate × mode × capability-tag matrix, the target/action enums, the perception channel (working memory), the rename protocol, and the deleted primitives ledger. This section used to duplicate a smaller inline table that drifted through ADR-146 → ADR-168; the matrix doc is the single source of truth going forward.

Current surface (post-ADR-168 Commit 3):
- **Chat mode** (~13 tools): entity-layer verbs + UpdateContext + lifecycle verbs (ManageAgent/Task/Domains) + RepurposeOutput + Clarify + WebSearch + list_integrations + GetSystemState.
- **Headless mode** (~15 static tools + `platform_*` dynamic): entity-layer verbs + file-layer verbs (ReadWorkspace/WriteWorkspace/SearchWorkspace/ListWorkspace/QueryKnowledge) + inter-agent verbs (DiscoverAgents/ReadAgentContext) + lifecycle verbs + WebSearch + GetSystemState.

The surface continues to evolve through ADR-168 Commits 4–5 (rename to `*Entity`/`*File` families; Commit 3 completed the CreateTask fold).

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

## Surface Architecture (ADR-163)

Four top-level destinations, each answering one question:

| Surface | Route | Question | Contents |
|---|---|---|---|
| **Chat** | `/chat` (HOME) | "What should I do? What's happening?" | TP chat + daily briefing dashboard fed by the `daily-update` task |
| **Work** | `/work` | "What is my workforce doing?" | Task list sorted by upcoming + task detail with output, actions, schedule |
| **Agents** | `/agents` | "Who's on my team?" | Agent roster + identity/health card |
| **Context** | `/context` | "What does my workspace know?" | Workspace filesystem browser |

**Mode collapse (surface only):** the schema preserves three task modes (`recurring | goal | reactive`) because the execution layer needs the distinction (ADR-149). The surface shows two labels — `Recurring` and `One-time` (`goal` and `reactive` both map to "One-time"). The `WorkModeBadge` component is the single place modes are rendered on the frontend; `taskModeLabel()` in `web/types/index.ts` is the canonical helper.

**Activity absorbed:** the old `/activity` top-level page is deleted. Per-task activity lives on `/work/{slug}`, per-agent activity on `/agents`, workspace-wide on the Chat briefing dashboard, diagnostic events in Settings → System Status.

**Inference visibility:** inferred content (IDENTITY.md, BRAND.md) is rendered via `InferenceContentView` which parses the `<!-- inference-meta: ... -->` HTML comment from ADR-162 Sub-phase D and renders source provenance captions + gap banners inline.

Full design doc: [SURFACE-ARCHITECTURE.md](../design/SURFACE-ARCHITECTURE.md) (v8).

---

## Feedback, Evaluation, and Reflection (ADR-149)

Three distinct mechanisms drive agent development:

- **Feedback** — User corrections (edits, comments) routed by TP to the appropriate scope: workspace-level (`/workspace/style.md`), agent-level (`/agents/{slug}/memory/`), or task-level (`/tasks/{slug}/feedback.md`).
- **Evaluation** — TP judges task output quality against the DELIVERABLE.md specification. Produces steering directives (`/tasks/{slug}/steering.md`) that guide the next execution cycle.
- **Reflection** — Agent self-assesses fitness and confidence post-run, written to `/agents/{slug}/memory/reflections.md`. Formerly "contributor assessment." Gives the agent a developmental voice independent of external judgment.

---

## Two Commerce Surfaces

YARNNN has two distinct commerce surfaces that must never be conflated:

### Platform Billing (YARNNN → User) — ADR-171, ADR-172

How YARNNN charges users for platform usage. Implemented.

- **Single gate**: `balance_usd`. All LLM calls deduct `cost_usd`. Hard stop at zero.
- **Balance sources**: $3 signup grant, top-ups ($10/$25/$50 via LS one-time orders), Pro subscription ($19/mo or $180/yr = $20 balance reset per cycle)
- **Billing rates**: 2x Anthropic API rates ($6/$30 per MTok Sonnet input/output). Cache discount not passed through.
- **All tier limits dissolved** (ADR-172): no message limits, task limits, source limits, or capability gates. Cost is the only gate.
- **Metering**: Universal `token_usage` table across all 7 LLM call sites. `cost_usd` computed at write time.

### Content Commerce (User → User's Customers) — ADR-183

How users sell content products their agent team produces. Phases 1-3 implemented.

- **Commerce as fourth platform class**: same `platform_connections` pattern as Slack/Notion/GitHub, API key auth
- **Two context domains**: `customers/` (per-customer entities) and `revenue/` (aggregate business metrics)
- **Commerce Bot**: 11th agent (scaffolded on commerce connection, not at signup), owns customer + revenue domains
- **Delivery to subscribers**: tasks can deliver to all active subscribers of a linked commerce product
- **Provider-agnostic**: Lemon Squeezy first. Architecture supports provider swap (Stripe Connect, Paddle) without pipeline changes.

See [commerce-substrate.md](commerce-substrate.md) for the architecture, [docs/features/commerce.md](../features/commerce.md) for user-facing docs.

### Product Health Metrics — ADR-184

Revenue as first-class perception. Proposed. Three-tier metrics hierarchy:

| Tier | What it measures | Source |
|---|---|---|
| **Product** (new) | Revenue, subscribers, churn, growth | `revenue/` + `customers/` domains via Commerce Bot |
| **Task** (exists) | Run history, output quality, deliverable adherence | `/tasks/{slug}/` |
| **Agent** (exists) | Approval rate, confidence, memory depth | `/agents/{slug}/memory/` |

Product health surfaces through existing patterns: daily update enrichment (business snapshot alongside agent activity), TP working memory (compact index gains `## Product Health` section), feedback loop closure (product metrics as quality signal). No new surfaces — revenue is context, not a dashboard. See [ADR-184](../adr/ADR-184-product-health-metrics.md).

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
| Commerce substrate | [commerce-substrate.md](commerce-substrate.md) |

---

## Deep-Dive References

| Topic | Document |
|-------|----------|
| First principles & axioms | [FOUNDATIONS.md](FOUNDATIONS.md) |
| Agent taxonomy & type registry | [agent-framework.md](agent-framework.md) |
| Execution model & trigger taxonomy | [agent-execution-model.md](agent-execution-model.md) |
| Execution loop & accumulation cycle | [execution-loop.md](execution-loop.md) |
| Task type orchestration | [task-type-orchestration.md](task-type-orchestration.md) |
| Workspace filesystem conventions | [workspace-conventions.md](workspace-conventions.md) |
| Output substrate & capabilities | [output-substrate.md](output-substrate.md) |
| Output surfaces (visual paradigms) | [output-surfaces.md](output-surfaces.md) |
| Compose substrate (filesystem→output) | [compose-substrate.md](compose-substrate.md) |
| Commerce substrate | [commerce-substrate.md](commerce-substrate.md) |
| Product health metrics | [ADR-184](../adr/ADR-184-product-health-metrics.md) |
| Platform billing strategy | [docs/monetization/STRATEGY.md](../monetization/STRATEGY.md) |
| Product narrative | [NARRATIVE.md](../NARRATIVE.md) |
| Core identity | [ESSENCE.md](../ESSENCE.md) |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-29 | v1 — Initial creation. Consolidates service topology from CLAUDE.md, execution model from agent-execution-model.md, entity model from FOUNDATIONS.md/ADR-138/ADR-140, primitives from registry.py. Establishes single canonical service description. |
| 2026-03-31 | v1.1 — ADR-153 platform_content sunset. Perception model updated: agents call platform APIs live, no intermediate staging. /platforms/ removed from entity model. Platform sync cron role updated. |
| 2026-04-15 | v1.2 — Revenue Model section rewritten for ADR-171/172 (balance model, tiers dissolved). Added "Two Commerce Surfaces" section covering platform billing vs. content commerce (ADR-183) and product health metrics (ADR-184). Composer reference removed (deleted by ADR-156). Deep-dive references updated. |
| 2026-04-17 | v1.3 — Domain-agnostic framework (ADR-188). Agent roster: "Pre-scaffolded roster" → "Universal roles, contextual application." Task types: "pre-meditated definitions" → "curated template library." Workspace: context domains described as extensible. Execution flow: task creation can be from template or TP-composed. |
