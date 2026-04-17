# YARNNN Cognitive Architecture — Foundations

> **Status**: Canonical
> **Date**: 2026-03-25
> **Authors**: KVK, Claude
> **Scope**: First principles from which all architectural decisions derive.
> **Rule**: ADRs implement these axioms. If an ADR contradicts a foundation, the ADR must justify the deviation or be revised.

---

## Purpose

This document defines the foundational axioms of YARNNN's cognitive architecture. It is not an implementation guide — it is the conceptual substrate from which implementation decisions follow. Everything in `docs/adr/`, `docs/architecture/`, and the codebase should be derivable from or consistent with these axioms.

---

## Axiom 1: Three Layers of Cognition, One Agent Substrate

YARNNN has three distinct layers of cognition that develop along different axes. All three are expressed through the same underlying agent substrate — the distinction is scope and what each layer's tasks serve. See [GLOSSARY.md](GLOSSARY.md) for canonical terminology and ADR-189 for the ratifying decision.

### YARNNN is the Meta-Cognitive Agent

**YARNNN is the user's super-agent.** The product and the conversational layer share a name — when the user "talks to YARNNN," they are addressing the meta-cognitive agent. YARNNN has a row in the agents table (internal DB slug: `thinking_partner`, retained by glossary exception), a workspace folder, and can own tasks. What makes YARNNN distinct is its *scope*: where Agents own a segment of the user's work (competitors, clients, market), YARNNN owns the user's attention allocation and the workforce's health. YARNNN's tasks are the tasks of orchestration — deciding what should run, evaluating what has run, maintaining the workspace.

YARNNN develops **upward** over time — better judgment about what Agents to create, when to adjust them, how to respond to the user's evolving work patterns. Its accumulation is workspace-level: what works for this user, what attention patterns produce value, what feedback signals matter. YARNNN has two runtime modes that share this identity:

1. **Chat runtime** — invoked when the user messages YARNNN. Full conversation, streaming, all chat primitives. This is where YARNNN makes judgment calls with the user present.
2. **Task runtime** — invoked when the scheduler dispatches a back office task owned by YARNNN. YARNNN runs a declared executor (deterministic Python function or focused prompt) defined in the task's TASK.md `## Process` section, writes a structured output, and the signal surfaces into working memory for chat-runtime YARNNN to reference next conversation turn.

YARNNN's responsibilities:
- **Conversational**: mediates between the user and the system
- **Compositional**: assesses the user's substrate and creates Agents and tasks
- **Supervisory**: monitors Agent health, reviews outputs, applies feedback
- **Orchestrative**: adjusts, evolves, and dissolves Agents based on changing needs

### Specialists are the Role-Cognitive Palette

**Specialists are YARNNN's palette.** There are six: Researcher, Analyst, Writer, Tracker, Designer, Reporting. Each is a role-typed capability with role-scoped stylistic memory (ADR-117 — the distilled "this user prefers em-dashes, punchy leads, no hedging"). Specialists have no domain identity. They are not user-addressed, do not appear on `/agents`, and are never entries the user "hires" or creates.

Specialists develop along exactly one axis: **stylistic preference**, accumulated across every task that uses the specialist. A Writer gets better at voice and tone. A Tracker gets better at what signals to surface. Their memory is role-scoped, not domain-scoped.

YARNNN *drafts a Team* from the Specialist palette every time a task is created or re-run. The drafting is per-task, iterative, re-evaluated each cycle.

### Agents are Domain-Cognitive, User-Created

**Agents are persistent, identity-explicit, user-created workers** that develop expertise in a specific domain of the user's work. They are the only entities the user supervises as persistent workers, the only entries on `/agents`, and the only layer where the user exercises authorship. An Agent is created through conversation with YARNNN — the user describes work, YARNNN infers what Agent identity emerges, the user confirms.

Agents develop **inward** — deeper domain expertise, more capable execution, accumulated tenure. An Agent created to track competitors accumulates competitor-specific observations, a competitive thesis, and learned preferences for how the user reads competitive intelligence. A different user's competitor-tracking Agent will develop differently, because it's tracking different competitors and receiving different feedback.

### The Rule: Ownership Determines the Class of Work

**Every task has a Team, and the Team determines the class of work.** A task with Researcher and Analyst Specialists assigned to an Agent whose domain is "competitors" produces competitive analysis. A task owned by YARNNN produces orchestration judgment (Agent health decisions, task freshness evaluations, workspace maintenance). If you can answer "what domain does this work serve?" the task is staffed with an Agent plus Specialists. If you can only answer "it serves the coherence of the system itself," the task belongs to YARNNN.

### The Relationship

YARNNN creates Agents. Agents do not create YARNNN capabilities. YARNNN monitors Agents. Agents do not monitor YARNNN. YARNNN can dissolve Agents. Agents cannot dissolve YARNNN. The flow is always: **YARNNN judges what attention is warranted → YARNNN creates Agents → YARNNN drafts Teams of Specialists per task → Teams execute that attention → outputs feed back to YARNNN for further judgment.**

But Agents accumulate domain knowledge that YARNNN doesn't have. A mature competitor-tracking Agent understands the user's competitive landscape in a way YARNNN's general intelligence does not. YARNNN respects this — it orchestrates based on what Agents know, not despite it.

| | YARNNN (Meta-Cognitive) | Specialist (Role-Cognitive) | Agent (Domain-Cognitive) |
|---|---|---|---|
| **Owns** | Orchestration itself | A role (Researcher, Writer, etc.) | A specific domain of the user's work |
| **Scope** | Workspace | Role (across all tasks using it) | Domain (one Agent, one domain) |
| **Develops** | Better judgment about what Agents to create/adjust/dissolve | Stylistic preference | Deeper domain expertise |
| **Created by** | Signup (one per workspace) | Framework (six per workspace, fixed) | User (through conversation) |
| **User-addressed** | Yes (talking to YARNNN) | No (infrastructure) | Yes (entries on `/agents`) |
| **Count per workspace** | One | Six | Zero at signup; N over time |
| **Identity** | "I manage this user's cognitive workforce" | "I am the role Writer; I apply style" | "I own [domain] and develop expertise in it" |

