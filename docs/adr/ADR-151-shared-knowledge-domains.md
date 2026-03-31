# ADR-151: Shared Context Domains — Workspace as Accumulated Intelligence

**Status:** Proposed  
**Date:** 2026-03-31  
**Supersedes:** ADR-150 (task-gated context — wrong; accumulated context must be shared)  
**Extends:** ADR-149 (task lifecycle), ADR-138 (agents as work units), ADR-140 (agent workforce), ADR-141 (unified execution)  
**Implements:** FOUNDATIONS.md Axiom 2 (recursive perception), Axiom 3 (knowledge depth), Axiom 4 (accumulated attention)

---

## Context

ADR-150 proposed task-gated knowledge — each task owns a `/tasks/{slug}/knowledge/` folder. Axiomatic reassessment reveals this is wrong:

- **FOUNDATIONS.md**: "The workspace filesystem acts as an **operating system for agent and human work** — a shared substrate where both contribute and both consume."
- **FOUNDATIONS.md**: "Task outputs ARE the accumulated knowledge — each run's output feeds the next run's context. **No separate knowledge layer.**"
- **Axiom 2**: The recursive loop flows through the SHARED workspace, not isolated task silos.
- **Axiom 4**: "Value comes from accumulated attention." Task isolation prevents the compounding — a stakeholder update can't see competitor intelligence, a meeting prep can't see relationship history.

**The correct model:** Accumulated context lives at workspace scope. Tasks are work orders that read from and write to shared context domains. The workspace IS the accumulated intelligence. Tasks produce derivative outputs from it.

### Why "context" not "knowledge"

The folder and concept is named `context/` because:
- It aligns with existing terminology: `UpdateContext` primitive, "context inference," "context readiness," "context pipeline"
- It's what it actually is — accumulated structured context that agents use to produce better outputs
- Avoids confusion between `/workspace/documents/` (user-uploaded reference) and agent-accumulated structured context
- The axioms say "accumulated attention" and "accumulated context" (ESSENCE.md), not "accumulated knowledge"

## Decision

### Three Registries

YARNNN has three registries, each governing a different architectural layer:

| Registry | Governs | Scope | Changes |
|---|---|---|---|
| **Context Domain Registry** | Context structure — WHAT the system knows | Workspace | Grows as user's work expands |
| **Agent Registry** | Worker capabilities — WHO does the work | Fixed at creation | Identity evolves, capabilities don't |
| **Task Type Registry** | Work patterns — HOW work gets done | Fixed templates | Tasks read/write to domains |

**The context domain registry is the most upstream.** It determines the workspace's accumulated context structure, which in turn determines what agents can accumulate, which determines what tasks can produce. Changes here cascade everywhere.

### Context Domain Registry

