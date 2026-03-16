# TP Composer Autonomy — Analysis

> **Status**: Analysis (pre-decision)
> **Date**: 2026-03-16 (v2)
> **Context**: Grounding TP's autonomous compositional role before agent-side developmental model. Informed by OpenClaw and Claude Agent SDK benchmarking + FOUNDATIONS.md v2 axioms.
> **Dependency**: This analysis informs revisions to ADR-111 (Agent Composer) and ADR-092 (Mode Taxonomy).

---

## The Question

What is TP's autonomous authority, and how does it exercise compositional and supervisory judgment?

This must be answered before the agent developmental model (Axiom 3) because TP is the control surface for agent lifecycle — who creates, adjusts, dissolves agents is TP's job (Axiom 1). The agent-side model is downstream.

---

## Industry Benchmarks

### OpenClaw — Single Agent, Heartbeat-Driven

- **Heartbeat**: Cron-triggered (every 30 min), agent evaluates HEARTBEAT.md checklist. "Nothing to do" = `HEARTBEAT_OK` (suppressed, never shown to user). Cheap checks first, LLM only when warranted.
- **Unified input queue**: All triggers (user message, cron, webhook, heartbeat) enter one lane queue. Queue doesn't care about source.
- **Sub-agents**: Orchestrator explicitly spawns via `sessions_spawn`. No autonomous self-replication.
- **Trust**: User-configured allowlists per-agent. Not auto-graduated — user controls the boundary.
- **Limitation**: Single agent per workspace. No meta-orchestrator creating agents.

### Claude Agent SDK — Orchestrator-Workers, Reactive

- **Purely reactive**: Agent loop runs until Claude stops calling tools. No proactive behavior.
- **Orchestrator-workers**: Recommended pattern for unpredictable subtasks. Central LLM delegates to worker LLMs.
- **Subagents**: Isolated context windows, curated tools, report back to parent.
- **Trust tiers**: Tier 1 (read) = automated, Tier 2 (reversible) = guardrails, Tier 3 (irreversible) = human-in-loop.
- **Autonomy research**: Users naturally shift toward monitor-and-intervene (~40% auto-approve by 750 sessions). Platform doesn't force graduation — users develop their own instincts.

### Convergent Patterns

1. **Orchestrator intelligence is centralized.** Nobody has agents autonomously spawning agents without a central decision-maker.
2. **"Think before acting" is universal but cheap.** Lightweight assessment → graduated response (nothing / note / act).
3. **Trust graduation exists in user behavior** but no platform has shipped automatic autonomy escalation. Users naturally grant more autonomy over time.

---

## Current State (YARNNN)

| Capability | Status | Notes |
|------------|--------|-------|
| TP reactive chat | Working | Responds to user messages, can call CreateAgent when asked |
| Onboarding bootstrap | Working | Deterministic, zero-LLM. Creates first digest after platform sync. |
| Proactive/coordinator review | Working | Haiku review pass — but lives in agent headless logic, not TP |
| Substrate assessment | Not built | TP has no awareness of what agents should exist |
| Periodic self-assessment | Not built | TP has no heartbeat — only fires on user message |
| Agent lifecycle management | Not built | TP doesn't monitor agent health or recommend changes |
| Autonomous creation on events | Partial | Bootstrap only (platform connect → first digest). No broader composition. |

---

## Foundational Framing

### Platform Content Is an Onramp, Not the Engine

Platform sync has two functions:

1. **Data seeding**: Meeting users where their work already lives. Pre-loading context so agents can start working immediately. This is the onramp — it jumpstarts autonomy from the user's existing work. In future, agents will also do work *on* these platforms (write-back, monitoring, responses).

2. **Platform-dedicated agent lanes**: Platform-specific agents (Slack recap, Gmail digest, etc.) operate in their own lanes with scoped tools and execution boundaries. The axis of work and tool scope defines what each agent can and cannot do.

**Critical implication**: As agent autonomy and output quality improve, dependency on platform sync *decreases* over time, not increases. The agents' own accumulated work — their outputs, observations, theses, cross-references — becomes the primary substrate (Axiom 2: recursive perception). Platform data is the seed; the recursive accumulation is the crop.

This means TP's compositional thinking cannot be framed primarily around "which platforms are connected." Agents do research, synthesis, monitoring, cross-platform analysis, write-back. Their work evolves beyond the platform data that seeded them. TP must reason about the full range of agent intentions and work, not just platform coverage.

### Two Orthogonal Axes: Feedback and Configuration

These are distinct and must not be conflated:

**Feedback loop** — qualitative in nature:
- Improves output quality over time
- Informs TP's compositional judgment ("this agent type works for this user")
- Signals: user edits, approvals, dismissals, chat corrections
- Drives agent learning (ADR-101 learned preferences)
- Accumulates — the value compounds

**Configuration** — control and scoping mechanisms:
- Defines what an agent can do (tool scope, execution boundaries)
- Set by TP at agent creation, adjustable by user
- Includes: instructions, sources, schedule, mode, available primitives
- Discrete — changed deliberately, not gradually

