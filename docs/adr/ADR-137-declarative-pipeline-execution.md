# ADR-137: Declarative Pipeline Execution

> **Status**: Phases 1-2, 4 Implemented. Phase 3 (quality gate + reflection) pending.
> **Date**: 2026-03-24
> **Authors**: KVK, Claude
> **Supersedes**: ADR-133 (PM-coordinated phase dispatch — PM as coordinator)
> **Evolves**: ADR-136 (PROCESS.md gains pipeline section), ADR-132 (inference produces pipeline)
> **Extends**: ADR-130 (type registry → pipeline agent selection), ADR-135 (chat coordination preserved)

---

## Context

ADR-133 introduced PM-coordinated phase dispatch: PM pulses every 30 minutes, reads project state, decides who to dispatch. This is expensive (~48 Haiku calls/day), unreliable (PM might dispatch wrong agent), and slow (multi-cycle latency between steps).

The core insight: **execution order is known at project creation time.** A competitive intelligence project always runs: scout → analyst → writer → quality gate → deliver. This doesn't need an LLM to figure out every 30 minutes. It needs a declared pipeline executed mechanically.

### The CrewAI/LangGraph parallel

Modern agent frameworks declare execution graphs as code:
```python
crew = Crew(agents=[researcher, analyst, writer], process=Process.sequential)
```

The sequence is declared, not inferred. We should do the same — but in our filesystem (PROCESS.md), not in Python code.

---

## Decision

### PROCESS.md declares the execution pipeline

Each project's `PROCESS.md` contains a declarative pipeline: ordered steps with dependencies, agent assignments, and execution modes.

```markdown
## Pipeline

- step: scan_competitors
  agent: scout
  trigger: cadence_open

- step: analyze_findings
  agent: analyst
  depends_on: scan_competitors

- step: write_briefing
  agent: writer
  depends_on: analyze_findings

- step: quality_check
  agent: pm
  mode: evaluate
  depends_on: write_briefing
  on_fail: retry(write_briefing, max=2)

- step: deliver
  agent: pm
  mode: compose
  depends_on: quality_check
```

### The scheduler executes the pipeline mechanically

No PM pulse deciding what to dispatch. The scheduler:
1. Checks: is cadence window open for this project?
2. Reads PROCESS.md pipeline definition
3. Reads `pipeline_state.json` for current step
4. Executes the next ready step (dependency met)
5. On completion: advances state, checks next dependency
6. On quality gate fail: steers agent + retries (bounded)
7. On final step: delivers, closes cadence window, writes reflection

### Pipeline state tracking

```json
// /projects/{slug}/memory/pipeline_state.json
{
  "cycle": 3,
  "status": "running",
  "started_at": "2026-03-24T09:00:00Z",
  "steps": {
    "scan_competitors": {"state": "completed", "completed_at": "2026-03-24T09:01:00Z"},
    "analyze_findings": {"state": "running", "started_at": "2026-03-24T09:01:05Z"},
    "write_briefing": {"state": "waiting"},
    "quality_check": {"state": "waiting"},
    "deliver": {"state": "waiting"}
  },
  "last_delivered_at": "2026-03-17T12:00:00Z",
  "retries": {}
}
```

### PM role simplified

PM is no longer an autonomous coordinator. PM is **embedded in the pipeline** as specific step types:

| PM Mode | When | What | Model | Cost |
|---------|------|------|-------|------|
| **evaluate** | After production steps | Check output against success criteria | Haiku | $0.001 |
| **compose** | After evaluate passes | Assemble components, apply layout, deliver | Sonnet | $0.05 |
| **reflect** | After delivery | Update briefs + criteria for next cycle | Haiku | $0.001 |

PM still exists for **chat interaction** (user talks to PM about project status) and **exception handling** (quality gate failures, missing data). But routine coordination is mechanical.

### Complexity-adaptive pipelines

Inference determines pipeline complexity based on project scope:

| Complexity | Pipeline | Agents | Example |
|-----------|----------|--------|---------|
| **Simple** | sense → deliver | 1 + PM passthrough | Daily Slack recap |
| **Standard** | sense → analyze → produce → evaluate → deliver | 2-3 + PM | Weekly competitive intel |
| **Complex** | sense → analyze → produce → review → refine → evaluate → deliver | 3+ + PM with retry loops | Quarterly board review |

Simple projects skip PM assembly — contributor output = deliverable. Direct delivery.

### Inference produces pipeline, not just team

The onboarding inference call outputs a complete pipeline spec per scope:

```json
{
  "name": "AI Competitive Intelligence",
  "complexity": "standard",
  "pipeline": [
    {"step": "scan", "agent_type": "scout"},
    {"step": "analyze", "agent_type": "analyst", "depends_on": "scan"},
    {"step": "write", "agent_type": "writer", "depends_on": "analyze"},
    {"step": "evaluate", "agent_type": "pm", "mode": "evaluate", "depends_on": "write"},
    {"step": "deliver", "agent_type": "pm", "mode": "compose", "depends_on": "evaluate"}
  ]
}
```

`scaffold_project()` writes this to PROCESS.md and creates the agents.

---

## Frontend: Pipeline Visualization

