# YARNNN Service Model

> **Status**: Canonical
> **Date**: 2026-03-29 (v1.6 revision 2026-04-20; taxonomy/autonomy hardening amended 2026-04-24; invocation/narrative amendment 2026-04-25; v1.7 OS framing canonized 2026-04-27)
> **Scope**: End-to-end service model — how the system works, from user intent to delivered output.
> **Rule**: This is the single document that describes the complete system. Deep-dive docs are linked, not duplicated.

> **Current canon note (2026-04-27):** ADR-222 canonizes the agent-native operating system framing. The substrate is the kernel; the primitive matrix is the syscall ABI; the chat agent is the shell; workspaces are userspaces; programs are applications; program bundles are `.app`-equivalents; a compositor layer (forthcoming) reads program-shipped composition manifests against substrate to render the cockpit. See [FOUNDATIONS Principle 16](FOUNDATIONS.md), [GLOSSARY "Operating System Framing"](GLOSSARY.md), and [docs/programs/](../programs/README.md) for canonical artifacts. Prior canon notes (ADR-216 YARNNN reclassification, ADR-217 AUTONOMY.md relocation) remain in force.

---

## What YARNNN Is

YARNNN is an **autonomous agent platform for recurring knowledge work — operated from a cockpit, not consumed as reports.** Users describe their work, AI agents are assigned to tasks, and the system produces work on schedule. The operator works *inside* YARNNN — reviewing performance, deciding on proposals, authoring and supervising the team, auditing past decisions. External distribution (email to stakeholders, Slack posts, PDF exports) is a **derivative Channel**, not the primary output.

**The product thesis**: Accumulated attention compounds. Each execution cycle benefits from prior outputs, user feedback, and learned preferences. The system gets smarter the longer it runs. The cockpit is where the operator sees and steers that compounding in real time.

---

## Architectural Preamble: Six Dimensions + Filesystem Substrate (FOUNDATIONS v6.0)

Before reading the rest of this document, internalize two axiomatic frames. Everything else in the service model derives from them.

### Frame 1 — The Six Dimensions (Axiom 0)

Every mechanic in YARNNN occupies a cell in six orthogonal dimensions. These are the irreducible questions the system must answer:

| Dimension | Interrogative | Decides |
|---|---|---|
| **Substrate** | What | What persists between invocations |
| **Identity** | Who | Which cognitive layer acts or authors |
| **Purpose** | Why | What intent drives the work |
| **Trigger** | When | What invokes execution (periodic / reactive / addressed) |
| **Mechanism** | How | By what means — spectrum from deterministic code to LLM judgment |
| **Channel** | Where | To what location or surface output is addressed |

When reading any section of this document, ask: which dimension(s) is this mechanic occupying? Most mechanics occupy one. Some deliberately cross-cut (e.g., compose substrate couples Mechanism + Channel per ADR-148) — these cross-cuts are justified, not accidental. A mechanic that spans dimensions without justification is a design error. See [FOUNDATIONS.md Axiom 0](FOUNDATIONS.md).

### Frame 2 — Filesystem Is the Substrate (Axiom 1)

The Substrate dimension has a single canonical home: **the filesystem holds all semantic state; every other layer is stateless computation over it.**

Scheduler, task pipeline, compose substrate, Reviewer, reconciler, render service — each reads the filesystem, acts, writes the filesystem, and terminates. None of them retain state of their own across invocations. Accumulation happens in files, cycle over cycle. This is what makes the recursive property (Axiom 7) work, and what made every prior substrate collapse (platform_content, projects, Composer, user_memory, action_outcomes) possible.

The database is narrowly permitted for four row kinds only:

1. **Scheduling indexes** — what needs to run, when (`tasks`, `agents` — lean pointers at TASK.md / AGENT.md).
2. **Neutral audit ledgers** — what happened for billing / debugging (`agent_runs`, `token_usage`, `activity_log`, `render_usage`). No semantic content.
3. **Credentials / auth** — encrypted secrets the filesystem cannot hold safely (`platform_connections`, `mcp_oauth_*`).
4. **Ephemeral queues / inboxes** — TTL-bounded items awaiting action (`action_proposals`). The row disappears after acceptance, rejection, or expiration.

