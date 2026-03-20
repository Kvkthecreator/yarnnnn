# Scheduler Evolution — From Top-Down Scheduler to Pulse Dispatcher

> **Status**: Phases 1-4 Implemented. Phase 5 (cadence evolution) implemented.
> **Date**: 2026-03-20
> **Authors**: KVK, Claude
> **Scope**: Evolution path for `unified_scheduler.py` and `composer.py` under ADR-126
> **Related**: ADR-126 (Agent Pulse), ADR-088 (Trigger Dispatch), ADR-092 (Mode Taxonomy), ADR-111 (Composer), ADR-120 (Project Execution)

---

## Current State

`unified_scheduler.py` runs every 5 minutes via Render cron. It does everything top-down:

```
Every 5 minutes:
├── 1. Query due agents (next_run_at <= now, mode in [recurring, goal])
│   ├── Freshness check (should_skip_agent)
│   ├── Work budget check
│   └── dispatch_trigger() → full generation
├── 2. [DEAD] Proactive/coordinator review (absorbed into Heartbeat — ADR-111 P4)
├── 3. Content cleanup (hourly)
├── 4. Workspace cleanup (hourly)
├── 5. Import jobs
├── 6. Composer Heartbeat (ADR-111 P3)
│   ├── Per-user data query
│   ├── should_composer_act() heuristic
│   ├── LLM Composer assessment (when warranted)
│   └── Supervisory reviews (proactive/coordinator agents)
├── 7. Memory extraction + session summaries (midnight)
└── 8. Scheduler heartbeat event
```

### Problems with current state

1. **Generate decision is scheduler's, not agent's**: Scheduler queries `next_run_at`, checks freshness, decides to generate. Agent has no say.
2. **Proactive agents orphaned**: After ADR-111 P4 absorbed proactive review into Heartbeat, the `get_due_proactive_agents()` function is dead code. Proactive/coordinator review happens inside Composer's per-user heartbeat, coupling agent intelligence to TP's compositional layer.
3. **Composer does too much**: `run_heartbeat()` in `composer.py` reimplements per-agent assessment that agents should own. ~1000 lines of assessment logic that could be ~300 lines reading pulse outcomes.
4. **No visible agent awareness**: Between runs, agents are invisible. No "thinking" events, no "decided to wait" events. Dashboard shows last run time, nothing more.
5. **Schedule conflates two concerns**: `next_run_at` means both "when to check if generation is needed" and "when to generate". These are different decisions.

---

## Target State

```
Every 5 minutes:
├── 1. PULSE DISPATCH — give each agent its turn
│   ├── Query agents where next_pulse_at <= now (ALL modes, not just recurring/goal)
│   ├── For each agent: run pulse (agent_pulse.py)
│   │   ├── Tier 1: Deterministic gates (fresh content? budget? recent run? cooldown?)
│   │   ├── Tier 2: Agent self-assessment (Haiku, associate+ seniority only)
│   │   └── Decision: generate | observe | wait | escalate
│   ├── On "generate" → dispatch_trigger() (existing pipeline, unchanged)
│   ├── On "observe" → write observation to workspace, log activity
│   ├── On "wait" → log activity only
│   ├── On "escalate" → flag for Composer attention
│   └── Update next_pulse_at based on seniority + mode
├── 2. PM PULSE DISPATCH (Tier 3)
│   ├── Query PM agents where next_pulse_at <= now
│   ├── PM reads project state (contributor freshness, quality, work plan, budget)
│   └── Decision: assemble | steer | advance_contributor | assess_quality | wait | escalate
├── 3. Content cleanup (hourly, unchanged)
├── 4. Workspace cleanup (hourly, unchanged)
├── 5. Import jobs (unchanged)
├── 6. COMPOSER — portfolio only (dramatically simplified)
│   ├── Read pulse outcomes from activity_log (bottom-up)
│   ├── Portfolio decisions: create project, dissolve project, rebalance
│   └── No per-agent assessment — agents self-report via pulse
├── 7. Memory extraction + session summaries (midnight, unchanged)
└── 8. Scheduler heartbeat event (updated with pulse stats)
```

---

## Migration Path

### Phase 1: Pulse Engine (`agent_pulse.py`)

**New file**: `api/services/agent_pulse.py`

```python
async def run_agent_pulse(client, agent: dict) -> PulseDecision:
    """
    Execute agent's autonomous sense→decide cycle.

    Tier 1 (deterministic, zero LLM):
    - Has fresh content since last run?
    - Work budget available?
    - Cooldown period elapsed?
    - First run? (always generate)

    Tier 2 (Haiku self-assessment, associate+ only):
    - Agent reads own workspace + fresh content summary
    - Haiku decides: generate | observe | wait | escalate
    - ~200 tokens context, ~50 tokens response

    Returns: PulseDecision(action, reason, observations)
    """
```

**Key design**:
- Tier 1 absorbs `should_skip_agent()` and work budget check from scheduler
- Tier 2 absorbs the proactive review logic from `proactive_review.py`
- PM gets Tier 3 (coordination pulse) — absorbs PM heartbeat from `agent_pipeline.py`
- All pulse decisions logged as `agent_pulsed` / `pm_pulsed` activity events

**Schema change**: `agents.next_run_at` → `agents.next_pulse_at` (migration)

### Phase 2: Scheduler becomes Pulse Dispatcher

**Changes to `unified_scheduler.py`**:

```python
# BEFORE (current)
agents = await get_due_agents(supabase)  # recurring/goal only
for agent in agents:
    should_skip, reason = await should_skip_agent(supabase, agent)
    if should_skip: continue
    budget_ok = check_work_budget(...)
    if not budget_ok: continue
    await process_agent(supabase, agent)  # always generates

# AFTER (pulse dispatcher)
agents = await get_due_pulse_agents(supabase)  # ALL modes
for agent in agents:
    decision = await run_agent_pulse(supabase, agent)  # agent decides
    if decision.action == "generate":
        await process_agent(supabase, agent)  # existing pipeline
    elif decision.action == "observe":
        await write_observation(supabase, agent, decision)
    # wait/escalate: logged in pulse, no further action
    await update_next_pulse_at(supabase, agent)
```

**What moves OUT of scheduler**:
- `should_skip_agent()` → absorbed into pulse Tier 1
- Work budget check → absorbed into pulse Tier 1
- Proactive review (already dead in scheduler, alive in Composer) → absorbed into pulse Tier 2

**What stays in scheduler** (infrastructure, not intelligence):
- Query due agents (but `next_pulse_at` instead of `next_run_at`)
- `process_agent()` execution pipeline (only when pulse says "generate")
- Content/workspace cleanup
- Import jobs
- Memory extraction
- Heartbeat event writing

### Phase 3: Composer Thins to Portfolio-Only

**Changes to `composer.py`**:

Current `run_heartbeat()` does:
1. `heartbeat_data_query()` — gather per-user assessment data (~150 lines)
2. `should_composer_act()` — heuristic check (~100 lines)
3. `_build_composer_prompt()` — build LLM prompt with full assessment (~200 lines)
4. `_run_supervisory_review()` — per-agent proactive review (~150 lines)
5. Execute Composer LLM call → parse actions → execute (~400 lines)

After ADR-126:
1. `heartbeat_data_query()` — read pulse outcomes from `activity_log` (~50 lines)
2. `should_composer_act()` — simplified: any escalations? portfolio gaps? (~30 lines)
3. `_build_composer_prompt()` — portfolio-level prompt, no per-agent assessment (~80 lines)
4. ~~`_run_supervisory_review()`~~ — DELETED (pulse Tier 2 replaces this)
5. Execute Composer LLM call → parse portfolio actions → execute (~150 lines)

**Estimated reduction**: ~1000 lines → ~300 lines

### Phase 4: Proactive/Coordinator Dissolution

- `proactive_review.py` logic absorbed into `agent_pulse.py` Tier 2
- `get_due_proactive_agents()` deleted from scheduler (already dead code)
- `process_proactive_agent()` deleted from scheduler (already dead code)
- Coordinator agents in DB: functionally equivalent to proactive, pulse like proactive
- `proactive_next_review_at` column → absorbed into `next_pulse_at`

### Phase 5: Pulse Cadence Evolution

Seniority-based cadence graduation:

| Seniority | Mode: recurring | Mode: proactive | Mode: reactive |
|-----------|----------------|-----------------|----------------|
| **new** | Pulse on schedule (= current behavior, training wheels) | Pulse every cycle (proactive from birth) | Pulse on event accumulation |
| **associate** | Pulse on schedule + Tier 2 self-assessment (can skip) | Pulse every cycle + Tier 2 | Pulse on event + Tier 2 |
| **senior** | Pulse every cycle (always sensing, generate when warranted) | Pulse every cycle | Pulse every cycle |

**Training wheels**: New recurring agents pulse exactly on their schedule — functionally identical to current behavior. As they mature (associate+), they gain the self-assessment capability to skip unnecessary runs or act early.

---

## Dead Code Cleanup (post-migration)

| Code | Status | Replacement |
|------|--------|-------------|
| `get_due_proactive_agents()` | Dead since ADR-111 P4 | Delete |
| `process_proactive_agent()` | Dead since ADR-111 P4 | Delete |
| `should_skip_agent()` | Active | Absorb into pulse Tier 1, then delete |
| `proactive_review.py` | Active (via Composer) | Absorb into `agent_pulse.py` Tier 2, then delete |
| `composer._run_supervisory_review()` | Active | Delete after pulse Tier 2 |
| `composer.heartbeat_data_query()` partial | Active | Simplify to read pulse outcomes |
| `agents.proactive_next_review_at` | Active | Absorb into `next_pulse_at`, then drop column |

---

## Non-Changes (explicitly preserved)

- **`dispatch_trigger()`** — remains the execution routing layer. Pulse decides IF to execute; dispatch routes HOW.
- **`process_agent()`** — remains the agent execution pipeline. Called when pulse decides "generate".
- **Content/workspace cleanup** — infrastructure, stays in scheduler.
- **Import jobs** — infrastructure, stays in scheduler.
- **Memory extraction** — midnight cron, stays in scheduler.
- **`calculate_next_run_from_schedule()`** — renamed to `calculate_next_pulse_from_schedule()`, same logic.

---

## Implementation Sequence

```
Phase 1 (agent_pulse.py)
    → Can ship independently, scheduler calls pulse before dispatch
    → Backward compatible: new agents pulse, old code still works

Phase 2 (scheduler refactor)
    → Depends on Phase 1
    → Migration: next_run_at → next_pulse_at
    → Dead code cleanup (proactive functions)

Phase 3 (Composer thinning)
    → Depends on Phase 2 (needs pulse events in activity_log)
    → Major code reduction in composer.py

Phase 4 (mode dissolution)
    → Depends on Phases 1-2
    → Documentation + proactive_review.py deletion
    → proactive_next_review_at column drop

Phase 5 (cadence evolution)
    → Depends on Phases 1-4
    → Seniority-based cadence graduation
    → Senior agents pulse every cycle
```

---

## Revision History

| Date | Change |
|------|--------|
| 2026-03-20 | v1 — Initial design plan for scheduler→pulse dispatcher evolution |
