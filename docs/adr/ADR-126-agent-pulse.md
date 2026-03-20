# ADR-126: Agent Pulse — Autonomous Awareness Engine

> **Status**: Implemented (Phases 1-6). Phase 5: role-based cadence in agent_framework.py + Composer pulse integration. Phase 6: frontend surfacing across all surfaces.
> **Date**: 2026-03-20
> **Authors**: KVK, Claude
> **Scope**: Foundational re-architecture of agent execution from top-down scheduling to bottom-up autonomous awareness.
> **Implements**: FOUNDATIONS.md Axioms 3 (developing entities), 4 (accumulated attention), 6 (autonomy as product direction)

---

## Context

YARNNN agents are currently **inert between runs**. The unified scheduler fires every 5 minutes, checks if any agent's `next_run_at` has passed, and runs them. TP's Composer Heartbeat (ADR-111) performs a top-down assessment of the entire agent workforce — 12 data dimensions, 20 heuristic checks — to decide if agents need creation, adjustment, or dissolution.

This architecture has three fundamental problems:

1. **Agents don't have life.** Between scheduled runs, agents are database rows. They don't sense their domain, don't notice patterns, don't decide when to act. The scheduler decides for them.

2. **TP does agents' thinking for them.** The Composer Heartbeat assesses per-agent maturity, staleness, and health — work that should belong to the agents themselves. This contradicts FOUNDATIONS Axiom 1 (TP develops upward in meta-judgment, agents develop inward in domain expertise).

3. **Invisible intelligence.** The only visible event is a "run" (agent generated output). Everything between runs — domain sensing, pattern recognition, coordination decisions — is invisible. Users see a list of outputs, not a workforce that thinks.

### What Exists Today

| Component | What It Does | Owner |
|-----------|-------------|-------|
| `unified_scheduler.py` | Checks `next_run_at`, dispatches agents | Top-down (scheduler) |
| `should_skip_agent()` | Freshness gate before generation | Top-down (scheduler decides for agent) |
| `proactive_review.py` | Per-agent "should I generate?" review | Agent self-assessment (but only for proactive/coordinator modes) |
| `dispatch_trigger()` | Routes signals to generation | Top-down (signal strength determines action) |
| Composer Heartbeat | 12-dimension workforce assessment | Top-down (TP assesses agents) |
| PM JSON decisions | PM reads project state, decides actions | Agent-owned (PM is already pulse-like) |

The key insight: `proactive_review.py` is already an agent pulse — but only for two modes. PM's JSON decision flow is already pulse-like. `should_skip_agent()` is already Tier 1 of a pulse. These patterns exist; they just aren't unified or generalized.

---

## Decision

**Every agent gets a pulse.** The pulse is the agent's autonomous sense→decide cycle — its awareness layer. It is upstream of execution. A pulse that decides "generate" produces a run. A pulse that decides "observe" does not — but the pulse still happened, and that's visible intelligence.

### Core Concepts

**Pulse** — Agent's sense→decide cycle (awareness, upstream of execution). Every agent has one. Fires on a cadence determined by agent maturity and role.

**Run** — Execution event triggered by a pulse decision. One of several possible pulse outcomes. Produces output to workspace.

**Schedule → Delivery** — Project-level delivery timing (downstream of run). When the user receives output. Owned by the PM, not the agent. See PROJECT-DELIVERY-MODEL.md.

### Pulse Decision Taxonomy

Every pulse produces one decision:

| Decision | Meaning | Produces Run? | Visible? |
|----------|---------|--------------|----------|
| `generate` | "I have something worth producing" | Yes | Yes — run event |
| `observe` | "I sensed my domain, nothing to act on" | No | Yes — observation logged |
| `wait` | "Deferring my next pulse" | No | Yes — wait reason logged |
| `escalate` | "I need guidance from PM or TP" | No | Yes — escalation event |

### Three-Tier Pulse Funnel

The pulse uses a cheap-first funnel. Most agents resolve at Tier 1 (zero LLM cost).

**Tier 1: Deterministic Pulse (zero LLM)**

