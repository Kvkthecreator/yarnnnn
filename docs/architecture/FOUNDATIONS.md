# YARNNN Cognitive Architecture — Foundations

> **Status**: Canonical
> **Date**: 2026-03-15
> **Authors**: KVK, Claude
> **Scope**: First principles from which all architectural decisions derive.
> **Rule**: ADRs implement these axioms. If an ADR contradicts a foundation, the ADR must justify the deviation or be revised.

---

## Purpose

This document defines the foundational axioms of YARNNN's cognitive architecture. It is not an implementation guide — it is the conceptual substrate from which implementation decisions follow. Everything in `docs/adr/`, `docs/architecture/`, and the codebase should be derivable from or consistent with these axioms.

---

## Axiom 1: Two Layers of Intelligence

YARNNN has two distinct layers of intelligence that develop along different axes.

### The Meta-Cognitive Layer (TP)

The Thinking Partner is the **singular meta-intelligence**. It does not own a domain — it owns the **system's attention allocation**. Its responsibilities:

- **Conversational**: mediates between the user and the system
- **Compositional**: assesses the user's substrate and scaffolds agents (Composer capability)
- **Supervisory**: monitors agent health, reviews outputs, applies feedback
- **Orchestrative**: adjusts, evolves, and dissolves agents based on changing needs

TP develops **upward** over time — better judgment about what agents to create, when to adjust them, how to respond to the user's evolving work patterns. Its accumulation is system-level: what works for this user, what attention patterns produce value, what feedback signals matter.

### The Domain-Cognitive Layer (Agents)

Agents are **persistent entities that develop expertise in a specific domain of the user's work**. They are not task executors. They are not static configurations. They are autonomous cognitive functions that deepen their understanding over time.

Agents develop **inward** — deeper domain expertise, more capable execution, higher autonomy. An agent that starts as a daily Slack digest may evolve to notice patterns, draft responses, and eventually act independently in its domain.

**An agent's domain can be coordination itself.** A Project Manager agent's domain is the execution of a specific project — tracking contributions, managing assembly timing, enforcing budget. Its domain knowledge is project-specific: which contributors are reliable, what assembly cadence works, how the user wants the deliverable structured. This is not a third layer of intelligence — it is domain-cognitive expertise applied to the domain of project coordination. The PM sits alongside other agents, not above them. TP creates PMs, monitors their health, and can dissolve them — exactly as with any agent. The PM's special primitives (assembly, freshness checks, contributor nudges) are domain-specific tools, just as a researcher has WebSearch.

### The Relationship

TP creates agents. Agents don't create TP capabilities. TP monitors agents. Agents don't monitor TP. TP can dissolve agents. Agents can't dissolve TP capabilities. The flow is always: **TP judges what attention is warranted → agents execute that attention → outputs feed back to TP for further judgment.**

But agents are not mere functions. They accumulate domain knowledge that TP doesn't have. A mature Slack agent understands the team's communication patterns in a way TP's general intelligence does not. A mature PM agent understands what its project needs — which contributions are stale, when to assemble, how to decompose the user's intent into executable work. TP respects this — it orchestrates based on what agents know, not despite it.

| | TP (Meta-Cognitive) | Agent (Domain-Cognitive) |
|---|---|---|
| **Owns** | System's attention allocation | A specific domain of the user's work |
| **Develops** | Better judgment about what agents to create/adjust/dissolve | Deeper expertise in domain, more capable execution |
| **Autonomy means** | Scaffolding agents without being asked | Taking multi-step action in domain without supervision |
| **Accumulates** | System-level patterns (what works for this user) | Domain-level knowledge (what matters in this area) |
| **Identity** | "I manage this user's cognitive workforce" | "I own [domain] and develop expertise in it" |
| **Examples** | Singular | Slack digest, revenue analyst, PM for Q2 review |

---

## Axiom 2: The Perception Substrate Is Recursive