Anything else belongs in the filesystem. When you read about "the scheduler reads TASK.md" or "the reconciler writes `_performance.md`" below, that is Axiom 1 in operation — not incidental design choice. See [FOUNDATIONS.md Axiom 1](FOUNDATIONS.md).

### Frame 3 — The Cockpit (ADR-198 v2)

The operator works *inside* YARNNN. The front-end model is a **cockpit**, not a report factory. Five Purpose-labeled destinations + ambient YARNNN rail:

| Destination | Purpose | Primary substrate read |
|---|---|---|
| **Overview** | "What's going on? What needs me?" | Temporal + Performance snapshot + Queue + Reviewer alerts |
| **Team** | "Let me check on my agents." | `/agents/*` — roster + identity + health |
| **Work** | "Let me check the work." | `/tasks/*` — schedules, status, outputs |
| **Context** | "What does my workspace know?" | `/workspace/context/*` + `/workspace/uploads/*` |
| **Review** | "Who decided what, why?" | `/workspace/review/*` + task `feedback.md` |

**YARNNN is ambient, not a destination.** A persistent rail is available on every surface; `/chat` is the expanded-focus form of the narrative — the single operator-facing log of every invocation the system performed (FOUNDATIONS Axiom 9). Operators don't travel *to* YARNNN; YARNNN is *with* them, and the narrative is where they return to see what happened while they weren't watching.

**Team and Work are peer destinations.** Agents and tasks are many-to-many — one agent runs several tasks, one complex task may involve several agents. "Check my agents" and "check the work" are two distinct operator Purposes (identity vs activity), so they get two destinations with cross-links between detail routes.

**External Channels are derivative, not primary.** Email (daily-update, weekly reports), Slack cross-posts, PDF exports — all are derivatives of work the operator reviewed in the cockpit. Notifications to external Channels are **expository pointers** (legible summary + deep-link back to cockpit), not replacement UX. See [ADR-198](../adr/ADR-198-surface-archetypes.md) for the full service-model pivot and the five archetype patterns (Document / Dashboard / Queue / Briefing / Stream) that compose inside destinations.

Implication: `produces_deliverable` task types (ADR-166) output a **cockpit-consumable surface**, not an emailable document as the primary artifact. The task output folder (`/tasks/{slug}/outputs/`) remains substrate per Axiom 1 — what changes is the operator's consumption Channel, not the filesystem. External distribution runs as a post-compose derivative per ADR-185 when a task's `## Delivery` names external recipients.

### Frame 4 — Invocation as the Atom, Narrative as the Log (Axiom 9)

One cycle of the six dimensions is an **invocation** — the atom of action. One actor fires once, applies some mechanism, reads and writes substrate, emits to some channel, terminates. Every actor class in YARNNN — persona-bearing Agents (Reviewer, user-authored domain Agents), the orchestration chat surface (YARNNN), orchestration capability bundles (production roles, platform integrations), and external callers (foreign LLMs via MCP) — emits invocations of the same shape. Only the Identity slot rotates.

Every invocation surfaces in one **narrative** — the chat-shaped operator-facing log of everything the system did. Ordered by time, attributed by Identity, filterable by Agent or task-nameplate. The narrative is not "the chat feature"; it is the Axiom 6 Channel that closes Derived Principle 12 (Channel legibility gates autonomy). The operator's own messages are one thread among many.

**Tasks are legibility wrappers, not parallel substrates.** A task is a nameplate + pulse + contract attached to a category of recurring invocations. `/work` is the narrative filtered by task slug — the data substrate is unchanged from ADR-138; the mental model sharpens. Inline actions are invocations without a nameplate; the inline-to-task transition (attach a nameplate + pulse) is gradient and reversible.

Deep dive: [invocation-and-narrative.md](invocation-and-narrative.md). ADR-219 (proposed) scopes implementation of the narrative-storage and /work-as-filter commitments.

