# ADR-092: Agent Intelligence & Mode Taxonomy

**Status:** Phase 5 Implemented — Signal Processing Dissolved (Phase 1: schema/types; Phase 2: reactive dispatch; Phase 3: RefreshPlatformContent headless; Phase 4: proactive review pass; Phase 5: coordinator primitives + signal processing removal)
**Partially superseded by:** [ADR-126: Agent Pulse](ADR-126-agent-pulse.md) — proactive self-assessment (Phase 4) generalized to ALL agents via pulse Tier 2; coordinator mode (Phase 5) dissolved into PM pulse Tier 3. Four modes remain (recurring, goal, reactive, proactive) as starting character — pulse evolves all of them. Mode taxonomy remains valid; mode-specific execution behaviors absorbed into pulse tiers.
**Date:** 2026-03-04
**Authors:** Kevin Kim, Claude (analysis)
**Supersedes:**
- [ADR-068: Signal-Emergent Agents](ADR-068-signal-emergent-agents.md) — signal processing as L3 infrastructure is dissolved; the capability moves into L4 agent intelligence
- [ADR-074: Signal Scheduling Heuristics](ADR-074-signal-scheduling-heuristics.md) — heuristics for signal cron cadence are replaced by per-mode scheduler behavior
- [ADR-089: Agent Autonomy & Context-Aware Triggers](ADR-089-agent-autonomy-context-aware-triggers.md) — the "periodic agent review" concept is absorbed and fully specified here

**Related:**
- [ADR-063: Four-Layer Model](ADR-063-activity-log-four-layer-model.md) — this ADR enforces the layer boundary L3 was violating
- [ADR-072: Unified Content Layer](ADR-072-unified-content-layer-tp-execution-pipeline.md) — L3 stays as defined; this ADR confirms L3 does not reason
- [ADR-080: Unified Agent Modes](ADR-080-unified-agent-modes.md) — headless mode gains new primitives under this ADR
- [ADR-085: RefreshPlatformContent Primitive](ADR-085-refresh-platform-content-primitive.md) — extended to headless mode
- [ADR-087: Agent Scoped Context](ADR-087-workspace-scoping-architecture.md) — `agent_instructions` and `agent_memory` are the foundation of agent intelligence
- [ADR-088: Trigger Dispatch](ADR-088-input-gateway-work-serialization.md) — dispatch routing per mode governs how each mode responds to triggers
- [Agent Model Comparison](../architecture/agent-model-comparison.md) — this ADR is the fullest expression of YARNNN's agent model position

---

## Problem

### The layer violation

YARNNN's four-layer model (ADR-063) is:

```
L1 Memory     — what YARNNN knows about the user
L2 Activity   — what YARNNN has done
L3 Context    — what's happening in the user's platforms (platform_content)
L4 Work       — what YARNNN produces (agents, versions)
```

Signal processing (ADR-068) runs at the L3 level: it reads `platform_content`, runs an LLM reasoning pass, and makes decisions about what L4 work should be created or triggered. This is **L3 infrastructure doing L4 intelligence work** — a layer violation.

Concretely:
- `signal_extraction.py` reads `platform_content` and builds a content snapshot
- `signal_processing.py` reasons over that snapshot with Haiku and decides to `create_signal_emergent | trigger_existing | no_action`
- `execute_signal_actions()` creates agent rows or advances schedules

The reasoning and decision-making belong in L4 — in the agent's own intelligence. L3 should not know what agents exist, what they're trying to accomplish, or when to create new ones.

### The accumulation mismatch

ADR-088's medium dispatch path appends raw platform event observations to `agent_memory`. This is also a layer violation: external platform events are L3 observations, not L4 operational knowledge. `agent_memory` should accumulate the agent's own learned understanding of how to do its job — not raw signals from external platforms.

### The mode gap

The `mode` field (ADR-087) has two values: `recurring` and `goal`. These describe execution lifecycle but not execution character. There is no way to express:
- A agent that waits for events and generates when a threshold is met (reactive)
- A agent that periodically reviews its domain and initiates work without being asked (proactive)
- A agent whose job is to observe the user's world and coordinate other agents (coordinator)

Without these, the proactive and living-agent behaviors that YARNNN's agent model promises cannot be configured by users or expressed cleanly in code.

### The RefreshPlatformContent gap

