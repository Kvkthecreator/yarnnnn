# Registry Matrix — Domains, Tasks, Agents

**Status:** Canonical  
**Date:** 2026-03-31  
**Related:** ADR-140 (Agent Workforce), ADR-145 (Task Type Registry), ADR-151 (Context Domains), ADR-152 (Unified Directory Registry)

---

## Three Registries, One System

YARNNN has three registries that work together:

| Registry | Governs | File | Key constant |
|---|---|---|---|
| **Directory Registry** | Workspace structure + context domains | `directory_registry.py` | `WORKSPACE_DIRECTORIES` |
| **Agent Templates** (v4 domain-steward) | Who does the work — domain-steward + synthesizer + bot | `agent_framework.py` | `AGENT_TEMPLATES` |
| **Task Types** (v3 atomic) | How work gets done — split into context + synthesis | `task_types.py` | `TASK_TYPES` |

**Read direction:** Domains are upstream → Context tasks WRITE to domains → Synthesis tasks READ from domains → Agent types execute task steps.

---

## Domain ↔ Task ↔ Agent Matrix

| Context Domain | Context Tasks (WRITE) | Synthesis Tasks (READ) | Agent (domain steward) |
|---|---|---|---|
| **competitors/** | track-competitors | competitive-brief, market-report, meeting-prep, launch-material, gtm-report | Competitive Intelligence |
| **market/** | track-market | market-report, launch-material, gtm-report | Market Research |
| **relationships/** | track-relationships | meeting-prep, stakeholder-update | Business Development |
| **projects/** | track-projects | project-status, stakeholder-update | Operations |
| **content/** | research-topics | content-brief, launch-material | Marketing & Creative |
| **signals/** | monitor-slack, monitor-notion, ALL context tasks | ALL synthesis tasks | Slack Bot, Notion Bot |
| **(cross-domain)** | — | stakeholder-update, market-report | Executive Reporting (synthesizer) |

---

## Task Type Catalog (v3 — Atomic Split)

Task types are split into two classes: **context tasks** (accumulate workspace knowledge) and **synthesis tasks** (produce deliverables from accumulated context). For full intelligence coverage, create one of each — e.g., `track-competitors` + `competitive-brief`.

### Context Tasks — Track & Research

Context tasks maintain your workspace knowledge domains. They run on schedule, update domain folders, and produce NO report output.

| Type Key | Display Name | Mode | Schedule | Bootstrap | Domains (writes) |
|---|---|---|---|---|---|
| **track-competitors** | Track Competitors | recurring | weekly | 3 entities, profile | competitors, signals |
| **track-market** | Track Market | recurring | monthly | 2 entities, analysis | market, signals |
| **track-relationships** | Track Relationships | recurring | weekly | 3 entities, profile | relationships, signals |
| **track-projects** | Track Projects | recurring | weekly | 2 entities, status | projects, signals |
| **research-topics** | Research Topics | goal | on-demand | 1 entity, research | content_research |
| **monitor-slack** | Monitor Slack | recurring | daily | — | signals |
| **monitor-notion** | Monitor Notion | recurring | weekly | — | signals |

### Synthesis Tasks — Reports & Outputs

Synthesis tasks read from accumulated context domains and produce deliverables.

| Type Key | Display Name | Mode | Schedule | Reads From | Output Category |
|---|---|---|---|---|---|
| **competitive-brief** | Competitive Brief | recurring | weekly | competitors, signals | briefs |
| **market-report** | Market Report | recurring | monthly | market, competitors, signals | reports |
| **meeting-prep** | Meeting Prep | reactive | on-demand | relationships, competitors, signals | briefs |
| **stakeholder-update** | Stakeholder Update | recurring | monthly | ALL domains | reports |
| **project-status** | Project Status Report | recurring | weekly | projects, signals | reports |
| **content-brief** | Content Brief | goal | on-demand | content_research, competitors, signals | content_output |
| **launch-material** | Launch Material | goal | on-demand | content_research, competitors, market, signals | content_output |
| **gtm-report** | GTM Report | weekly | content | competitors, market, signals | reports |

### Outputs — Tasks Own Their Outputs (ADR-154)

`/workspace/outputs/` directory and `output_category` field **REMOVED**. Tasks own their outputs directly at `/tasks/{slug}/outputs/`. Users access outputs by clicking tasks in the nav. Context tasks write to `/workspace/context/{domain}/`.

---

## Agent Roster (Default — Pre-Scaffolded at Signup)

| Agent | Class | Domain Owned | Capabilities Summary |
|---|---|---|---|
| **Competitive Intelligence** | domain-steward | competitors/ | web_search, investigate, chart |
| **Market Research** | domain-steward | market/ | web_search, investigate, chart |
| **Business Development** | domain-steward | relationships/ | read_slack, read_notion, read_github, investigate |
| **Operations** | domain-steward | projects/ | read_slack, read_notion, read_github, chart |
| **Marketing & Creative** | domain-steward | content/ | web_search, chart, image, video_render, compose_html |
| **Executive Reporting** | synthesizer | (cross-domain) | compose_html, chart |
| **Slack Bot** | platform-bot | platform-scoped observer | read_slack, write_slack |
| **Notion Bot** | platform-bot | platform-scoped observer | read_notion, write_notion |

**Key principle:** Each domain-steward agent owns one context domain. The synthesizer (Executive) reads all domains. Templates are bootstrapping — AGENT.md is the runtime source of truth.

---

## How It Works Together

### Creating Tasks
1. User describes work → TP infers task type(s) from registry
2. For full intelligence coverage, TP creates BOTH a context task AND a synthesis task (e.g., `track-competitors` + `competitive-brief`)
3. Each task type defines: agent assignment, context domains (reads/writes), default schedule/mode
4. Task creation scaffolds: TASK.md, DELIVERABLE.md (synthesis only), memory files
5. Domain folders scaffolded if not yet present (idempotent)

### Running a Context Task (Example: Track Competitors)
1. Scheduler triggers (next_run_at <= now)
2. Research Agent gathers fresh intelligence (workspace context, web search, task-scoped source reads)
3. Agent writes findings to `/workspace/context/competitors/` (entity files, analysis)
4. Agent appends signal to `/workspace/context/signals/`
5. No output produced — context accumulates silently

### Running a Synthesis Task (Example: Competitive Brief)
1. Scheduler triggers (next_run_at <= now)
2. Content Agent reads from `/workspace/context/competitors/` and `/workspace/context/signals/`
3. Agent composes a deliverable from the accumulated context
4. Output saved to `/tasks/{slug}/outputs/`
5. Delivered per TASK.md config

### Accumulation Across Tasks
- `track-competitors` writes to `competitors/` → `competitive-brief` and `market-report` READ from it
- `track-relationships` writes to `relationships/` → `meeting-prep` READS from it
- ALL context tasks write signals → `signals/` provides temporal awareness to all synthesis tasks
- **Context compounds across tasks. Synthesis tasks get richer as context tasks accumulate.**

---

## Expansion Guidelines

### Adding a New Context Domain
1. Add entry to `WORKSPACE_DIRECTORIES` in `directory_registry.py`
2. Define entity_structure, synthesis_file, signal_log
3. Update relevant task types with `context_reads`/`context_writes`
4. Update workspace-conventions.md
5. Increment directory registry version

### Adding a New Task Type
1. Add entry to `TASK_TYPES` in `task_types.py`
2. Define process steps, default_objective, default_deliverable, context_reads/writes
3. Map to existing agent types (or document if new agent type needed)
4. Add to this matrix document
5. Update docs/features/task-types.md

### Adding a New Agent Type
1. Add entry to `AGENT_TYPES` in `agent_framework.py`
2. Define capabilities, methodology playbooks, default_instructions
3. Update DB role constraint (migration)
4. Add to DEFAULT_ROSTER if pre-scaffolded
5. Map to relevant task type process steps

---

## File System Summary

```
/workspace/                          # User workspace
├── IDENTITY.md                     # User profile (visible in Settings)
├── BRAND.md                        # Output style (visible in Settings)
├── AWARENESS.md                    # TP situational notes (visible in Settings)
├── notes.md                        # Standing instructions (visible in Settings)
├── preferences.md                  # Learned preferences (visible in Settings)
├── playbook-orchestration.md       # TP methodology (HIDDEN — system file)
├── WORKSPACE.md                    # Init manifest (HIDDEN — system file)
├── uploads/                        # User-uploaded references
├── context/                        # ACCUMULATED CONTEXT (domains)
│   ├── competitors/                # Managed by: track-competitors
│   │   ├── _tracker.md             # Entity registry (HIDDEN — pipeline-maintained)
│   │   ├── _landscape.md           # Cross-entity synthesis (VISIBLE — domain summary)
│   │   └── {entity}/              # Per-entity files (VISIBLE)
│   ├── market/                     # Managed by: track-market
│   ├── relationships/              # Managed by: track-relationships
│   ├── projects/                   # Managed by: track-projects
│   ├── content_research/           # Managed by: research-topics
│   └── signals/                    # Temporal signal log (HIDDEN — no user browse)

/agents/{slug}/                     # WHO — identity only (HIDDEN — all of it)
├── AGENT.md                        # Identity + behavioral instructions
└── playbook-*.md                   # Type-seeded methodology

/tasks/{slug}/                      # HOW — task infrastructure (HIDDEN — accessed via task UI)
├── TASK.md, DELIVERABLE.md, awareness.md, memory/, outputs/
```
