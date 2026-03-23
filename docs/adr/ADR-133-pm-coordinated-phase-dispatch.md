# ADR-133: PM-Coordinated Phase Dispatch

> **Status**: Phase 1 Implemented (PM coordination pulse + contributor dispatch routing). Phase 2-3 proposed.
> **Date**: 2026-03-23
> **Authors**: KVK, Claude
> **Supersedes**: ADR-126 (independent contributor pulse), ADR-088 (trigger dispatch — caller changes)
> **Evolves**: ADR-120 (PM → phase orchestrator), ADR-121 (steering → phase-aware), ADR-128 (coherence → cross-phase context)
> **Extends**: ADR-130 (type registry informs capability-aware decomposition)

---

## Context

YARNNN's current execution model gives every agent an independent pulse — each agent senses its domain, decides whether to act, and generates autonomously. This was the right model for single-agent work (ADR-126). But for multi-agent projects, it creates a fundamental coordination problem:

**Agents run independently when they should run in sequence.**

A quarterly business review needs: researcher gathers data → analyst finds patterns → writer crafts narrative → PM assembles. Today, all four agents pulse on their own cadence. The writer might run before the researcher has produced anything. The analyst might synthesize stale data. The PM triggers assembly whenever contributions exist, regardless of whether the work is coherent.

The current model is **co-located agents sharing a folder**, not **a coordinated team executing a plan**.

### What we have today

```
Scheduler (every 5 min)
  → For each agent with next_pulse_at <= now:
    → Tier 1: deterministic gates (budget, freshness, cooldown)
    → Tier 2: Haiku self-assessment (should I generate?)
    → If generate: run agent independently
    → PM: check contributor freshness → maybe assemble
```

### What's wrong

1. **No sequencing**: agents run in whatever order their pulse cadence dictates
2. **No dependency graph**: "drafter needs researcher's output" is nowhere in the system
3. **No work decomposition**: the project objective exists but nothing breaks it into phases
4. **No cross-agent data flow**: contributor A's output doesn't flow into contributor B's context
5. **PM is reactive**: checks freshness after the fact, doesn't orchestrate execution order

### The real-world analogy

A team manager doesn't give every team member an alarm clock and hope they coordinate. The manager runs the standup, assigns tasks in order, ensures handoffs, and advances the project through phases.

---

## Decision

### PM owns the heartbeat. Contributors are dispatched.

The execution model inverts: from **N independent pulses** to **1 PM pulse that dispatches N contributors**.

```
PM pulses on cadence (every 2h)
  → PM reads structured work plan (phases, dependencies)
  → PM checks: what phase are we in? what's blocking?
  → PM decides: which contributor(s) should run next?
  → PM dispatches contributor runs with phase context
  → Contributors execute within injected context
  → PM reads assessments on next pulse
  → PM advances phase or re-steers
```

### Three execution modes

| Mode | Pulse Owner | Example |
|------|------------|---------|
| **Standalone agent** (no project) | Agent itself | A lone briefer running daily recaps |
| **Project contributor** (in a project) | Project PM | A researcher assigned to Phase 1 of quarterly review |
| **PM agent** | PM itself | The project coordinator, pulses every 2h |

Standalone agents retain independent pulse (Tier 1 + Tier 2). They have no PM, so they self-govern. Project contributors lose independent pulse — the PM dispatches them when their phase is ready.

### Work plan as structured phases

The PM's work plan evolves from free text to structured phases with dependencies:

```markdown
# Work Plan

## Objective
Produce quarterly business review for the board.

## Phases

### Phase 1: Research (parallel)
- **status**: complete
- **contributors**:
  - [x] market-researcher: Competitive landscape analysis
  - [x] data-analyst: Internal metrics Q2 vs Q1

### Phase 2: Synthesis (depends on Phase 1)
- **status**: in_progress
- **contributors**:
  - [ ] board-writer: Executive narrative combining research + analysis

### Phase 3: Assembly (depends on Phase 2)
- **status**: blocked
- **contributors**:
  - [ ] pm: Assemble final deliverable + deliver
```

The PM reads this plan, checks phase status, and dispatches. The format is markdown (PM is an LLM, it reads markdown naturally). Phase state tracking uses a sidecar file:

```json
// /projects/{slug}/memory/phase_state.json
{
  "current_phase": "Phase 2: Synthesis",
  "phases": {
    "Phase 1: Research": {
      "status": "complete",
      "completed_at": "2026-03-23T14:00:00Z",
      "outputs": ["market-researcher/outputs/2026-03-23T1200", "data-analyst/outputs/2026-03-23T1300"]
    },
    "Phase 2: Synthesis": {
      "status": "in_progress",
      "dispatched_at": "2026-03-23T14:30:00Z",
      "contributors_dispatched": ["board-writer"]
    }
  }
}
```

### Cross-phase context injection

When the PM dispatches a Phase N+1 contributor, it writes a **phase brief** — not a raw dump of prior phase outputs, but a PM-curated summary of what Phase N produced and what Phase N+1 should build on:

```markdown
// Written by PM to /projects/{slug}/contributions/{writer-slug}/brief.md

## Phase Context (from Phase 1: Research)

### Key Findings
- Market researcher found 3 new entrants in enterprise segment
- Data analyst shows 33% revenue growth, driven by expansion not new logos
- Churn improved from 3.2% to 2.1%

### What This Phase Should Do
Craft the board narrative around the expansion story. Lead with revenue growth,
contextualize with competitive landscape, close with churn improvement as
operational excellence signal.

### Source Material
Full research output: /agents/market-researcher/outputs/2026-03-23T1200/output.md
Full analysis: /agents/data-analyst/outputs/2026-03-23T1300/output.md
```

This is the **contribution brief** mechanism (ADR-121) evolved to carry cross-phase context. The brief already exists — it now includes phase outputs.

### PM coordination pulse (Tier 3)

The PM's pulse becomes a three-step coordination cycle:

```
1. SENSE: Read work plan + phase_state.json + contributor assessments
2. DECIDE:
   - Current phase complete? → advance to next phase
   - Phase blocked? → steer contributor or escalate
   - All phases complete? → trigger assembly
   - Budget exhausted? → escalate to Composer
3. ACT:
   - Write phase briefs for next phase contributors
   - Dispatch contributor runs (set their next_run_at)
   - Update phase_state.json
   - Log pm_pulsed event
```

### Capability-aware decomposition (ADR-130 connection)

When the PM (or Composer) decomposes an objective into phases, the type registry informs assignment:

- Need charts? → assign an analyst (has chart capability)
- Need external research? → assign a researcher (has web_search)
- Need video? → assign a drafter (has video_render)
- Need polished prose? → assign a writer

The `AGENT_TYPES` registry is the vocabulary for work decomposition. The PM doesn't need to know implementation details — it knows "this phase needs data visualization, which means an analyst."

---

## What changes

### `agent_pulse.py` — Refactored

- **Standalone agents**: Tier 1 + Tier 2 preserved (independent pulse)
- **Project contributors**: Skip pulse entirely — `next_pulse_at` set by PM dispatch, not by agent cadence
- **PM agents**: Tier 1 + new Tier 3 (PM coordination pulse replaces generic Tier 2)
- The `run_agent_pulse()` function checks: is this agent in a project? If PM → Tier 3. If contributor → skip (PM dispatches). If standalone → Tier 1 + Tier 2.

### Unified scheduler — Caller changes

- **Current**: `for agent in get_due_agents(): run_agent_pulse(agent)`
- **New**: Same loop, but `run_agent_pulse()` routes differently:
  - PM: coordination pulse (sense→decide→dispatch)
  - Standalone: independent pulse (Tier 1 + Tier 2)
  - Project contributor: no-op (PM dispatches via `next_pulse_at` override)

### PM execution strategy — Phase orchestration

