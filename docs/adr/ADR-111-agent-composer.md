# ADR-111: Agent Composer — TP's Compositional Capability

**Status:** Implemented (Phases 1-5) — Revised 2026-03-16
**Date:** 2026-03-13 (original), 2026-03-16 (revised)
**Supersedes:** None
**Related:** ADR-092 (Mode Taxonomy — proactive/coordinator reframed as TP capabilities), ADR-109 (Agent Framework), ADR-110 (Onboarding Bootstrap — becomes Bootstrap bounded context), ADR-106 (Workspace Architecture), ADR-116 (Agent Identity & Inter-Agent Knowledge — extends Composer with agent dependency graph and supply chain reasoning)
**Analysis:** [TP Composer Autonomy Analysis](../analysis/tp-composer-autonomy-analysis.md), [FOUNDATIONS.md Axiom 5](../architecture/FOUNDATIONS.md)

---

## Context

### The Naming Problem (unchanged)

The current codebase has two agent creation mechanisms that are both mislabeled:

1. **`Write` primitive** (chat mode) — A generic entity creator that handles agents, memories, and documents via `ref="type:new"`. The agent path inside it is 100+ lines of field processing (`_process_agent()`). This is not "writing" — it's agent creation buried inside a generic write tool.

2. **`CreateAgent` primitive** (headless/coordinator only) — A dedicated agent creator, but scoped exclusively to coordinator agents. Has its own field processing, origin tracking, and workspace seeding — duplicating logic from Write's `_process_agent()`.

**Problem:** Two code paths for the same operation (creating agents), with different defaults, different field handling, and different mode gating. This violates singular implementation.

### The Missing Capability (reframed)

Between "user has substrate" and "agents exist" there is no compositional judgment. Today:

- **Platform connections** → user must manually create matching digest agents (or bootstrap creates one deterministically)
- **Uploaded files** → no agent creation at all
- **Multi-platform substrate** → no cross-platform agent creation
- **Agent maturity** → no lifecycle progression
- **TP has no heartbeat** — only fires when user sends a chat message

This is a missing **TP capability** — not a missing service. Per FOUNDATIONS.md Axiom 5: the Composer is TP exercising judgment about what attention patterns the user's work requires. It is not a separate service, agent type, or subsystem.

### Platform Content Is an Onramp, Not the Engine

