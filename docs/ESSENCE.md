# YARNNN Essence

**Purpose**: Canonical product narrative. What YARNNN is, what users are buying, and what must remain true as the implementation evolves.
**Status**: Active
**Date**: 2026-01-28
**Updated**: 2026-04-20 (v12.3 — Cockpit service model ratified per ADR-198 v2. "What Stays Constant" extended to six elements; operator works *inside* YARNNN rather than consuming deliverables elsewhere.)

---

## Core Thesis

YARNNN is an **autonomous agent platform for recurring knowledge work** — the team you build by chatting.

The user describes their work to YARNNN, creates Agents around it through that conversation, and supervises outcomes as the Agents run on cadence with accumulated context. The relationship is authorship, not delegation: the team is the user's, built up over time, switching cost accumulates from the first Agent.

**The product promise in one sentence:**
> Describe your work. Create the agents that do it.

Short form: *Your work, your agents.*

## What Stays Constant

The product essence has six stable elements:

1. **Agents built around your work, not generic assistants**  
   Agents are created by the user through conversation with YARNNN, scoped to a specific domain of the user's work, with identity, directives, memory, workspace, sources, and execution history. Zero Agents are pre-scaffolded — the team is authored, not provisioned (ADR-189).

2. **Accumulated context, not prompt reconstruction**  
   Slack, Notion, GitHub, workspace memory, prior outputs, and user feedback all compound into future runs. Specialists accumulate role-scoped style; Agents accumulate domain-scoped expertise. The two axes are distinct and both compound (ADR-117, ADR-189).

3. **Supervision, not manual operation**  
   The user does not re-prompt from zero every time. The user reviews, redirects, and refines a running system. The team the user built keeps running.

4. **Recurring work products, not one-off answers**  
   The system exists to produce useful work on cadence: recaps, briefs, monitoring outputs, research, synthesis, and richer rendered artifacts when the job requires them.

5. **Money-truth, not vibe-truth**  
   YARNNN is a money-making platform for operators. Every action the team takes is attributable to a capital outcome — trades to P&L, campaigns to revenue, discounts to attribution. Accumulated context is pruned by what actually made money, not by what sounded good. Reviewers (human or AI) judge proposals in expected-value terms given the operator's book and track record. The team gets better at its job, and the job is making the operator money (FOUNDATIONS Axiom 8, ADR-194, ADR-195).