### Frame 5 — Agent-Native Operating System Architecture (FOUNDATIONS Principle 16, ADR-222)

YARNNN is canonized as an agent-native operating system. The framing is literal — every box in OS architecture has a corresponding YARNNN artifact. The OS layering is what makes vertical specialization possible without sacrificing the agnostic substrate, and what makes the kernel boundary structurally enforceable.

| OS layer | YARNNN equivalent | Status |
|---|---|---|
| **Kernel** | Substrate primitives + axioms + filesystem + privileged daemons (Reviewer, back-office tasks) | Shipped |
| **Filesystem** | `workspace_files` + ADR-209 authored substrate | Shipped |
| **Syscall ABI** | The primitive matrix (ADR-168) | Shipped |
| **Shell** | YARNNN chat agent (`api/agents/yarnnn.py`) — application code, not kernel | Shipped (per ADR-205) |
| **Init system** | `workspace_init.py` | Shipped |
| **Application** | A program (alpha-trader is the first active program; alpha-prediction + alpha-defi are reference SPECs; alpha-commerce is deferred — homes shipped commerce artifacts) | Shipped via ADR-222 + ADR-223; 4 bundles in repo |
| **Application bundle** | Program bundle at `docs/programs/{program}/` — `MANIFEST.yaml` + `README.md` + `SURFACES.yaml` + `reference-workspace/` | Spec landed via [ADR-223](../adr/ADR-223-program-bundle-specification.md); kernel/program boundary enforced in code via [ADR-224](../adr/ADR-224-kernel-program-boundary-refactor.md) (bundle_reader.py + test gate) |
| **Compositor / window manager** | The composition layer — FE/API infrastructure that resolves a program's composition manifest against substrate paths | Phase 1+2 shipped via [ADR-225](../adr/ADR-225-compositor-layer.md) — `GET /api/programs/surfaces` API, `web/lib/compositor/` FE module, `MiddleResolver` replaces hardcoded KindMiddle switch, `web/components/library/` initial component set |
| **Userspace** | An operator's `/workspace/` | Shipped |
| **Workspace overlay** | Operator-authored `/workspace/SURFACES.yaml` overrides of program defaults | **Not yet built** |
| **System component library** | `web/components/library/` — universal building blocks (PerformanceSnapshot, PositionsTable, RiskBudgetGauge, TradingProposalQueue, MiddleResolver, BundleBanner, README convention) | Convention shipped via [ADR-225](../adr/ADR-225-compositor-layer.md) Phase 2; library grows additively as bundles surface new components |

The framing dissolves "workspace type / workspace mode" as housing for vertical specialization: workspaces don't have types; they run programs; the program declaration is the implicit type; specialization happens at the compositor (a separate architectural layer), not the kernel. Adding a program is purely additive — a new bundle, possibly new system component library entries, no kernel touch.

Deep dive: [ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md). Implementation roadmap: [os-framing-implementation-roadmap.md](os-framing-implementation-roadmap.md).

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

### Persona-bearing Agents (WHO)

Persistent judgment-bearing entities with three independent axes:

| Axis | What | Mutability |
|------|------|------------|
| **Identity** | AGENT.md — name, domain, persona | Evolves with use |
| **Capabilities** | Type registry — tools and runtimes available | Fixed at creation |
| **Tasks** | TASK.md assignments — what work to do | Come and go |

Current persona-bearing Agents:
- **Reviewer** — the sole systemic persona-bearing Agent today; independent judgment seat at `/workspace/review/`, reading shared delegation from `/workspace/context/_shared/AUTONOMY.md`
- **User-authored domain Agents** — zero-to-many instance Agents under `/agents/{slug}/`
- **Future judgment archetypes** — Auditor, Advocate, Custodian, etc.

### Orchestration (HOW work is routed)

The orchestration layer includes:
- **YARNNN** — the platform-authored chat surface the operator addresses
- **The Orchestrator** — task pipeline, dispatch routing, team composition logic, capability gating
- **Production roles** — Researcher, Analyst, Writer, Tracker, Designer, Reporting
- **Platform integrations** — Slack, Notion, GitHub, Commerce, Trading

