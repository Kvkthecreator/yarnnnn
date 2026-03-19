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

1. **External perception** — platform sync fills `platform_content` from Slack, Gmail, Notion, Calendar. This is the surface area for onboarding and existing work.

2. **Internal perception** — agent outputs, written to `/knowledge/` files in `workspace_files` (ADR-107, superseding ADR-102's `platform_content` rows), feed back into the shared knowledge layer. An agent's output is another agent's input. TP's observations are part of the substrate.

3. **Reflexive perception** — user feedback (edits, approvals, dismissals, conversational corrections) and TP's own compositional reasoning create a shared recursive layer. As time progresses, this accumulated judgment becomes the most valuable signal — more valuable than raw platform data.

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

### The Agent Lifecycle

An agent progresses through seniority levels, driven by accumulated experience and earned trust:

```
Creation → New → Associate → Senior → [Evolved | Dissolved]
```

At each level, the agent's relationship to its domain deepens:

- **New**: Single duty, single trigger, read-only. Produces drafts for review. Learning what the user cares about from edits and feedback.
- **Associate**: Consistent performer with earned trust (≥5 runs, ≥60% approval). Holds a developing domain thesis. Accumulating observations and preferences.
- **Senior**: Eligible for expanded duties within pre-configured career tracks (≥10 runs, ≥80% approval). What started as a digest agent now monitors, researches, and acts within its domain — each as a separate duty sharing the accumulated workspace context.
- **Evolved**: Agent's duty portfolio is fully expanded. Domain thesis is refined through extensive accumulated feedback. TP may split a senior agent into specialized sub-patterns, or an agent may absorb adjacent responsibilities.

### Three Dimensions of Agent Development

**Duties** — what the agent is responsible for.

An agent's duties expand with seniority and can be multiple. A senior Slack agent might simultaneously:
- Digest daily activity (recurring duty — seed role)
- Monitor for escalation signals (reactive duty — earned at senior seniority)

Duties are pre-configured per role portfolio (ADR-117 Phase 3). A duty can be earned through feedback-gated seniority progression — Composer promotes along deterministic tracks. Each duty carries its own trigger type and uses the duty's role for execution (prompt, primitives, output skills).

Note: "Objectives" at the project level (ADR-123) are distinct — they represent the project's north star (what, for whom, why, in what form), not agent responsibilities.

**Capabilities** — what actions the agent can take.

Capabilities expand with tenure:
- **Read**: observe and summarize (default, always available)
- **Analyze**: cross-reference, identify patterns, produce insights (available early)
- **Write-back**: post to platforms, send messages, update documents (earned through demonstrated quality)
- **Act**: take consequential actions in external systems (highest trust, requires explicit user authorization)

The progression is not automatic — it's gated by feedback history. An agent that consistently produces approved outputs earns write-back capability. An agent whose outputs are frequently edited stays in supervised mode longer.

**Autonomy** — how much supervision each action requires.

Autonomy is graduated and domain-specific:
- **Supervised**: all outputs are drafts, user must approve before delivery
- **Semi-autonomous**: routine outputs auto-deliver, novel or high-stakes outputs require review
- **Autonomous**: agent acts within its domain without supervision, user is notified post-hoc
- **Trusted**: agent can take consequential external actions (e.g., post to social media, send emails)

Autonomy is earned per-capability, not globally. An agent might be autonomous for digests but supervised for write-backs.

### Implication: The Trigger Is a Property of the Duty, Not the Agent

The current taxonomy treats trigger as a static agent property (recurring, goal, reactive). Under the developmental model, trigger is a property of each **duty**:

- A recurring duty executes on a schedule (daily digest)
- A goal-driven duty executes until a condition is met (investigate this pattern)
- A reactive duty executes when an event occurs (escalation detected)

A senior agent holds multiple duties with different triggers simultaneously. The agent's "mode" is the composite of its active duties, not a single static setting.

### Objectives at Project Scope (ADR-123)

Projects have objectives — their north star — and they exhibit a key paradox: **an objective is flat data from the user, but its ramifications can be wide-reaching.** Compare:

- "I want an Excel and PPT on my company's Q2 report" — bounded objective, 2-3 agents, known skills, predictable work
- "I want the most comprehensive analysis possible on market trends" — unbounded objective, potentially infinite agents/files/runs

The PM agent's core cognitive task is **translating the objective into executable, bounded work** — decomposing a user's project objective into an operational work plan: which agents contribute, which skills produce output, what cadence, what assembly format, and how much budget to allocate. The work budget (ADR-120) prevents unbounded objectives from consuming infinite resources.

Objectives include delivery and format preferences: the user wants email delivery, or a PPTX deck, or both CSV and PDF. These preferences are data in PROJECT.md's `## Objective` section — they shape the PM's assembly decisions and skill selection. The PM's operational execution plan lives separately in `memory/work_plan.md` (ADR-123: charter vs. operations separation).

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

Under the previous swarm framing, proactive and coordinator were agent modes — agents that assessed and orchestrated. Under this framing:

- **Proactive review** (per-agent "should I generate?") is better understood as **TP's supervisory capability** — TP assessing whether a specific agent should produce output right now. The review logic accumulates in the agent's workspace (review logs, observations), but the *decision to review* belongs to TP.

- **Coordinator mode** (creating child agents) is **the Composer capability itself** — TP spawning agents based on assessed need. This is not an agent behavior; it's a TP behavior.

The existing code for proactive review and coordination may be preserved mechanically (the Haiku review pass, the CreateAgent primitive), but conceptually they are TP functions, not agent modes.

---

## Axiom 6: Autonomy Is the Product Direction

The product vision is: **sign up, connect, watch it work for you.**

### The Autonomous Flow

**Standalone agents** (existing):
```
1. User connects platform
2. Sync fires (L0 — external perception)
3. TP/Composer assesses substrate (need recognition)
4. High-confidence agents scaffolded automatically
5. First agent run executes immediately
6. User sees output on dashboard within 30-60 seconds
7. User feedback refines future runs (reflexive perception)
8. Agents develop over time — deeper expertise, broader capabilities, higher autonomy
```

**Projects** (multi-agent, ADR-120):
```
1. User requests project (or Composer detects composition opportunity)
2. TP/Composer creates PM agent + identifies/creates contributors
3. PM decomposes objective into work plan with budget bounds
4. Contributing agents run on their schedules, writing to project contributions/
5. PM detects contribution freshness → triggers assembly when ready
6. Assembly produces composed deliverable (PPTX, PDF, etc.) via skills
7. Deliverable arrives — user feedback refines PM's coordination + contributors' outputs
8. Recursive: next cycle's contributions are better because agents learned, PM learned
```

Steps 1-3 are the Composer capability. Steps 4-6 are PM execution. Step 7 closes the recursive loop. Step 8 is the compounding mechanism across the project lifecycle.

For the canonical phase-by-phase breakdown of standalone agent flow — including timeline, separation of concerns, and the compounding mechanism — see [VALUE-CHAIN.md](VALUE-CHAIN.md).

### Two Modes of Value

Both are valid. The architecture optimizes for the autonomous path while fully supporting the directed path.

- **Autonomous work**: System recognizes need → creates agents → delivers value → user refines
- **Directed work**: User asks TP → TP responds or creates agents → user gets what they asked for

Over time, the balance shifts toward autonomous. Early users direct more; tenured users supervise more. This is the natural consequence of agents developing expertise (Axiom 3) and the recursive substrate accumulating judgment (Axiom 2).

### Implication: First-Run Quality Over Configuration Breadth

A user who sees one excellent, automatically-generated output within 60 seconds of connecting Slack has more confidence in the system than a user who spends 5 minutes configuring 3 agents manually. The Composer should optimize for first-run quality over coverage.

---

## Derived Principles

These follow from the axioms and are stated explicitly for implementation guidance:

1. **Two layers, clear separation** — TP handles meta-cognition (composition, supervision, orchestration). Agents handle domain cognition (expertise, execution, accumulation). Neither does the other's job. A coordination-domain agent (PM) is still domain-cognitive — it doesn't become a third layer.
2. **Workspace is the shared OS** — All persistent state (agent memory, outputs, user knowledge, TP assessments) lives in the workspace filesystem. External platforms flow through `platform_content` with TTLs; internal content persists and compounds.
3. **Agents are the write path** — All modifications to workspace files, project folders, and agent state flow through agent primitives, not direct user manipulation. The frontend is read-only on workspace (objective editing via API is the exception — it's charter-level, not operational). User intent goes through TP → agents. This protects the structural conventions (folder hierarchy, manifests, lifecycle metadata) that agents depend on for coordination. User feedback on outputs is the exception — it flows through the feedback distillation pipeline, which is itself an agent-mediated write.
4. **Accumulation over extraction** — Prioritize the health of the recursive accumulation loop over the breadth of external integrations. The internal/reflexive perception layers are more valuable long-term than the external layer.
5. **Agents develop, they don't just execute** — The architecture must support intention evolution, capability progression, and autonomy graduation. Static configuration is the starting point, not the steady state.
6. **Feedback is perception** — User edits, approvals, and dismissals are first-class signals, equivalent in architectural importance to platform data. They drive both agent development (Axiom 3) and TP's compositional judgment (Axiom 5).
7. **Singular implementation** — One way to do things. If TP can compose, there is no separate composer service. If intentions subsume triggers, there is no parallel trigger system.
8. **Work is bounded** — Autonomous work (agent runs, assemblies, renders) consumes work units. The system must have a governor that bounds total autonomous compute per user, regardless of how many agents or projects exist. This prevents unbounded objectives from consuming infinite resources and is the basis for the service model users pay for.

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
| ADR-118 (Skills as Capability Layer) | Implements Axiom 1 capability axis — skill library as agent toolbox | Aligned |
| ADR-119 (Workspace Filesystem) | Implements Axiom 2 workspace-as-OS — folder conventions, project folders, manifests | Aligned |
| ADR-120 (Project Execution & Work Budget) | Implements Axioms 1+5+6 — PM agents, project heartbeat, work budget governor | Implemented |
| ADR-121 (PM Intelligence Director) | Implements Axiom 1 (PM developmental trajectory) + Axiom 3 (agents develop inward) — PM evolves from logistics to quality assessment, directive steering, investigation | Proposed |

---

## Open Questions

These require further design work before implementation:

1. **Intention model** — How are agent intentions represented? Are they explicit (stored in workspace) or implicit (derived from agent behavior)? How does TP create, modify, or retire an agent's intentions?

2. **Capability gating mechanism** — How does the system track and enforce which capabilities an agent has earned? Is this a property of the agent record, derived from feedback history, or managed by TP?

3. **Autonomy graduation criteria** — What constitutes "enough feedback" to graduate from supervised to semi-autonomous? Is this per-capability or global? Who decides — TP or the user?

4. **Multi-intention scheduling** — If an agent holds multiple intentions with different temporal profiles (daily digest + event-driven monitoring + goal-driven research), how does the scheduler express this? Is it multiple scheduled entries for one agent?

5. **Agent evolution mechanics** — When an agent's domain expands (e.g., Slack digest agent starts also monitoring email threads from the same team), does it become a new agent or does the existing agent's scope expand? Who decides?

6. **Composer bootstrapping** — What is the minimum substrate assessment needed to scaffold a high-confidence agent within 30 seconds? This is a product question with architectural implications.

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