Pure DB checks. Resolves ~80% of pulses:
- Is there fresh content since my last run? (absorbs `should_skip_agent()`)
- Is my budget exhausted? (absorbs scheduler budget gate)
- Have I run recently enough? (schedule-derived minimum interval)
- Do I have pending observations above threshold? (reactive agents)

If all gates pass → generate. If any gate fails → observe/wait with reason.

New agents resolve entirely at Tier 1. Their pulse cadence equals their schedule — they generate whenever their schedule fires, because they have no basis for richer judgment.

**Tier 2: Agent Self-Assessment (Haiku LLM — cheap)**

For agents with enough accumulated state to reason about:
- Agent reads its workspace (AGENT.md, thesis, memory, observations, review log)
- Agent reads fresh content from its domain
- Agent decides: "Given what I know and what's new, should I generate?"
- Generalizes `proactive_review.py` to all agent modes at associate+ seniority

Cost: One Haiku call per pulse (only when Tier 1 passes but agent has reasoning capability). Associate agents and above. New agents skip to Tier 1 resolution.

**Tier 3: PM Coordination Pulse (Haiku LLM)**

PM agents have a specialized pulse that reads project state:
- Contributor freshness (who has new output?)
- Work plan status (what's pending?)
- Quality assessment history
- Budget status
- Assembly readiness

PM decides: `assemble | steer | advance_contributor | assess_quality | update_work_plan | wait | escalate`

This already exists in the PM JSON decision flow (`_handle_pm_decision()`). The change is framing it as PM's pulse, not a scheduled run that happens to produce JSON.

### Pulse Cadence and Agent Development

Pulse cadence evolves with agent maturity:

| Seniority | Pulse Cadence | Tier Available | Behavior |
|-----------|--------------|----------------|----------|
| **New** | Schedule-derived (e.g., daily) | Tier 1 only | Generates on schedule unless no fresh content. Training wheels. |
| **Associate** | Schedule-derived, can increase | Tier 1 + 2 | Self-assesses before generating. May skip scheduled runs. |
| **Senior** | Every cycle (always sensing) | Tier 1 + 2 | May generate off-schedule when domain signals warrant it. |
| **PM** | Every cycle + contributor-triggered | Tier 1 + 3 | Coordination pulse. Senses project state continuously. |

`next_run_at` evolves to `next_pulse_at` — semantics change from "when to generate" to "when to sense."

### How the Scheduler Changes

The unified scheduler becomes a **pulse dispatcher**:

```
Current (top-down):
  for agent in get_due_agents():
      should_skip, reason = should_skip_agent(agent)
      if not should_skip:
          budget_ok = check_work_budget(agent.user_id)
          if budget_ok:
              process_agent(agent)  # always generates

Proposed (bottom-up):
  for agent in get_agents_due_for_pulse():
      decision = agent_pulse(agent)  # agent decides
      if decision.action == "generate":
          dispatch_trigger(agent, "pulse", "high")
      log_pulse_event(agent, decision)  # always visible
```

The scheduler doesn't decide what agents should do. It gives each agent its turn to pulse, and acts on the agent's decision.

### How the Composer Thins

With agents self-reporting via pulse events, the Composer no longer needs to assess per-agent health. It reads pulse outcomes:

**Current Composer Heartbeat (12 dimensions, 20 heuristics, ~1000 lines):**
- Queries all agents, computes maturity signals, checks staleness, measures knowledge corpus, builds agent graph, classifies workspace density, checks coverage gaps...

**Proposed Composer (portfolio-only, ~200 lines):**
- Read recent pulse events for this user's agents
- Read PM pulse outcomes for this user's projects
- Portfolio-level decisions only:
  - Platform without project coverage → scaffold project
  - Project with escalation from PM → intervene
  - No cross-project synthesis → propose synthesis project
  - Agent consistently escalating → investigate or dissolve

The 20 heuristics in `should_composer_act()` largely dissolve. Most were doing bottom-up work (per-agent assessment) from the top down. With agents self-reporting, Composer only needs portfolio-level pattern recognition.

---

## Pulse Visibility — The Data Surface

Every pulse decision is a first-class event, surfaceable in:

- **Project Meeting Room** (ADR-124): Agent pulse events appear in the conversation timeline
- **Agent detail pages**: Pulse history shows the agent's awareness over time
- **Dashboard**: Project health derived from pulse outcomes, not just run counts

Example project timeline:
```
09:00  slack-recap pulsed: observe — "No new activity in #engineering since last run"
09:05  gmail-digest pulsed: generate — "12 new threads since yesterday"
09:06  gmail-digest run #14 started
09:08  gmail-digest run #14 complete — output to /agents/gmail-digest/outputs/2026-03-20/
09:10  PM pulsed: wait — "1/2 contributors have fresh output, waiting for slack-recap"
14:00  slack-recap pulsed: generate — "47 messages in #engineering, 12 in #product"
14:03  slack-recap run #8 complete
14:05  PM pulsed: assemble — "Both contributors fresh, triggering assembly"
14:08  Assembly complete → delivery queued
```

This is an agent workforce you can **watch living** — not just a list of outputs.

---

## What This Supersedes

| Superseded | Disposition |
|-----------|------------|
| **ADR-088 (Trigger Dispatch)** | Partially absorbed — `dispatch_trigger()` remains as the execution path, but the decision to dispatch moves from scheduler/signal to pulse |
| **ADR-092 (Proactive/Coordinator Modes)** | Absorbed — proactive self-assessment generalizes to all agents via pulse Tier 2. "Proactive" and "coordinator" as distinct modes dissolve; all agents pulse, PM agents have coordination pulse |
| **ADR-111 Phases 3-5 (Heartbeat/Composer)** | Superseded — Composer Heartbeat replaced by reading pulse outcomes. Lifecycle assessment moves to agents (via pulse) and portfolio-level Composer. Phase 1-2 (Bootstrap, Composer creation) preserved |

| Preserved | Reason |
|-----------|--------|
| `dispatch_trigger()` | Still the execution path once pulse decides "generate" |
| `execute_agent_generation()` | Still the headless generation pipeline |
| Execution strategies | Still control context gathering for different scopes |
| PM JSON decision flow | Already is the PM pulse — just reframed |
| Composer project scaffolding | Still deterministic, still needed |
| Work budget enforcement | Moves into Tier 1 pulse check |

---

## Phased Implementation

### Phase 1: Agent Pulse Function ✅ Implemented

Generalize `proactive_review.py` + absorb `should_skip_agent()` into a unified `agent_pulse()`:

```python
# api/services/agent_pulse.py

async def agent_pulse(client, agent: dict) -> PulseDecision:
    """
    Agent's autonomous sense→decide cycle.

    Tier 1: Deterministic checks (zero LLM)
    Tier 2: Agent self-assessment (Haiku, associate+ only)

    Returns PulseDecision with action, reason, observations.
    """
```

- New file: `api/services/agent_pulse.py`
- Absorbs: `should_skip_agent()` from `unified_scheduler.py`, `run_proactive_review()` from `proactive_review.py`
- Delete: `proactive_review.py` (singular implementation — no dual approaches)
- Pulse decision logged to `activity_log` as `agent_pulsed` event

### Phase 2: Scheduler Inversion ✅ Implemented

Rewrite scheduler's agent processing to call `agent_pulse()`:

- Scheduler iterates agents due for pulse (query on `next_pulse_at`)
- Calls `agent_pulse()` for each
- On "generate" decision → `dispatch_trigger()`
- All other decisions → log and update `next_pulse_at`
- Delete: `get_due_agents()` + `process_agent()` top-down logic (replaced by pulse)
- Delete: `get_due_proactive_agents()` + `process_proactive_agent()` dead code

Schema change: `agents.next_run_at` → `agents.next_pulse_at` (rename, semantics change)

### Phase 3: PM Pulse Formalization ✅ Implemented

Reframe PM's JSON decision flow as PM pulse:

- New: `pm_pulse()` in `agent_pulse.py` — wraps existing PM context gathering + decision
- PM pulse fires on contributor output (existing `_maybe_trigger_project_heartbeat()`) + schedule
- PM pulse decision logged as `pm_pulsed` event (distinct from `agent_pulsed`)
- Delete: `_maybe_trigger_project_heartbeat()` name (rename to `trigger_pm_pulse()`)

### Phase 4: Composer Thinning ✅ Implemented (partial)

Deleted per-agent supervisory review from Composer (`_run_supervisory_review`, `_get_due_supervisory_agents`, Step 4 loop). Composer heartbeat now focuses on workforce composition only. Full heartbeat_data_query simplification (reading pulse events instead of computing maturity) deferred — current maturity signals still useful for Composer's portfolio heuristics.

Replace Composer Heartbeat's 12-dimension assessment with pulse outcome reading:

- `heartbeat_data_query()` → simplified: read recent pulse events + project health
- `should_composer_act()` → portfolio-only heuristics (coverage gaps, escalations, composition opportunities)
- Composer prompt → project-centric world model (not agent-centric)
- Delete: per-agent maturity signal computation (agents self-report via pulse)
- Delete: workspace density classification (Composer doesn't need this — agents know their own state)
- Significant line reduction in `composer.py` (~1000 lines → ~300 lines)

### Phase 5: Delivery Separation + Pulse Cadence Evolution

- Agent `schedule` field reframed as default pulse rhythm + delivery preference
- Project delivery cadence in PROJECT.md (already captured in PROJECT-DELIVERY-MODEL.md)
- Senior agents get faster pulse cadence (every cycle vs. schedule-derived)
- `next_pulse_at` computation considers agent seniority

---

## Migration Path

### Database

- Rename: `agents.next_run_at` → `agents.next_pulse_at` (migration)
- New event type: `agent_pulsed` in `activity_log` (no schema change — uses existing `event_type` text field)
- New event type: `pm_pulsed` in `activity_log`

### Code

Phase 1-2 are the critical path. Phase 3 is mostly renaming (PM already works this way). Phase 4 is the payoff (Composer simplification). Phase 5 is the developmental trajectory.

Each phase is independently deployable and backwards-compatible during transition.

---

## Relationship to FOUNDATIONS.md

| Axiom | How Pulse Implements It |
|-------|----------------------|
| **Axiom 1** (Two layers) | Agents own domain awareness (pulse). TP owns portfolio awareness (Composer). Clean separation. |
| **Axiom 3** (Developing entities) | Pulse cadence and tier evolve with seniority. New agents pulse on schedule; senior agents pulse continuously. |
| **Axiom 4** (Accumulated attention) | Pulse observations accumulate in workspace. Each pulse builds on prior observations. |
| **Axiom 5** (Composer) | Composer reads pulse outcomes instead of reimplementing agent assessment. Thinner, focused on portfolio. |
| **Axiom 6** (Autonomy) | Agents have life — they sense, decide, act. The pulse IS the mechanism of autonomy. |

---

## Cost Model

| Current | Proposed |
|---------|----------|
| 1 Composer Heartbeat per user per cycle (~12 DB queries + maybe 1 Haiku call) | N agent pulses per user per cycle (most: 3 DB queries each, no LLM) |
| Free: 1 heartbeat at midnight | Free: agent pulses at midnight (same gate) |
| Pro: 1 heartbeat per 5-min cycle | Pro: agent pulses per 5-min cycle (most resolve at Tier 1) |

Net cost is similar or lower — Tier 1 resolution (zero LLM) handles the majority. The Composer's Haiku call (currently fires on sparse/developing workspaces) is replaced by per-agent Tier 2 calls that only fire for associate+ agents with accumulated state. Most early-stage workspaces have only new agents → pure Tier 1 → zero LLM.

---

## Open Questions

1. **Pulse event storage**: Use `activity_log` (existing, indexed) or a dedicated `agent_pulses` table for higher-frequency data? Activity log is simpler; dedicated table allows richer querying.

2. **Pulse cadence governance**: Who sets the pulse cadence? Currently derived from schedule + seniority. Should users be able to adjust? Probably not — pulse cadence is an internal optimization, not a user-facing setting.

3. **Cross-agent pulse coordination**: Should agents in the same project coordinate their pulses? (e.g., "gmail-digest just pulsed observe, so I should wait too"). This is PM's job — PM's pulse considers contributor state. Individual agents don't need to know about siblings.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-20 | v1 — Initial proposal: Agent Pulse as autonomous awareness engine |
