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

## Axiom 1: One Intelligence, Many Attention Patterns

YARNNN has **one cognitive entity**: the Thinking Partner (TP). TP is the singular intelligence that mediates between the user and the autonomous system.

**Agents are not independent intelligences.** They are **delegated, specialized attention patterns** — recurring cognitive functions that TP creates, governs, and can dissolve. The metaphor is not "a team of agents." It is **one mind that decides what to pay sustained attention to, how often, and with what purpose.**

This means:
- TP has full situational awareness: all platforms, all agents, all outputs, all user context.
- Agents have scoped awareness: one domain, one skill, one cadence.
- An agent's existence is an expression of TP's judgment that "this domain warrants sustained, recurring attention."
- Agent creation is a significant act — it represents a commitment of the system's cognitive resources.

### Implication: The Composer is a TP Capability

The Composer is not a separate service or agent type. It is TP exercising the judgment: **"given what I can perceive, what sustained attention patterns are warranted?"**

This assessment can be triggered by:
- A platform connection event (new substrate available)
- A user's conversational request
- A periodic self-assessment (TP reviewing its own coverage)
- A feedback signal (user edits, approvals, dismissals)

The Composer capability gives TP proactive self-awareness about the user's work substrate. It answers: "Am I paying attention to the right things, at the right cadence, with the right specialization?"

---

## Axiom 2: The Perception Substrate Is Recursive

Perception is not just external platform data. The perception substrate is **everything the system can observe**, including its own outputs.

### The Three Layers of Perception

1. **External perception** — platform sync fills `platform_content` from Slack, Gmail, Notion, Calendar. This is the surface area for onboarding and "existing work happens."

2. **Internal perception** — agent outputs, written as `platform_content` (platform="yarnnn") and workspace files, feed back into the shared content layer. An agent's output is another agent's input. TP's observations are part of the substrate.

3. **Reflexive perception** — user feedback (edits, approvals, dismissals, conversational corrections) and the Composer's own reasoning create a shared recursive layer. As time progresses, this accumulated judgment becomes the most valuable signal — more valuable than raw platform data.

### The Recursive Property

```
External platforms → platform_content → agent execution → agent output →
  platform_content (yarnnn) + workspace → next agent execution → ...
                                    ↑                           |
                                    └── user feedback ──────────┘
```

This is deliberate. The YARNNN content filesystem (`workspace_files` + `platform_content`) acts as an **operating system for agent and human work** — a shared substrate where both contribute and both consume. Over time, the internal and reflexive layers become more important than the external layer, because they encode accumulated judgment, not just raw signals.

### Implication: Optimize for Accumulation, Not Extraction

The external platform integrations are the onramp. The enduring value is in the recursive accumulation: agent memory, learned preferences, domain theses, cross-agent insights. Architecture decisions should prioritize the health of this recursive loop over the breadth of external integrations.

As LLM capabilities improve, the quality of each recursive cycle improves — the system's reasoning gets better at the same substrate. This compounds. The architecture should accommodate that compounding, not constrain it.

---

## Axiom 3: Value Comes from Accumulated Attention, Not One-Shot Execution

A Slack digest is not valuable because it summarizes today. It is valuable because it summarizes today **knowing what it summarized yesterday, what the user edited last time, and what its domain thesis says matters.**

The agent's **tenure** — its accumulated memory, observations, learned preferences, and domain understanding — is the moat. Agents are persistent entities, not functions.

This means:
- Agent workspace is a first-class architectural concern (not metadata).
- Memory and feedback from prior runs are injected into every subsequent execution.
- The Composer's judgment isn't just "what agents to create" but "what sustained attention patterns are warranted" — because creating an agent is committing to an accumulation trajectory.
- Destroying an agent destroys accumulated judgment. This should be treated with gravity.

### Implication: The Information Hierarchy

Accumulated attention produces layered value:

| Level | What | Example |
|-------|------|---------|
| L0 | Raw signals | Slack messages, email threads, Notion pages |
| L1 | Digests | "Here's what happened in #engineering today" |
| L2 | Insights | "The team discussed migration 3 times this week" |
| L3 | Analysis | "There's a misalignment between eng and product on the migration timeline" |
| L4 | User knowledge | Learned preferences, domain theses, standing instructions |

Lower levels feed higher levels. Higher levels refine what lower levels pay attention to. This is the recursive property in action. Agents at different scopes operate at different levels of this hierarchy.

---

## Axiom 4: The Taxonomy Describes Configuration, Not Identity

The scope × skill × trigger taxonomy (ADR-109) describes **how** an agent is configured:

| Axis | Question | Values |
|------|----------|--------|
| **Scope** | What can it perceive? | platform, cross_platform, knowledge, research, autonomous |
| **Skill** | What does it produce? | digest, prepare, monitor, research, synthesize, orchestrate, act |
| **Trigger** | When does it execute? | recurring, goal, reactive, proactive, coordinator |

But an agent's **identity** is: *"I pay sustained attention to X, in order to produce Y, because this user's work requires it."*

Templates are a convenience layer that maps common identities to configurations. The Composer reasons at the identity level ("this user needs someone watching their team's Slack for alignment issues") and maps to configuration (scope=platform, skill=monitor, trigger=proactive).

### Implication: Composer Reasons About Need, Not Configuration

The Composer's input is the perception substrate (what's available). Its output is agent identities (what attention is warranted). The translation from identity to configuration is mechanical — the taxonomy handles it. The judgment is in the identity recognition.