`RefreshPlatformContent` (ADR-085) is `["chat"]` mode only. Headless mode uses a separate `freshness.sync_stale_sources()` call baked into the orchestration pipeline. This means a proactive or reactive agent running in headless mode cannot trigger a targeted content refresh for a specific platform mid-execution — it gets whatever the scheduler already fetched. This limits headless mode's ability to act on current context.

---

## Decision

### 1. L3 is genuinely dumb. Signal processing dissolves.

**L3 (`platform_content`) has exactly two writers going forward:**
1. **Platform sync** (`platform_worker.py`) — writes ephemeral content; knows nothing about significance
2. **Downstream consumers** marking content `retained=true` after they use it (agent execution, TP sessions)

Signal processing as a separate L3-level subsystem is dissolved. The LLM reasoning it performed belongs in L4 agent intelligence. The content snapshot it built (`SignalSummary`) is replaced by headless mode's native L3 access via primitives.

**What this removes:**
- `api/services/signal_extraction.py` — content snapshot builder
- `api/services/signal_processing.py` — LLM reasoning pass + action execution
- The hourly signal processing block in `api/jobs/unified_scheduler.py`
- `signal_history` table — deduplication now handled by agent memory on coordinator agents
- `trigger_existing` orchestration — replaced by coordinator agent actions (see below)
- ADR-068 `origin=signal_emergent` creation path — coordinator agents create child agents instead

**What remains from the ADR-068 era:**
- `origin` field on agents — `signal_emergent` remains valid provenance for agents created by coordinator agents. The origin records how a agent was born; that concept is unchanged.
- The three origins: `user_configured`, `analyst_suggested`, `coordinator_created` (replaces `signal_emergent`)

**Migration:** Existing `origin=signal_emergent` agents are relabeled `coordinator_created` in a migration. Functionally identical — the origin field is provenance only.

---

### 2. Agent modes — the full taxonomy

The `mode` field on `agents` is expanded from `recurring | goal` to:

```
recurring | goal | reactive | proactive | coordinator
```

Each mode defines the agent's **execution character** — how it decides when to act, what triggers it, and how its `agent_memory` accumulates.

---

#### Mode: `recurring`

**Character:** Clockwork. Reliable, predictable, scheduled.

**Trigger path:** `trigger_type="schedule"` → `dispatch_trigger(..., signal_strength="high")` → always generate.

**`agent_memory` role:** Accumulates operational knowledge across runs — what formats work, what the user edits, what context tends to be most relevant. Each generation makes the next one better.

**Scheduler behavior:** `next_run_at` calculated from `schedule` config. Scheduler queries `WHERE next_run_at <= NOW()`.

**When to use:** Fixed-cadence work products where regularity is the value. Weekly digests, daily briefs, monthly reports.

**Example:** "Every Monday at 9am, summarize #engineering and send to my Slack DM."

---

#### Mode: `goal`

**Character:** Project. Runs until a stated objective is met, then stops.

**Trigger path:** Same as `recurring` — `trigger_type="schedule"` → high dispatch → generate. After each generation, the headless agent assesses goal completion state and writes a structured update to `agent_memory.goal`.

**`agent_memory` role:** Tracks goal progress explicitly. Structure: `{goal: {description, status, milestones, completion_assessment}}`. When `status="complete"`, scheduler skips future runs.

**Scheduler behavior:** Same as `recurring`, but before dispatch checks `agent_memory.goal.status`. If `"complete"`, skips and logs. Agent remains `active` (user can reopen goal); it just doesn't generate.

**When to use:** Time-bounded work products with a clear completion signal. "Prepare board materials for Q1 review" — stops when the review is done. "Research competitive landscape until I've covered 5 competitors."

**Example:** "Generate competitive intelligence on these 3 companies. Stop when each has been covered."

---

#### Mode: `reactive`

**Character:** On-call. Watches configured sources; accumulates context; generates when a threshold is crossed.

**Trigger path:** `trigger_type="event"` → `dispatch_trigger(..., signal_strength="medium")` → append observation to `agent_memory.observations`. When `len(observations) >= threshold` (configurable in `trigger_config`, default: 5), upgrades to `signal_strength="high"` and generates. Observations are cleared after generation.

**`agent_memory` role:** `observations` array accumulates structured notes from events. Not raw platform content — the headless agent (during a medium dispatch) extracts a brief, meaningful observation from the event context and appends that. The agent is building its own understanding of what's accumulating in its domain.

**Scheduler behavior:** No `next_run_at`. Reactive agents are invisible to the `get_due_agents()` query. They execute only via the event trigger path in `event_triggers.py`.