```python
# api/services/domain_registry.py

CONTEXT_DOMAINS: dict[str, dict] = {

    "competitors": {
        "display_name": "Competitors",
        "description": "Companies and products we compete with",
        "entity_type": "company",
        "folder": "competitors",
        "entity_structure": {
            "profile.md": "# {name}\n\n## Overview\n\n## Funding & Size\n\n## Leadership\n",
            "signals.md": "# Signals — {name}\n<!-- Dated findings, newest first -->\n",
            "product.md": "# Product — {name}\n\n## Offering\n\n## Pricing\n\n## Recent Changes\n",
            "strategy.md": "# Strategy — {name}\n\n## Positioning\n\n## Threat Assessment\n\n## Opportunities\n",
        },
        "entity_assets": ["logo.png"],
        "synthesis_file": "_landscape.md",
        "synthesis_template": (
            "# Competitive Landscape\n\n"
            "## Market Map\n\n"
            "## Key Trends\n\n"
            "## Our Position\n"
        ),
        "shared_assets": ["competitor-matrix.svg"],
    },

    "market": {
        "display_name": "Market",
        "description": "Market segments, sizing, trends, and opportunities",
        "entity_type": "segment",
        "folder": "market",
        "entity_structure": {
            "analysis.md": "# {name}\n\n## Market Size & Growth\n\n## Key Players\n\n## Trends\n\n## Opportunities\n",
        },
        "entity_assets": [],
        "synthesis_file": "_overview.md",
        "synthesis_template": (
            "# Market Overview\n\n"
            "## Landscape Summary\n\n"
            "## Cross-Segment Patterns\n\n"
            "## Strategic Implications\n"
        ),
        "shared_assets": ["market-map.svg"],
    },

    "relationships": {
        "display_name": "Relationships",
        "description": "People and organizations we work with",
        "entity_type": "contact",
        "folder": "relationships",
        "entity_structure": {
            "profile.md": "# {name}\n\n## Role & Company\n\n## How We Know Them\n\n## Notes\n",
            "history.md": "# Interaction History — {name}\n<!-- Dated, newest first -->\n",
            "open-items.md": "# Open Items — {name}\n\n## Follow-ups Due\n\n## Commitments Made\n",
        },
        "entity_assets": [],
        "synthesis_file": "_portfolio.md",
        "synthesis_template": (
            "# Relationship Portfolio\n\n"
            "## Health Overview\n\n"
            "## At-Risk\n\n"
            "## Follow-Up Priorities\n"
        ),
        "shared_assets": [],
    },

    "projects": {
        "display_name": "Projects",
        "description": "Internal initiatives, workstreams, and milestones",
        "entity_type": "project",
        "folder": "projects",
        "entity_structure": {
            "status.md": "# {name}\n\n## Current State\n\n## Progress\n\n## Blockers\n\n## Next Steps\n",
            "milestones.md": "# Milestones — {name}\n\n## Achieved\n\n## Upcoming\n",
        },
        "entity_assets": ["roadmap.svg"],
        "synthesis_file": "_status.md",
        "synthesis_template": (
            "# Project Portfolio Status\n\n"
            "## Overall Health\n\n"
            "## Active Blockers\n\n"
            "## Resource Needs\n"
        ),
        "shared_assets": ["project-roadmap.svg"],
    },

    "content": {
        "display_name": "Content",
        "description": "Research, drafts, and creative work in progress",
        "entity_type": "topic",
        "folder": "content",
        "entity_structure": {
            "research.md": "# Research — {name}\n\n## Key Points\n\n## Sources\n\n## Audience Considerations\n",
            "outline.md": "# Outline — {name}\n\n## Key Messages\n\n## Structure\n\n## Tone\n",
        },
        "entity_assets": [],
        "synthesis_file": None,
        "synthesis_template": None,
        "shared_assets": [],
    },

    "signals": {
        "display_name": "Signals",
        "description": "Temporal signal log — what happened when, across all domains",
        "entity_type": None,  # Not entity-based — date-based
        "folder": "signals",
        "entity_structure": None,
        "synthesis_file": None,
        "signal_log": True,  # Date-stamped files: {YYYY-MM-DD}.md
        "shared_assets": [],
    },
}
```

### Domain Registry Design Principles

**1. Domains are context categories, not task types.** "Competitors" is a domain. "Competitive intelligence brief" is a task type that reads/writes the competitors domain.

**2. Domains have entity structure.** Most domains organize around entities (companies, contacts, projects). Each entity gets a subfolder with structured files. The registry declares the template — agents create entity folders as they discover entities.

**3. Domains have synthesis files.** A `_landscape.md` or `_overview.md` file synthesizes across all entities in the domain. Agents update this when cross-entity patterns emerge. The `_` prefix convention distinguishes synthesis files from entity folders.

**4. Assets are domain-scoped.** A competitor's logo lives in `competitors/acme-corp/assets/logo.png`. A cross-domain matrix lives in `/workspace/context/assets/competitor-matrix.svg`. Assets co-locate with the context they represent.

**5. Domains grow dynamically.** The registry defines the initial set. TP can create new domains when the user's work outgrows the defaults. The registry is a starting point, not a constraint.

**6. The signal log is cross-domain.** `/workspace/context/signals/` captures temporal events from any domain. Date-stamped files. Any agent can append. This provides the "what happened when" timeline that diff-aware outputs need.

### Workspace Filesystem (Canonical — Supersedes ADR-150)