Production roles and integrations are capability bundles, not Agents. They do not hold standing intent; they are dispatched under task and workspace constraints. See [orchestration.md](orchestration.md).

### Tasks (WHAT)

A task is a **nameplate + pulse + contract** (FOUNDATIONS Axiom 9 Clause C) attached to a category of recurring, goal-bounded, or reactive invocations. Two charter files carry the task's contract:

- **TASK.md** — operational charter + nameplate: objective, mode, schedule (the pulse), delivery, process steps.
- **DELIVERABLE.md** — output specification: what the final artifact should look like (format, structure, quality criteria, audience). The north star for generation and evaluation.

A task does not create a parallel substrate. Its invocations write to `/tasks/{slug}/outputs/`, update context domains, and emit narrative entries tagged with the task slug. `/work` is the narrative filtered by those slugs — not a separate `agent_runs` log. Inline actions (operator asks "pull today's revenue" once) are invocations without a task nameplate; the inline-to-task transition is a nameplate-attach operation, reversible.

| Field | Purpose |
|-------|---------|
| `objective` | What to produce (deliverable, audience, format, purpose) |
| `mode` | Temporal behavior: `recurring` (indefinite cadence), `goal` (bounded, completes), `reactive` (on-demand/event) |
| `schedule` | When to run: daily, weekly, biweekly, monthly, on-demand |
| `delivery` | Where to send: email, Slack channel, Notion page |
| `process` | Multi-step agent sequence (from task type registry, if applicable) |

Mode is a property of the task, not the Agent. A Research Agent can simultaneously have a recurring weekly briefing and a goal-based one-off investigation. Mode also signals YARNNN's management posture — recurring tasks get periodic review, goal tasks get completion tracking, reactive tasks get trigger monitoring.

**Task types** (ADR-145, ADR-188): A curated template library of deliverable definitions. YARNNN can select from the library ("Competitive Intelligence Brief") or compose novel task definitions from the user's work description. The template library encodes domain-specific patterns (step instructions, context domain mappings, process configurations); YARNNN can draw from it or compose beyond it. At execution time, the pipeline reads TASK.md — not the registry. See [task-type-orchestration.md](task-type-orchestration.md).

### Workspace (WHERE)

Virtual filesystem over Postgres (`workspace_files` table). Three content areas: identity, brand, and accumulated context domains (`/workspace/context/` — extensible per ADR-151, ADR-188). The directory registry provides curated domain templates (e.g., competitors, market, customers, trading); YARNNN can scaffold these or compose novel domains with custom entity structures from the user's work description. Path conventions are the schema — new capabilities extend paths, not database tables. See [workspace-conventions.md](workspace-conventions.md).

---

## Orchestration + Judgment over One Filesystem Substrate

| Class | Entity | Scope | Role | Develops |
|-------|--------|-------|------|----------|
| **Orchestration surface** | YARNNN | Workspace-level | Conversational surface of the orchestrator; drafts work, routes updates, keeps the system legible | Operational awareness in `/workspace/memory/` |
| **Orchestration capability bundles** | Production roles + platform integrations | Task / integration-level | Execute production work under dispatch and permission gates | Capability catalog evolves; no persona-bearing development axis |
| **Instance judgment Agents** | User-authored domain Agents | Domain-level | Execute domain work, accumulate expertise, represent operator intent in a domain | Inward — deeper knowledge through accumulated work in their domain |
| **Systemic judgment Agent** | Reviewer (human user / AI / impersonation — interchangeable seat) | Proposal-level (structurally separate) | Independent judgment on proposed writes; audit trail author | Through calibration against `_performance.md` |

**All four classes share one substrate — the filesystem.** None retains state of its own across invocations. YARNNN, production roles, domain Agents, and Reviewer all read `/workspace/`, `/agents/`, `/tasks/`, and (for Reviewer) `/workspace/review/`, act, write back, and terminate.

