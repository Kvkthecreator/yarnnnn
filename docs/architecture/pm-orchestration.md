# PM Orchestration Model

> **Status**: Canonical. Honest assessment of implemented vs. gap state.
> **Date**: 2026-03-23
> **Rule**: All PM coordination decisions should be consistent with this document.
> **Related**: ADR-120 (PM role), ADR-121 (intelligence director), ADR-128 (coherence), ADR-133 (phase dispatch), ADR-135 (chat as coordination substrate)

---

## What the PM Is

The PM is a **domain-cognitive agent whose domain is project coordination**. It's an agent type in the registry (`role: "pm"`) with specialized capabilities: read workspace, check freshness, steer contributors, trigger assembly, manage work plan.

The PM is NOT a third layer of intelligence. It's a specialized agent within the second layer (alongside contributors). TP creates PMs; PMs coordinate contributors. Two layers, not three.

Every project has exactly one PM. PM agents are infrastructure — excluded from tier agent limits. They're auto-created by `scaffold_project()`.

---

## Two Decision Engines (Current Reality)

The PM has TWO independent decision paths that do NOT coordinate:

### Engine 1: Tier 3 Pulse (Haiku, every 30 min)

**What it does**: Quick coordination assessment. Reads work plan + phase state + contributor assessments. Decides: dispatch, advance_phase, generate, wait, escalate.

**Side effects it can execute**:
- Set `next_pulse_at` on contributors (dispatch)
- Write `phase_state.json` (advance phase)
- Write contribution briefs (phase context injection)
- Log activity events

**What it CANNOT do**:
- Write work_plan.md
- Trigger assembly
- Steer specific contributors with detailed briefs
- Assess quality

**Model**: Haiku (cheap, ~$0.001/call)
**Frequency**: Every 30 min cadence + event-triggered (when contributor completes)

### Engine 2: Headless Run (Sonnet, when pulse decides "generate")

**What it does**: Deep project assessment using 5-layer cognitive model. Produces structured JSON with assessment + action.

**Actions it can execute**:
- `assemble` — compose contributions into deliverable, deliver
- `steer_contributor` — write contribution brief with directive
- `assess_quality` — score contributor outputs
- `advance_contributor` — set next_pulse_at to trigger run
- `wait` — no action
- `escalate` — log event (currently no handler beyond logging)

**What it CANNOT do**:
- Update `phase_state.json` (Tier 3 only)
- Dispatch multiple contributors simultaneously (Tier 3 only)
- Update `work_plan.md` (action in prompt but NO HANDLER)

**Model**: Sonnet (full intelligence, ~$0.01-0.05/call)
**Trigger**: Only when Tier 3 decides "generate"

### The Gap: No Coordination Between Engines

Tier 3 runs Haiku for quick dispatch decisions. If it decides "generate," the headless PM runs Sonnet independently — it doesn't know what Tier 3 decided or what was dispatched. The two engines share workspace files but not decision state.

---

## PM Execution Flow (What Actually Happens)

```
Scheduler (every 1 min) picks up PM where next_pulse_at <= now
  │
  ├── Tier 1: Deterministic gates (budget, cooldown)
  │     └── If blocked → wait
  │
  └── Tier 3: PM Coordination (Haiku)
        │
        ├── Reads: work_plan.md, phase_state.json, contributor assessments
        ├── Decides: dispatch | advance_phase | generate | wait | escalate
        │
        ├── If DISPATCH:
        │     ├── Write phase briefs for target contributors
        │     ├── Set next_pulse_at on contributors (triggers their run)
        │     └── Return action="generate" (PM should also run)
        │
        ├── If ADVANCE_PHASE:
        │     ├── Update phase_state.json
        │     ├── Log phase_advanced event
        │     └── Return action="generate"
        │
        ├── If GENERATE:
        │     └── PM runs headless (Sonnet, full assessment)
        │           │
        │           ├── 5-layer cognitive model assessment
        │           ├── Produces JSON: {project_assessment, action, ...}
        │           ├── Writes project_assessment.md (always)
        │           │
        │           ├── If action=ASSEMBLE:
        │           │     ├── Read all contributions
        │           │     ├── Compose with Sonnet + RuntimeDispatch
        │           │     ├── Write to /assemblies/{date}/
        │           │     └── Deliver (email/slack/notion)
        │           │
        │           ├── If action=STEER_CONTRIBUTOR:
        │           │     └── Write contribution brief
        │           │
        │           ├── If action=ASSESS_QUALITY:
        │           │     └── Write quality_assessment.md
        │           │
        │           ├── If action=ADVANCE_CONTRIBUTOR:
        │           │     └── Set next_pulse_at (trigger run)
        │           │
        │           └── If action=WAIT/ESCALATE:
        │                 └── Log only
        │
        └── If WAIT/ESCALATE:
              └── Log, compute next_pulse_at
```