```
/workspace/                                  # THE SHARED WORKSPACE OS
├── IDENTITY.md                              # User identity (ADR-144)
├── BRAND.md                                 # Output style (ADR-144)
├── documents/                               # User-uploaded references (permanent)
│   ├── ir-deck-march-2026.md
│   └── product-roadmap.md
├── context/                                 # ACCUMULATED CONTEXT (domain registry)
│   ├── competitors/
│   │   ├── _landscape.md                    # Cross-entity synthesis
│   │   ├── acme-corp/
│   │   │   ├── profile.md
│   │   │   ├── signals.md
│   │   │   ├── product.md
│   │   │   ├── strategy.md
│   │   │   └── assets/
│   │   │       └── logo.png
│   │   └── globex-inc/
│   │       └── ...
│   ├── market/
│   │   ├── _overview.md
│   │   └── ai-agents/
│   │       └── analysis.md
│   ├── relationships/
│   │   ├── _portfolio.md
│   │   └── john-smith/
│   │       ├── profile.md
│   │       ├── history.md
│   │       └── open-items.md
│   ├── projects/
│   │   ├── _status.md
│   │   └── product-launch/
│   │       ├── status.md
│   │       └── milestones.md
│   ├── content/
│   │   └── blog-ai-agents/
│   │       ├── research.md
│   │       └── outline.md
│   ├── signals/
│   │   ├── 2026-03-31.md
│   │   └── 2026-03-24.md
│   └── assets/                              # Cross-domain shared assets
│       ├── competitor-matrix.svg
│       ├── market-map.svg
│       └── manifest.json
├── notes.md                                 # TP observations
└── preferences.md                           # Learned preferences

/agents/{slug}/                              # AGENT = capability + evolving identity
├── AGENT.md                                 # Identity (specializes over time)
├── memory/
│   ├── reflections.md                       # Agent self-reflection (ADR-149)
│   ├── feedback.md                          # Cross-task behavioral feedback
│   └── playbook-*.md                        # Methodology

/tasks/{slug}/                               # TASK = work order + derived output
├── TASK.md                                  # Charter: objective, process, mode, context domains
├── DELIVERABLE.md                           # Output spec: expected output + asset refs + quality criteria
├── memory/
│   ├── run_log.md                           # Execution history (append-only)
│   ├── feedback.md                          # Task-level feedback: user + TP evaluations (ADR-149)
│   └── steering.md                          # TP management notes for next cycle (ADR-149)
├── outputs/                                 # DERIVED deliverables (mode-dependent, ADR-149)
│   ├── latest/
│   │   ├── output.md                        # Primary derived content
│   │   ├── output.html                      # Composed HTML
│   │   ├── manifest.json                    # Run metadata + asset references
│   │   └── assets/                          # Per-output generated assets (charts, tables)
│   │       └── *.svg
│   └── {date}/                              # Run archive
└── working/                                 # Ephemeral scratch (24h TTL)
```

### Task Filesystem — Pure Work Order

With accumulated context at workspace scope, the task becomes a **pure work order + output container**:

- **TASK.md** declares WHAT to do: objective, which context domains to read/write, process steps, mode, schedule.
- **DELIVERABLE.md** declares WHAT the output looks like: format, layout, expected assets (referencing workspace context assets + per-output assets), quality criteria.
- **memory/** is operational state for THIS task's execution lifecycle.
- **outputs/** is where derived deliverables live. These are VIEWS over workspace context, not primary artifacts.

**What tasks DON'T have:**
- No `context/` or `knowledge/` folder (accumulated context is at workspace scope)
- No persistent task-level assets (persistent assets are domain-scoped in workspace)

**The task is thin by design.** All the accumulated value lives in workspace context, which survives task deletion, agent reassignment, and mode changes. Delete a competitive-intel task → the competitor context persists. Create a new task against the same domain → it picks up where the old one left off.

**Context outlives tasks. Tasks come and go. Context compounds.**

### Task Type Registry — context_reads + context_writes

Task types declare which domains they interact with:

```python
# In task_types.py — replaces knowledge_schema

"competitive-intel-brief": {
    "context_reads": ["competitors"],
    "context_writes": ["competitors", "signals"],
    "process": [
        {
            "agent_type": "research",
            "step": "update-context",
            "instruction": "Read /workspace/context/competitors/. Research new signals. "
                          "Update entity files with new findings. Create new entity folders "
                          "for newly discovered competitors. Update _landscape.md. "
                          "Append to /workspace/context/signals/{date}.md. "
                          "Output: changelog of what changed.",
        },
        {
            "agent_type": "content",
            "step": "derive-output",
            "instruction": "Read all files in /workspace/context/competitors/. "
                          "Produce the deliverable per DELIVERABLE.md. Emphasize what "
                          "CHANGED since last cycle. Reference shared assets.",
        },
    ],
},

"stakeholder-update": {
    "context_reads": ["competitors", "market", "projects", "relationships"],
    "context_writes": ["projects", "signals"],
    "process": [
        {
            "agent_type": "research",
            "step": "update-context",
            "instruction": "Read /workspace/context/projects/. Update project status "
                          "files from platform context. Cross-reference with competitors/ "
                          "and market/ for strategic framing. Output: changelog.",
        },
        {
            "agent_type": "content",
            "step": "derive-output",
            "instruction": "Read projects/, competitors/, market/, relationships/ context. "
                          "Produce board-ready stakeholder update per DELIVERABLE.md.",
        },
    ],
},

"meeting-prep-brief": {
    "context_reads": ["relationships", "competitors"],
    "context_writes": ["relationships", "signals"],
    "process": [
        {
            "agent_type": "crm",
            "step": "update-context",
            "instruction": "Read /workspace/context/relationships/{contact}/. "
                          "Update interaction history from platform context. "
                          "Check competitors/ if contact works at a tracked company. "
                          "Output: updated relationship context.",
        },
        {
            "agent_type": "research",
            "step": "derive-output",
            "instruction": "Read relationship context + competitor context if relevant. "
                          "Produce meeting brief per DELIVERABLE.md.",
        },
    ],
},
```

### Agent Registry — Unchanged, Identity Evolves

Agent types stay as capability bundles (ADR-140). The agent registry does NOT map to domains. Instead:

- **Agents carry skill** (research, composition, platform I/O)
- **Tasks assign agents to domains** via `context_reads`/`context_writes`
- **Agent identity specializes over time** through accumulated task experience

TP may suggest renaming the agent based on domain specialization — but this is identity evolution, not type change.

### Domain Scaffolding

**At workspace creation** (signup): No context domains scaffolded. Empty `/workspace/context/` folder. Domains get created when tasks need them.

**At task creation**: TP checks `context_writes` for the task type. If the domain folder doesn't exist, scaffold it from the registry template.

**Entity creation**: Agents create entity folders during the `update-context` step when they discover new entities. The domain registry provides the template.

### Metadata for Recursive Context

Each context file carries metadata via the `workspace_files` table (existing columns):

| Field | Purpose | Example |
|---|---|---|
| `updated_at` | Last modified timestamp | `2026-03-31T09:00:00Z` |
| `tags` | Domain + entity identifiers | `["competitors", "acme-corp", "signals"]` |
| `metadata` JSONB | Structured operational data | `{"domain": "competitors", "entity": "acme-corp", "updated_by_task": "weekly-competitive-brief", "signal_freshness": "2026-03-31"}` |

No schema change needed — `workspace_files` already has these columns.

### The Execution Loop

```
Scheduler triggers task
  → Read TASK.md + DELIVERABLE.md + steering.md + feedback.md
  → Read task mode from DB
  → Resolve context domains from task type (context_reads, context_writes)
  
  Step 1: UPDATE CONTEXT (research/CRM agent)
    → Read existing context files from context_reads domains
    → Research new signals (web, platforms)  
    → Write updates to context_writes domains (update entity files, append signals)
    → Output: changelog (what changed this cycle)
  
  Step 2: DERIVE OUTPUT (content agent)
    → Read ALL context from context_reads domains (now updated)
    → Read changelog from step 1
    → Produce deliverable per DELIVERABLE.md
    → Emphasis on diffs — what's new since last cycle
    → Reference shared assets from context domains
  
  → Render inline assets → Compose HTML
  → Mode-aware output save (ADR-149 Phase 2)
  → Deliver
```

### DELIVERABLE.md — Asset References

Since assets are domain-scoped, DELIVERABLE.md references them by path:

```markdown
## Expected Assets

### Persistent (domain-scoped, updated with context)
- /workspace/context/assets/competitor-matrix.svg — Competitive positioning chart
- /workspace/context/assets/market-map.svg — Market landscape diagram

### Per-Entity (co-located with context)
- /workspace/context/competitors/{entity}/assets/logo.png — Company logos
- /workspace/context/projects/{entity}/assets/roadmap.svg — Project timelines

### Per-Output (generated fresh each cycle)
- Trend charts from this cycle's quantified data
- Data tables backing analysis

### Referenced (user-uploaded)
- /workspace/documents/ — User reference material
```

---

## Phases

### Phase 1: Domain Registry + Context Scaffold
- Create `api/services/domain_registry.py` with CONTEXT_DOMAINS
- Update task type registry: replace `knowledge_schema` with `context_reads`/`context_writes`
- Update `handle_create_task()` to scaffold domain folders when tasks need them
- Update workspace-conventions.md with `/workspace/context/` hierarchy
- Update all impacted docs (SERVICE-MODEL, FOUNDATIONS, CLAUDE.md, features/)
- Archive ADR-150 as superseded

### Phase 2: Pipeline Reads Shared Context
- `gather_task_context()` reads from `/workspace/context/{domain}/` based on task's `context_reads`
- Context files injected into agent prompt as primary context
- Metadata (updated_at, tags) used for recency-aware context selection

### Phase 3: Agent Write-Back to Shared Context
- Extend headless tool set: agent can write to `/workspace/context/{domain}/` during execution
- Scoped by task's `context_writes` — agent can only write to declared domains
- Entity creation from templates using domain registry

### Phase 4: Diff-Aware Output + Asset Management
- Output derivation step reads changelog from context-update step
- DELIVERABLE.md "Derivative Mode" for recurring tasks
- Persistent asset updates in domain-scoped asset folders

### Phase 5: TP Domain Awareness
- TP working memory includes domain health: which domains exist, entity counts, freshness
- TP can scaffold new domains dynamically
- ManageTask `evaluate` checks context health alongside output quality

---

## Consequences

### Positive
- Context compounds across tasks — the canonical product promise
- Cross-task intelligence sharing without explicit orchestration
- Natural workspace growth: more tasks → richer context → better outputs
- Clean separation: domains (what we know), agents (who works), tasks (what gets produced)
- Filesystem IS the product — the user's accumulated context is visible and browsable
- Terminology alignment: "context" consistent with UpdateContext, context_inference, context_readiness

### Negative
- Write conflicts: two tasks writing to same domain simultaneously. Mitigation: append-heavy patterns; workspace_files has row-level conflict resolution.
- Context sprawl: domains accumulate files without bound. Mitigation: TP heartbeat flags stale entities; signal log rolls over.
- Three registries to maintain. Mitigation: domain registry is small and stable; changes are rare.

### Risks
- Agent writes corrupt shared context. Mitigation: write-scoping via `context_writes`; filesystem versioning provides rollback.
- Domain structure too rigid. Mitigation: templates are starting points; agents can create files outside the template.
- Users confused by context/ vs. documents/. Mitigation: context is agent-managed (grows automatically); documents are user-uploaded. Clear UX distinction.

---

## Key Files

| Concern | Location |
|---|---|
| Context domain registry (NEW) | `api/services/domain_registry.py` |
| Task type registry (updated: context_reads/writes) | `api/services/task_types.py` |
| Agent type registry (unchanged) | `api/services/agent_framework.py` |
| Context scaffold at task creation | `api/services/primitives/task.py` |
| Context gathering in pipeline | `api/services/task_pipeline.py` |
| Workspace conventions (updated) | `docs/architecture/workspace-conventions.md` |

## Relationship to Existing ADRs

- **ADR-150**: Superseded. Task-gated context was wrong. Context is workspace-scoped and shared.
- **ADR-149** (Task Lifecycle): Preserved. DELIVERABLE.md, mode semantics, feedback/evaluation/reflection all remain. Task filesystem loses `knowledge/`. Gains `context_reads`/`context_writes` references.
- **ADR-138** (Agents as Work Units): Preserved. Agents gain write access to workspace context scoped by task assignment.
- **ADR-140** (Agent Workforce): Preserved. Agent types are capability bundles. Identity specializes through accumulated domain experience.
- **ADR-141** (Unified Execution): Extended. Pipeline gains context-read and context-write phases.
- **ADR-142** (Unified Filesystem): Extended. `/workspace/context/` becomes a major workspace section.
- **ADR-144** (Inference-First Shared Context): Extended. Context domains are another inference surface — aligns with existing `UpdateContext` primitive naming.
- **ADR-145** (Task Type Registry): Extended. Task types gain `context_reads`/`context_writes`.
- **FOUNDATIONS.md**: Directly fulfills Axiom 2 (recursive perception through shared workspace), Axiom 3 (agents develop through knowledge depth in shared domains), Axiom 4 (accumulated attention compounds across all tasks).
