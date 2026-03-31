# ADR-151: Shared Knowledge Domains — Workspace as Accumulated Intelligence

**Status:** Proposed  
**Date:** 2026-03-31  
**Supersedes:** ADR-150 (task-gated knowledge — wrong; knowledge must be shared)  
**Extends:** ADR-149 (task lifecycle), ADR-138 (agents as work units), ADR-140 (agent workforce), ADR-141 (unified execution)  
**Implements:** FOUNDATIONS.md Axiom 2 (recursive perception), Axiom 3 (knowledge depth), Axiom 4 (accumulated attention)

---

## Context

ADR-150 proposed task-gated knowledge — each task owns a `/tasks/{slug}/knowledge/` folder. Axiomatic reassessment reveals this is wrong:

- **FOUNDATIONS.md**: "The workspace filesystem acts as an **operating system for agent and human work** — a shared substrate where both contribute and both consume."
- **FOUNDATIONS.md**: "Task outputs ARE the accumulated knowledge — each run's output feeds the next run's context. **No separate knowledge layer.**"
- **Axiom 2**: The recursive loop flows through the SHARED workspace, not isolated task silos.
- **Axiom 4**: "Value comes from accumulated attention." Task isolation prevents the compounding — a stakeholder update can't see competitor intelligence, a meeting prep can't see relationship history.

The solo founder scenario proves it: competitive intel discovers Acme raised $50M. The stakeholder update needs this for the board deck. Meeting prep with Acme's CEO needs it. If knowledge is task-gated, each task is blind to the others' findings.

**The correct model:** Knowledge lives at workspace scope. Tasks are work orders that read from and write to shared knowledge domains. The workspace IS the accumulated intelligence. Tasks produce derivative outputs from it.

## Decision

### Three Registries

YARNNN has three registries, each governing a different architectural layer:

| Registry | Governs | Scope | Changes |
|---|---|---|---|
| **Domain Registry** | Knowledge structure — WHAT the system knows | Workspace | Grows as user's work expands |
| **Agent Registry** | Worker capabilities — WHO does the work | Fixed at creation | Identity evolves, capabilities don't |
| **Task Type Registry** | Work patterns — HOW work gets done | Fixed templates | Tasks read/write to domains |

**The domain registry is the most upstream.** It determines the workspace's knowledge structure, which in turn determines what agents can accumulate, which determines what tasks can produce. Changes here cascade everywhere.

### Domain Registry

```python
# api/services/domain_registry.py

KNOWLEDGE_DOMAINS: dict[str, dict] = {

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

**1. Domains are knowledge categories, not task types.** "Competitors" is a domain. "Competitive intelligence brief" is a task type that reads/writes the competitors domain.

**2. Domains have entity structure.** Most domains organize around entities (companies, contacts, projects). Each entity gets a subfolder with structured files. The registry declares the template — agents create entity folders as they discover entities.

**3. Domains have synthesis files.** A `_landscape.md` or `_overview.md` file synthesizes across all entities in the domain. Agents update this when cross-entity patterns emerge. The `_` prefix convention distinguishes synthesis files from entity folders.

**4. Assets are domain-scoped.** A competitor's logo lives in `competitors/acme-corp/assets/logo.png`. A cross-competitor matrix lives in `/workspace/knowledge/assets/competitor-matrix.svg`. Assets co-locate with the knowledge they represent.

**5. Domains grow dynamically.** The registry defines the initial set. TP can create new domains when the user's work outgrows the defaults. The registry is a starting point, not a constraint.

**6. The signal log is cross-domain.** `/workspace/knowledge/signals/` captures temporal events from any domain. Date-stamped files. Any agent can append. This provides the "what happened when" timeline that diff-aware outputs need.

### Workspace Filesystem (Canonical — Supersedes ADR-150)

```
/workspace/                                  # THE SHARED KNOWLEDGE OS
├── IDENTITY.md                              # User identity (ADR-144)
├── BRAND.md                                 # Output style (ADR-144)
├── documents/                               # User-uploaded references (permanent)
│   ├── ir-deck-march-2026.md
│   └── product-roadmap.md
├── knowledge/                               # ACCUMULATED INTELLIGENCE (domain registry)
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
├── TASK.md                                  # Charter: objective, process, mode, knowledge domains
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

### Task Filesystem — What It Is Now

With knowledge moved to workspace scope, the task becomes a **pure work order + output container**:

- **TASK.md** declares WHAT to do: objective, which knowledge domains to read/write, process steps, mode, schedule.
- **DELIVERABLE.md** declares WHAT the output looks like: format, layout, expected assets (referencing workspace knowledge assets + per-output assets), quality criteria.
- **memory/** is operational state for THIS task's execution lifecycle — run history, user feedback on THIS task's outputs, TP steering for THIS task's next cycle.
- **outputs/** is where derived deliverables live. These are VIEWS over workspace knowledge, not primary artifacts. Mode-dependent (ADR-149): recurring accumulates, goal revises, reactive one-shots.
- **outputs/latest/assets/** are per-output generated assets — fresh charts from this cycle's data, tables backing this report. NOT the persistent knowledge-scoped assets (those live in `/workspace/knowledge/{domain}/assets/`).

**What tasks DON'T have anymore:**
- No `knowledge/` folder (moved to `/workspace/knowledge/`)
- No persistent task-level assets (persistent assets are domain-scoped in workspace)
- No accumulated intelligence (that's workspace knowledge, not task state)

**The task is thin by design.** It's a work order with output history. All the accumulated value lives in workspace knowledge, which survives task deletion, agent reassignment, and mode changes. Delete a competitive-intel task → the competitor knowledge persists. Create a new task against the same domain → it picks up where the old one left off.

This is the correct architecture: **knowledge outlives tasks. Tasks come and go. Knowledge compounds.**

### Task Type Registry — knowledge_reads + knowledge_writes

Task types declare which domains they interact with:

```python
# In task_types.py — replaces knowledge_schema

"competitive-intel-brief": {
    "knowledge_reads": ["competitors"],
    "knowledge_writes": ["competitors", "signals"],
    "process": [
        {
            "agent_type": "research",
            "step": "update-knowledge",
            "instruction": "Read /workspace/knowledge/competitors/. Research new signals. "
                          "Update entity files with new findings. Create new entity folders "
                          "for newly discovered competitors. Update _landscape.md. "
                          "Append to /workspace/knowledge/signals/{date}.md. "
                          "Output: changelog of what changed.",
        },
        {
            "agent_type": "content",
            "step": "derive-output",
            "instruction": "Read all files in /workspace/knowledge/competitors/. "
                          "Produce the deliverable per DELIVERABLE.md. Emphasize what "
                          "CHANGED since last cycle. Reference shared assets.",
        },
    ],
    # ... existing fields
},

"stakeholder-update": {
    "knowledge_reads": ["competitors", "market", "projects", "relationships"],
    "knowledge_writes": ["projects", "signals"],
    "process": [
        {
            "agent_type": "research",
            "step": "update-knowledge",
            "instruction": "Read /workspace/knowledge/projects/. Update project status "
                          "files from platform context. Cross-reference with competitors/ "
                          "and market/ for strategic framing. Output: changelog.",
        },
        {
            "agent_type": "content",
            "step": "derive-output",
            "instruction": "Read projects/, competitors/, market/, relationships/ knowledge. "
                          "Produce board-ready stakeholder update per DELIVERABLE.md.",
        },
    ],
},

"meeting-prep-brief": {
    "knowledge_reads": ["relationships", "competitors"],
    "knowledge_writes": ["relationships", "signals"],
    "process": [
        {
            "agent_type": "crm",
            "step": "update-knowledge",
            "instruction": "Read /workspace/knowledge/relationships/{contact}/. "
                          "Update interaction history from platform context. "
                          "Check competitors/ if contact works at a tracked company. "
                          "Output: updated relationship context.",
        },
        {
            "agent_type": "research",
            "step": "derive-output",
            "instruction": "Read relationship knowledge + competitor context if relevant. "
                          "Produce meeting brief per DELIVERABLE.md.",
        },
    ],
},
```

### Agent Registry — Unchanged, Identity Evolves

Agent types stay as capability bundles (ADR-140). The agent registry does NOT map to domains. Instead:

- **Agents carry skill** (research, composition, platform I/O)
- **Tasks assign agents to domains** via `knowledge_reads`/`knowledge_writes`
- **Agent identity specializes over time** through accumulated task experience

A Research Agent that handles competitive-intel tasks for 3 months develops a competitive intelligence identity — its AGENT.md evolves, its reflections reference competitive analysis quality, its feedback is about competitor report preferences. But its CAPABILITY (web_search, investigate, chart) doesn't change.

TP may suggest renaming the agent ("Your Research Agent has been focused on competitive intelligence — want me to rename it to 'Competitive Intelligence Analyst'?") — but this is identity evolution, not type change.

### Domain Scaffolding

**At workspace creation** (signup): No knowledge domains scaffolded. Empty `/workspace/knowledge/` folder. Domains get created when tasks need them.

**At task creation**: TP checks `knowledge_writes` for the task type. If the domain folder doesn't exist, scaffold it:

```python
# In handle_create_task():
if type_key:
    task_type = get_task_type(type_key)
    for domain_key in task_type.get("knowledge_writes", []):
        domain = KNOWLEDGE_DOMAINS.get(domain_key)
        if domain:
            folder = f"knowledge/{domain['folder']}"
            # Check if domain folder exists
            existing = await um.read(f"{folder}/_exists")  # or list folder
            if not existing:
                # Scaffold domain
                if domain.get("synthesis_file"):
                    await um.write(
                        f"{folder}/{domain['synthesis_file']}",
                        domain["synthesis_template"],
                    )
                # Entity folders created by agents during execution
```

**Entity creation**: Agents create entity folders during the `update-knowledge` step when they discover new entities (new competitor, new contact). The domain registry provides the template. The agent uses `WriteWorkspace` to create the files.

### Metadata for Recursive Context

Each knowledge file carries metadata via the `workspace_files` table (existing columns):

| Field | Purpose | Example |
|---|---|---|
| `updated_at` | Last modified timestamp | `2026-03-31T09:00:00Z` |
| `tags` | Domain + entity identifiers | `["competitors", "acme-corp", "signals"]` |
| `metadata` JSONB | Structured operational data | `{"domain": "competitors", "entity": "acme-corp", "updated_by_task": "weekly-competitive-brief", "signal_freshness": "2026-03-31"}` |

This enables:
- **Diff-aware execution**: "Read competitors/acme-corp/signals.md — last updated March 24. Research what's new since then."
- **Stale detection**: TP heartbeat checks `updated_at` across knowledge files. Flags domains with stale entities.
- **Context relevance**: When gathering context for a task, filter knowledge files by domain + recency + tags.

No schema change needed — `workspace_files` already has these columns.

### The Execution Loop (Revised)

```
Scheduler triggers task
  → Read TASK.md + DELIVERABLE.md + steering.md + feedback.md
  → Read task mode from DB
  → Resolve knowledge domains from task type (knowledge_reads, knowledge_writes)
  
  Step 1: UPDATE KNOWLEDGE (research/CRM agent)
    → Read existing knowledge files from knowledge_reads domains
    → Research new signals (web, platforms)  
    → Write updates to knowledge_writes domains (update entity files, append signals)
    → Output: changelog (what changed this cycle)
  
  Step 2: DERIVE OUTPUT (content agent)
    → Read ALL knowledge from knowledge_reads domains (now updated)
    → Read changelog from step 1
    → Produce deliverable per DELIVERABLE.md
    → Emphasis on diffs — what's new since last cycle
    → Reference shared assets from knowledge domains
  
  → Render inline assets → Compose HTML
  → Mode-aware output save (ADR-149 Phase 2)
  → Deliver
```

### DELIVERABLE.md — Asset References (Revised)

Since assets are domain-scoped, DELIVERABLE.md references them by path:

```markdown
## Expected Assets

### Persistent (domain-scoped, updated with knowledge)
- /workspace/knowledge/assets/competitor-matrix.svg — Competitive positioning chart
- /workspace/knowledge/assets/market-map.svg — Market landscape diagram

### Per-Entity (co-located with knowledge)
- /workspace/knowledge/competitors/{entity}/assets/logo.png — Company logos (when available)
- /workspace/knowledge/projects/{entity}/assets/roadmap.svg — Project timelines

### Per-Output (generated fresh each cycle)
- Trend charts from this cycle's quantified data
- Data tables backing analysis

### Referenced (user-uploaded)
- /workspace/documents/ — User reference material
- /workspace/assets/ — Brand assets (if uploaded)
```

---

## Phases

### Phase 1: Domain Registry + Workspace Knowledge Scaffold
- Create `api/services/domain_registry.py` with KNOWLEDGE_DOMAINS
- Update `handle_create_task()` to scaffold domain folders when tasks need them
- Update task type registry: replace `knowledge_schema` with `knowledge_reads`/`knowledge_writes`
- Update workspace-conventions.md with shared knowledge hierarchy
- Archive ADR-150 as superseded

### Phase 2: Pipeline Reads Shared Knowledge
- `gather_task_context()` reads from `/workspace/knowledge/{domain}/` based on task's `knowledge_reads`
- Knowledge files injected into agent prompt as primary context
- Metadata (updated_at, tags) used for recency-aware context selection
- Existing tasks without knowledge domains continue to work (graceful fallback)

### Phase 3: Agent Write-Back to Shared Knowledge
- Extend headless tool set: agent can write to `/workspace/knowledge/{domain}/` during execution
- Scoped by task's `knowledge_writes` — agent can only write to declared domains
- Entity creation from templates: agent creates new entity folders using domain registry templates
- Signal log appending: any write-domain agent can append to `/workspace/knowledge/signals/`

### Phase 4: Diff-Aware Output + Asset Management
- Output derivation step reads changelog from knowledge-update step
- DELIVERABLE.md "Derivative Mode" for recurring tasks
- Persistent asset updates: agents update domain-scoped assets when knowledge changes
- Asset manifest at `/workspace/knowledge/assets/manifest.json`

### Phase 5: TP Domain Awareness
- TP working memory includes domain health: which domains exist, entity counts, freshness
- TP can scaffold new domains dynamically (user says "start tracking investors" → new domain)
- ManageTask `evaluate` checks knowledge health alongside output quality
- Agent identity evolution: TP suggests renaming based on domain specialization

---

## Consequences

### Positive
- Knowledge compounds across tasks — the canonical product promise
- Cross-task intelligence sharing without explicit orchestration
- Natural workspace growth: more tasks → richer knowledge → better outputs
- Clean separation: domains (what we know), agents (who works), tasks (what gets produced)
- Filesystem IS the product — the user's accumulated knowledge is visible and browsable
- Scalable: new domains added without architectural change

### Negative
- Write conflicts: two tasks writing to same domain simultaneously. Mitigation: workspace_files has row-level conflict resolution; knowledge files are append-heavy (signals), not rewrite-heavy.
- Knowledge sprawl: domains accumulate files without bound. Mitigation: TP heartbeat flags stale entities; signal log rolls over (90d).
- Complexity: three registries to maintain (domain, agent, task type). Mitigation: domain registry is small and stable; changes are rare.

### Risks
- Agent writes corrupt shared knowledge. Mitigation: write-scoping via task's `knowledge_writes`; filesystem versioning provides rollback.
- Domain structure too rigid. Mitigation: templates are starting points; agents can create files outside the template structure.
- Users confused by knowledge vs. documents. Mitigation: knowledge is agent-managed (grows automatically); documents are user-uploaded (explicit action). Clear UX distinction.

---

## Key Files

| Concern | Location |
|---|---|
| Domain registry (NEW) | `api/services/domain_registry.py` |
| Task type registry (updated: knowledge_reads/writes) | `api/services/task_types.py` |
| Agent type registry (unchanged) | `api/services/agent_framework.py` |
| Knowledge scaffold at task creation | `api/services/primitives/task.py` |
| Knowledge context gathering | `api/services/task_pipeline.py` |
| Agent write-back to knowledge | `api/services/task_pipeline.py` |
| Workspace conventions (updated) | `docs/architecture/workspace-conventions.md` |

## Relationship to Existing ADRs

- **ADR-150**: Superseded. Task-gated knowledge was wrong. Knowledge is workspace-scoped and shared.
- **ADR-149** (Task Lifecycle): Preserved. DELIVERABLE.md, mode semantics, feedback/evaluation/reflection all remain. Task filesystem loses `knowledge/` (moves to workspace). Gains `knowledge_reads`/`knowledge_writes` references.
- **ADR-138** (Agents as Work Units): Preserved. Agent → Task hierarchy unchanged. Agents gain write access to workspace knowledge scoped by task assignment.
- **ADR-140** (Agent Workforce): Preserved. Agent types are capability bundles. Identity specializes through accumulated domain experience, not registry change.
- **ADR-141** (Unified Execution): Extended. Pipeline gains knowledge-read and knowledge-write phases.
- **ADR-142** (Unified Filesystem): Extended. `/workspace/knowledge/` becomes the fifth major workspace section (alongside IDENTITY.md, BRAND.md, documents/, notes.md).
- **ADR-144** (Inference-First Shared Context): Extended. Knowledge domains are another inference surface — TP can infer which domains a user needs from their work description.
- **ADR-145** (Task Type Registry): Extended. Task types gain `knowledge_reads`/`knowledge_writes` replacing `knowledge_schema`.
- **FOUNDATIONS.md**: Directly fulfills Axiom 2 (recursive perception through shared workspace), Axiom 3 (agents develop through knowledge depth in shared domains), Axiom 4 (accumulated attention compounds across all tasks touching a domain).