Platform sync seeds context and meets users where their work already lives. But agent work extends far beyond platform digests — research, synthesis, monitoring, write-back, cross-platform analysis. As agent quality and accumulated substrate improve, dependency on fresh platform data decreases. The recursive accumulation (agent outputs → next agent's input → user feedback → refined output) is the enduring value.

**Implication:** TP's compositional triggers cannot be framed primarily around "which platforms are connected." TP must reason about the full range of agent intentions and work patterns.

### Autonomy Is the Architecture, Not a Feature

The system is designed autonomous-first. TP's default is to act; the user's default is to correct through feedback. This means:

- Bias toward creating agents, not suggesting them
- Existing feedback infrastructure (stop/edit/delete, edit history learning) is the correction mechanism
- The ability to constrain autonomy is the business model lever (tier gating), not the architectural foundation

---

## Decision

### 1. Unify Agent Creation into a Single Primitive (unchanged)

**Rename and harden the agent creation path.** Extract `_process_agent()` from `Write` into a dedicated `CreateAgent` primitive available in **both** chat and headless modes, with mode-specific defaults.

| Aspect | Current Write (chat) | Current CreateAgent (headless) | Unified CreateAgent |
|--------|---------------------|-------------------------------|-------------------|
| **Name** | `Write` | `CreateAgent` | `CreateAgent` |
| **Mode** | chat only | headless only | chat + headless |
| **Origin default** | (none) | `coordinator_created` | mode-dependent: `user_configured` (chat), `composer` (headless/composer), `system_bootstrap` (bootstrap) |
| **Field processing** | `_process_agent()` in write.py | inline in coordinator.py | shared `create_agent_record()` in `agent_creation.py` |
| **Workspace seeding** | Yes (AGENT.md) | Yes (AGENT.md) | Yes (shared) |
| **Scope inference** | Yes (ADR-109) | Yes (ADR-109) | Yes (shared) |
| **Dedup check** | No | Yes (coordinator memory) | Optional (caller decides) |
| **Immediate execution** | No (TP offers separately) | Yes (next_run_at=now) | Optional `execute_now` flag |

**`Write` primitive continues to exist** for memories and documents — it just no longer handles `ref="agent:new"`. If TP calls `Write(ref="agent:new", ...)`, it gets a clear error: "Use CreateAgent to create agents."

### 2. Composer as TP Capability (revised — was "Composer Service")

**The Composer is not a service.** It is TP exercising compositional judgment, implemented as three bounded contexts that are architecturally cohesive but independently controllable.

#### Three Bounded Contexts

**Bootstrap** — first-run seeding after platform connection:
- Deterministic, zero-LLM fast-path for highest-confidence agents
- Fires synchronously post-OAuth + first sync completion
- Template mapping: Slack→Recap, Gmail→Digest, Notion→Summary
- Unique timing requirement: must be fast (30-60 seconds to first value)
- Preserves existing `onboarding_bootstrap.py` mechanics
- Tier-gatable: all tiers get bootstrap, count/type varies

**Heartbeat** — periodic TP self-assessment:
- TP's autonomous cadence for evaluating agent workforce health and completeness
- Independent of external triggers — TP thinks on its own schedule
- Lightweight data query first (cheap, no LLM); LLM reasoning only when assessment warrants action
- "Nothing to do" is first-class outcome (HEARTBEAT_OK equivalent)
- Assesses: coverage gaps, underperforming agents, stale agents, maturity signals, user behavior shifts
- Tier-gatable: frequency varies by tier (Free: daily, Pro: more frequent)

**Composer** — the compositional judgment itself:
- Assessment logic that evaluates substrate and decides what agents should exist
- Invoked by Bootstrap (on platform connect), Heartbeat (on schedule), or events (feedback, maturity)
- Creates agents with detailed first-order configuration (instructions, scope, tools, schedule, sources)
- Also adjusts, expands, or dissolves existing agents based on accumulated judgment
- Tier-gatable: scope and agent count limits vary by tier

```
Bootstrap ⊂ Composer (bootstrap is a specific Composer invocation)
Heartbeat → Composer (heartbeat triggers Composer assessment)
Events → Composer (platform connect, feedback, maturity → Composer assessment)

Composer is the capability.
Heartbeat is the autonomous cadence.
Bootstrap is the first-run special case.
```

#### Composer Assessment Model

When Composer fires (via heartbeat, event, or bootstrap), it evaluates:

1. **Substrate**: Connected platforms, synced sources, uploaded files, user chat topics, accumulated workspace content
2. **Workforce**: Existing agents — modes, scopes, recent output quality, feedback patterns
3. **Gaps**: What attention is warranted that no agent currently provides?
4. **Health**: Which agents are producing value? Which are stale or underperforming?
5. **Maturity**: Which agents are ready for scope expansion? Which should be dissolved?

**Priority, dedup, and override handling:**
- **Hierarchy**: Some agents are higher-value than others. Platform digest before cross-platform synthesis before research.
- **Dedup**: Don't create an agent that duplicates existing coverage.
- **Manual overrides**: If user has manually created/configured an agent, Composer respects that as explicit signal.
- **Accumulated judgment**: What has this user kept vs dismissed? TP learns from feedback patterns.

#### Two Orthogonal Axes

**Feedback** (qualitative) — improves output quality, informs TP's compositional judgment. Signals: edits, approvals, dismissals. Accumulates and compounds.

**Configuration** (control/scoping) — defines what an agent can do. Set by TP at creation, adjustable by user. Includes: instructions, sources, schedule, mode, tool scope. Changed deliberately, not gradually.

TP Composer operates on both: it *configures* agents at creation and *learns from feedback* to improve compositional judgment.

#### Two Orders of Control

**First order — TP Composer**: Creates agents with configuration (instructions, scope, tools, schedule). Manages lifecycle. Meta-cognitive orchestration.

**Second order — Agent execution**: Each agent operates within configured boundaries. Tool scope, execution limits, feedback-driven quality improvement. Domain-cognitive controls.

### 3. Proactive/Coordinator Reframe (new — see also ADR-092 revision notes)

Per FOUNDATIONS.md Axiom 5:

> "Proactive review (per-agent 'should I generate?') is better understood as **TP's supervisory capability** — TP assessing whether a specific agent should produce output right now."
> "Coordinator mode (creating child agents) is **the Composer capability itself** — TP spawning agents based on assessed need."

**Disposition of existing code:**

| Existing | Disposition |
|----------|------------|
| `proactive_review.py` | **Becomes TP's per-agent supervisory check** — invoked by Heartbeat. Mechanically similar (Haiku review pass), but conceptually owned by TP, not agent self-assessment. |
| Coordinator CreateAgent primitive | **Absorbed into Composer** — TP is the only entity that creates agents. The primitive is preserved; the invocation shifts from agent headless → TP compositional mode. |
| `onboarding_bootstrap.py` | **Becomes Bootstrap bounded context** — preserved as fast-path for deterministic creation. Composer subsumes for non-obvious cases. |
| `unified_scheduler.py` | **Extended** — adds Heartbeat as a scheduled TP event alongside agent runs. |

### 4. Composer Triggers (revised — was event-only)

| Trigger | Source | What Composer Assesses |
|---------|--------|----------------------|
| **Platform connected + first sync** | Event (sync completion) | What agents does this platform warrant? (Bootstrap fast-path) |
| **Heartbeat cadence** | Periodic (cron) | Is the agent workforce healthy and complete? Gaps? Stale agents? Maturity signals? |
| **Agent run + user feedback** | Event (edit/approve/dismiss) | Does this agent need adjustment? Does feedback pattern suggest new agents? |
| **Agent maturity threshold** | Event (N runs with stable output) | Ready for scope expansion or capability upgrade? |
| **User chat topic** | Event (TP session) | User discusses topic no agent covers → note for next Heartbeat assessment |
| **File uploaded** | Event (workspace write) | What knowledge/research agents does this warrant? |

### 5. Cost Model

Following OpenClaw's "cheap checks first, models only when you need them":

- **Heartbeat data query**: ~0 cost (DB queries for agent stats, run counts, feedback)
- **LLM reasoning**: Only when assessment identifies potential action. Est: 1-3 LLM calls/day/user at steady state.
- **Bootstrap**: Zero LLM for deterministic templates.
- **Per-agent supervisory review** (reframed proactive): Lightweight Haiku call, same as current `proactive_review.py`.

---

## Phased Implementation

### Phase 1: CreateAgent Primitive Unification ✓ (Implemented 2026-03-16)

- ✓ `api/services/agent_creation.py` — shared `create_agent_record()` with `infer_scope()`
- ✓ `api/services/primitives/coordinator.py` — CreateAgent in chat + headless modes
- ✓ `api/services/primitives/write.py` — rejects `ref="agent:new"` with redirect
- ✓ `api/routes/agents.py` — POST `/agents` delegates to `create_agent_record()`
- ✓ `api/agents/tp_prompts/tools.py` + `behaviors.py` — CreateAgent documented
- ✓ `api/prompts/CHANGELOG.md` — updated

All agent creation paths now funnel through single `create_agent_record()`.

### Phase 2: Bootstrap Bounded Context ✓ (Implemented 2026-03-16)

- ✓ `api/services/onboarding_bootstrap.py` — deterministic fast-path
- ✓ Calls `create_agent_record()` with `origin="system_bootstrap"`
- ✓ Wired into platform sync completion handler (`platform_worker.py`)
- ✓ First run executes immediately (Axiom 6: 30-60 second value)

### Phase 3: Heartbeat + Composer Assessment ✓ (Implemented 2026-03-16)

- ✓ `api/services/composer.py` — full Heartbeat + Composer module:
  - `heartbeat_data_query()`: zero-LLM DB assessment (platforms, agents, coverage, health, feedback)
  - `should_composer_act()`: pure logic gate — most heartbeats return HEARTBEAT_OK
  - `run_composer_assessment()`: LLM (Haiku) only when warranted; deterministic fast-path for coverage gaps
  - `run_heartbeat()`: entry point orchestrating full cycle per user
- ✓ `api/jobs/unified_scheduler.py` — Heartbeat wired as scheduled event:
  - Free tier: daily (midnight UTC window)
  - Pro tier: every scheduler cycle (5 min, cheap-first = negligible cost)
  - User discovery: platform connections OR active agents (not platform-bound — FOUNDATIONS.md)
  - `composer_heartbeat` + `agent_bootstrapped` activity log events
- ✓ `origin="composer"` for Composer-created agents
- ✓ Dashboard "Auto" badge extended to cover `composer` + `system_bootstrap` origins
- ✓ Frontend `Agent.origin` type updated to include `'composer'`

### Phase 4: Supervisory Reframe ✓ (Implemented 2026-03-16)

- ✓ `api/services/composer.py` — `_run_supervisory_review()` + `_get_due_supervisory_agents()`
  - Heartbeat invokes per-agent review for proactive/coordinator agents due for review
  - Agent provides domain assessment via `proactive_review.py` → TP (Heartbeat) decides action
  - Activity log events attributed to `trigger: "heartbeat"` (TP ownership)
- ✓ `api/jobs/unified_scheduler.py` — proactive section absorbed into Heartbeat
  - `get_due_proactive_agents()` and `process_proactive_agent()` deprecated (kept for tests)
  - `proactive_reviewed` counter populated from Heartbeat supervisory results
- ✓ `api/services/proactive_review.py` — docstring reframed as TP's supervisory capability
  - Mechanical flow preserved; conceptual ownership is TP's Heartbeat

### Phase 5: Lifecycle Progression ✓ (Implemented 2026-03-16)

- ✓ `api/services/composer.py` — maturity signals + lifecycle assessment:
  - `heartbeat_data_query()` enriched with per-agent maturity signals: run count, weighted approval rate (explicit approval=1.0, auto-delivered=0.5 — prevents maturity inflation from unreviewed outputs), edit distance trend, tenure, origin, maturity classification (nascent/developing/mature), underperformer detection
  - `should_composer_act()` extended with lifecycle triggers: underperformer detection (fires even at tier limit), mature agent expansion, cross-agent pattern consolidation
  - `run_lifecycle_assessment()`: deterministic lifecycle actions — auto-pause underperformers (<30% approval, 8+ runs, **only system-created agents** — user_configured agents are never auto-paused per manual override invariant), auto-create synthesis agents from mature digests, cross-agent consolidation
  - `run_composer_assessment()` routes lifecycle triggers to `run_lifecycle_assessment()` (no LLM needed)
  - `_build_composer_prompt()` includes maturity data for LLM assessment path
  - `run_heartbeat()` logs lifecycle actions to activity log
- ✓ `api/jobs/unified_scheduler.py` — `composer_lifecycle` counter in summary + heartbeat metadata
- ✓ Cost model preserved: maturity signals are pure DB queries, lifecycle actions are deterministic

---

## Consequences

### Positive
- **Single agent creation path** — eliminates dual Write/_process_agent vs CreateAgent
- **Autonomy-first** — TP acts on judgment; user corrects through feedback
- **Full taxonomy becomes accessible** — knowledge, research, and autonomous agents surfaced through Composer assessment
- **TP gets a heartbeat** — periodic self-assessment closes the gap between reactive-only TP and the autonomous system vision
- **Cohesive but controllable** — three bounded contexts can be independently tier-gated
- **Platform dependency decreases over time** — Composer's assessment increasingly uses recursive substrate (agent outputs, user feedback), not just platform data
- **Agent supply chain reasoning** (future, ADR-116 Phase 5) — Composer will reason about agent dependency graphs: which agents produce knowledge, which consume it, and where the supply chain has gaps (orphaned producers, missing producers, stale dependencies)

### Negative
- **Composer assessment quality** — auto-created agents may not match user intent (mitigated: feedback loop + stop/edit/delete)
- **Primitive rename requires prompt update** — TP must learn `CreateAgent` instead of `Write(ref="agent:new")`
- **Heartbeat adds compute cost** — lightweight data queries are free; LLM calls are not (mitigated: tier gating, cheap-first pattern)

### Neutral
- Bootstrap (ADR-110) preserved mechanically — Composer enhances but doesn't block it
- `Write` primitive continues for memories and documents
- `origin` field gains `composer` value alongside existing `system_bootstrap`, `user_configured`, `coordinator_created`

---

## Open Questions

1. **Heartbeat cadence**: Daily baseline + event-driven? Tied to sync frequency tier? Start with daily, observe.
2. **Heartbeat execution model**: Headless TP call with Composer context? Or specialized lightweight pipeline? Likely headless — reuses infrastructure.
3. **Per-agent supervisory integration**: Heartbeat reviews all agents in one pass, or one-at-a-time triggered by Heartbeat? Latter is more scalable.
4. **Coordinator mode sunset timeline**: When does coordinator shift from agent mode to TP Composer capability? Phase 4 target — mechanical code preserved, conceptual ownership shifts.
5. **Attribution UX**: How does dashboard communicate "system created this agent"? Dismiss/keep flow?
6. **Tier boundary design**: What's gated per tier? Agent count? Agent types? Heartbeat frequency? Composer scope?

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-13 | v1 — Composer as backend service, three confidence tiers, event-only triggers |
| 2026-03-16 | v2 — Major revision: Composer reframed as TP capability (not service) per FOUNDATIONS Axiom 5. Three bounded contexts (Composer/Heartbeat/Bootstrap). Autonomy-first posture (bias toward action). Platform content as onramp. Proactive/coordinator reframe. Heartbeat as TP's autonomous cadence. Two-order control model. |
| 2026-03-16 | v2.1 — Autonomy hardening: (1) Origin guard on lifecycle pause — user_configured agents never auto-paused. (2) Weighted approval rate — explicit approval=1.0, auto-delivered=0.5, prevents maturity inflation. (3) Heartbeat broadened to users with agents but no platform connections. |

## References

- [FOUNDATIONS.md](../architecture/FOUNDATIONS.md) — Axiom 5 (Composer as TP capability), Axiom 6 (autonomy as direction)
- [TP Composer Autonomy Analysis](../analysis/tp-composer-autonomy-analysis.md) — benchmarks, corrections, hardened framing
- [ADR-092: Agent Intelligence & Mode Taxonomy](ADR-092-agent-intelligence-mode-taxonomy.md) — proactive/coordinator modes (being reframed as TP capabilities)
- [ADR-109: Agent Framework](ADR-109-agent-framework.md) — Scope × Skill × Trigger taxonomy, canonical template table
- [ADR-110: Onboarding Bootstrap](ADR-110-onboarding-bootstrap.md) — becomes Bootstrap bounded context
- [ADR-106: Agent Workspace Architecture](ADR-106-agent-workspace-architecture.md) — workspace as substrate signal
- [Agent Model Comparison](../architecture/agent-model-comparison.md) — YARNNN position, two-layer intelligence, decision tests
