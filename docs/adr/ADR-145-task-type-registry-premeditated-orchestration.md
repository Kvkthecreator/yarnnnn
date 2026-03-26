# ADR-145: Task Type Registry — Pre-Meditated Orchestration

**Status:** Proposed
**Date:** 2026-03-26
**Supersedes:** None
**Extends:** ADR-138 (Agents as Work Units), ADR-140 (Agent Workforce Model), ADR-141 (Unified Execution Architecture), ADR-143 (Agent Methodology Layer)
**Depends on:** ADR-138 (tasks as work units), ADR-140 (pre-scaffolded roster + capability registry), ADR-141 (task pipeline), ADR-143 (agent playbooks)

---

## Context

YARNNN has a working execution pipeline (ADR-141), a pre-scaffolded agent roster (ADR-140), and a clean Agent/Task/Workfloor separation (ADR-138). Users can create tasks via TP, and agents execute them on schedule.

**The problem:** Users encounter two conversion blockers:
1. **Capability ambiguity** — "Sounds powerful, but I can't picture it doing my specific thing." The agent metaphor raises the bar to a real team member; users can't translate agent types into concrete outputs they'll receive.
2. **Trust deficit** — "Even if I could picture it, I don't believe it will actually work." Users need to see the seam — what exactly will be delivered, in what format, on what schedule.