### Workfloor tab shows live pipeline state

```
● Scan ──→ ● Analyze ──→ ○ Write ──→ ○ QA ──→ ○ Deliver
Scout      Analyst       Writer      PM        PM
✓ done     ● running     ○ waiting   ○ waiting  ○ waiting
```

Each node: agent avatar + type badge + state indicator + thought bubble.

### State indicators
- `○` waiting (gray)
- `●` running (blue, animated)
- `✓` completed (green)
- `✗` failed (red)
- `↻` retrying (amber, animated)

### Complexity-adaptive rendering
- **Simple** (1 agent): single agent card + delivery status. No pipeline flow.
- **Standard** (2-3 agents): horizontal pipeline flow.
- **Complex** (3+ agents): horizontal pipeline flow with retry indicators.

### Pipeline state API

`GET /projects/{slug}` returns pipeline state:
```json
{
  "pipeline_state": {
    "cycle": 3,
    "status": "running",
    "steps": [
      {"name": "scan", "agent_type": "scout", "state": "completed"},
      {"name": "analyze", "agent_type": "analyst", "state": "running"},
      ...
    ]
  }
}
```

10s polling for live updates during execution.

---

## Recurring execution

For recurring projects, the pipeline re-runs on cadence:

```
Cycle 1: sense → analyze → produce → evaluate → deliver → reflect
Cycle 2: sense → analyze → produce → evaluate → deliver → reflect
  (reflect from cycle 1 updated briefs, so cycle 2 is better)
```

The reflect step produces `memory/cycle_insights.md` — accumulated learning that feeds into the next cycle's agent context.

For bounded projects, the pipeline runs once. No reflection step.

---

## Cost model (revised)

### Per-cycle cost (standard project, 3 agents)
| Step | Model | Cost |
|------|-------|------|
| Scout (sense) | Sonnet | $0.05 |
| Analyst (reason) | Sonnet | $0.04 |
| Writer (produce) | Sonnet | $0.03 |
| PM evaluate | Haiku | $0.001 |
| PM compose + deliver | Sonnet | $0.05 |
| PM reflect | Haiku | $0.001 |
| **Total** | | **~$0.17** |

### Eliminated costs
- PM Tier 3 coordination pulses: $0 (was ~$0.05/day)
- PM Tier 2 self-assessment: $0 (was ~$0.001/pulse × 48/day)
- Haiku pre-screen per agent: $0 (pipeline is deterministic — no pre-screen needed)

### Monthly (weekly cadence)
~$0.70/month per project. Down from ~$2.00 with PM coordination overhead.

---

## What gets deleted

- PM Tier 3 coordination pulse (`_tier3_pm_coordination()`)
- PM dispatch logic (`_dispatch_contributors()`)
- PM coordination prompts (`_build_tier3_prompt()`)
- PM pulse cadence (`ROLE_PULSE_CADENCE["pm"]`)
- `pm_coordination.py` `pm_announce()` for routine decisions (kept for exceptions)
- Independent contributor pulse for project agents

### What stays
- PM in chat (user interaction, exception handling)
- PM evaluate/compose/reflect as pipeline steps
- Cadence enforcement (Tier 1)
- Chat as coordination substrate (agent completion messages)
- Type registry (ADR-130)
- Charter file split (ADR-136)
- Compose engine (ADR-130 Phase 2)
- Feedback distillation (ADR-117)

---

## Phases

### Phase 1: Pipeline executor
- Parse PROCESS.md pipeline format
- Scheduler reads pipeline, advances steps mechanically
- `pipeline_state.json` tracking
- Delete PM Tier 3 coordination

### Phase 2: Inference produces pipeline
- Update `infer_work_scopes()` to output pipeline spec per scope
- `scaffold_project()` writes pipeline to PROCESS.md
- Complexity-adaptive pipeline selection

### Phase 3: Quality gate + reflection
- PM evaluate step: Haiku checks output against success criteria
- Retry logic: steer + re-run failed step (bounded, max 2)
- PM reflect step: update briefs + criteria for next cycle

### Phase 4: Frontend pipeline visualization
- Pipeline flow component (horizontal nodes with states)
- Complexity-adaptive rendering (simple vs standard vs complex)
- Pipeline state API + 10s polling
- Delivery history linked to pipeline cycles

---

## Trade-offs

### Accepted
1. **Less PM autonomy** — PM doesn't decide execution order. Accepted because order is deterministic and LLM-decided coordination was expensive + unreliable.
2. **Pipeline changes require re-scaffold** — changing team composition means updating PROCESS.md. Accepted because this is a user/TP action, not routine.
3. **Quality gate adds latency** — evaluate step adds one Haiku call before delivery. Accepted because catching bad output is worth $0.001.

### Rejected
1. **Dynamic pipeline modification by PM** — PM could rewrite PROCESS.md at runtime. Rejected: pipeline should be stable between cadence cycles. Changes happen at reflect time.
2. **Parallel step execution** — steps in the same phase could run in parallel. Rejected for v1: sequential is simpler, correct, and still fast enough. Add parallelism when proven needed.
3. **PM pulse alongside pipeline** — keeping PM coordination as fallback. Rejected per discipline #1: singular implementation.