YARNNN is the orchestration chat surface. It may retain a row in the `agents` table for pragmatic continuity, but current canon treats that row as implementation substrate, not classification.

**The Reviewer is the structurally separate judgment seat** (ADR-194, amended by ADR-217). Where YARNNN composes the future (what Agents to create, what tasks to scaffold), the Reviewer applies independent judgment to specific proposed writes. The separation is load-bearing: YARNNN emits many autonomous proposals, and having YARNNN review its own proposals is a conflict of interest. Because the Reviewer seat is structurally separate, a human user and an AI system fill it interchangeably without architectural change (FOUNDATIONS Derived Principle 14: *Roles persist; occupants rotate*). Reviewer state lives in `/workspace/review/` as six seat files, with delegation read from shared `/workspace/context/_shared/AUTONOMY.md`.

YARNNN has two runtimes that share one orchestration surface:
- **Chat runtime**: user-present conversation via `YarnnnAgent` class in `api/agents/yarnnn.py` (ADR-189)
- **Task runtime**: scheduler-triggered back office task execution via `task_pipeline._execute_tp_task()`

Domain Agents accumulate domain knowledge YARNNN does not have. Production roles and platform integrations do not accumulate standing identity; they execute against the current substrate. See [FOUNDATIONS.md](FOUNDATIONS.md) Axiom 1.

### Back Office Tasks (ADR-164)

Back office tasks are tasks owned by YARNNN. They are scaffolded at workspace init as essential tasks alongside the daily-update heartbeat (ADR-161):

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
  → YARNNN decomposes into task definition (from template library or composed novel)
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
  → YARNNN evaluates task output quality against DELIVERABLE.md (evaluation loop)
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

**Layer 3 — YARNNN Intelligence** (user-driven)
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

4 services on Render.com (Singapore region). Per Axiom 0, each service is stateless — it reads the filesystem (via Supabase `workspace_files`) + the four permitted DB row kinds, acts, writes back, and terminates. No service holds in-memory state across invocations.

| Service | Type | What It Does |
|---------|------|-------------|
| **yarnnn-api** | Web (FastAPI) | API endpoints, YARNNN chat, OAuth, all user-facing operations |
| **yarnnn-unified-scheduler** | Cron (*/5 min) | Task execution, workspace cleanup, back-office task dispatch, outcome reconciliation |
| **yarnnn-mcp-server** | Web (FastAPI) | MCP protocol for Claude Desktop/Code/foreign LLMs (ADR-169) |
| **yarnnn-render** | Web (Docker) | Output gateway — PDF, chart, mermaid, xlsx, image rendering (ADR-118) |

**yarnnn-platform-sync was removed** (ADR-153, 2026-04-01) — platform_content sunset; platform data now flows through tracking tasks into `/workspace/context/` domains during task execution. OAuth token lifecycle handled inline by the task pipeline.

**Critical shared state**: All services share Supabase (Postgres). `INTEGRATION_ENCRYPTION_KEY` must be on API + scheduler. See [CLAUDE.md](/CLAUDE.md) "Render Service Parity" section for full env var matrix.

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
4. **Reflexive** — User feedback (edits, approvals), YARNNN observations (`/workspace/notes.md`, `/workspace/style.md`).

The recursive property: external data → agent output → next cycle's context → better output. Accumulated attention compounds.

### Inference Hardening (ADR-162)

Inference is the upstream lever for everything downstream — bad inference at IDENTITY.md cascades into wrong domain entities, expensive bootstrap research, and mediocre outputs. ADR-162 makes inference **measurable**, **iterative**, **proactive on uploads**, and **traceable**:

- **Measurable**: `api/eval/run_inference_eval.py` runs a fixture set (10 fixtures) through `infer_shared_context()` and scores entity recall, section completeness, anti-fabrication, length, and richness. Run before any prompt change to detect regressions. See [inference-evaluation.md](inference-evaluation.md).