**When to use:** Event-driven work where individual events don't warrant output but patterns do. "When enough relevant Slack mentions accumulate, draft a response brief." "When my inbox has received 10 messages on a topic, summarize them."

**Example:** "Watch #product-feedback. When 5+ relevant threads have accumulated since my last brief, generate a summary."

**Key distinction from `proactive`:** Reactive waits to be triggered. It does not self-initiate. It watches a configured source and responds to defined event types.

---

#### Mode: `proactive`

**Character:** Living specialist. Periodically reviews its own domain. Decides whether to generate — without being asked.

**Trigger path:** Slow periodic cron cadence (configurable; default: daily). Scheduler dispatches to headless mode with a **review prompt** rather than a generation prompt. The agent reads its `agent_memory` and its sources, assesses whether conditions warrant generating a new version, and either:
- Returns `{"action": "generate"}` → orchestration proceeds to full generation
- Returns `{"action": "observe", "note": "..."}` → orchestration appends the note to `agent_memory.observations` and exits (no version created)
- Returns `{"action": "sleep", "until": "..."}` → orchestration schedules next review at the specified time

**`agent_memory` role:** The agent's working awareness of its domain. It accumulates self-authored observations from each review cycle — not raw platform events, but the agent's own assessments. Over time this becomes a rich operational log: "Last three reviews showed increasing activity in X area. Generated version on 2026-02-15. User edited it significantly. Adjusted understanding: user prefers X format."

**Scheduler behavior:** Separate `proactive_next_review_at` timestamp (distinct from `next_run_at`). Scheduler queries these agents on their review cadence. Review pass is a lightweight Haiku call; generation pass is a full Opus call. Most review cycles result in `observe` or `sleep`, not `generate` — preserving cost efficiency.

**When to use:** Standing-order intelligence work where the value is the agent's ongoing awareness, not a fixed schedule. "Keep tabs on competitive developments and brief me when something significant happens." "Monitor my relationship health and surface relationship gaps I should address."

**Example:** "Watch for significant shifts in how the team is using #general. Brief me when something worth addressing emerges — I don't need a fixed schedule, just timely signal."

**Key distinction from `reactive`:** Proactive self-initiates the review. It is not waiting for a configured event type. It has standing instructions defining its domain and uses its own judgment to decide when to act.

**Key distinction from signal processing (dissolved):** Signal processing was infrastructure that ran for all users and scanned all platform content. A proactive agent is user-configured and domain-specific. Its intelligence is scoped to its `agent_instructions` and accumulated in its `agent_memory`. Multiple proactive agents are multiple independent specialists — not one global scanner.

---

#### Mode: `coordinator`

**Character:** Meta-specialist. Watches the user's world and creates or activates other agents when conditions are met. The replacement for signal processing's `create_signal_emergent` and `trigger_existing` capabilities.