---

## What the PM Writes (Workspace Artifacts)

| File | Written By | When | Semantics |
|------|-----------|------|-----------|
| `memory/project_assessment.md` | Headless PM | Every headless run | Overwrite — 5-layer assessment |
| `memory/quality_assessment.md` | Headless PM | action=assess_quality | Overwrite — per-contributor scores |
| `contributions/{slug}/brief.md` | Tier 3 (phase dispatch) OR Headless (steer) | On dispatch or steer | Overwrite — PM directive to contributor |
| `memory/phase_state.json` | Tier 3 only | On advance_phase | Overwrite — phase completion tracking |
| `assemblies/{date}/output.md` | Assembly pipeline | On assemble | New folder per assembly |
| `assemblies/{date}/manifest.json` | Assembly pipeline | On assemble | Delivery metadata |
| `memory/decisions.md` | Chat PM only | User makes decision in chat | Append — durable decisions |

**NOT written by PM**:
- `memory/work_plan.md` — action exists in prompt but **no handler implemented**
- `AGENT.md` — read only
- `memory/self_assessment.md` — PM doesn't self-assess (contributors only)

---

## PM's 5-Layer Cognitive Model

The headless PM prompt (v6.0) implements prerequisite-layer reasoning:

```
Layer 1: COMMITMENT — Is the objective clear?
  → If deliverable/audience/format/purpose incomplete → STOP. Escalate.

Layer 2: STRUCTURE — Do we have the right team?
  → Are contributor types adequate for the objective?
  → Is there a capability gap? (e.g., need charts but no analyst)

Layer 3: CONTEXT — Is the data fresh?
  → Have contributors run recently?
  → Is platform content current?

Layer 4: QUALITY — Are contributions good enough?
  → Read contributor assessments (mandate/fitness/context/confidence)
  → Are outputs thin, off-topic, or stale?

Layer 5: READINESS — Ready to assemble and deliver?
  → All contributions present?
  → Work plan schedule says deliver now?
  → Budget available?
```

**Rule**: Stop at the first broken layer. Don't assess quality if structure is wrong. Don't assemble if context is stale.

---

## Critical Gaps (Honest Assessment)

### 1. `update_work_plan` is Not Implemented

The PM prompt lists `update_work_plan` as a valid action. The output validation checks for it. But there is **no handler** in `_handle_pm_decision()`. A PM that returns this action will fail silently.

**Impact**: PM cannot evolve the work plan through headless execution. Work plans are static after scaffold unless manually edited or Tier 3 writes phase_state.json.

**Fix needed**: Add handler that writes `memory/work_plan.md` from the PM's decision payload.

### 2. Two Engines Don't Coordinate

Tier 3 (Haiku) and headless (Sonnet) run independently. Tier 3 might dispatch contributors, then headless PM runs and tries to dispatch the same contributors again. No shared decision state.

**Impact**: Potential duplicate dispatches. Tier 3 decisions not available to headless PM.

**Fix needed**: Tier 3 should write its decision to `memory/last_pulse_decision.json`. Headless PM reads it to avoid redundant actions.

### 3. Headless PM Cannot Update Phase State

Only Tier 3 (via `_advance_phase_state()`) can write `phase_state.json`. Headless PM cannot.