- **Iterative**: After every successful inference, `detect_inference_gaps()` (pure-Python, zero LLM cost) examines the output for missing-but-load-bearing fields. The structured gap report is returned to YARNNN, which issues at most one targeted Clarify per inference cycle when the most important gap is high-severity. Deterministic by design — no shadow LLM judgment, preserves single-intelligence-layer (ADR-156).

- **Proactive on uploads**: `working_memory.py` surfaces documents uploaded in the last 7 days as a "Recent uploads" entry in YARNNN's compact index. YARNNN sees this on every chat turn and proactively offers to process the upload via `UpdateContext`, with user consent. Filesystem-as-notification — no separate notification table.

- **Traceable**: Every inference output ends with a `<!-- inference-meta: {...} -->` HTML comment recording target, timestamp, and source provenance (chat text, document filenames, URLs). Frontend can parse this to show "Last updated from: 2 documents + 1 URL · 2h ago" captions on the Identity/Brand surfaces.

These four pieces compound: measurement validates that gap detection is helping; gap detection makes thin inference recoverable; upload surfacing puts the richest source material in front of YARNNN automatically; traceability lets users see and trust the result.

---

## Surface Architecture (ADR-198 v2 — supersedes ADR-163)

Five Purpose-labeled destinations + ambient YARNNN rail. The nav organizes by operator *Purpose*, not by Substrate. Chat is ambient (always-present rail + dedicated expanded form), not a destination.

| Surface | Route | Question | Contents |
|---|---|---|---|
| **Overview** | `/overview` (HOME) | "What's going on? What needs me?" | Temporal (since-last-look) + Performance snapshot + Queue (pending proposals) + Reviewer alerts |
| **Team** | `/team` | "Let me check on my agents." | Agent roster + identity/health card + per-agent detail (tasks owned, memory excerpts, reflections) |
| **Work** | `/work` | "Let me check the work." | Task list filterable by `output_kind` / agent / status / schedule; task detail with output, schedule, feedback, run log |
| **Context** | `/context` | "What does my workspace know?" | Workspace filesystem browser — domains, entities, uploads, source provenance |
| **Review** | `/review` | "Who decided what, why?" | Reviewer identity + principles + decisions audit trail (impersonation chrome when active) |

**Ambient YARNNN rail** on every surface. `/chat` is the expanded-focus form of the rail; it is not a primary nav destination. Surface-aware prompt profiles (ADR-186) flow surface metadata into YARNNN's prompt automatically.

**Archetype patterns inside destinations.** Each destination composes from five Channel-archetype patterns: **Document** (composed output files), **Dashboard** (live substrate slice, no action affordances), **Queue** (pending actionable items with approve/reject), **Briefing** (periodic summary with pointers, not duplication), **Stream** (append-only chronological log). See ADR-198 §3 for the full archetype invariants.

**External Channels are derivative.** Daily-update email, weekly-report emails, Slack cross-posts, PDF exports all flow from cockpit surfaces via post-compose distribution per ADR-185. Alerts (push/SMS) are pointer-notifications into the cockpit, not replacement UX.

**Mode collapse (surface only):** the schema preserves three task modes (`recurring | goal | reactive`) because the execution layer needs the distinction (ADR-149). The surface shows two labels — `Recurring` and `One-time` (`goal` and `reactive` both map to "One-time"). The `WorkModeBadge` component is the single place modes are rendered on the frontend; `taskModeLabel()` in `web/types/index.ts` is the canonical helper.

**Activity absorbed:** the old `/activity` top-level page is deleted. Per-task activity lives in Work task-detail; per-agent activity on agent-detail within Team; workspace-wide on Overview; diagnostic events in Settings → System Status.

**Inference visibility:** inferred content (IDENTITY.md, BRAND.md) is rendered via `InferenceContentView` which parses the `<!-- inference-meta: ... -->` HTML comment from ADR-162 Sub-phase D and renders source provenance captions + gap banners inline.

Full design doc: [SURFACE-CONTRACTS.md](../design/SURFACE-CONTRACTS.md) (ADR-215 — per-tab contracts + CRUD matrix).

---

## Feedback, Evaluation, and Reflection (ADR-149)

