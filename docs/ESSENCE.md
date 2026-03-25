# YARNNN Essence

**Purpose**: Canonical product narrative. What YARNNN is, what users are buying, and what must remain true as the implementation evolves.
**Status**: Active
**Date**: 2026-01-28
**Updated**: 2026-03-25 (v11.0 — ADR-138 agents as work units, ADR-139 workfloor surface architecture)

---

## Core Thesis

YARNNN is an **autonomous agent platform for recurring knowledge work**.

It connects to the tools where work already lives, accumulates context over time, creates persistent agents around recurring jobs, and lets the user supervise outcomes instead of rebuilding the same context and drafts every cycle.

**The value proposition in one sentence:**
> Persistent agents with accumulated context do recurring work products for you, and supervision gets lighter the longer they run.

## What Stays Constant

The product essence has four stable elements:

1. **Persistent agents, not session threads**  
   Each agent has its own identity, directives, memory, workspace, sources, and execution history.

2. **Accumulated context, not prompt reconstruction**  
   Slack, Gmail, Notion, Calendar, workspace memory, prior outputs, and user feedback all compound into future runs.

3. **Supervision, not manual operation**  
   The user does not re-prompt from zero every time. The user reviews, redirects, and refines a running system.

4. **Recurring work products, not one-off answers**  
   The system exists to produce useful work on cadence: recaps, briefs, monitoring outputs, research, synthesis, and richer rendered artifacts when the job requires them.

## What Changed Recently

ADR-138 simplified the execution model. The project layer (PM agents, phase dispatch, meeting rooms) was dissolved. The new model separates WHO from WHAT:

- **Agents = WHO** — persistent domain experts with identity, memory, and capabilities. Four archetypes: monitor, researcher, producer, operator.
- **Tasks = WHAT** — defined work units with objective, cadence, delivery, and success criteria. TASK.md is the source of truth.
- **TP orchestrates** — creates agents and tasks, monitors health, coordinates multi-agent work directly. No PM intermediary.

The product promise is unchanged: compounding autonomous work through supervision. The architecture got simpler and cheaper (~65% cost reduction per cycle).

> Users are still buying compounding autonomous work.
> Agents are domain experts. Tasks define the work. TP orchestrates.

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

### 1. TP: The Meta-Cognitive Layer

The Thinking Partner (TP) is the system's meta-intelligence.

Its job is not to own a domain. Its job is to manage the user's cognitive workforce:

- converse with the user
- scaffold agents
- supervise agent health
- interpret feedback
- adjust the system over time

TP is the interface through which the user directs and supervises the system.

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
- Simple tasks: 1 agent. Complex tasks: multiple agents, TP orchestrates the sequence.

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
  TP is an interface into a running system, not the whole product.

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

> YARNNN connects to the tools where your work already lives, creates persistent agents for recurring jobs, and helps you supervise outputs that improve with every cycle.

Short forms that remain valid:

- **Autonomous AI that knows your work**
- **Compounding autonomy for recurring knowledge work**
- **Connect once. Supervise from there.**

---

## Source Of Truth Hierarchy

For product narrative and architecture, use this order:

1. `docs/ESSENCE.md` — product essence and stable value proposition
2. `docs/architecture/FOUNDATIONS.md` — first-principles cognitive architecture
3. `docs/adr/ADR-138-agents-as-work-units.md` — agents + tasks architecture (supersedes projects)
4. `docs/adr/ADR-139-workfloor-task-surface-architecture.md` — frontend surfaces
5. `docs/architecture/agent-framework.md` — canonical agent taxonomy
6. `docs/adr/ADR-118-skills-as-capability-layer.md` — output skills and output gateway

If lower-level docs contradict this essence without justification, the lower-level docs should be revised.