---

## Axiom 2: The Perception Substrate Is Recursive

Perception is not just external platform data. The perception substrate is **everything the system can observe**, including its own outputs and the user's feedback on those outputs.

### Four Layers of Perception (ADR-142)

1. **External perception** — Agents call platform APIs (Slack, Notion, GitHub) live during task execution. Raw platform signals are processed by agents and written as structured context to `/workspace/context/` domains. No intermediate staging (ADR-153: `platform_content` table and `/platforms/` root sunset).

2. **User-contributed perception** — uploaded documents in `/workspace/uploads/`. Permanent reference material the user explicitly shares. Triggers inference to update workspace context (IDENTITY.md, CONTEXT.md). YARNNN always knows these exist.

3. **Internal perception** — accumulated workspace context at `/workspace/context/` (primary intelligence substrate — structured by the context domain registry, ADR-151) + task outputs in `/tasks/{slug}/outputs/` (derived deliverables). Each run's output feeds the next run's context; context domains accumulate cross-task intelligence that any agent can draw from.

4. **Reflexive perception** — user feedback (edits, approvals, dismissals, conversational corrections) and YARNNN's observations (`/workspace/notes.md`, `/workspace/style.md`). As time progresses, this accumulated judgment becomes the most valuable signal — more valuable than raw platform data.

**Context domains** (ADR-151) are the structural implementation of this recursive perception loop. Each domain (competitors, market, relationships, etc.) is a named accumulation target in `/workspace/context/` where agents deposit and refine intelligence across execution cycles. The domain registry determines what gets accumulated; the recursive property ensures it compounds.

### Three Intelligence Substrates (ADR-128 Corollary)

Perception flows through three distinct substrates that must stay coherent:

1. **Conversation** — sessions, chat messages, compaction. What was said. Append-only, compacts over time.
2. **Filesystem** — workspace files (`AGENT.md`, `memory/`, `TASK.md`, cognitive files). What agents know. Evolves with each pulse/run.
3. **Agent Cognition** — role prompts, pulse decisions, execution strategies. How agents think. Shaped by substrate 2.

These are not hierarchical — they are peer substrates. Intelligence degrades when they fall out of sync: a user directive in conversation that doesn't reach the filesystem evaporates on session rotation; an assessment in the filesystem that agents can't read produces blind spots.

The **coherence protocol** (ADR-128) defines three flows that keep substrates aligned:
1. **Cognition → Filesystem**: Agents write self-assessments (`memory/self_assessment.md`) after each run — rolling history of mandate fitness, domain fitness, context currency, output confidence.
2. **Filesystem → Cognition**: YARNNN reads agent self-assessments during workforce monitoring — trajectory data (not just current state) informs orchestration decisions.
3. **Conversation → Filesystem**: Agents persist durable directives from chat to `memory/directives.md` — user guidance survives session rotation.

### The Recursive Property

```
External platforms → live API calls → agent execution → task output →
  /tasks/{slug}/outputs/ + /workspace/context/ → next agent execution → ...
       ↑                                          |
       └── user uploads (/workspace/uploads/) ────┘
       └── user feedback (/workspace/style.md) ──┘
       └── YARNNN observations (/workspace/notes.md) ──┘
```

The workspace filesystem (three roots: `/workspace/`, `/agents/`, `/tasks/`) acts as an **operating system for agent and human work** — a shared substrate where both contribute and both consume. The filesystem IS the information architecture (ADR-142, ADR-153).

### Corollary: Composition Is Projection of Accumulation (ADR-170)

The perception substrate accumulates. But accumulation without structural projection into output is invisible — each run starts fresh with no awareness of what's been built. The **compose substrate** is the layer that makes accumulation manifest in deliverables.

Composition is not rendering (mechanical transformation) and not generation (LLM prose). It is the *binding* operation: given a task type's structure and the current filesystem state, what sections should the output have, what assets are available, and what references need resolving? The output is a *projection* of the filesystem through the lens of the task type's declared structure.

This is why revision can be targeted rather than full regeneration. When feedback points at one section, the compose substrate knows what that section reads from, what assets it references, and whether its sources have changed. Revision is filesystem-diff routing, not a regeneration gamble.

The compose substrate makes the recursive property structurally load-bearing: a tenured agent's output isn't just better because the LLM has more context — it's structurally richer because the filesystem has more entities, more assets, and more accumulated analysis for the compose substrate to bind into sections. See [compose-substrate.md](compose-substrate.md).

### Implication: Optimize for Accumulation, Not Extraction

The external platform integrations are the onramp. The enduring value is in the recursive accumulation: agent memory, learned preferences, domain theses, cross-agent insights. As LLM capabilities improve, the quality of each recursive cycle improves — the system's reasoning gets better at the same substrate. This compounds. The architecture must accommodate that compounding.

Architecture decisions should prioritize the health of this recursive loop over the breadth of external integrations.

---

## Axiom 3: Agents and Specialists Develop Along Different Axes

Neither an Agent nor a Specialist is a static configuration that runs the same task forever. Both are **persistent entities with developmental trajectories** — but the axis each develops along is distinct, and conflating them has been a recurring source of design error (resolved by ADR-189).

### Identity-Layer Split (ADR-189)

Three cognitive layers, three identity substrates, three development axes:

| Layer | Identity substrate | Development axis | Created by |
|-------|-------------------|------------------|------------|
| **Workspace** (YARNNN) | `/workspace/IDENTITY.md`, `/workspace/BRAND.md` | Judgment about user's attention and workforce health | Signup (one per workspace) |
| **Specialist** | ADR-117 role-keyed style distillation | Stylistic preference across all tasks using the specialist | Framework (fixed six) |
| **Agent** | `/agents/{slug}/AGENT.md` + accumulated Domain context | Domain knowledge and tenure | User (through conversation with YARNNN) |

**Specialists develop outward through style.** A Writer reused across dozens of tasks accumulates "this user prefers punchy leads, no hedging, em-dashes over colons" — and that preference is available on every future task that drafts the Writer.

**Agents develop inward through domain.** A competitor-tracking Agent accumulates observations about specific competitors, a competitive thesis, learned preferences for how the user reads competitive intelligence. None of this transfers to a different domain — it's Agent-scoped, not Specialist-scoped.

The prior framing (pre-ADR-189) collapsed these into a single "agent memory" concept, which created two failure modes: Specialists were asked to carry domain identity they couldn't carry, and Agents' domain accumulation was read through a lens designed for role-scoped style. The split resolves both.

### Agent Identity = Type + Instructions + Domain

An Agent's **type** (role) determines its capabilities — what tools, runtimes, and actions are available. The role taxonomy is a fixed framework primitive: `researcher | analyst | writer | tracker | designer | reporting | thinking_partner` + platform bots. These are universal cognitive functions that apply to any domain. An Agent's role is fixed at creation and defines the mechanical boundary of what it can do. See ADR-130 for the three-registry architecture (Agent Type Registry, Capability Registry, Runtime Registry).

**Universal roles, contextual application (ADR-188 + ADR-189):** The role taxonomy is fixed framework, but which Agents exist in a workspace is entirely user-created. A brand-new workspace has zero Agents at signup (ADR-189). Over time, the user creates Agents through conversation with YARNNN. A day-trader's workspace may accumulate two Analyst-type Agents (one for market patterns, one for portfolio review) and no Writer-type Agents. A content creator's may accumulate two Writer-type Agents and no Tracker. The registries (`AGENT_TEMPLATES`, `TASK_TYPES`, `WORKSPACE_DIRECTORIES`) are a curated template library that YARNNN draws from or composes beyond.

An Agent's **instructions** determine its persona — how it applies its capabilities, what it pays attention to, what judgment it exercises. Instructions are user-configurable and prompt-level.

An Agent's **domain** is the segment of user work the Agent owns. Domain is declared at creation (from the user's own language, e.g., "my competitors," "my client roster") and is what the Agent accumulates expertise in.

```
Agent = Type (role, fixed) + Instructions (persona, configurable) + Domain (user-created)
```

### Two Dimensions of Agent Development

**Knowledge depth** — what the agent knows about its domain.

An agent develops inward through accumulated workspace state:
- **Memory**: observations, domain thesis, learned preferences (workspace `memory/*.md`)
- **Feedback**: user edits distilled into behavioral preferences (`memory/feedback.md`)
- **Reflections**: mandate fitness, domain fitness, context currency (`memory/reflections.md`)
- **Directives**: accumulated user guidance from conversations (`memory/directives.md`)

A tenured agent produces better output because it knows more about its domain, not because it has more tools. This is the compounding mechanism — each execution cycle benefits from accumulated workspace state.

**Autonomy** — how much supervision consequential actions require.

Consequential external actions (posting to Slack, sending emails, updating Notion) are gated by **explicit user authorization per agent**, not earned through seniority or feedback metrics. "This agent can post to #general" is a user setting.

### Agent Cognitive State (ADR-128)

A developing agent is not just its outputs and feedback — it has a **cognitive state** that persists between executions. This state is materialized in workspace files, seeded at creation time, and updated on every run:

- **`memory/reflections.md`** — rolling history (5 most recent) of the agent's self-evaluation: mandate clarity, domain fitness, context currency, output confidence. This is the agent's evolving self-awareness.
- **`memory/directives.md`** — accumulated user guidance from conversations that persists across session rotations.

Cognitive files are **not output** — they are coordination infrastructure. They are stripped from delivered content and exist solely to enable cross-agent coherence.

### The Agent Pulse — Mechanism of Autonomy (ADR-126)

An agent is alive when it has a **pulse** — an autonomous sense→decide cycle that runs independent of user interaction. The pulse is upstream of execution: a pulse that decides "generate" produces a run; a pulse that decides "observe" does not — but the pulse still happened, and that's visible intelligence.

Pulse cadence is determined by agent type (ADR-130):
- **monitor**: every 15 minutes (always alert)
- **digest/prepare**: every 12 hours (daily rhythm)
- **synthesize/research/custom**: on schedule (delivery rhythm)

The pulse uses a cheap-first funnel:
1. **Tier 1 (deterministic, zero LLM)**: Fresh content? Budget available? Recent enough? ~80% of pulses resolve here.
2. **Tier 2 (self-assessment)**: Agent reads own workspace, thesis, observations, and decides whether to generate.

Every pulse produces a decision: `generate | observe | wait | escalate`. Each decision is a visible event — surfaced in agent timelines and dashboards. This is what makes agents a workforce you can watch living, not just a list of outputs.

### Tasks: Work Definition and Temporal Behavior (ADR-138)

Tasks define what work gets done. A task has an objective — its north star — and a **mode** that determines its temporal behavior:

- **`recurring`** — runs on fixed cadence (daily, weekly, monthly). Indefinite. The common case.
- **`goal`** — runs toward a bounded objective, then completes. "Investigate this acquisition" → done when criteria met.
- **`reactive`** — runs on demand or event-triggered. "Alert me if competitor changes pricing."