TP Composer operates on both axes: it *configures* agents at creation (scope, tools, instructions) and it *learns from feedback* to improve its compositional judgment over time.

### Two Orders of Control

**First order — TP Composer**: Autonomous agent creation and configuration. TP assesses what agents should exist, creates them with relevant detailed configuration (instructions, scope, tools, schedule, sources), and manages their lifecycle. This is meta-cognitive orchestration.

**Second order — Agent execution**: Each agent has its own controls and configurations within its lane. Tool scope defines what it can/cannot do. Execution boundaries define how far it can go. Feedback loops improve its output quality. These are domain-cognitive controls that TP sets at creation and the user can override.

The hierarchy is clear: TP composes and configures → agents execute within their configured boundaries → feedback flows back to both layers.

---

## Autonomy as First-Class Architecture

### The Principle

**Autonomy is the default. It is not a feature to be enabled — it is the architecture.**

The system is designed autonomous-first. The ability to constrain, pause, or gate autonomy is the business model lever (tier gating), not the architectural foundation. This means:

- The autonomous path is the primary code path, not a branch
- Manual/reactive modes are constraints on the autonomous default
- Tier gating controls *how much* autonomy, not *whether* autonomy exists

### Bias Toward Action, Not Permission

"Autonomy" here means: TP acts on its judgment. The user corrects through feedback. This applies to:

- **Agent creation**: TP creates agents when its assessment warrants them
- **Agent configuration**: TP sets initial config based on substrate + learned patterns
- **Agent adjustment**: TP modifies agents based on performance signals
- **Agent dissolution**: TP removes agents that aren't producing value

The existing infrastructure supports this posture:
- Dashboard shows all agents and outputs (visibility)
- User can stop/edit/delete any agent (control)
- Edit history feeds into agent learning (correction)
- Activity log tracks all system actions (transparency)

### What "Autonomous" Does NOT Mean

