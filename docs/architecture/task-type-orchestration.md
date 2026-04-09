# Task Type Orchestration Architecture

> Canonical reference for the task type registry, process execution model, and orchestration scalability.
>
> **Terminology:** "Process" is the canonical term for the multi-step agent sequence, used in both user-facing surfaces and the data model (`"process"` field in task type registry). The internal execution engine file is `task_pipeline.py` (the engine IS a pipeline; the data it executes is a "process").
> ADR: [ADR-145](../adr/ADR-145-task-type-registry-premeditated-orchestration.md)
> Product catalog: [docs/features/task-types.md](../features/task-types.md)

---

## Overview

Task types are YARNNN's product surface — concrete deliverables or recurring
work contracts users select, backed by pre-meditated multi-agent execution
pipelines. The system resolves "I want a Competitive Intelligence Brief" into a
deterministic sequence of agent steps, each contributing its best capability.

**Core principle:** Deliverable-first, not agent-first. Users think in outcomes; the platform resolves outcomes into agent orchestration.

---

## Registry Design

### Location

`api/services/task_types.py` — single source of truth.

### Schema

```python
TASK_TYPES: dict[str, TaskTypeDefinition] = {
    "type-key": {
        "display_name": str,           # User-facing name
        "description": str,            # One-line description for onboarding cards
        "output_kind": str,            # accumulates_context | produces_deliverable | external_action | system_maintenance
        "default_mode": str,           # recurring | goal | reactive
        "default_schedule": str,        # daily | weekly | biweekly | monthly | on-demand
        "layout_mode": str,             # document | digest | email | message | comment
        "output_format": str,           # html | markdown
        "export_options": list[str],    # ["pdf", "pptx", "xlsx"]
        "process": list[ProcessStep],   # Ordered execution steps
        "context_reads": list[str],     # Domains or ["*"] for all domains
        "context_writes": list[str],    # Domains written by tracking tasks
        "requires_platform": str|None,  # "slack" | "notion" | None
        "default_deliverable": dict,    # Deliverable contract scaffold for DELIVERABLE.md
        "bootstrap": dict|None,         # Optional readiness criteria for context tasks
    }
}
```

### Process Step Schema

```python
ProcessStep = {
    "agent_type": str,      # Key from AGENT_TYPES registry (ADR-140)
    "step": str,            # Human-readable step name: "investigate", "compose", "extract"
    "instruction": str,     # Step-specific instruction merged into task execution prompt
    "requires": list[str],  # Optional capability requirements: ["web_search", "chart"]
}
```

### Resolution Path

```
User selects task type
    → look up TASK_TYPES[type_key]
    → assign output_kind + default_mode + context wiring
    → for each process step:
        → resolve agent from user's roster by agent_type
        → verify required capabilities via AGENT_TYPES registry
        → inject step instruction into execution prompt
    → scaffold TASK.md with type_key, objective, process reference
```

---

## Pipeline Execution Model

### Single-Step (Simple)

Most platform digests and single-domain tasks.

```
Scheduler → read TASK.md → resolve agent → execute → save output → deliver
```

Identical to current ADR-141 flow. No change.

### Multi-Step (Collaborative)

Research, operations, and content tasks that benefit from agent specialization.

```
Scheduler → read TASK.md → resolve pipeline from type_key
    → Step 1: execute agent_type[0] with step instruction
        → save to /tasks/{slug}/outputs/{date}/step-1/output.md
    → Step 2: execute agent_type[1] with step instruction + Step 1 output as context
        → save to /tasks/{slug}/outputs/{date}/step-2/output.md
    → ...
    → Final step output → post-generation (compose HTML) → deliver
```

### Handoff Mechanism

Step N+1 receives Step N's output as **explicit context injection** in the user message, not via knowledge-base discovery. This is critical — it ensures deterministic context flow, not probabilistic search.

```python
# In execute_task() pipeline loop:
prior_output = read_step_output(task_slug, date, step_n)
step_context = f"""
## Prior Step Output ({pipeline[step_n]['step']})
The {pipeline[step_n]['agent_type']} agent produced the following:

{prior_output}

Your role: {pipeline[step_n+1]['instruction']}
"""
```

### Output Storage Convention

```
/tasks/{slug}/outputs/{date}/
├── step-1/
│   ├── output.md          # Step 1 agent's raw output
│   └── manifest.json      # Step metadata
├── step-2/
│   ├── output.md          # Step 2 agent's raw output
│   └── manifest.json
├── output.md              # Final deliverable (copy of last step)
├── output.html            # Composed HTML (post-generation)
├── manifest.json          # Pipeline-level manifest
└── assets/                # Charts, diagrams, images from any step
```

### Live Execution Progress

During multi-step execution, a `status.json` file is written to the output folder at three points:
1. **Before first step:** `{status: "running", current_step: 0, total_steps: N}`
2. **After each step completes:** `{status: "running", current_step: K, completed_steps: [...]}`
3. **After pipeline completes:** `{status: "completed", completed_at: ...}`

The frontend "Process" tab polls `GET /api/tasks/{slug}/status` every 3s during execution, showing a live stepper with completed/active/pending step states. Falls back to 10s polling when idle.

```
/tasks/{slug}/outputs/{date}/
├── status.json              # Ephemeral — live execution progress
├── step-1/...
├── step-2/...
└── ...
```

`status.json` uses `lifecycle=ephemeral` — cleaned up by workspace cron.

### Empty Step Handling

If a pipeline step produces empty or minimal output (e.g., Marketing Agent finds no signals):
- The step writes a short explanation: "No significant signals detected this period."
- Next step receives this and adapts (e.g., Research Agent skips investigation, outputs summary)
- Final output is still delivered — never silent