Perception is not just external platform data. The perception substrate is **everything the system can observe**, including its own outputs and the user's feedback on those outputs.

### Three Layers of Perception

1. **External perception** — platform sync fills `platform_content` from Slack and Notion. This is the surface area for platform data enrichment.

2. **Internal perception** — agent outputs, written to `/knowledge/` files in `workspace_files` (ADR-107, superseding ADR-102's `platform_content` rows), feed back into the shared knowledge layer. An agent's output is another agent's input. TP's observations are part of the substrate.

3. **Reflexive perception** — user feedback (edits, approvals, dismissals, conversational corrections) and TP's own compositional reasoning create a shared recursive layer. As time progresses, this accumulated judgment becomes the most valuable signal — more valuable than raw platform data.

### Three Intelligence Substrates (ADR-128 Corollary)

Perception flows through three distinct substrates that must stay coherent:

1. **Conversation** — project sessions, chat messages, compaction. What was said. Append-only, compacts over time.
2. **Filesystem** — workspace files (`AGENT.md`, `memory/`, `PROJECT.md`, cognitive files). What agents know. Evolves with each pulse/run.
3. **Agent Cognition** — role prompts, pulse decisions, execution strategies. How agents think. Shaped by substrate 2.

These are not hierarchical — they are peer substrates. Intelligence degrades when they fall out of sync: a user directive in conversation that doesn't reach the filesystem evaporates on session rotation; a PM assessment in the filesystem that agents can't read produces coordination blind spots.

The **coherence protocol** (ADR-128) defines four flows that keep substrates aligned:
1. **Cognition → Filesystem**: Contributors write self-assessments (`memory/self_assessment.md`) after each run — rolling history of mandate fitness, domain fitness, context currency, output confidence.
2. **Filesystem → Cognition**: PM reads contributor self-assessments during its pulse — trajectory data (not just current state) informs steering decisions.
3. **Conversation → Filesystem**: Agents persist durable directives from chat to `memory/directives.md` — user guidance survives session rotation.
4. **Filesystem → Conversation**: Contributors read PM's `project_assessment.md` — they know which prerequisite layer constrains the project.

### The Recursive Property

```
External platforms → platform_content → agent execution → agent output →
  /knowledge/ (workspace_files) → next agent execution → ...
                              ↑                           |
                              └── user feedback ──────────┘
                              └── TP assessment ──────────┘
```

The YARNNN knowledge filesystem (`workspace_files`: `/knowledge/` for accumulated outputs, `/agents/` for agent state) acts as an **operating system for agent and human work** — a shared substrate where both contribute and both consume.

### Implication: Optimize for Accumulation, Not Extraction

The external platform integrations are the onramp. The enduring value is in the recursive accumulation: agent memory, learned preferences, domain theses, cross-agent insights. As LLM capabilities improve, the quality of each recursive cycle improves — the system's reasoning gets better at the same substrate. This compounds. The architecture must accommodate that compounding.

Architecture decisions should prioritize the health of this recursive loop over the breadth of external integrations.

---

## Axiom 3: Agents Are Developing Entities

An agent is not a static configuration that runs the same task forever. An agent is a **persistent entity with a developmental trajectory**.

### Agent Identity = Type + Instructions

An agent's **type** determines its capabilities — what tools, runtimes, and actions are available. Type is deterministic, fixed at creation, and defines the mechanical boundary of what an agent can do. See ADR-130 for the three-registry architecture (Agent Type Registry, Capability Registry, Runtime Registry).

An agent's **instructions** determine its persona — how it applies its capabilities, what it pays attention to, what judgment it exercises. Instructions are user-configurable and prompt-level.

```
Agent = Type (capabilities, fixed) + Instructions (persona, configurable)
```

### Two Dimensions of Agent Development

**Knowledge depth** — what the agent knows about its domain.

An agent develops inward through accumulated workspace state:
- **Memory**: observations, domain thesis, learned preferences (workspace `memory/*.md`)
- **Feedback**: user edits distilled into behavioral preferences (`memory/preferences.md`)
- **Self-assessment**: mandate fitness, domain fitness, context currency (`memory/self_assessment.md`)
- **Directives**: accumulated user guidance from conversations (`memory/directives.md`)

A tenured agent produces better output because it knows more about its domain, not because it has more tools. This is the compounding mechanism — each execution cycle benefits from accumulated workspace state.

**Autonomy** — how much supervision consequential actions require.

Consequential external actions (posting to Slack, sending emails, updating Notion) are gated by **explicit user authorization per agent**, not earned through seniority or feedback metrics. "This agent can post to #general" is a user setting.

Note: "Objectives" at the project level (ADR-123) are distinct — they represent the project's north star (what, for whom, why, in what form), not agent responsibilities.

### Agent Cognitive State (ADR-128)

A developing agent is not just its outputs and feedback — it has a **cognitive state** that persists between executions. This state is materialized in workspace files, seeded at creation time, and updated on every run:

- **`memory/self_assessment.md`** — rolling history (5 most recent) of the agent's self-evaluation: mandate clarity, domain fitness, context currency, output confidence. This is the agent's evolving self-awareness.
- **`memory/directives.md`** — accumulated user guidance from meeting room conversations that persists across session rotations.

PM agents maintain additional cognitive files at the project level:
- **`memory/project_assessment.md`** — the PM's layered evaluation of the project, rewritten each pulse. This is the authoritative project health snapshot.
- **`memory/decisions.md`** — project-level decisions from meeting room conversations.

Cognitive files are **not output** — they are coordination infrastructure. They are stripped from delivered content and exist solely to enable cross-agent coherence. The asymmetry is intentional: contributor assessments use rolling append (trajectory data for PM), PM assessments use overwrite (authoritative snapshot for contributors).

### The Agent Pulse — Mechanism of Autonomy (ADR-126)

An agent is alive when it has a **pulse** — an autonomous sense→decide cycle that runs independent of user interaction. The pulse is upstream of execution: a pulse that decides "generate" produces a run; a pulse that decides "observe" does not — but the pulse still happened, and that's visible intelligence.

Pulse cadence is determined by agent type (ADR-130):
- **monitor**: every 15 minutes (always alert)
- **pm**: every 30 minutes (responsive to contributor output)
- **digest/prepare**: every 12 hours (daily rhythm)
- **synthesize/research/custom**: on schedule (delivery rhythm)

The pulse uses a cheap-first funnel:
1. **Tier 1 (deterministic, zero LLM)**: Fresh content? Budget available? Recent enough? ~80% of pulses resolve here.
2. **Tier 2 (self-assessment)**: Agent reads own workspace, thesis, observations, and decides whether to generate.
3. **Tier 3 (PM coordination)**: PM reads contributor freshness, quality, work plan, decides coordination action.

Every pulse produces a decision: `generate | observe | wait | escalate`. Each decision is a visible event — surfaced in project meeting rooms, agent timelines, and dashboards. This is what makes agents a workforce you can watch living, not just a list of outputs.

### Objectives at Project Scope (ADR-123)

Projects have objectives — their north star — and they exhibit a key paradox: **an objective is flat data from the user, but its ramifications can be wide-reaching.** Compare:

- "I want a Q2 report with data analysis and an executive summary" — bounded objective, 2-3 agents, known capabilities, predictable work
- "I want the most comprehensive analysis possible on market trends" — unbounded objective, potentially infinite agents/files/runs

The PM agent's core cognitive task is **translating the objective into executable, bounded work** — decomposing a user's project objective into an operational work plan: which agents contribute, which skills produce output, what cadence, what assembly format, and how much budget to allocate. The work budget (ADR-120) prevents unbounded objectives from consuming infinite resources.

Objectives include delivery and format preferences: the user wants email delivery, or a presentation-style report, or a data-rich dashboard. These preferences are data in PROJECT.md's `## Objective` section — they shape the PM's assembly decisions, layout mode selection, and export format. The PM's operational execution plan lives separately in `memory/work_plan.md` (ADR-123: charter vs. operations separation). Output is HTML-native (ADR-130): agents produce structured content, the platform renders it visually, and legacy formats (PDF, XLSX) are mechanical exports for external sharing.

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

---

## Axiom 5: TP's Compositional Capability (The Composer)

The Composer is not a separate service, agent type, or subsystem. It is **TP exercising judgment about what attention patterns the user's work requires.**

### What the Composer Does

1. **Substrate Assessment** — "What can I perceive?" Evaluates connected platforms, available data, existing agents, projects, user feedback patterns.
2. **Need Recognition** — "What sustained attention is warranted?" Identifies cognitive patterns that would produce value (Axiom 4 — this is about sustained attention, not one-shot tasks). This includes recognizing when multiple agents' outputs should combine into a project.
3. **Agent & Project Scaffolding** — "What entity should I create?" Maps recognized needs to agent identities or project structures, then to configurations. For projects: creates a PM agent, identifies or creates contributing agents, writes PROJECT.md with objective and assembly spec. High-confidence needs are auto-scaffolded; medium-confidence are suggested to the user.
4. **Lifecycle Management** — "Are my entities developing well?" Reviews agent and project health, output quality, feedback patterns. Adjusts, evolves, or dissolves agents and projects.

### Composer vs. Project Manager: Separation of Concerns

The Composer decides **whether** a project should exist. The PM agent decides **how** it executes.

| Concern | Composer (TP) | PM Agent |
|---------|--------------|----------|
| Create/dissolve projects | Yes | No |
| Create/dissolve agents | Yes | No (requests TP via escalation) |
| Set project objective & contributors | Yes | Refines over time |
| Monitor project health (top-level) | Yes (reads PM status) | No — IS the status source |
| Track contribution freshness | No | Yes |
| Trigger assembly | No | Yes |
| Enforce project work budget | No | Yes |
| Adjust assembly timing/format | No | Yes |
| Escalate when stuck | No | Yes (communicates to TP) |

This prevents TP bloat. TP's heartbeat sees project health *through* PM status reports, not by reimplementing project-level logic.

### Composer Triggers

The Composer capability activates when:
- A platform is connected (new substrate → what attention is now warranted?)
- A user provides feedback (approval/edit → should agents adjust?)
- A periodic self-assessment fires (are agents healthy? is anything missing?)
- A user conversationally requests (explicit direction → scaffold or adjust)

### Relationship to Proactive and Coordinator Modes

> **Note (2026-03-20):** ADR-126 (Agent Pulse) supersedes the framing below. Proactive self-assessment is no longer a TP supervisory capability invoked top-down — it is generalized into every agent's pulse. All agents sense their domain and decide whether to act. The distinction between "proactive" and "recurring" dissolves: every agent has a pulse, and the pulse's sophistication scales with seniority. Coordinator mode dissolves similarly — project coordination belongs to PM agents via their coordination pulse (Tier 3), not to a special agent mode.

Under the previous swarm framing, proactive and coordinator were agent modes — agents that assessed and orchestrated. Under ADR-126:

- **Proactive review** generalizes into the **Agent Pulse** — every agent's autonomous sense→decide cycle. The review logic (workspace reading, domain assessment, generate/observe/wait decision) is the agent's own intelligence, not TP's. TP's role is portfolio-level: reading pulse outcomes to make compositional decisions.

- **Coordinator mode** dissolves into **PM pulse** — project coordination is a PM agent's domain expertise, expressed through its specialized coordination pulse (Tier 3). PM agents are created by Composer, not by coordinator agents.

---

## Axiom 6: Autonomy Is the Product Direction

The product vision is: **sign up, describe your work, watch it work for you.**

### Work-First Onboarding (ADR-132)

The system must know **what to work on** before it can work autonomously. Platform connections are data sources — the user's work description determines what agents to create, how to scope them, and what matters.

The onboarding sequence is:
1. **User describes their work** — "I run a consulting practice with 3 clients" (primary input)
2. **System extracts work units** — each discrete scope of recurring attention becomes a project
3. **User connects platforms** — platform sources get mapped to work units (Slack channels → client projects)
4. **Agents activate** — scoped to work context, not platform topology

Platform connection without work context produces generic digests (the fallback). Work description without platform connection produces correctly-scoped projects with placeholder agents (enriched when platforms connect). The work description is always more valuable than the platform connection.

### The Autonomous Flow

**All projects** (work-scoped + platform-scoped, unified model):
```
1. User describes work (or connects platform, or Composer detects opportunity)
2. Work units extracted → scaffold_project() creates project + member agents + PM agent
3. Agent pulses begin (sense→decide cycle on cadence)
4. Agent pulse decides "generate" → run produces output to workspace
5. PM pulse senses contributor freshness → coordinates delivery
6. For single-agent projects: PM passthrough (contribution = output, deliver immediately)
   For multi-agent projects: PM assembles contributions, delivers composed deliverable
7. User feedback refines PM's coordination + contributors' outputs
8. Recursive: next cycle's pulses are smarter because agents learned, PM learned
```

Steps 1-2 are the onboarding/Composer/Bootstrap capability. Steps 3-6 are pulse-driven execution. Step 7 closes the recursive loop. Step 8 is the compounding mechanism — each pulse cycle benefits from accumulated workspace state.

**Three distinct concerns** (ADR-126):
- **Pulse cadence**: How often does the agent sense its domain? (scales with seniority)
- **Generation decision**: Should I produce output? (agent's own pulse decides)
- **Delivery timing**: When does the user receive it? (project-level, PM-coordinated)

**Key axiom**: Every project gets a PM. No exceptions. PM agents are project infrastructure, excluded from tier agent limits. Agents produce; projects deliver. See [PROJECT-DELIVERY-MODEL.md](../design/PROJECT-DELIVERY-MODEL.md).

For the canonical phase-by-phase breakdown of standalone agent flow — including timeline, separation of concerns, and the compounding mechanism — see [VALUE-CHAIN.md](VALUE-CHAIN.md).

### Two Modes of Value

Both are valid. The architecture optimizes for the autonomous path while fully supporting the directed path.

- **Autonomous work**: System recognizes need → creates agents → delivers value → user refines
- **Directed work**: User asks TP → TP responds or creates agents → user gets what they asked for

Over time, the balance shifts toward autonomous. Early users direct more; tenured users supervise more. This is the natural consequence of agents developing expertise (Axiom 3) and the recursive substrate accumulating judgment (Axiom 2).

### Implication: Work Context Over Configuration Breadth

A user who describes their work and sees correctly-scoped projects with agents that understand their domain has more confidence than a user who connects Slack and gets a generic recap of everything. The system should optimize for understanding the user's work over maximizing platform coverage.

### Implication: Work Types Carry Lifecycle

Work descriptions carry implicit lifecycle. "I have 3 clients" implies persistent, recurring work. "I need a board deck" implies bounded, deliverable-scoped work. The system infers lifecycle from the work description — the user does not configure it. Persistent work gets full PM coordination. Bounded work gets lightweight PM that dissolves on completion. See ADR-132.

---

## Derived Principles

These follow from the axioms and are stated explicitly for implementation guidance:

1. **Two layers, clear separation** — TP handles meta-cognition (composition, supervision, orchestration). Agents handle domain cognition (expertise, execution, accumulation). Neither does the other's job. A coordination-domain agent (PM) is still domain-cognitive — it doesn't become a third layer.
2. **Workspace is the shared OS** — All persistent state (agent memory, outputs, user knowledge, TP assessments) lives in the workspace filesystem. External platforms flow through `platform_content` with TTLs; internal content persists and compounds.
3. **Agents are the write path** — All modifications to workspace files, project folders, and agent state flow through agent primitives, not direct user manipulation. The frontend is read-only on workspace (objective editing via API is the exception — it's charter-level, not operational). User intent goes through TP → agents. This protects the structural conventions (folder hierarchy, manifests, lifecycle metadata) that agents depend on for coordination. User feedback on outputs is the exception — it flows through the feedback distillation pipeline, which is itself an agent-mediated write.
4. **Accumulation over extraction** — Prioritize the health of the recursive accumulation loop over the breadth of external integrations. The internal/reflexive perception layers are more valuable long-term than the external layer.
5. **Agents develop through knowledge, not capability expansion** — Agent capabilities are fixed by type. Development is about knowledge depth: accumulated memory, learned preferences, refined domain expertise. The architecture supports this deepening through workspace state (memory, feedback distillation, self-assessment), not through mechanical capability unlocking.
6. **Feedback is perception** — User edits, approvals, and dismissals are first-class signals, equivalent in architectural importance to platform data. They drive both agent development (Axiom 3) and TP's compositional judgment (Axiom 5).
7. **Singular implementation** — One way to do things. If TP can compose, there is no separate composer service. If intentions subsume triggers, there is no parallel trigger system.
8. **Work is bounded** — Autonomous work (agent runs, assemblies, renders) consumes work units. The system must have a governor that bounds total autonomous compute per user, regardless of how many agents or projects exist. This prevents unbounded objectives from consuming infinite resources and is the basis for the service model users pay for.
9. **Agent types determine capabilities; output is structured, not formatted** — Agent capabilities are determined by agent type (deterministic, fixed at creation), not earned through seniority or feedback. Three registries define the capability substrate: Agent Types (capability bundles), Capabilities (what each enables + where it executes), Runtimes (where compute happens). Capabilities, presentation, and export are three separate concerns: agents produce structured content, the platform renders it visually via layout modes, and legacy formats are mechanical exports. Agent development is knowledge depth (accumulated memory, preferences, domain expertise), not capability breadth. See ADR-130.

---

## Relationship to Existing ADRs

| ADR | Relationship to Foundations | Status Under Foundations |
|-----|---------------------------|------------------------|
| ADR-072 (Unified Content Layer) | Implements Axiom 2 — shared content substrate | Aligned |
| ADR-073 (Unified Fetch Architecture) | Implements Axiom 2 L0 — single perception path | Aligned |
| ADR-080 (Unified Agent Modes) | Implements Axiom 1 — one agent, two modes (chat + headless) | Aligned |
| ADR-092 (Mode Taxonomy) | Implements trigger axis — **needs revision**: proactive/coordinator are TP capabilities (Axiom 5), not agent modes | Partially superseded |
| ADR-101 (Intelligence Model) | Implements Axiom 4 — four-layer knowledge model | Aligned |
| ADR-102 (YARNNN Content Platform) | Implements Axiom 2 — agent outputs as perception | Aligned |
| ADR-106 (Workspace Architecture) | Implements Axiom 2/4 — workspace as shared OS | Aligned |
| ADR-109 (Agent Framework) | Implements taxonomy — **needs revision**: trigger axis and static skill model don't accommodate agent development (Axiom 3) | Partially superseded |
| ADR-111 (Agent Composer) | Implements Axiom 5 — Composer delegates project execution to PM agents (v3 update) | Aligned (post v3) |
| ADR-112 (Sync Efficiency) | Implements Axiom 2 L0 — perception reliability | Aligned |
| ADR-118 (Skills as Capability Layer) | Implements Axiom 1 capability axis — skill library as agent toolbox. **Phase D format-builder skills partially superseded by ADR-130** | Partially superseded (Phase D) |
| ADR-119 (Workspace Filesystem) | Implements Axiom 2 workspace-as-OS — folder conventions, project folders, manifests | Aligned |
| ADR-120 (Project Execution & Work Budget) | Implements Axioms 1+5+6 — PM agents, project heartbeat, work budget governor | Implemented |
| ADR-121 (PM Intelligence Director) | Implements Axiom 1 (PM developmental trajectory) + Axiom 3 (agents develop inward) — PM evolves from logistics to quality assessment, directive steering, investigation | Proposed |
| ADR-124 (Project Meeting Room) | Implements Axiom 2 (conversation as fourth perception layer — project transcript alongside external/internal/reflexive), Axiom 3 (agents as participants with presence), Axiom 4 (accumulated attention visible in conversation). Three data scopes (agent/group/project). Project surface as group chat. Extends ADR-080 with `agent_chat` mode. | Proposed |
| ADR-128 (Multi-Agent Coherence Protocol) | Corollary to Axiom 2 (three intelligence substrates + four coherence flows), Axiom 3 (cognitive files as developmental mechanism). Contributor self-assessment, PM project assessment, chat directive persistence, cross-agent visibility. | Proposed |
| ADR-130 (Agent Capability Substrate) | Implements Derived Principle 9 — three-registry architecture (Agent Types, Capabilities, Runtimes). Deterministic type-based capabilities replace seniority-gated progression. Three-concern separation (capability/presentation/export). Supersedes ADR-118 Phase D + ADR-117 seniority-gated capabilities. | Proposed |

---

## Open Questions

These require further design work before implementation:

1. **Intention model** — How are agent intentions represented? Are they explicit (stored in workspace) or implicit (derived from agent behavior)? How does TP create, modify, or retire an agent's intentions?

2. ~~**Capability gating mechanism** — How does the system track and enforce which capabilities an agent has earned?~~ → **Resolved by ADR-130.** Capabilities are determined by agent type, fixed at creation. No earning, no tracking. Three-registry architecture (Agent Types, Capabilities, Runtimes).

3. ~~**Autonomy graduation criteria** — What constitutes "enough feedback" to graduate from supervised to semi-autonomous?~~ → **Resolved by ADR-130.** Consequential actions gated by explicit user authorization per agent, not earned through seniority.

4. **Multi-intention scheduling** — If an agent holds multiple intentions with different temporal profiles (daily digest + event-driven monitoring + goal-driven research), how does the scheduler express this? Is it multiple scheduled entries for one agent?

5. **Agent evolution mechanics** — When an agent's domain expands (e.g., Slack digest agent starts also monitoring email threads from the same team), does it become a new agent or does the existing agent's scope expand? Who decides?

6. ~~**Composer bootstrapping** — What is the minimum substrate assessment needed to scaffold a high-confidence agent within 30 seconds? This is a product question with architectural implications.~~ → **Addressed by ADR-132.** Work description is the primary onboarding input. Work units extracted → projects scaffolded. Platform connections enrich existing projects rather than creating new ones.

7. **Proactive/coordinator code disposition** — The existing proactive review and coordinator primitives implement TP capabilities as agent modes. Can the mechanics be preserved while reframing conceptually, or does the code need structural changes?

8. ~~**Project execution mechanics** — How does the PM agent's heartbeat work? What are its primitives? How does it detect assembly readiness?~~ → **Addressed by ADR-120.**

9. ~~**Work budget model** — How are work units counted, allocated, and enforced? Per-project budgets vs. global user budget?~~ → **Addressed by ADR-120.** Pricing model (credits vs. subscription) deferred to post-validation.

10. **Filesystem hardening** — What frontend surfaces need read-only constraints? How do user edits on output flow through feedback distillation without bypassing agent-mediated writes? (Partially addressed by Derived Principle 3.)

11. ~~**PM qualitative intelligence** — How does the PM assess contribution quality beyond freshness? How does it steer contributors toward underexplored aspects of the project objective?~~ → **Addressed by ADR-121.** PM evolves from logistics coordinator to intelligence director with quality assessment, contribution briefs, and investigation requests. **ADR-123** clarifies ownership: objective is User/Composer/TP-owned; PM reads it as quality reference but doesn't change it.

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