---

## Axiom 5: TP Subsumes Orchestration

TP is not "the chat interface." TP is the **general-purpose cognitive layer** with full capabilities:

- **Conversational**: responds to user in chat (today)
- **Compositional**: assesses substrate and scaffolds agents (Composer capability)
- **Supervisory**: reviews agent outputs, applies feedback (existing via edit history)
- **Orchestrative**: coordinates across agents, manages lifecycle (today partially via coordinator mode)

The existing `proactive` and `coordinator` agent modes should be understood as **TP delegating a subset of its orchestration to a scheduled process.** They are extensions of TP's judgment running on a timer, not independent actors with their own goals.

This framing clarifies a design question: should `proactive` and `coordinator` remain as agent modes, or should they be folded into TP's capabilities? The answer depends on whether they need independent accumulation trajectories (agent workspace, tenure) or whether they're pure orchestration logic.

**Current assessment**: Proactive review (Haiku pass → generate/observe/sleep) is valuable as an agent mode because the review itself accumulates judgment (review logs, observations). Coordinator mode may be better modeled as a TP capability since its purpose is spawning other agents, not accumulating domain knowledge.

---

## Axiom 6: Autonomy Is the Product Direction

The product vision is evolving toward: **sign up, connect, watch it work for you.**

This means:
- The system must deliver value within 30-60 seconds of minimum setup (platform connection).
- The Composer capability is not optional — it's the mechanism by which the system becomes autonomous.
- "Requested work" (user asks TP) and "autonomous work" (system recognizes and acts) are both valid, but the architecture should optimize for the autonomous path.
- The user's role shifts from "directing work" to "providing feedback on autonomous work" — supervision, not instruction.

### The Autonomous Flow

```
1. User connects platform
2. Sync fires (L0 perception)
3. TP/Composer assesses substrate (L1 recognition)
4. High-confidence agents scaffolded automatically
5. First agent run executes immediately
6. User sees output on dashboard
7. User feedback refines future runs (L4 reflexive loop)
```

Steps 3-5 are the Composer capability. Step 7 closes the recursive loop (Axiom 2).

### Implication: First-Run Quality Matters More Than Configuration Breadth

A user who sees one excellent, automatically-generated digest within 60 seconds of connecting Slack has more confidence in the system than a user who spends 5 minutes configuring 3 agents manually. The Composer should optimize for first-run quality over coverage breadth.

---

## Derived Principles

These follow from the axioms but are stated explicitly for implementation guidance:

1. **Singular implementation** — One way to do things. If TP can compose, there is no separate composer service.
2. **Workspace is the shared OS** — All persistent state (agent memory, outputs, user knowledge) lives in the workspace filesystem. External platforms flow through `platform_content` with TTLs; internal content persists.
3. **Accumulation over extraction** — Architectural decisions should favor the health of the recursive accumulation loop over the breadth of external integrations.
4. **Enforcement follows taxonomy** — Scope determines data access boundaries. Skill determines available primitives. These must be enforced, not advisory.
5. **Feedback is perception** — User edits, approvals, and dismissals are first-class signals, equivalent in architectural importance to platform data.

---

## Relationship to Existing ADRs

| ADR | Relationship to Foundations |
|-----|---------------------------|
| ADR-072 (Unified Content Layer) | Implements Axiom 2 — shared content substrate |
| ADR-073 (Unified Fetch Architecture) | Implements Axiom 2 L0 — single perception path |
| ADR-080 (Unified Agent Modes) | Implements Axiom 1 — one agent, two modes |
| ADR-092 (Mode Taxonomy) | Implements Axiom 4 — trigger axis |
| ADR-101 (Intelligence Model) | Implements Axiom 3 — four-layer knowledge model |
| ADR-102 (YARNNN Content Platform) | Implements Axiom 2 — agent outputs as perception |
| ADR-106 (Workspace Architecture) | Implements Axiom 2/3 — workspace as shared OS |
| ADR-109 (Agent Framework) | Implements Axiom 4 — scope × skill × trigger |
| ADR-111 (Agent Composer) | Implements Axiom 1/6 — TP's compositional capability |
| ADR-112 (Sync Efficiency) | Implements Axiom 2 L0 — perception reliability |

---

## Open Questions

These are not resolved by the axioms and require further design work:

1. **Coordinator mode disposition** — Should coordinator remain an agent mode (with its own accumulation trajectory) or be folded into TP's compositional capability? (See Axiom 5 discussion.)

2. **Proactive mode vs. Composer overlap** — Both assess "should something happen?" Proactive does it per-agent; Composer does it system-wide. Are these the same judgment at different scopes, or fundamentally different operations?

3. **Reactive mode's relationship to event-driven Composer** — If the Composer fires on `platform_connected` events, and reactive agents fire on platform events, what distinguishes them? (Likely: Composer creates agents, reactive agents create outputs.)

4. **Scope boundary enforcement** — How strictly should knowledge-scope agents be walled off from `platform_content`? The inception principle (ADR-109) says "no access," but the current workspace-driven architecture relies on `QueryKnowledge` which reads `platform_content` as fallback.

5. **First-run optimization** — What is the minimum substrate assessment needed to scaffold a high-confidence agent within 30 seconds? This is a product question with architectural implications.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-15 | Initial version — synthesized from architectural audit and product direction conversation |