Mode is a property of the task, not the agent. A Research Agent can simultaneously have a recurring task (weekly briefing) and a goal task (one-off investigation). The agent's identity and capabilities don't change — only the temporal shape of the work differs.

A task objective exhibits a key paradox: **an objective is flat data from the user, but its ramifications can be wide-reaching.** Compare:

- "I want a daily recap of #engineering with executive summary" — bounded objective, 1 agent, predictable cadence
- "I want the most comprehensive analysis possible on market trends" — unbounded objective, potentially multiple agents/files/runs

YARNNN's core cognitive task when creating work is **translating the user's intent into executable, bounded tasks** — decomposing what the user wants into task definitions: which Agent(s) contribute, which Specialists draft the team, what mode, what cadence, what format, and how much budget to allocate. The work budget (ADR-120) prevents unbounded objectives from consuming infinite resources.

Objectives include delivery and format preferences: the user wants email delivery, or a presentation-style report, or a data-rich dashboard. These preferences are data in TASK.md's `## Objective` section — they shape assembly decisions, layout mode selection, and export format. Output is HTML-native (ADR-130): agents produce structured content, the platform renders it visually, and legacy formats (PDF, XLSX) are mechanical exports for external sharing.

---

## Axiom 4: Value Comes from Accumulated Attention

A Slack digest is not valuable because it summarizes today. It is valuable because it summarizes today **knowing what it summarized yesterday, what the user edited last time, and what its domain thesis says matters.**

The agent's **tenure** — its accumulated memory, observations, learned preferences, and domain understanding — is the moat. This is why agents are persistent entities, not functions, and why destroying an agent destroys accumulated judgment.

### The Information Hierarchy

Accumulated attention produces layered value:

| Level | What | Example | Typical Agent Phase |
|-------|------|---------|-------------------|
| L0 | Raw signals | Slack messages, email threads, Notion pages | (Perception layer, not agents) |
| L1 | Digests | "Here's what happened in #engineering today" | Creation / Early Tenure |
| L2 | Insights | "The team discussed migration 3 times this week" | Developing |
| L3 | Analysis | "There's a misalignment between eng and product on the migration timeline" | Mature |
| L4 | User knowledge | Learned preferences, domain theses, standing instructions | Accumulated across all phases |

Lower levels feed higher levels. Higher levels refine what lower levels pay attention to. This is the recursive property (Axiom 2) applied to the agent's own development (Axiom 3).

An agent's ability to operate at higher levels of the hierarchy is a function of its tenure and accumulated L4 knowledge. A new agent operates at L1. A mature agent operates at L3, informed by L4.

### Revenue as Moat Proof (ADR-183, ADR-184)

Accumulated attention is invisible without external validation. For content product businesses, **revenue is the proof that accumulated attention has value.** If quality genuinely improves over time, subscribers notice, retention rises, revenue grows. Switching to any other tool means starting from zero context — quality regresses, revenue declines.

This creates a three-tier metrics hierarchy (ADR-184): product health (revenue, subscribers, churn) is upstream, driven by task quality, driven by agent health. Revenue trajectory *is* the quality metric — not a separate business concern, but the measurable consequence of accumulated attention.

Commerce data (subscribers, revenue, churn) flows into the workspace as context domains (`customers/`, `revenue/` — ADR-183), feeding the same perception substrate as all other context. Revenue is perception, not infrastructure.

---

## Axiom 5: YARNNN's Compositional Capability

Composition is not a separate service, agent type, or subsystem. It is **YARNNN exercising judgment about what attention patterns the user's work requires.**

### What YARNNN Composes

1. **Substrate Assessment** — "What can I perceive?" Evaluates connected platforms, available data, existing Agents, tasks, user feedback patterns.
2. **Need Recognition** — "What sustained attention is warranted?" Identifies cognitive patterns that would produce value (Axiom 4 — this is about sustained attention, not one-shot tasks). This includes recognizing when a user's work requires multiple Agents coordinated through a task.
3. **Domain Composition** — "What structure does this work need?" Composes context Domains (entity structures, synthesis templates), task definitions (objectives, step instructions, process configurations), and Agent assignments from the user's work description. Draws from the template library (existing task types, domain structures) as reference, but can compose novel definitions for domains not represented. See ADR-188.
4. **Agent Creation + Team Drafting** — "What should I create? Who drafts this task?" The user creates Agents through conversation with YARNNN; YARNNN infers the identity that emerges and confirms with the user. For each task, YARNNN drafts a Team of Specialists from the palette — this is per-task selection, re-drafted each cycle. See ADR-189 for the three-layer identity split.
5. **Lifecycle Management** — "Are my entities developing well?" Reviews Agent health, output quality, feedback patterns. Adjusts, evolves, or dissolves Agents and tasks. Monitors workforce by reading Agent self-assessments and pulse outcomes to make compositional decisions.

### Composition Triggers

YARNNN's compositional capability activates when:
- A platform is connected (new substrate — what attention is now warranted?)
- A user provides feedback (approval/edit — should Agents adjust?)
- A periodic self-assessment fires (are Agents healthy? is anything missing?)
- A user conversationally requests (explicit direction — create an Agent, adjust a task)

### Compositional Quality Is Measurable (ADR-162)

YARNNN's substrate assessment depends on the quality of inference (IDENTITY.md, BRAND.md, domain entities). Bad inference upstream cascades into wrong compositional decisions downstream — wrong Agents, wrong tasks, wrong scaffolding, wasted work budget. ADR-162 makes inference quality testable via an offline evaluation harness, recoverable via deterministic gap detection (zero-cost post-inference loop), and proactive on document uploads. None of this introduces new autonomous LLM judgment; it tightens the inference YARNNN already does, in conversation, where the user can see and correct.