### Graceful Degradation

If an agent type required by a pipeline step is missing from the user's roster:
- Skip the step
- Remaining steps execute with available context
- Log a suggestion to TP: "This task would benefit from a {missing_type} agent"

---

## Pre-Meditated vs. Improvised Orchestration

Two orchestration modes coexist:

| Aspect | Pre-Meditated | Improvised |
|--------|--------------|------------|
| When | Task has registered type_key | Custom/novel task (no type_key) |
| Who decides | Registry (product decision) | TP at runtime (AI decision) |
| Cost | Deterministic (steps * ~$0.05) | Variable (depends on TP reasoning) |
| Quality | Consistent, improving via feedback | Variable, depends on TP prompt |
| Use case | Known deliverable patterns | Novel user requests |

**Promotion path:** When TP consistently improvises the same pattern (e.g., "research topic → format as report" repeated 3+ times), suggest promoting it to a registered task type.

## Surface Implications

Task types should not produce one bespoke page per `type_key`. The shell should
follow the same registry boundary the execution model uses:

1. `output_kind` decides the primary `/work` detail shape
2. registry metadata (`requires_platform`, `bootstrap`, `layout_mode`) adds
   bounded secondary modules
3. `type_key` specializes copy and small task-family affordances

This keeps task presentation aligned with the execution model:

- `accumulates_context` tasks are about context growth, freshness, and change logs
- `produces_deliverable` tasks are about rendering and delivering an artifact
- `external_action` tasks are about target, payload, and delivery result
- `system_maintenance` tasks are about deterministic upkeep and observability

Each task run should emit a surface-ready packet for the frontend, but
"surface-ready output" is not always the same thing as a complete task view.
Deliverable tasks can be artifact-led; the other three kinds still need
operational context, history, and provenance around the artifact.

---

## The Five-Layer Capability Web

```
Layer 1: DELIVERABLES (task types — what users see and select)
    ↕ Product decisions: curated, deliberate
Layer 2: PROCESSES (execution plans — ordered agent steps)
    ↕ Platform decisions: deterministic, versioned
Layer 3: AGENTS (identity + capabilities — who executes)
    ↕ Roster decisions: pre-scaffolded, expandable
Layer 4: CAPABILITIES (skills + runtimes — what's technically possible)
    ↕ Engineering decisions: tools, integrations
Layer 5: KNOWLEDGE (workspace + platforms + memory — what agents know)
    ↕ Emergent: accumulates from usage
```

### Change Propagation

**Upward:** New capability (L4) → new agent ability (L3) → new pipeline option (L2) → new task type (L1)
*Example:* Add `write_email` capability → CRM agent gains it → "Follow-Up Email" pipeline becomes possible → new task type registered.

**Downward:** User demand for deliverable (L1) → pipeline design (L2) → capability gap identified (L4) → engineering work
*Example:* Users want "Data Dashboard" → pipeline needs Analytics agent → need SQL capability → build it.

### Adding a New Agent Type

1. Define in Agent Type Registry (ADR-140: `AGENT_TYPES`)
2. Add to default roster if universal (ADR-140: `DEFAULT_ROSTER`)
3. Review existing task types: can any pipeline benefit from this agent?
4. Define new task types this agent enables
5. Update capability matrix

### Adding a New Capability

1. Register in Capability Registry (ADR-140: `CAPABILITIES`)
2. Assign to relevant agent types
3. Review task types using those agents: does the capability enhance delivery?
4. Potentially unlock new task types or new pipeline steps

---

## Pipeline Evolution Model

### Phase 1: Deterministic Defaults (Ship)

Registry defines canonical pipelines. Scheduler executes mechanically. No runtime adaptation.

### Phase 2: Agent-Level Learning (Already Built)

Each agent in the pipeline improves independently via:
- Feedback consolidation (ADR-143): user edits → `feedback.md` → adjusted output
- Self-assessment (ADR-128): output evaluated against task criteria
- Playbook evolution: `playbook-outputs.md` absorbs what works

Same pipeline, better output over time.

### Phase 3: Pipeline-Level Observation (Proposed)

After pipeline completion, capture signals:
- Step contribution value (which step's output appears most in final deliverable?)
- Handoff sufficiency (did step N+1 have enough context?)
- Over-production signals (user consistently ignores certain sections)

Stored in `/tasks/{slug}/memory/pipeline_observations.md`. Read by TP during heartbeat.

### Phase 4: TP Pattern Recognition (Future)

TP heartbeat reads pipeline health signals and:
- Suggests pipeline adjustments ("step 2 adds low value → collapse to 2 steps")
- Promotes successful improvised patterns to registered types
- Recommends new task types based on usage patterns

---

## Orchestration as Platform Capability

Pipeline orchestration is not an agent's capability — it's the platform's. This means:

1. **Versioned:** Pipeline templates follow prompt versioning rigor (CHANGELOG.md)
2. **Observable:** Each step logged with timing, cost, output size, agent used
3. **Bounded:** Max 4 steps per pipeline (cost governance + latency)
4. **Discoverable:** TP can identify successful improvised orchestrations for promotion

---

## Key Files

| File | Purpose |
|------|---------|
| `api/services/task_types.py` | Task type registry + scaffold + resolve |
| `api/services/task_pipeline.py` | Pipeline-aware execution (extends ADR-141), writes status.json for live progress |
| `web/components/tasks/ProcessTab.tsx` | Process visualization with live progress polling |
| `api/services/task_workspace.py` | Step-scoped output storage |
| `api/services/agent_framework.py` | Agent type + capability registries (ADR-140) |
| `api/routes/tasks.py` | `GET /api/tasks/types` endpoint |
| `docs/features/task-types.md` | User-facing catalog |