PM's execution path gains:
1. Read `phase_state.json` (which phase, what's complete)
2. Check current phase contributor outputs
3. Write phase briefs for next phase (cross-phase context)
4. Set `next_pulse_at` on dispatched contributors (triggers their run)
5. Update `phase_state.json`

### Workspace conventions (ADR-119 extension)

New project workspace files:
- `/projects/{slug}/memory/work_plan.md` — structured phases (evolves from current free-text)
- `/projects/{slug}/memory/phase_state.json` — phase tracking sidecar
- `/projects/{slug}/contributions/{agent-slug}/brief.md` — phase-aware briefs (already exists, gains phase context)

### Activity events

- `agent_pulsed` — retained for standalone agents only
- `pm_pulsed` — PM coordination pulse (already declared)
- New: `phase_advanced` — PM advanced project to next phase
- New: `contributor_dispatched` — PM dispatched a contributor for a phase

---

## Different project shapes

### Simple recurring (1 contributor + PM)

```
Phase 1: briefer runs daily
Phase 2: PM delivers
```

PM pulse is simple: check if briefer has new output → deliver. No multi-phase complexity. This is the common case and it works like today, just with PM as the trigger instead of independent pulse.

### Multi-agent bounded (quarterly review)

```
Phase 1: Research (researcher + analyst, parallel)
Phase 2: Synthesis (writer, sequential)
Phase 3: Assembly + delivery (PM)
```

PM orchestrates phases. Each phase gates the next. Cross-phase briefs carry context forward.

### Ongoing monitoring with periodic rollup

```
Phase 1: Scout runs weekly (recurring)
Phase 2: Analyst processes scout output (triggered by Phase 1 completion)
Phase 3: PM assembles monthly report (triggered by N Phase 2 cycles)
```

PM manages the cadence — scout runs on schedule, analyst runs after each scout output, monthly rollup assembles N analyst outputs.

---

## What stays unchanged

- **Agent types and capabilities** (ADR-130) — unchanged, used for decomposition
- **Self-assessment extraction** (ADR-128 Flow 1) — contributors still produce assessments
- **Feedback distillation** (ADR-117) — user edits still flow to preferences.md
- **Composer heartbeat** (ADR-111) — still portfolio-level, now reads PM phase state
- **Workspace filesystem** (ADR-119) — conventions extended, not replaced
- **Delivery pipeline** (ADR-118 D.3) — unchanged, reads from output folder
- **Compose engine** (ADR-130 Phase 2) — unchanged, post-generation step

---

## Phases

### Phase 1: PM coordination pulse + structured work plan

- Refactor `agent_pulse.py`: route PM → Tier 3, contributor → skip, standalone → Tier 1+2
- Implement Tier 3: PM reads work plan + phase_state.json, decides next action
- Structured work plan format: markdown phases with dependency conventions
- `phase_state.json` sidecar for deterministic phase tracking
- PM dispatches contributors by setting `next_pulse_at` on their agent record
- Activity events: `pm_pulsed`, `phase_advanced`, `contributor_dispatched`

### Phase 2: Cross-phase context injection

- PM writes phase briefs with prior phase context (evolves contribution briefs)
- Contributor context loading reads phase brief (already reads brief.md — gains phase context)
- Phase output references in briefs (paths to prior phase output.md files)

### Phase 3: Capability-aware work decomposition

- PM (or Composer) decomposes objective into phases using type registry vocabulary
- Phase contributor assignment informed by `AGENT_TYPES[type].capabilities`
- Work plan auto-generation from project objective + available contributor types

---

## Trade-offs

### Accepted

1. **Contributors lose autonomy in projects** — they run when PM says, not on their own schedule. Accepted because coordination > independence for multi-agent work.
2. **PM is a bottleneck** — if PM pulse fails, no contributors run. Accepted because a coordinator bottleneck is better than uncoordinated chaos. Escalation to Composer handles PM failures.
3. **Simple projects have overhead** — a single-contributor project still goes through PM dispatch. Accepted because singular implementation means one execution model, not two.

### Rejected

1. **Contributor-to-contributor direct dispatch** — contributors triggering each other without PM. Rejected: PM is the single coordination point. Direct dispatch creates invisible dependencies.
2. **Complex DAG engine** — a formal workflow engine with conditional branching. Rejected: PM is an LLM, it reads markdown phases. Keep it simple. Add complexity when proven needed.
3. **Keeping independent contributor pulse alongside PM dispatch** — dual approach. Rejected per discipline #1: singular implementation.

---

## Axiom Alignment

| Foundation | Alignment |
|---|---|
| **Axiom 1 (Two Layers)** | PM is domain-cognitive (project execution domain). TP creates PMs. PMs orchestrate contributors. Still two layers — PM is not a third layer, it's a specialized agent within the second layer. |
| **Axiom 2 (Recursive Perception)** | Cross-phase context injection adds a new perception channel: contributors perceive prior phases via PM-curated briefs. Three substrates preserved. |
| **Axiom 3 (Developing Entities)** | PM develops coordination intelligence through accumulated phase execution history. Contributors develop domain expertise through feedback. Development is still knowledge depth. |
| **Axiom 6 (Autonomy)** | PM is autonomous (pulses, decides, dispatches). Contributors are autonomous within their phase (choose how to investigate, what to emphasize). Autonomy is scoped, not removed. |