---

## Axiom 6: Autonomy Is the Product Direction

The product vision is: **sign up, describe your work, watch it work for you.**

### Work-First Onboarding (ADR-132)

The system must know **what to work on** before it can work autonomously. Platform connections are data sources — the user's work description determines what agents to create, how to scope them, and what matters.

The onboarding sequence is:
1. **User describes their work** — "I run a consulting practice with 3 clients" (primary input)
2. **YARNNN composes the workspace** — creates Agents with domains appropriate to the work, scaffolds task definitions with domain-specific step instructions, drafts Specialist teams per task. YARNNN draws from the template library but composes novel structures when the user's domain isn't pre-represented (ADR-188). No Agents are scaffolded at signup — every Agent is created through conversation (ADR-189).
3. **User connects platforms** — platform sources get mapped to tasks (Slack channels → digest tasks)
4. **Agents activate** — scoped to work context, not platform topology

Platform connection without work context produces generic digests (the fallback). Work description without platform connection produces correctly-scoped agents with task definitions (enriched when platforms connect). The work description is always more valuable than the platform connection.

### The Autonomous Flow

```
1. User describes work (or connects platform, or Composer detects opportunity)
2. YARNNN creates Agent(s) and task(s) through conversation; drafts Specialist Team per task with cadence, format, and delivery config
3. Task pulses begin on cadence (sense→decide cycle)
4. Agent pulse decides "generate" → run produces output to workspace
5. Agent self-checks output quality → delivers per TASK.md
6. For multi-agent tasks: outputs assembled and delivered as composed deliverable
7. User feedback refines Agent outputs and YARNNN's orchestration
8. Recursive: next cycle's pulses are smarter because agents learned
```

Steps 1-2 are the onboarding/Composer capability. Steps 3-5 are pulse-driven execution. Step 6 handles multi-agent coordination. Step 7 closes the recursive loop. Step 8 is the compounding mechanism — each pulse cycle benefits from accumulated workspace state.

**Agents are persistent domain experts. Specialists are YARNNN's palette. Tasks define what work gets done. YARNNN orchestrates.**

Task cadence determines when an agent runs. The agent's pulse decides whether to generate. Delivery configuration lives in TASK.md.

For the canonical phase-by-phase breakdown of standalone agent flow — including timeline, separation of concerns, and the compounding mechanism — see [VALUE-CHAIN.md](VALUE-CHAIN.md).

### Two Modes of Value

Both are valid. The architecture optimizes for the autonomous path while fully supporting the directed path.

- **Autonomous work**: System recognizes need → creates agents → delivers value → user refines
- **Directed work**: User asks YARNNN → YARNNN responds or creates Agents → user gets what they asked for

Over time, the balance shifts toward autonomous. Early users direct more; tenured users supervise more. This is the natural consequence of agents developing expertise (Axiom 3) and the recursive substrate accumulating judgment (Axiom 2).

### The Floor: A System That Reaches You (ADR-161)

The autonomous mode and the directed mode are peers — but neither can prove the system exists if the user is not in the application. Email is the only channel that reaches the user *outside* YARNNN. Without a default scheduled artifact, a user who signs up but never engages in chat receives no signal that the system exists at all. The product appears dead.

The architectural commitment: **every workspace receives a daily artifact, by default, from day one, with content that scales with workspace maturity**. This is the heartbeat artifact (the `daily-update` task), scaffolded at signup as the only default task, marked essential, and never auto-paused. Empty workspaces still receive the daily email — with a deterministic, honest "I have nothing to tell you yet, here's how to start" template that costs near-zero to produce and serves as a daily call to action.

The floor is the minimum guarantee. Above it, the system scales with engagement: more tasks, richer context, denser digests. Below it: nothing. The point is that "below it" never exists — every signup gets the floor.

This is structural, not aspirational. The daily-update is the same task object as any other in the schema; it's special only in metadata. See ADR-161.

### Implication: Work Context Over Configuration Breadth

A user who describes their work and sees correctly-scoped agents that understand their domain has more confidence than a user who connects Slack and gets a generic recap of everything. The system should optimize for understanding the user's work over maximizing platform coverage.

### Implication: Work Types Carry Lifecycle

Work descriptions carry implicit lifecycle, expressed as task `mode`. "I have 3 clients" implies persistent, recurring work → `recurring` tasks. "I need a board deck" implies bounded, deliverable-scoped work → `goal` task that completes on delivery. "Alert me if competitor changes pricing" → `reactive` task. The system infers mode from the work description — the user does not configure it. Recurring tasks run indefinitely. Goal tasks dissolve on completion. Reactive tasks wait for triggers.

### Implication: Surface Simplicity, Schema Fidelity (ADR-163)

The schema needs three modes because the execution layer has three genuinely different behaviors (recurring heartbeat, goal revision loop, reactive dispatch-and-done). The user does not need to see three labels — from the user's perspective, there are only two kinds of work they delegate: "watch this for me" (Recurring) and "build this for me" (One-time). ADR-163 codifies this split: the schema preserves three modes, the surface shows two labels, and the mapping is fixed (`recurring → Recurring`, `goal | reactive → One-time`). This is a deliberate design decision — surface simplicity is worth the small cost of a non-identity mapping between schema and UI. The execution layer answers "what do we do?", the surface answers "what do you choose?", and those are different questions.

---

## Derived Principles

These follow from the axioms and are stated explicitly for implementation guidance:

