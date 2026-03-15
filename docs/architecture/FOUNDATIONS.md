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

### The Relationship

TP creates agents. Agents don't create TP capabilities. TP monitors agents. Agents don't monitor TP. TP can dissolve agents. Agents can't dissolve TP capabilities. The flow is always: **TP judges what attention is warranted → agents execute that attention → outputs feed back to TP for further judgment.**

But agents are not mere functions. They accumulate domain knowledge that TP doesn't have. A mature Slack agent understands the team's communication patterns in a way TP's general intelligence does not. TP respects this — it orchestrates based on what agents know, not despite it.

| | TP (Meta-Cognitive) | Agent (Domain-Cognitive) |
|---|---|---|
| **Owns** | System's attention allocation | A specific domain of the user's work |
| **Develops** | Better judgment about what agents to create/adjust/dissolve | Deeper expertise in domain, more capable execution |
| **Autonomy means** | Scaffolding agents without being asked | Taking multi-step action in domain without supervision |
| **Accumulates** | System-level patterns (what works for this user) | Domain-level knowledge (what matters in this area) |
| **Identity** | "I manage this user's cognitive workforce" | "I own [domain] and develop expertise in it" |

---

## Axiom 2: The Perception Substrate Is Recursive

Perception is not just external platform data. The perception substrate is **everything the system can observe**, including its own outputs and the user's feedback on those outputs.

### Three Layers of Perception

1. **External perception** — platform sync fills `platform_content` from Slack, Gmail, Notion, Calendar. This is the surface area for onboarding and existing work.

2. **Internal perception** — agent outputs, written to `platform_content` (platform="yarnnn") and workspace files, feed back into the shared content layer. An agent's output is another agent's input. TP's observations are part of the substrate.

3. **Reflexive perception** — user feedback (edits, approvals, dismissals, conversational corrections) and TP's own compositional reasoning create a shared recursive layer. As time progresses, this accumulated judgment becomes the most valuable signal — more valuable than raw platform data.

### The Recursive Property

```
External platforms → platform_content → agent execution → agent output →
  platform_content (yarnnn) + workspace → next agent execution → ...
                                    ↑                           |
                                    └── user feedback ──────────┘
                                    └── TP assessment ──────────┘
```

The YARNNN content filesystem (`workspace_files` + `platform_content`) acts as an **operating system for agent and human work** — a shared substrate where both contribute and both consume.

### Implication: Optimize for Accumulation, Not Extraction

The external platform integrations are the onramp. The enduring value is in the recursive accumulation: agent memory, learned preferences, domain theses, cross-agent insights. As LLM capabilities improve, the quality of each recursive cycle improves — the system's reasoning gets better at the same substrate. This compounds. The architecture must accommodate that compounding.

Architecture decisions should prioritize the health of this recursive loop over the breadth of external integrations.

---

## Axiom 3: Agents Are Developing Entities

An agent is not a static configuration that runs the same task forever. An agent is a **persistent entity with a developmental trajectory**.

### The Agent Lifecycle

An agent progresses through phases, driven by accumulated experience and earned trust:

```
Creation → Early Tenure → Developing → Mature → [Evolved | Dissolved]
```

At each phase, the agent's relationship to its domain deepens:

- **Creation**: Single skill, single trigger, read-only. Produces drafts for review.
- **Early Tenure**: Accumulating observations. Learning what the user cares about from edits and feedback.
- **Developing**: Multiple concurrent intentions emerge. May notice patterns worth investigating beyond its initial skill. Begins to hold a domain thesis.
- **Mature**: Multi-step execution within its domain. Has earned autonomy for routine actions. Domain thesis is refined through accumulated feedback.
- **Evolved**: Agent's capabilities have expanded. What started as a digest agent now monitors, researches, and acts within its domain. TP may split a mature agent into specialized sub-patterns, or an agent may absorb adjacent responsibilities.

### Three Dimensions of Agent Development

**Intentions** — what the agent is currently trying to accomplish.

An agent's intentions are dynamic and can be multiple. A Slack agent might simultaneously:
- Digest daily activity (recurring intention)
- Investigate a misalignment pattern it noticed (goal-driven intention)
- Monitor for escalation signals (reactive intention)

Intentions are not the agent's static trigger — they are the agent's evolving understanding of what its domain requires. An intention can emerge from the agent's own observations, from TP's assessment, or from user direction.

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

### Implication: The Trigger Is a Property of the Intention, Not the Agent

The current taxonomy treats trigger as a static agent property (recurring, goal, reactive). Under the developmental model, trigger is a property of each **intention**:

- A recurring intention executes on a schedule (daily digest)
- A goal-driven intention executes until a condition is met (investigate this pattern)
- A reactive intention executes when an event occurs (escalation detected)

A mature agent holds multiple intentions with different triggers simultaneously. The agent's "mode" is the composite of its active intentions, not a single static setting.

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

1. **Substrate Assessment** — "What can I perceive?" Evaluates connected platforms, available data, existing agents, user feedback patterns.
2. **Need Recognition** — "What sustained attention is warranted?" Identifies cognitive patterns that would produce value (Axiom 4 — this is about sustained attention, not one-shot tasks).
3. **Agent Scaffolding** — "What entity should I create?" Maps recognized needs to agent identities, then to configurations. High-confidence needs are auto-scaffolded; medium-confidence are suggested to the user.
4. **Lifecycle Management** — "Are my agents developing well?" Reviews agent health, output quality, feedback patterns. Adjusts, evolves, or dissolves agents.

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

Steps 3-5 are the Composer capability. Step 7 closes the recursive loop (Axiom 2). Step 8 is agent development (Axiom 3).

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

1. **Two layers, clear separation** — TP handles meta-cognition (composition, supervision, orchestration). Agents handle domain cognition (expertise, execution, accumulation). Neither does the other's job.
2. **Workspace is the shared OS** — All persistent state (agent memory, outputs, user knowledge, TP assessments) lives in the workspace filesystem. External platforms flow through `platform_content` with TTLs; internal content persists and compounds.
3. **Accumulation over extraction** — Prioritize the health of the recursive accumulation loop over the breadth of external integrations. The internal/reflexive perception layers are more valuable long-term than the external layer.
4. **Agents develop, they don't just execute** — The architecture must support intention evolution, capability progression, and autonomy graduation. Static configuration is the starting point, not the steady state.
5. **Feedback is perception** — User edits, approvals, and dismissals are first-class signals, equivalent in architectural importance to platform data. They drive both agent development (Axiom 3) and TP's compositional judgment (Axiom 5).
6. **Singular implementation** — One way to do things. If TP can compose, there is no separate composer service. If intentions subsume triggers, there is no parallel trigger system.

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
| ADR-111 (Agent Composer) | Implements Axiom 5 — but as a separate service, not TP capability | Needs reframe |
| ADR-112 (Sync Efficiency) | Implements Axiom 2 L0 — perception reliability | Aligned |

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

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-15 | v1 — Initial axioms: one intelligence, recursive perception, accumulated attention, taxonomy as configuration, TP subsumes orchestration, autonomy as direction |
| 2026-03-15 | v2 — Major revision: two-layer intelligence model (TP meta-cognitive + agent domain-cognitive), agent developmental trajectory (intentions, capabilities, autonomy), recursive perception expanded to include internal/reflexive layers as primary long-term value, proactive/coordinator reframed as TP capabilities, trigger as intention property not agent property |