- Acting without judgment (TP still reasons about what's warranted)
- Flooding the user (start with highest-value agents, expand deliberately)
- No user override (user can always stop, edit, delete, or direct TP manually)
- No transparency (all autonomous actions are visible and attributed)

---

## Proposed Architecture: TP Composer

### Three Bounded Contexts

Architecturally cohesive but independently controllable. Each can be toggled for tier gating.

#### 1. Composer — Agent Lifecycle Management

**What**: TP's capability to create, configure, adjust, and dissolve agents based on compositional judgment.

**Responsibilities**:
- Assess what agents should exist given the user's substrate and work patterns
- Create agents with detailed configuration (instructions, scope, tools, schedule, sources)
- Adjust agent configuration based on performance signals
- Dissolve agents that aren't producing value
- Expand agent scope when maturity warrants

**Tier gating**: Number of auto-created agents, types available (platform-only vs cross-platform vs research)

#### 2. Heartbeat — Periodic Self-Assessment

**What**: TP's autonomous cadence for evaluating the health and completeness of the user's agent workforce.

**Responsibilities**:
- Periodic evaluation independent of any external trigger
- Assess: coverage gaps, underperforming agents, stale agents, user behavior shifts, cross-agent patterns
- Decide: should Composer act? (create/adjust/dissolve)
- Log: observations even when no action taken (accumulates system-level knowledge)

**Execution model**: Lightweight data query first (cheap, no LLM). LLM reasoning only when assessment warrants action. "Nothing to do" is first-class outcome.

**Tier gating**: Heartbeat frequency (Free: daily, Pro: every sync cycle or more frequent)

#### 3. Bootstrap — First-Run Seeding

**What**: The specific case of Composer firing immediately after platform connection + first sync.

**Responsibilities**:
- Create highest-confidence agents immediately after first sync completes
- Execute first run within 30-60 seconds (Axiom 6)
- Surface output on dashboard immediately

**Why separate bounded context**: Bootstrap has unique timing requirements (must be fast, synchronous with OAuth callback flow) and is the critical first-impression moment. It may use deterministic templates (current `onboarding_bootstrap.py`) or LLM judgment (future Composer), but the *event* is distinct.

**Tier gating**: All tiers get bootstrap (it's the hook). Number/type of bootstrapped agents varies by tier.

### How the Three Relate

```
Bootstrap ⊂ Composer (bootstrap is a specific Composer invocation)
Heartbeat → Composer (heartbeat triggers Composer assessment)
Events → Composer (platform connect, feedback, maturity → Composer assessment)

Composer is the capability.
Heartbeat is the autonomous cadence.
Bootstrap is the first-run special case.
```

All three share: assessment logic, agent creation primitives, configuration templates, feedback integration. They differ in: trigger source, timing requirements, tier gating.

### Composer Assessment Model

When Composer fires (via heartbeat, event, or bootstrap), it evaluates:

1. **Substrate**: What platforms are connected? What sources are synced? What files are uploaded? What does the user discuss in chat?
2. **Workforce**: What agents exist? What are their modes, scopes, recent output quality, feedback patterns?
3. **Gaps**: What attention is warranted that no agent currently provides?
4. **Health**: Which agents are producing value? Which are stale or underperforming?
5. **Maturity**: Which agents are ready for scope expansion? Which should be dissolved?

**Priority and dedup**: Composer must handle:
- **Hierarchy**: Some agents are higher-value than others (platform digest before cross-platform synthesis before research)
- **Dedup**: Don't create an agent that duplicates an existing agent's coverage
- **Manual overrides**: If user has manually created/configured an agent, Composer respects that as an explicit signal and doesn't override it
- **Accumulated judgment**: What has this user kept vs dismissed in the past? (TP learns from feedback)

### Relationship to Existing Code

| Existing | Disposition |
|----------|------------|
| `onboarding_bootstrap.py` | **Becomes Bootstrap context** — may be preserved mechanically for the fast deterministic path, or absorbed into Composer with template-based fast path |
| `proactive_review.py` | **Becomes TP's per-agent supervisory check** — invoked by Heartbeat or Composer, not by agent self-assessment. Mechanical similarity preserved, conceptual ownership shifts to TP. |
| Coordinator mode (ADR-092) | **Absorbed into Composer** — TP is the only entity that creates agents. Coordinator as agent mode → Composer as TP capability. |
| `unified_scheduler.py` | **Extended** — adds Heartbeat as a scheduled TP event alongside agent runs |
| CreateAgent primitive | **Preserved** — TP's tool for agent creation in both reactive chat and compositional mode |

### Cost Model

Following OpenClaw's "cheap checks first, models only when you need them":

- **Heartbeat data query**: ~0 cost (database queries for agent stats, run counts, feedback)
- **LLM reasoning**: Only when assessment identifies potential action. Estimated frequency: 1-3 LLM calls per day per user at steady state.
- **Bootstrap**: Zero LLM for deterministic templates, one LLM call for Composer-assessed creation.
- **Tier gating**: Heartbeat frequency and Composer scope vary by tier.

---

## Open Questions for ADR

1. **Heartbeat cadence**: Daily baseline + event-driven? Tied to sync frequency tier? Start with daily, observe.
2. **Heartbeat execution model**: Headless TP call with Composer context injection? Or specialized lightweight pipeline? Likely headless — reuses existing infrastructure.
3. **Proactive review integration**: Does per-agent supervisory review merge into Heartbeat (TP reviews all agents in one pass) or remain separate (TP reviews one agent at a time, triggered by Heartbeat)? Latter is more scalable.
4. **Coordinator mode sunset**: Timeline for reframing coordinator agents as TP Composer invocations. Mechanical code may be preserved; conceptual ownership shifts.
5. **Attribution UX**: How does dashboard communicate "system created this agent"? What's the first-run experience?
6. **Bootstrap → Composer migration**: Does Bootstrap remain as a deterministic fast-path, or does Composer eventually handle all creation with template-based shortcuts?
7. **Tier boundary design**: What exactly is gated per tier? Agent count? Agent types (platform vs research)? Heartbeat frequency? Composer scope?

---

## Relationship to FOUNDATIONS.md Axioms

| Axiom | How This Analysis Implements It |
|-------|-------------------------------|
| 1 (Two Layers) | TP owns meta-cognition (composition, supervision, lifecycle). Agents own domain execution within configured boundaries. First-order vs second-order control. |
| 2 (Recursive Perception) | Platform content is the onramp; recursive accumulation is the enduring value. TP Heartbeat consumes all three perception layers. As agent quality improves, platform dependency decreases. |
| 3 (Developing Entities) | Deferred — agent developmental model follows TP Composer clarity (see `agent-developmental-model-considerations.md`). TP's Composer is the control surface for agent development. |
| 4 (Accumulated Attention) | TP's compositional judgment improves with tenure — it learns what agents this user keeps, what configurations work, what feedback patterns indicate. |
| 5 (Composer as TP Capability) | Directly implements. Three bounded contexts (Composer, Heartbeat, Bootstrap) — cohesive but independently controllable. Not a separate service. |
| 6 (Autonomy as Direction) | Autonomy is the architecture, not a feature. Bias toward action. Feedback is correction. Tier gating controls scope, not existence, of autonomy. |

---

## Relationship to Agent-Side Architecture

This analysis deliberately defers agent developmental model decisions. However, it establishes the control surface:

- **TP Composer creates agents** with first-order configuration (instructions, scope, tools, schedule)
- **Agents execute within configured boundaries** with second-order controls
- **Feedback flows to both layers**: to agents (output quality) and to TP (compositional judgment)
- **TP Heartbeat assesses agent maturity** and triggers scope expansion/contraction via Composer

The agent developmental trajectory (Axiom 3: intentions, capabilities, autonomy graduation) becomes implementable once this TP-side architecture is solid — because TP is the entity that manages that development.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-16 | v1 — benchmarked against OpenClaw + Claude Agent SDK, corrected event-only trigger assumption, established auto-create default posture, introduced TP heartbeat |
| 2026-03-16 | v2 — hardened framing: platform content as onramp not engine, feedback vs configuration as orthogonal axes, first-order/second-order control hierarchy, three bounded contexts (Composer/Heartbeat/Bootstrap) with independent tier gating, autonomy as architecture not feature |