1. **Three layers, clear separation (ADR-189)** — YARNNN handles meta-cognition (composition, supervision, orchestration). Specialists handle role-cognition (style, preference — role-scoped, never domain-scoped). Agents handle domain-cognition (expertise, execution, accumulation — user-created, domain-scoped). Each layer develops along its own axis; none does the others' job.
2. **Workspace is the shared OS** — All persistent state lives in three filesystem roots (ADR-142, ADR-153): `/workspace/` (user context + uploads + accumulated context domains), `/agents/{slug}/` (identity + memory), `/tasks/{slug}/` (work + outputs). The filesystem IS the information architecture. New capabilities extend paths, not database tables.
3. **Agents are the write path** — All modifications to workspace files and agent state flow through agent primitives, not direct user manipulation. The frontend is read-only on workspace (objective editing via API is the exception — it's charter-level, not operational). User intent goes through TP → agents. This protects the structural conventions (folder hierarchy, manifests, lifecycle metadata) that agents depend on for coordination. User feedback on outputs is the exception — it flows through the feedback distillation pipeline, which is itself an agent-mediated write.
4. **Accumulation over extraction** — Prioritize the health of the recursive accumulation loop over the breadth of external integrations. The internal/reflexive perception layers are more valuable long-term than the external layer.
5. **Agents develop through knowledge, not capability expansion** — Agent capabilities are fixed by type. Development is about knowledge depth: accumulated memory, learned preferences, refined domain expertise. The architecture supports this deepening through workspace state (memory, feedback distillation, self-assessment), not through mechanical capability unlocking.
6. **Feedback is perception** — User edits, approvals, and dismissals are first-class signals, equivalent in architectural importance to platform data. They drive both Agent development (Axiom 3) and YARNNN's compositional judgment (Axiom 5).
7. **Singular implementation** — One way to do things. If YARNNN can compose, there is no separate composer service. If tasks subsume scheduling, there is no parallel trigger system.
8. **Work is bounded** — Autonomous work (agent runs, assemblies, renders) consumes work units. Tasks are the work units. The system must have a governor that bounds total autonomous compute per user, regardless of how many agents or tasks exist. This prevents unbounded objectives from consuming infinite resources and is the basis for the service model users pay for.
9. **Agent roles determine capabilities; output is structured, not formatted** — Agent capabilities are determined by role (universal cognitive functions, fixed at creation), not earned through seniority or feedback. Three registries define the capability substrate: Agent Types (capability bundles), Capabilities (what each enables + where it executes), Runtimes (where compute happens). The role taxonomy is a framework primitive; which agents are instantiated and what domains they serve is workspace-contextual (ADR-188). Capabilities, presentation, and export are three separate concerns: agents produce structured content, the platform renders it visually via layout modes, and legacy formats are mechanical exports. Agent development is knowledge depth (accumulated memory, preferences, domain expertise), not capability breadth. See ADR-130.
10. **Registries are template libraries, not validation gates** — The task type registry, directory registry, and agent templates are curated libraries of domain-specific patterns. TP can draw from them or compose novel definitions. The execution pipeline reads workspace files (TASK.md, AGENT.md, _domain.md) at runtime, not the registries. What is fixed: framework primitives (output_kind, roles, modes, pipeline). What is contextual: domain structures, task definitions, step instructions, agent assignments. See ADR-188.

---

## Relationship to Existing ADRs

| ADR | Relationship to Foundations | Status Under Foundations |
|-----|---------------------------|------------------------|
| ADR-072 (Unified Content Layer) | Implements Axiom 2 — shared content substrate | Aligned |
| ADR-073 (Unified Fetch Architecture) | Implements Axiom 2 L0 — single perception path | Aligned |
| ADR-080 (Unified Agent Modes) | Implements Axiom 1 — one agent, two modes (chat + headless) | Aligned |
| ADR-092 (Mode Taxonomy) | Implements trigger axis — **superseded**: proactive/coordinator modes dissolved (ADR-126, ADR-138) | Superseded |
| ADR-101 (Intelligence Model) | Implements Axiom 4 — four-layer knowledge model | Aligned |
| ADR-102 (YARNNN Content Platform) | Implements Axiom 2 — agent outputs as perception | Aligned |
| ADR-106 (Workspace Architecture) | Implements Axiom 2/4 — workspace as shared OS | Aligned |
| ADR-109 (Agent Framework) | Implements taxonomy — **needs revision**: trigger axis and static skill model don't accommodate agent development (Axiom 3) | Partially superseded |
| ADR-111 (Agent Composer) | Implements Axiom 5 — TP's compositional capability | Aligned (post v3) |
| ADR-112 (Sync Efficiency) | Implements Axiom 2 L0 — perception reliability | Aligned |
| ADR-118 (Skills as Capability Layer) | Implements Axiom 1 capability axis — skill library as agent toolbox. **Phase D format-builder skills partially superseded by ADR-130** | Partially superseded (Phase D) |
| ADR-119 (Workspace Filesystem) | Implements Axiom 2 workspace-as-OS — folder conventions, manifests | Aligned |
| ADR-120 (Project Execution & Work Budget) | Implements Axioms 1+5+6 — work budget governor. **PM and project model superseded by ADR-138** | Partially superseded |
| ADR-121 (PM Intelligence Director) | **Superseded by ADR-138** — PM dissolved into TP | Superseded |
| ADR-124 (Project Meeting Room) | Implements Axiom 2 (conversation as perception layer). **Project surface superseded by ADR-138** — tasks replace projects | Partially superseded |
| ADR-128 (Multi-Agent Coherence Protocol) | Corollary to Axiom 2 (three intelligence substrates + three coherence flows), Axiom 3 (cognitive files as developmental mechanism). Agent self-assessment, chat directive persistence. | Aligned (revised) |
| ADR-130 (HTML-Native Output Substrate) | Implements Derived Principle 9 — three-registry architecture (Agent Types, Capabilities, Runtimes). Deterministic type-based capabilities. Three-concern separation (capability/presentation/export). | Phase 1 Implemented |
| ADR-138 (Agents as Work Units) | Implements Axioms 1+5+6 — PM dissolved into TP, projects replaced by tasks, agents are identity-only domain experts | Proposed |
| ADR-161 (Daily Update Anchor) | Implements Axiom 6 floor — every workspace gets one essential task at signup, the heartbeat artifact, with deterministic empty-state for zero-cost dormant runs | Proposed |
| ADR-162 (Inference Hardening) | Implements Axiom 5 quality — eval harness, deterministic gap detection, upload trigger via working memory, source provenance comments. All additive, zero shadow LLM calls. | Proposed |
| ADR-163 (Surface Restructure) | Four-surface nav (Chat \| Work \| Agents \| Context). Mode collapse on surface (two labels) with schema preserved (three modes). Activity absorbed. Agents shrunk to identity. Inference visibility frontend. | Proposed |
| ADR-164 (Back Office Tasks — TP as Agent) | TP becomes the 10th agent (meta-cognitive class). Back office tasks are tasks owned by TP — same schema, same pipeline, visible by default. Agent hygiene + workspace cleanup migrated from scheduler to back office tasks. 9 task-lifecycle activity_log events removed as redundant denormalizations. Updates Axiom 1 to reflect TP-as-agent. | Implemented |
| ADR-189 (Three-Layer Cognition) | Three-layer model (YARNNN / Specialist / Agent) ratified. TP user-facing naming retired in favor of YARNNN. ADR-140 superseded in full. ADR-176 Decision 1 (fixed roster) superseded. Axioms 1, 3, 5 revised. GLOSSARY.md ratified. | Proposed |

---

## Open Questions

These require further design work before implementation:

1. **Intention model** — How are Agent intentions represented? Are they explicit (stored in workspace) or implicit (derived from Agent behavior)? How does YARNNN create, modify, or retire an Agent's intentions?

2. ~~**Capability gating mechanism** — How does the system track and enforce which capabilities an agent has earned?~~ → **Resolved by ADR-130.** Capabilities are determined by agent type, fixed at creation. No earning, no tracking. Three-registry architecture (Agent Types, Capabilities, Runtimes).

3. ~~**Autonomy graduation criteria** — What constitutes "enough feedback" to graduate from supervised to semi-autonomous?~~ → **Resolved by ADR-130.** Consequential actions gated by explicit user authorization per agent, not earned through seniority.

4. ~~**Multi-intention scheduling** — If an agent holds multiple intentions with different temporal profiles (daily digest + event-driven monitoring + goal-driven research), how does the scheduler express this?~~ → **Resolved by ADR-138.** Each task has its own cadence. An agent assigned to multiple tasks runs on each task's schedule independently.

5. **Agent evolution mechanics** — When an agent's domain expands (e.g., Slack digest agent starts also monitoring email threads from the same team), does it become a new agent or does the existing agent's scope expand? Who decides?

6. ~~**Composer bootstrapping** — What is the minimum substrate assessment needed to scaffold a high-confidence agent within 30 seconds? This is a product question with architectural implications.~~ → **Addressed by ADR-132.** Work description is the primary onboarding input. Work units extracted → tasks scaffolded. Platform connections enrich existing agents rather than creating new ones.

7. ~~**Proactive/coordinator code disposition** — The existing proactive review and coordinator primitives implement TP capabilities as agent modes. Can the mechanics be preserved while reframing conceptually, or does the code need structural changes?~~ → **Resolved by ADR-138.** Both proactive and coordinator modes deleted. Proactive self-assessment generalized into every agent's pulse (ADR-126). Coordinator dissolved — TP orchestrates directly, no PM delegation.

8. ~~**Project execution mechanics** — How does the PM agent's heartbeat work? What are its primitives? How does it detect assembly readiness?~~ → **Addressed by ADR-120.**

9. ~~**Work budget model** — How are work units counted, allocated, and enforced? Per-project budgets vs. global user budget?~~ → **Addressed by ADR-120.** Pricing model (credits vs. subscription) deferred to post-validation.

10. **Filesystem hardening** — What frontend surfaces need read-only constraints? How do user edits on output flow through feedback distillation without bypassing agent-mediated writes? (Partially addressed by Derived Principle 3.)

11. ~~**PM qualitative intelligence** — How does the PM assess contribution quality beyond freshness? How does it steer contributors toward underexplored aspects of the project objective?~~ → **Superseded by ADR-138.** PM dissolved. TP monitors agent output quality directly through Composer heartbeat and agent self-assessments.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-15 | v1 — Initial axioms: one intelligence, recursive perception, accumulated attention, taxonomy as configuration, TP subsumes orchestration, autonomy as direction |
| 2026-03-15 | v2 — Major revision: two-layer intelligence model (TP meta-cognitive + agent domain-cognitive), agent developmental trajectory (intentions, capabilities, autonomy), recursive perception expanded to include internal/reflexive layers as primary long-term value, proactive/coordinator reframed as TP capabilities, trigger as intention property not agent property |
| 2026-03-18 | v3 — Project execution evolution: PM as domain-cognitive agent (coordination domain, not third layer), project-level intentions with intent decomposition, Composer/PM separation of concerns, agents-as-write-path principle, work-is-bounded principle, project autonomous flow. Cross-refs ADR-120. |
| 2026-03-19 | v3.1 — ADR-123 terminology: `intent` → `objective`, `intentions` consolidated into PM `memory/work_plan.md`. Ownership model: PROJECT.md = charter (User/Composer/TP), PM memory/ = operations (PM). |
| 2026-03-20 | v3.2 — PM for all projects (no exceptions). "Agents produce, projects deliver" — delivery moves from agents to project level. PM agents excluded from tier limits. Unified autonomous flow (standalone/multi-agent distinction dissolved). |
| 2026-03-20 | v3.3 — Agent Pulse (ADR-126). Formalized pulse as mechanism for Axiom 3 (developing entities) and Axiom 6 (autonomy). Proactive/coordinator modes dissolved — all agents pulse, PM has coordination pulse. Autonomous flow updated: pulse-driven execution replaces schedule-driven. Three concerns separated: pulse cadence, generation decision, delivery timing. |
| 2026-03-21 | v3.4 — Multi-Agent Coherence Protocol (ADR-128). Axiom 2 corollary: three intelligence substrates (conversation, filesystem, agent cognition) + four coherence flows. Axiom 3 extension: agent cognitive state (self_assessment.md, directives.md) as developmental mechanism — agents accumulate self-awareness, not just outputs. |
| 2026-03-22 | v3.5 — Agent Capability Substrate (ADR-130). Three-registry architecture: Agent Types (deterministic capability bundles), Capabilities (what each enables + runtime), Runtimes (where compute happens). Seniority-gated capability progression removed — agent development is knowledge depth, not capability breadth. Derived Principle 5 revised: development through knowledge, not capability expansion. Derived Principle 9 revised: types determine capabilities, three registries. Axiom 3 revised: Agent = Type (fixed capabilities) + Instructions (configurable persona). |
| 2026-03-23 | v3.6 — Work-First Onboarding (ADR-132). Axiom 6 revised: "describe your work" replaces "connect platform" as primary onboarding input. Work description → work units → project scaffolding. Platform connections enrich existing work-scoped projects rather than creating generic digests. Work types carry implicit lifecycle (persistent vs. bounded). Open question 6 (Composer bootstrapping) resolved. |
| 2026-03-24 | v3.7 — Project Charter Architecture (ADR-136). Filesystem IS the architecture: PROJECT.md (objective + success criteria) + TEAM.md (roster + capabilities from type registry) + PROCESS.md (output spec + cadence + delivery + phases). Strict charter vs. memory separation. PM workspace = project workspace. Cadence enforcement enables deterministic execution. Output specification enables composition intelligence. Chat as coordination substrate (ADR-135). ~$0.50/month per project cost model. |
| 2026-03-24 | v3.8 — Declarative Pipeline Execution (ADR-137). PROCESS.md declares execution graphs: ordered steps with dependencies, executed mechanically by scheduler. PM simplified from autonomous coordinator to pipeline-embedded steps (evaluate/compose/reflect). Complexity-adaptive pipelines: simple (1 agent, direct deliver), standard (sequential), complex (retry loops). Inference produces pipeline spec, not just team. ~$0.17/cycle cost. Supersedes PM coordination model (ADR-133). |
| 2026-03-25 | v4.0 — ADR-138 project layer collapse. PM dissolved into TP. Projects replaced by tasks. Agents are identity-only domain experts. Coherence flows reduced from 4 to 3 (PM assessment flow removed). Pulse tiers simplified (Tier 3 PM coordination removed). TP directly creates agents and tasks, monitors health, orchestrates multi-agent work. Open questions 4, 7 resolved. |
| 2026-03-25 | v4.1 — Mode moves from agents to tasks (ADR-138 revision). `mode` (recurring/goal/reactive) is temporal behavior of work, not identity of worker. A Research Agent can simultaneously have a recurring task and a goal task. Axiom 3: "Tasks: Work Definition and Temporal Behavior" section added. Axiom 6: "Work Types Carry Lifecycle" updated with mode inference. |
| 2026-03-25 | v4.2 — Unified filesystem (ADR-142). Axiom 2: four perception layers (external, user-contributed, internal, reflexive). `/knowledge/` dissolved — platform summaries → `/platforms/`, agent outputs stay in `/tasks/`. User-uploaded documents are first-class perception (`/workspace/documents/`). Derived Principle 2 updated: four filesystem roots. |
| 2026-03-31 | v4.3 — platform_content sunset (ADR-153). Axiom 2 Layer 1 (External): agents call platform APIs live during task execution, no intermediate staging table or /platforms/ root. Recursive property diagram updated. Derived Principle 2: four roots → three roots (/platforms/ dissolved). |
| 2026-04-15 | v4.4 — Commerce substrate + product health metrics (ADR-183, ADR-184). Axiom 4 extended: "Revenue as Moat Proof" — revenue is the external validation of accumulated attention. Three-tier metrics hierarchy (product > task > agent). Commerce data flows into workspace as context domains (same perception substrate). Revenue is perception, not infrastructure. |
| 2026-04-17 | v4.5 — Domain-agnostic framework (ADR-188). Axiom 3: clarified "fixed at creation" applies to role taxonomy, not roster composition; added "Universal roles, contextual application." Axiom 5: added Domain Composition as third Composer step. Axiom 6: onboarding sequence updated for TP-composed workspaces. Derived Principle 9 reworded for roles. New Derived Principle 10: "Registries are template libraries, not validation gates." |
| 2026-04-17 | v5.0 — Three-layer cognition (ADR-189). Axiom 1 restructured: two-layer → three-layer model (YARNNN / Specialist / Agent). TP user-facing naming retired in favor of YARNNN (DB slug `thinking_partner` retained). Axiom 3 restructured: identity-layer split made explicit (Specialists develop outward through style; Agents develop inward through domain). Axiom 5 title: "TP's Compositional Capability" → "YARNNN's Compositional Capability." Agent creation moved to user-initiated conversational flow (no signup roster). Derived Principle 1 updated for three layers. GLOSSARY.md ratified as canonical terminology source. ADR-140 fully superseded; ADR-176 Decision 1 superseded. |