**Trigger path:** Runs on a slow periodic cadence (same scheduler path as `proactive`). Headless mode review pass, but with access to a **write primitive** not available to other modes: `CreateAgent` (creates a child agent with `origin=coordinator_created`). Also has access to `AdvanceAgentSchedule` (the replacement for `trigger_existing` — advances another agent's `next_run_at` to now).

**`agent_memory` role:** Tracks what it has created and triggered. Maintains a deduplication log (replaces `signal_history` table). Records patterns it has observed and actions it has taken. Prevents re-creating agents for the same underlying event.

**Scheduler behavior:** Same as `proactive` — `proactive_next_review_at` cadence, lightweight review pass, acts only when warranted.

**When to use:** This is the replacement for the meeting_prep signal processing path. A coordinator agent with instructions like: "Watch my calendar. When I have an upcoming meeting with external attendees I haven't corresponded with recently, create a meeting_prep brief for it." This is what signal processing was doing — but now it's user-configured, domain-specific, and transparent.

**Key design principle:** A coordinator agent is just a proactive agent with write primitives. The distinction is in the primitives available during headless execution, not a fundamentally different architecture. The user creates a coordinator by choosing a agent type that signals coordinator capability (or by configuring it explicitly in `agent_instructions`).

**Why this is better than signal processing:**
- **Configurable:** Users control what the coordinator watches and what it creates
- **Transparent:** The coordinator's `agent_memory` shows exactly what it has observed and why it acted
- **Scoped:** Each coordinator is responsible for one domain, not the whole user's platform world
- **Consistent:** Coordinator agents are normal agents — same schema, same execution model, same audit trail
- **No tier gate surprise:** Signal processing was Starter+ only, invisibly. Coordinator agents are tier-gated by agent count limit, which is already user-visible.

---

### 3. RefreshPlatformContent extended to headless mode

`RefreshPlatformContent` (ADR-085) is extended from `["chat"]` to `["chat", "headless"]`.

**Motivation:** Proactive and reactive agents running in headless mode need to be able to refresh their platform sources before assessing whether conditions warrant action. Without this, a proactive agent's review pass operates on potentially stale L3 content — weakening the quality of its `observe / generate / sleep` decision.

**Headless behavior differences from chat:**
- No 30-minute staleness guard (headless runs are already infrequent and purposeful)
- Scoped to the agent's configured `sources` only — not arbitrary platforms
- Returns a summary of what was refreshed; agent uses this in its review assessment
- Cost: same sync pipeline as chat mode (`_sync_platform_async()`), awaited inline

**Implementation note:** The `freshness.sync_stale_sources()` call currently baked into the orchestration pipeline for scheduled (`recurring`) agents is **not** replaced — it runs before headless mode is invoked, as a pre-flight. The new headless `RefreshPlatformContent` is available for mid-execution targeted refresh, callable by the agent itself during its tool-use loop.

**ADR-085 update:** ADR-085's "Known Concern" about dual freshness implementations becomes relevant here. The two staleness check paths (`refresh.py` at 30 min, `freshness.py` at 24h) serve distinct purposes and remain separate for now. If headless `RefreshPlatformContent` needs sophisticated per-source staleness logic, extract a shared utility at that point (not prematurely).

---

### 4. dispatch_trigger() routing per mode

ADR-088's `dispatch_trigger()` is extended to route based on agent `mode`:

| Mode | Trigger path | dispatch behavior |
|------|-------------|------------------|
| `recurring` | schedule | always `high` → generate |
| `goal` | schedule | `high` → generate, unless `agent_memory.goal.status == "complete"` → `low` |
| `reactive` | event | `medium` → observe; `high` (threshold met) → generate |
| `proactive` | slow periodic review | review pass → agent returns `generate / observe / sleep` |
| `coordinator` | slow periodic review | review pass → agent returns `generate / create_child / advance_schedule / observe / sleep` |

The `proactive` and `coordinator` paths are new. They do not go through the existing `_dispatch_high / _dispatch_medium / _dispatch_low` branching — they invoke a **review pass** first, then act on the agent's assessment.

---

### 5. Scheduler changes

**Removed:** The hourly signal processing block in `unified_scheduler.py` (the `if now.minute < 5` block that runs `extract_signal_summary → process_signal → execute_signal_actions`).

**Added:** A `proactive_next_review_at` timestamp on agents. Scheduler queries:

```sql
SELECT * FROM agents
WHERE status = 'active'
AND mode IN ('proactive', 'coordinator')
AND proactive_next_review_at <= NOW()
```

This runs in the existing 5-minute cron cycle — no new cron needed.

**Digest processing:** The weekly digest block in the scheduler is a legacy path (pre-agent-model). It should be evaluated for migration to a `recurring` agent in a future ADR. Not addressed here.

---

## Agent intelligence: how memory accumulates per mode

The `agent_memory` JSONB field (ADR-087) carries different structured content depending on mode:

```json
// recurring and goal modes
{
  "observations": [
    {"date": "2026-03-04", "source": "event", "note": "..."}
  ],
  "goal": {
    "description": "...",
    "status": "in_progress | complete",
    "milestones": [],
    "completion_assessment": "..."
  }
}

// reactive mode
{
  "observations": [
    {"date": "2026-03-04", "source": "event", "note": "...", "threshold_count": 3}
  ],
  "threshold": 5,
  "last_generated_at": "2026-03-01T09:00:00Z"
}

// proactive mode
{
  "review_log": [
    {
      "date": "2026-03-04",
      "action": "observe | generate | sleep",
      "note": "No significant change since last review. Volume up slightly in X area.",
      "next_review_at": "2026-03-05T09:00:00Z"
    }
  ],
  "last_generated_at": "2026-03-01T09:00:00Z"
}

// coordinator mode
{
  "review_log": [...],
  "created_agents": [
    {
      "agent_id": "...",
      "title": "Meeting Prep: Q1 Review with Acme",
      "created_at": "2026-03-04T08:00:00Z",
      "event_ref": "calendar_event_id_xyz",
      "dedup_key": "meeting_prep:calendar_event_id_xyz"
    }
  ],
  "advanced_schedules": [
    {
      "agent_id": "...",
      "advanced_at": "2026-03-04T08:00:00Z",
      "reason": "Urgent signal: meeting in 2h with no prep brief yet"
    }
  ]
}
```

The `created_agents` array on coordinator agents replaces the `signal_history` table. Deduplication is per-coordinator, per-event-ref — the coordinator checks its own memory before creating a child agent.

---

## What this means for existing agent types

Signal processing created agents of specific types (`meeting_prep`, `silence_alert`, `contact_drift`). Under this ADR:

| Old path | New path |
|----------|----------|
| Signal processing → creates `meeting_prep` | Coordinator agent with calendar-watching instructions → creates `meeting_prep` |
| Signal processing → creates `silence_alert` | Coordinator agent with Gmail-silence-watching instructions → creates `silence_alert` |
| Signal processing → `trigger_existing` | Coordinator agent → `AdvanceAgentSchedule` primitive |
| Signal processing → `no_action` | Coordinator → `observe` or `sleep` |

The agent types themselves (`meeting_prep`, `silence_alert`, `contact_drift`) are unchanged — they remain valid types that can be created by coordinators, by users, or by TP.

---

## Implementation phases

### Phase 1: Schema + mode taxonomy (documentation + migration)
- Add `mode` values: `reactive`, `proactive`, `coordinator` to DB constraint
- Add `proactive_next_review_at` column to `agents`
- Relabel existing `origin=signal_emergent` to `origin=coordinator_created`
- Update `AgentCreate` / `AgentUpdate` Pydantic models
- Update `docs/architecture/agents.md`, `four-layer-model.md`, `agent-execution-model.md`
- Update ADR-068 status to Superseded (by this ADR)

### Phase 2: Reactive mode
- Extend `dispatch_trigger()` threshold logic in `trigger_dispatch.py`
- Medium dispatch observation extraction: agent-authored note, not raw event string
- `trigger_config` gains `observation_threshold` field (default: 5)
- Scheduler: reactive agents excluded from `get_due_agents()` query

### Phase 3: RefreshPlatformContent in headless mode
- Extend `refresh.py` primitive to `["chat", "headless"]`
- Remove staleness guard for headless calls
- Scope to agent's configured sources
- Update headless mode primitive registry

### Phase 4: Proactive mode
- Scheduler: new `proactive_next_review_at` query
- Review pass: lightweight Haiku call with review prompt
- `dispatch_trigger()` extended with `proactive_review` action
- `proactive_next_review_at` updated from agent's `sleep` response

### Phase 5: Coordinator mode + write primitives
- New headless primitive: `CreateAgent` (creates child with `origin=coordinator_created`)
- New headless primitive: `AdvanceAgentSchedule` (advances `next_run_at` to now)
- Coordinator mode scheduler path
- `agent_memory.created_agents` deduplication logic
- Remove `signal_processing.py`, `signal_extraction.py`
- Remove signal processing block from `unified_scheduler.py`
- Drop `signal_history` table (migration)

### Phase 6: Digest migration (future ADR)
- Evaluate migrating weekly digest to a `recurring` coordinator agent
- Out of scope for this ADR

---

## Consequences

### Positive
- **L3 is genuinely dumb.** Platform sync writes; downstream consumers mark retained. No reasoning at L3. The four-layer boundary is enforced.
- **Intelligence compounds per specialist.** Each proactive or coordinator agent accumulates understanding of its specific domain. Signal processing had one shared reasoning pass for all users — no accumulation.
- **Configurable and transparent.** Users control what their coordinator watches. The `agent_memory` audit log shows exactly what it has observed and why it acted. Signal processing was a black box.
- **Consistent model.** Proactive and coordinator agents are normal agents — same schema, same execution, same UI surface, same versioning. No special infrastructure.
- **Strengthens YARNNN's position.** The agent model now provides the "living agent" experience that OpenClaw achieves with a persistent always-on process — but YARNNN achieves it with sleeping specialists that only wake when warranted. Cost-efficient. Quality-compounding. Architecturally clean.

### Negative
- **Migration cost.** Signal processing provided live value (meeting_prep briefs). Phase 5 complete: signal_extraction.py, signal_processing.py, routes/signal_processing.py deleted; signal_history table dropped; unified_scheduler signal block removed. Coordinator agents now provide the equivalent capability with user-configured domain scope and accumulated memory.
- **Coordinator agent UX.** Users must understand that a coordinator agent is a meta-agent. This requires clear product communication and UI design. The concept is correct; the onboarding is non-trivial.
- **No global scan.** Signal processing scanned all platform content for all users holistically. Coordinator agents are user-configured and domain-scoped. A signal that doesn't fall within any configured coordinator's domain will not be caught. This is intentional — YARNNN's model is explicit configuration, not ambient surveillance.

### Neutral
- `origin=signal_emergent` agents relabeled `coordinator_created` — cosmetic migration, no behavioral change
- TP can still create agents on user request — unchanged
- Conversation Analyst (`analyst_suggested`) is unchanged — separate path, not addressed here
- ADR-088 `dispatch_trigger()` extended but backward-compatible for `recurring` and `goal` modes

---

## Revision Notes (2026-03-16): Proactive/Coordinator as TP Capabilities

FOUNDATIONS.md v2 (Axiom 1: Two Layers of Intelligence, Axiom 5: Composer as TP Capability) reframes the conceptual ownership of proactive and coordinator modes:

### What Changes Conceptually

**Proactive mode** — described above as "living specialist that periodically reviews its own domain and decides whether to generate." Under FOUNDATIONS.md:
- The review pass is reframed as **TP's supervisory capability** — TP assessing whether a specific agent should produce output right now.
- The agent still provides the domain assessment (it knows its domain better than TP). But the *decision to review* and the *decision to act on the assessment* belong to TP.
- Mechanically: TP's Heartbeat (ADR-111 revised) invokes per-agent review. Agent returns domain observations. TP/Heartbeat decides: generate / observe / sleep.

**Coordinator mode** — described above as "meta-specialist that creates or activates other agents." Under FOUNDATIONS.md:
- Agent creation is **TP's Composer capability** — TP spawning agents based on assessed need.
- The coordinator agent's domain knowledge (what events warrant new agents) remains valuable as input to TP's composition.
- Mechanically: The CreateAgent primitive shifts from agent-invoked to TP/Composer-invoked. The assessment logic that lives in coordinator agent instructions becomes part of Composer's assessment model.

### What Does NOT Change

- **The mode taxonomy** (recurring, goal, reactive, proactive, coordinator) remains valid as execution character descriptions
- **The scheduler mechanics** (proactive_next_review_at, review cadence, lightweight Haiku review) are preserved
- **The agent_memory structures** (review_log, observations, created_agents) remain as designed
- **The graduated response** (observe / generate / sleep) is preserved
- **RefreshPlatformContent in headless mode** — unchanged

### What Changed Mechanically (ADR-111 Phase 4 — Implemented 2026-03-16)

- ✓ TP Heartbeat (`composer._run_supervisory_review()`) triggers proactive/coordinator reviews, replacing direct scheduler dispatch
- ✓ Agent review pass returns assessment to TP — activity log events attributed to `trigger: "heartbeat"`
- ✓ Scheduler's proactive section absorbed into Heartbeat; `get_due_proactive_agents()` deprecated
- CreateAgent invocation shift from coordinator → Composer is architecturally enabled (coordinator CreateAgent still works)
- AdvanceAgentSchedule remains available as a TP/Composer primitive

### Impact on Decision Tests

The five decision tests below remain valid. Two additional tests from agent-model-comparison.md (2026-03-16 revision):
- 6: Does this strengthen TP's compositional authority?
- 7: Does this reduce platform dependency over time?

---

## Decision tests (per agent-model-comparison.md)

1. **Does this strengthen the agent as the unit of intelligence?** Yes. Intelligence moves entirely into agents. L3 stops reasoning.
2. **Does this maintain sleep efficiency?** Yes. Proactive and coordinator agents sleep between review cycles. Review cycles are lightweight (Haiku). Full generation only when warranted.
3. **Does this compound quality per specialist?** Yes. Each coordinator's `agent_memory` accumulates domain-specific knowledge. No dilution across a global pass.
4. **Does this keep the graduated response?** Yes. `observe / generate / sleep` is a graduated response. Most review cycles don't generate.
5. **Does this respect the orchestration boundary?** Yes. The agent agent does not manage its own scheduling — it returns a `sleep` response with a suggested next review time, and the orchestrator sets `proactive_next_review_at`. The agent produces text; orchestration manages lifecycle.