6. **Cockpit, not report factory**
   The operator works *inside* YARNNN. Five destinations — Overview (what's going on), Team (agents), Work (tasks), Context (what the workspace knows), Review (the judgment trail) — plus an always-present YARNNN rail. This is the operator's cockpit: where performance is consulted, the team is supervised, pending decisions are made, the workforce is tuned, and the judgment trail is audited. External distribution (email to stakeholders, Slack posts, PDF exports) is a **derivative Channel**, not the primary output. Autonomous writes have a legible cockpit Channel back to the operator — an operator who can't see the workforce cannot trust it. The cockpit framing is what makes trusted autonomy possible (ADR-198, FOUNDATIONS Derived Principle 12).

## What Changed Recently

ADR-189 introduced the three-layer cognition model. The prior model conflated "agents" as a single concept; the new model separates three distinct layers with distinct scopes and developmental axes:

- **YARNNN = the super-agent** — the product and the conversational layer share a name. The user addresses YARNNN directly. YARNNN composes, supervises, and orchestrates.
- **Specialists = YARNNN's palette** — six role-typed capabilities (Researcher, Analyst, Writer, Tracker, Designer, Reporting). Infrastructure; not user-addressed. Develop stylistic preference across all tasks using them.
- **Agents = WHO (user-created)** — persistent, identity-explicit, domain-scoped workers. Each Agent is created by the user through conversation with YARNNN. Appear on `/agents`. Develop domain expertise over tenure.
- **Tasks = WHAT** — defined work units with objective, cadence, delivery, and success criteria. TASK.md is the source of truth. A task's Team is drafted by YARNNN from the Specialist palette per cycle.

Users are buying an authored team that compounds. The team is theirs — built up through conversation, supervised over time, richer with tenure.

> Users buy an authored team that compounds.
> YARNNN orchestrates. Specialists draft style. Agents carry domain. Tasks define the work.

---

## The Product Model

### From Operator To Supervisor

YARNNN embodies a shift in how users relate to AI-assisted work:

**From**: user as operator  
**To**: user as supervisor

The user is no longer responsible for repeatedly:

- gathering source context
- restating goals
- regenerating the same recurring draft
- manually stitching work across tools

Instead, the system maintains context, runs recurring jobs, delivers work, and improves through supervision.

### From Prompts To Persistent Attention

The unit of value is not the chat turn. It is the **persistent agent**.

An agent is a standing unit of attention allocated to some part of the user's work:

- a Slack recap
- a meeting-prep specialist
- a competitor watch
- a weekly cross-platform brief
- a domain researcher

Each agent compounds because the same specialist keeps running against the same domain over time.

### From Answers To Work Products

YARNNN is not primarily a system for answering questions.

It is a system for producing recurring work products such as:

- summaries and recaps
- meeting briefs
- monitoring updates
- research reports
- cross-platform syntheses
- rendered artifacts and attachments when the job requires them

The work product may be plain text, email-ready content, or a rendered artifact. That output variation does not change the product category. The job is still the same: autonomous recurring work with supervision.

---

## The System Shape

### 1. YARNNN: The Meta-Cognitive Layer

YARNNN is the system's meta-intelligence — the super-agent the user addresses directly. Product and conversational layer share the name (ADR-189).

Its job is not to own a domain. Its job is to manage the user's cognitive workforce:

- converse with the user
- create Agents through that conversation
- draft Specialist Teams per task
- supervise Agent health
- interpret feedback
- adjust the system over time

YARNNN is the interface through which the user builds, directs, and supervises the team.

### 2. Agents: The Domain-Cognitive Layer (WHO)

Agents are persistent domain experts. Each handles the full thinking chain: sense context, reason about it, produce output.

They exist as developing workers with:

- an archetype (monitor, researcher, producer, operator)
- a workspace with identity file (AGENT.md) and accumulated memory
- learned preferences from user feedback
- domain knowledge that compounds with every run

Agents are where recurring attention lives.

### 3. Tasks: The Work Definition Layer (WHAT)

Tasks define units of work: what to produce, for whom, on what cadence, delivered where.

- TASK.md carries the objective, success criteria, output spec, and agent assignment
- Tasks run on schedule — the scheduler queries tasks, not agents
- Output accumulates in task workspace (`/tasks/{slug}/outputs/`)
- Simple tasks: 1 Agent, small Specialist Team. Complex tasks: multiple Agents, larger Specialist Team, YARNNN orchestrates the sequence.

Tasks are where work definition lives. Agents are assigned to tasks — one agent can work on multiple tasks.

### 4. Workspace: The Shared Operating Substrate

The workspace is where accumulated intelligence persists:

- agent identity files
- memory
- working notes
- knowledge outputs
- output folders
- user-level context

This is what allows the system to improve with tenure instead of resetting with each interaction.

### 5. Output Skills: The Execution Layer

Output skills make agents more capable, but they do not redefine the product.

They are the agent's toolbox:

- PDF
- presentation
- spreadsheet
- chart
- future delegated or local skills

Output skills enrich the deliverable. They do not change the agent's identity.

---

## The User Experience Loop

The core loop is:

1. **Describe your work — connect tools to enrich it**
2. **System creates the right agents and tasks**
3. **Tasks run on cadence, agents produce, outputs deliver**
4. **The user reviews, refines, or redirects**
5. **Agent memory, preferences, and domain knowledge compound**
6. **Future supervision gets lighter**

That loop is the product.

Everything else is implementation support.

---

## Why This Is Different

Most AI systems fail on recurring work for one of two reasons:

1. They are **session-based**, so they forget the operating context between runs.
2. They are **persistent**, but they do not act autonomously on that persistence.

YARNNN does both:

- it **accumulates**
- it **acts**

That combination is the moat.

The system becomes more valuable with time because:

- the same agents keep running
- the same domains keep deepening
- the same user preferences keep sharpening
- the same outputs keep feeding better future outputs

## The Moat

The moat is not "AI agents" in the abstract.

The moat is **accumulated attention**:

- context from real systems
- agent-specific memory
- recursive knowledge outputs
- user supervision patterns
- durable work history

The longer an agent runs, the harder its judgment is to replicate elsewhere.

---

## What YARNNN Is Not

YARNNN is not:

- **just a chat UI**  
  YARNNN (the conversational layer) is an interface into a running system, not the whole product.

- **generic task automation**  
  The value is recurring, high-context work, not arbitrary one-off commands.

- **template-fill drafting**  
  Agents operate from live context and accumulated judgment, not static input forms.

- **uncontrolled autonomous action**  
  The model is supervised autonomy with history, visible outputs, delivery controls, and explicit user direction.

- **a file conversion product**  
  Rich output skills matter, but they support the recurring-work model. They are not the core category.

---

## Canonical Positioning

If YARNNN must be described simply, the canonical external framing is:

**Primary:**
> Describe your work. Create the agents that do it.

**Short form:**
> Your work, your agents.

**Expanded:**
> YARNNN is the super-agent the user talks to. The user describes their work, creates persistent Agents through that conversation, and supervises outputs that improve with every cycle. The team is built, not provisioned. Switching cost accumulates from the first Agent.

Short forms that remain valid in voice-variation contexts:

- **The team you build by chatting**
- **Compounding autonomy for recurring knowledge work** (internal/architectural)
- **Connect once. Build from there.**

---

## Source Of Truth Hierarchy

For product narrative and architecture, use this order:

1. `docs/ESSENCE.md` — product essence and stable value proposition
2. `docs/architecture/FOUNDATIONS.md` — first-principles cognitive architecture
3. `docs/adr/ADR-138-agents-as-work-units.md` — agents + tasks architecture (supersedes projects)
4. `docs/adr/ADR-139-workfloor-task-surface-architecture.md` — frontend surfaces
5. `docs/architecture/agent-registry.md` — canonical agent taxonomy
6. `docs/adr/ADR-118-skills-as-capability-layer.md` — output skills and output gateway

If lower-level docs contradict this essence without justification, the lower-level docs should be revised.