**Impact**: Phase advancement only happens during quick Haiku pulses, not during deep Sonnet assessments. If headless PM identifies phase completion during a thorough assessment, it can't act on it.

**Fix needed**: Add phase_state.json write capability to headless PM execution path.

### 4. `escalate` is a No-Op

The escalate action logs an activity event but nothing reads escalation events to trigger Composer action. Composer's `should_composer_act()` checks for `pulse_escalation` events, but the connection between PM escalation and Composer response is untested.

**Impact**: PM can cry for help but nobody answers.

**Fix needed**: Verify Composer heartbeat reads PM escalation events and responds.

### 5. Chat PM is Advisory Only

Chat PM has full tool access but cannot dispatch contributors, update phases, or trigger assembly. It can only write briefs and decisions.

**Impact**: User asking PM to "run the briefer now" in chat gets a text response but no action. The PM would need to wait for next Tier 3 pulse.

**Fix needed**: Add dispatch capability to chat PM (via RequestContributorAdvance primitive, already available in agent_chat mode).

### 6. Tier 3 JSON Response Format Undocumented in Prompt

The `_build_tier3_prompt()` ends with a JSON example but doesn't say "respond with ONLY JSON." Haiku sometimes wraps the JSON in explanation text, which `_parse_pulse_response()` may fail to extract.

**Impact**: "PM pulsed — unknown" events in production (visible in user's activity feed).

**Fix needed**: Add explicit "Respond with ONLY a JSON object. No explanation." instruction.

---

## How Recent Refactoring Impacted PM

### ADR-130 (Type Registry)
- PM is now a registered type with fixed capabilities
- `has_asset_capabilities("pm")` returns False (correct — PM doesn't produce visual assets)
- PM's pulse cadence defined in `ROLE_PULSE_CADENCE` (30 min)
- No capability regression — PM tools unchanged

### ADR-133 (Phase Dispatch)
- **New**: Tier 3 coordination pulse (positive — PM now has a dedicated coordination path)
- **New**: Contributors are PM-dispatched (positive — PM controls execution order)
- **Gap**: Tier 3 and headless are decoupled (see gap #2)
- **Gap**: Phase state only writable from Tier 3 (see gap #3)

### ADR-134 (Project Surface)
- PM visible on workfloor as team card (positive)
- PM activity shown when PM card selected (positive)
- Assembly config shown under PM detail (positive)
- No execution impact — frontend only

### v2 Type Names
- PM role unchanged (always "pm")
- `resolve_role("pm")` passes through correctly
- PM prompt template key is "pm" in ROLE_PROMPTS — no mapping needed
- No regression

---

## Architecture Principles (From FOUNDATIONS.md)

1. **PM is domain-cognitive, not a third layer**. PM's domain is this specific project's execution. It reasons about contributor fitness, phase readiness, and delivery timing — not about what agents should exist (that's Composer).

2. **PM develops through knowledge accumulation**. A tenured PM knows its project's patterns: which contributors need more guidance, what the user typically edits, when content is typically fresh. This knowledge lives in workspace files, not in capability progression.

3. **PM coordinates, contributors produce**. PM never produces user-facing content (except assembly). It reads, steers, gates, and delivers. Contributors produce the work product.

4. **One PM per project, always**. PM is infrastructure. No exceptions, including simple digest projects. Even a 1-contributor project has a PM that manages delivery cadence.

---

## Recommended Fix Priority

| Gap | Severity | Effort | Fix |
|-----|----------|--------|-----|
| #6 (Tier 3 JSON format) | High (production errors) | Low | Add "ONLY JSON" to prompt |
| #1 (update_work_plan) | High (silently fails) | Medium | Add handler in _handle_pm_decision |
| #5 (Chat PM advisory) | Medium (UX friction) | Low | RequestContributorAdvance already in agent_chat mode |
| #2 (engine coordination) | Medium (duplicate work) | Medium | Write last_pulse_decision.json |
| #3 (phase state from headless) | Medium (limits assessment) | Low | Add write path |
| #4 (escalate no-op) | Low (rare path) | Low | Verify Composer reads escalation events |