**Root cause:** The product presents agents (WHO) and asks users to imagine deliverables. The correct framing is deliverable-first: present concrete output types (WHAT you'll receive), backed by pre-meditated orchestration plans that determine which agents produce them and how.

**Why multi-agent matters:** Single-agent assignment limits output quality to one agent's capability set. A competitive intelligence brief produced by Research Agent alone has charts but no brand formatting. A meeting prep brief from CRM Agent alone has relationship context but no fresh external research. Pre-meditated multi-agent pipelines produce fuller outcomes — each agent contributes what it's best at, with explicit handoffs rather than improvised TP orchestration at runtime.

---

## Decision

### 1. Task Type Registry

A curated registry of **task types** — each defining a concrete deliverable, its execution pipeline, default schedule, output format, and example output. This is the "menu" users pick from.

Task types are **deliverable-centric** (what you get), not agent-centric (who does it).

```python
TASK_TYPES = {
    "competitive-intel-brief": {
        "display_name": "Competitive Intelligence Brief",
        "description": "Research-backed competitive analysis with charts, diagrams, and evidence-linked findings",
        "category": "intelligence",
        "default_schedule": "weekly",
        "output_format": "html",       # composed HTML with brand
        "export_options": ["pdf"],
        "pipeline": [
            {"agent_type": "research", "step": "investigate", "instruction": "Investigate competitive landscape, gather evidence, identify trends"},
            {"agent_type": "content", "step": "compose", "instruction": "Format findings into branded deliverable with charts and diagrams"},
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "example_output_path": "docs/examples/competitive-intel-brief.md",
    },
    # ... more types
}
```

### 2. Pipeline Execution Model

Each task type carries a `pipeline` — an ordered list of agent steps with explicit handoffs.

**Execution flow:**
1. Scheduler picks due task
2. Read TASK.md → resolve `type_key` → look up pipeline from registry
3. For each pipeline step:
   a. Resolve agent by type from user's roster
   b. Inject prior step's output as context (explicit handoff, not knowledge-base discovery)
   c. Execute agent with step-specific instruction merged into task objective
   d. Store step output in `/tasks/{slug}/outputs/{date}/step-{N}/`
4. Final step's output becomes the deliverable
5. Post-generation: compose HTML, deliver per TASK.md config

**Single-step tasks** are pipelines with one entry — no special case.

**Cost model:** Each pipeline step is one Sonnet call (~$0.03-0.08). A 2-step pipeline costs ~$0.06-0.16 per execution. Pre-meditated orchestration eliminates TP coordination overhead ($0 vs. $0.05/cycle under old PM model).

### 3. The Task Type Catalog

Derived from first principles: what each agent type can produce, what multi-agent collaboration improves, and what users actually want delivered.

#### Intelligence & Research

| Type Key | Display Name | Pipeline | Schedule | Category |
|----------|-------------|----------|----------|----------|
| `competitive-intel-brief` | Competitive Intelligence Brief | Research → Content | weekly | intelligence |
| `market-research-report` | Market Research Report | Research → Content | monthly | intelligence |
| `industry-signal-monitor` | Industry Signal Monitor | Marketing → Research | weekly | intelligence |
| `due-diligence-summary` | Due Diligence Summary | Research → Content | on-demand | intelligence |

#### Business Operations

| Type Key | Display Name | Pipeline | Schedule | Category |
|----------|-------------|----------|----------|----------|
| `meeting-prep-brief` | Meeting Prep Brief | CRM → Research | on-demand | operations |
| `stakeholder-update` | Stakeholder / Board Update | Research → Content | monthly | operations |
| `relationship-health-digest` | Relationship Health Digest | Slack Bot → CRM | weekly | operations |
| `project-status-report` | Project Status Report | Slack Bot → CRM → Content | weekly | operations |

#### Platform Digests

| Type Key | Display Name | Pipeline | Schedule | Category |
|----------|-------------|----------|----------|----------|
| `slack-recap` | Slack Recap | Slack Bot | daily/weekly | platform |
| `notion-sync-report` | Notion Sync Report | Notion Bot | weekly | platform |

#### Content & Communications

| Type Key | Display Name | Pipeline | Schedule | Category |
|----------|-------------|----------|----------|----------|
| `content-brief` | Content Brief / Blog Draft | Research → Content | on-demand | content |
| `launch-material` | Launch / Announcement Material | Marketing → Content | on-demand | content |

#### Data & Tracking

| Type Key | Display Name | Pipeline | Schedule | Category |
|----------|-------------|----------|----------|----------|
| `gtm-tracker` | GTM Tracker | Marketing → Content | weekly | tracking |

### 4. Pre-Meditated vs. Improvised Orchestration

**Pre-meditated (this ADR):** Pipeline is defined at task type level. Scheduler executes steps mechanically. Each agent step has a predetermined role. Deterministic, predictable cost, no TP coordination at runtime.

**Improvised (current):** TP decides at runtime how to orchestrate agents. Works for novel/custom requests. Non-deterministic, variable cost, requires TP intelligence.

**Both coexist.** Task types with registered pipelines use pre-meditated orchestration. Custom tasks (user describes something novel to TP) use improvised orchestration. Over time, successful improvised patterns can be promoted to registered task types.

### 5. Onboarding Integration

Onboarding presents task types as the "menu":
- "What do you want delivered?" → category cards (Intelligence, Operations, Content, etc.)
- Each card shows: name, description, example output preview, default schedule
- User picks one or more → tasks scaffolded with correct pipeline, agent assignments, schedule
- First run executes immediately → user evaluates a concrete deliverable against a clear promise

This kills capability ambiguity: the deliverable IS the explanation.

---

## Pipeline Evolution Model

### Default-Then-Evolve

Task type pipelines start as **deterministic defaults** — the registry defines the canonical execution plan. But pipelines should improve over time through three feedback mechanisms:

#### 1. Agent-Level Learning (Already in Architecture)

Each agent in the pipeline develops independently:
- **Feedback consolidation** (ADR-143): user edits → `feedback.md` → agent adjusts output in future runs
- **Self-assessment** (ADR-128): agents evaluate their own output against task criteria after each run
- **Playbook evolution**: `playbook-outputs.md` and `playbook-research.md` absorb what works

This means the same pipeline produces better output over time, even without changing the pipeline itself.

#### 2. Pipeline-Level Observation (New — Proposed)

After pipeline execution completes, capture pipeline-level signals:
- Which step produced the most value? (measured by user engagement with final output)
- Were handoff instructions sufficient? (measured by whether step N+1 needed to ask for more context)
- Did the pipeline over-produce? (user consistently ignores certain sections → signal to slim down)

These observations accumulate in `/tasks/{slug}/memory/pipeline_observations.md` — read by TP during heartbeat for potential adjustment suggestions.

#### 3. TP-Level Pattern Recognition (Future)

TP's periodic heartbeat (ADR-141 Layer 3) already reads health signals. Extend to pipeline health:
- "This 2-step pipeline consistently produces output the user edits heavily at the composition step → suggest adding a review step or adjusting the compose instruction"
- "This 3-step pipeline's middle step adds negligible value → suggest collapsing to 2 steps"
- Successful custom orchestrations (improvised) that repeat → suggest promoting to registered task type

**Inspiration from existing recursive learning:**
- Agent self-assessment after each run (ADR-128) → pipeline self-assessment after each cycle
- TP Composer's substrate assessment (FOUNDATIONS Axiom 5) → pipeline substrate assessment
- Feedback distillation (ADR-117: edits → preferences.md) → pipeline feedback distillation

### The Deterministic-Adaptive Spectrum

```
Deterministic ←————————————————————→ Adaptive

Registry default     Agent learning      Pipeline observation     TP pattern recognition
(fixed pipeline)     (agents improve)    (signals accumulate)     (pipeline restructuring)

Phase 1              Already built       Phase 2                  Phase 3 (future)
```

Phase 1 ships with deterministic defaults. The architecture supports evolution without requiring it from day one.

---

## Scalability: The Capability Matrix

### Adding New Agent Types

When a new agent type is added to the roster (e.g., `analytics` agent with SQL/data capabilities):

1. Define capabilities in Agent Type Registry (ADR-140)
2. For each existing task type, ask: "Does this pipeline benefit from this agent's capabilities?"
3. Create new task types that the new agent enables (e.g., `data-driven-report`: Analytics → Content)
4. Existing task types gain the option to include the new agent as an additional step

**The matrix:**
```
                    research  content  marketing  crm  slack_bot  notion_bot  [future: analytics]
competitive-intel      ●         ●
market-research        ●         ●
industry-signal                           ●
meeting-prep                                        ●
stakeholder-update     ●         ●
relationship-health                                 ●     ●
slack-recap                                               ●
notion-sync                                                          ●
content-brief          ●         ●
gtm-tracker                      ●        ●
data-dashboard                   ●                                       ●      [new task type]
```

Each row is a task type. Each column is an agent type. Filled cells mean "this agent participates in this pipeline." Adding a column (new agent type) potentially adds new rows (new task types) and fills existing cells (enhanced existing pipelines).

### Adding New Capabilities

When a new capability is added (e.g., `write_email` on CRM agent):

1. Register in Capability Registry (ADR-140)
2. Existing task types that use CRM agent can now optionally deliver via email
3. New task types become possible (e.g., `follow-up-email`: CRM with write_email)
4. Pipeline steps can carry capability requirements: `{"agent_type": "crm", "requires": ["write_email"]}`

### The Multi-Layered Web

Five interconnected layers, each independently evolvable:

```
Layer 1: Deliverables (task types — what users see)
    ↕
Layer 2: Pipelines (execution plans — how work flows)
    ↕
Layer 3: Agents (identity + capabilities — who does the work)
    ↕
Layer 4: Capabilities (skills + runtimes — what's technically possible)
    ↕
Layer 5: Knowledge (workspace + platforms + accumulated memory — what agents know)
```

**Management principles:**
- Layers 1-2 are **product decisions** (curated, deliberate, user-facing)
- Layers 3-4 are **platform decisions** (engineering, capability expansion)
- Layer 5 is **emergent** (accumulates from usage, feedback, platform sync)
- Changes propagate upward: new capability (L4) → new agent ability (L3) → new pipeline option (L2) → new task type (L1)
- Changes also propagate downward: user demand for a deliverable (L1) → pipeline design (L2) → capability gap identified (L4) → engineering work

### Orchestration as Capability

The pipeline orchestration itself is a capability — not of any single agent, but of the platform. This means:

1. **Pipeline templates are versioned artifacts** — same rigor as prompt versioning (CHANGELOG.md)
2. **Pipeline execution is observable** — each step logged, handoff quality measurable
3. **Pipeline patterns are discoverable** — TP can identify successful improvised orchestrations and propose registry additions
4. **Pipeline complexity is bounded** — max 4 steps per pipeline (governs cost and latency)

---

## Stress-Test Scenarios

The following scenarios must be validated at the conceptual level before implementation:

### Scenario 1: Cold Start (No Platform Context)
User picks "Competitive Intelligence Brief" but hasn't connected Slack or Notion.
- **Expected:** Research Agent uses web_search only (no platform context). Content Agent formats. Output is thinner but functional.
- **Question:** Is the output good enough to demonstrate value without platform enrichment?

### Scenario 2: Single-Agent Roster Gap
User picks "Meeting Prep Brief" (CRM → Research pipeline) but has renamed/repurposed their CRM agent.
- **Expected:** TP resolves by agent type, not by name. If user has no CRM-type agent, fallback to single-step Research-only execution.
- **Question:** How does the pipeline degrade gracefully when a step's agent type is unavailable?

### Scenario 3: Pipeline Output Quality Mismatch
Research Agent produces excellent raw findings, but Content Agent's composition is too generic.
- **Expected:** User edits final output → feedback flows to Content Agent's feedback.md → next cycle improves.
- **Question:** Does feedback correctly attribute to the right pipeline step, or does it all go to the last agent?

### Scenario 4: Over-Orchestration
A "Slack Recap" doesn't need Content Agent formatting — Slack Bot's markdown is sufficient.
- **Expected:** Single-step pipeline. No unnecessary composition step.
- **Question:** How do we resist the temptation to make every task type multi-agent when single-agent is sufficient?

### Scenario 5: Custom Task Doesn't Fit Registry
User asks TP "I want a weekly summary of academic papers in my field."
- **Expected:** TP creates custom task with improvised orchestration (Research Agent, weekly). Not a registered type.
- **Question:** How does the system track that this custom pattern is common enough to promote to a registered type?

### Scenario 6: Pipeline Step Produces Nothing Useful
Industry Signal Monitor: Marketing Agent finds no signals this week. Research Agent has nothing to investigate.
- **Expected:** Pipeline short-circuits. Output: "No significant signals this week." Not silence.
- **Question:** How does step N+1 handle "step N produced empty output"?

### Scenario 7: Cost Scaling
User has 5 active task types, all multi-agent. That's potentially 10-15 Sonnet calls per week.
- **Expected:** Within work budget (Free: 60 credits/mo, Pro: 1000/mo). Each pipeline step = 1 credit.
- **Question:** Is the credit model aligned with multi-step pipelines? Does a 3-step pipeline cost 3 credits or 1?

### Scenario 8: Agent Memory Cross-Contamination
Research Agent is assigned to both "Competitive Intel" and "Market Research" tasks. Its memory accumulates from both.
- **Expected:** Agent memory is agent-scoped, not task-scoped. This is a feature — Research Agent gets better at research across all its tasks.
- **Question:** Could mixed signals from different task types confuse the agent's self-assessment?

---

## Impact Radius

### Documentation Updates Required

**Architecture docs:**
- `docs/architecture/FOUNDATIONS.md` — update Axiom 6 (Autonomy direction) to reference task type registry as the onboarding path
- `docs/architecture/output-substrate.md` — add pipeline execution section (multi-step output storage)
- `docs/architecture/workspace-conventions.md` — add `/tasks/{slug}/outputs/{date}/step-{N}/` convention
- `docs/architecture/agent-execution-model.md` — update with pipeline execution flow
- `docs/architecture/backend-orchestration.md` — update with pre-meditated vs. improvised distinction

**Feature docs:**
- `docs/features/agent-types.md` — reference task types as the user-facing mapping
- `docs/features/agent-modes.md` — clarify that task mode (recurring/goal/reactive) is orthogonal to task type
- NEW: `docs/features/task-types.md` — canonical user-facing documentation of all task types with examples

**ADR updates:**
- ADR-138: Note that TASK.md gains `type_key` field linking to registry
- ADR-140: Note that agent types are the capability layer consumed by task type pipelines
- ADR-141: Note that `execute_task()` gains pipeline-aware execution path

**Changelogs:**
- `api/prompts/CHANGELOG.md` — when TP prompt is updated with task type awareness
- `api/services/agent_framework.py` changelog comments — when TASK_TYPES registry is added

### Code Changes (Estimated)

**Backend (api/):**
- `api/services/task_types.py` — NEW: task type registry + `scaffold_task_from_type()` + `resolve_pipeline()`
- `api/services/task_pipeline.py` — extend `execute_task()` with pipeline-aware multi-step execution
- `api/services/task_workspace.py` — add step-scoped output storage (`step-{N}/` subdirectories)
- `api/routes/tasks.py` — add `GET /api/tasks/types` endpoint for frontend catalog
- `api/agents/thinking_partner.py` — update TP prompt with task type awareness for scaffolding
- `api/services/primitives/task.py` — `CreateTask` gains optional `type_key` parameter

**Frontend (web/):**
- `web/app/(authenticated)/workfloor/page.tsx` — task creation flow uses type catalog
- NEW or updated onboarding page — "What do you want delivered?" type selection
- `web/types/index.ts` — `TaskType` interface + `TaskTypeCategory` type

**Prompt changes (requires CHANGELOG.md update):**
- TP system prompt: awareness of task type registry for scaffolding
- Task execution prompt: step-specific instructions from pipeline definition

---

## Phases

### Phase 1: Registry + Single-Step Execution (MVP)
- Task type registry (`api/services/task_types.py`)
- `GET /api/tasks/types` endpoint
- `CreateTask` with `type_key` → scaffold TASK.md from registry template
- Onboarding type selection UI
- All task types execute as single-agent initially (last pipeline step only)

### Phase 2: Multi-Step Pipeline Execution
- Extend `execute_task()` for pipeline-aware execution
- Step-scoped output storage (`step-{N}/`)
- Explicit handoff: step N output injected into step N+1 context
- Pipeline cost tracking (credits per step)

### Phase 3: Pipeline Observation + Feedback Attribution
- Pipeline observation signals → `/tasks/{slug}/memory/pipeline_observations.md`
- Feedback attribution to correct pipeline step
- TP heartbeat reads pipeline health signals

### Phase 4: Pattern Promotion + Adaptive Pipelines (Future)
- TP identifies successful improvised patterns → suggests promotion to registered type
- Pipeline-level adjustments based on accumulated observations
- User-customizable pipeline overrides (advanced)

---

## Decision Record

**Why pre-meditated over improvised:** Predictable cost, deterministic quality, explainable to users ("here's exactly what will happen"), and the orchestration logic is a product decision, not a runtime AI decision.

**Why task-type-first over agent-first:** Users think in deliverables ("I want a competitive brief"), not in agent capabilities ("I want a research agent with web_search capability to run weekly"). The task type IS the product promise.

**Why multi-agent pipelines as default:** Each agent type has a specific capability set. No single agent can produce the best possible version of most deliverables. Pre-meditated collaboration produces fuller outputs without runtime coordination overhead.

**Why deterministic-then-adaptive:** Ship with working defaults. The architecture supports evolution through existing learning mechanisms (agent feedback, self-assessment, TP heartbeat). Don't require adaptivity for v1 — but don't prevent it.