Three distinct mechanisms drive agent development:

- **Feedback** — User corrections (edits, comments) routed by YARNNN to the appropriate scope: workspace-level (`/workspace/style.md`), agent-level (`/agents/{slug}/memory/`), or task-level (`/tasks/{slug}/feedback.md`).
- **Evaluation** — YARNNN judges task output quality against the DELIVERABLE.md specification. Produces steering directives (`/tasks/{slug}/steering.md`) that guide the next execution cycle.
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

Product health surfaces through existing patterns: daily update enrichment (business snapshot alongside agent activity), YARNNN working memory (compact index gains `## Product Health` section), feedback loop closure (product metrics as quality signal). No new surfaces — revenue is context, not a dashboard. See [ADR-184](../adr/ADR-184-product-health-metrics.md).

---

## Key Files

| Concern | File |
|---------|------|
| YARNNN (orchestrator) | `api/agents/yarnnn.py` |
| Task execution | `api/services/task_pipeline.py` |
| Agent types & capabilities | `api/services/orchestration.py` |
| Task type registry | `api/services/task_types.py` |
| Primitive registry | `api/services/primitives/registry.py` |
| Workspace abstraction | `api/services/workspace.py` |
| Working memory (YARNNN context) | `api/services/working_memory.py` |
| Delivery | `api/services/delivery.py` |
| Scheduler | `api/jobs/unified_scheduler.py` |
| Outcome reconciliation | `api/services/back_office/outcome_reconciliation.py` + `api/services/outcomes/` |
| Action proposal queue | `api/services/primitives/propose_action.py` + `action_proposals` ephemeral table |
| Commerce substrate | [commerce-substrate.md](commerce-substrate.md) |

---

## Deep-Dive References

| Topic | Document |
|-------|----------|
| First principles & axioms | [FOUNDATIONS.md](FOUNDATIONS.md) |
| Agent taxonomy & type registry | [orchestration.md](orchestration.md) |
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
| 2026-04-17 | v1.3 — Domain-agnostic framework (ADR-188). Agent roster: "Pre-scaffolded roster" → "Universal roles, contextual application." Task types: "pre-meditated definitions" → "curated template library." Workspace: context domains described as extensible. Execution flow: task creation can be from template or YARNNN-composed. |
| 2026-04-20 | v1.4 — FOUNDATIONS v5.1 alignment. Added Architectural Preamble on Axiom 0 (filesystem is substrate; four permitted DB row kinds). "Three Layers of Cognition" → "Four Layers of Cognition, One Filesystem Substrate" (Reviewer added per ADR-194). Deployed Services reduced from 5 to 4 (yarnnn-platform-sync removed per ADR-153 — this was stale). Key files table extended with outcome reconciliation and action proposal queue. |
| 2026-04-20 | v1.5 — FOUNDATIONS v6.0 alignment. Architectural Preamble restructured into two frames: Six Dimensions (new Axiom 0 dimensional model) + Filesystem Substrate (renumbered Axiom 1, content preserved). Axiom references updated throughout (filesystem substrate: Ax0→Ax1; money-truth: Ax7→Ax8; recursion: Ax2→Ax7). Doc now aligned with dimensional-purity discipline per Derived Principle 1. |
| 2026-04-20 | v1.6 — Cockpit service model ratified per ADR-198 v2. Preamble extends to three frames (Six Dimensions + Filesystem Substrate + Cockpit). "What YARNNN Is" rewritten to lead with cockpit framing; operator works inside YARNNN, external distribution is derivative. Surface Architecture section rewritten: ADR-163 nav (Chat/Work/Agents/Context) superseded by ADR-198 v2 nav — **Overview / Team / Work / Context / Review** + ambient YARNNN rail. Five operator-native destinations (Team and Work are peer destinations — agents-as-identity vs tasks-as-activity). Five archetype patterns (Document / Dashboard / Queue / Briefing / Stream) compose inside destinations per ADR-198 §3. Activity-absorbed routing updated to post-cockpit locations. |
