# Registry Matrix — Domains, Tasks, Agents

**Status:** Canonical  
**Date:** 2026-03-31  
**Related:** ADR-140 (Agent Workforce), ADR-145 (Task Type Registry), ADR-151 (Context Domains)

---

## Three Registries, One System

YARNNN has three registries that work together:

| Registry | Governs | File | Key constant |
|---|---|---|---|
| **Context Domains** | What the system accumulates | `domain_registry.py` | `CONTEXT_DOMAINS` |
| **Agent Types** | Who does the work | `agent_framework.py` | `AGENT_TYPES` |
| **Task Types** | How work gets done | `task_types.py` | `TASK_TYPES` |

**Read direction:** Domains are upstream → Task types read/write domains → Agent types execute task steps.

---

## Domain ↔ Task ↔ Agent Matrix

| Context Domain | Task Types that READ | Task Types that WRITE | Agent Types involved |
|---|---|---|---|
| **competitors** | competitive-intel, due-diligence, stakeholder-update, meeting-prep, launch-material, gtm-tracker | competitive-intel, due-diligence, gtm-tracker | research, marketing, content |
| **market** | market-research, stakeholder-update, launch-material, gtm-tracker | market-research | research, content |
| **relationships** | relationship-health, meeting-prep, stakeholder-update | relationship-health, meeting-prep | crm, research, content |
| **projects** | project-status, stakeholder-update | project-status, stakeholder-update | research, content |
| **content** | content-brief, launch-material | content-brief, launch-material | research, content |
| **signals** | industry-signal, slack-recap, notion-sync | ALL task types (signal routing) | all agent types |

---

## Task Type Catalog

### Intelligence & Research

| Task Type | Default Mode | Schedule | Process | Domains (R/W) |
|---|---|---|---|---|
| **Competitive Intel Brief** | recurring | weekly | research → content | R: competitors / W: competitors, signals |
| **Market Research Report** | recurring | monthly | research → content | R: market / W: market, signals |
| **Industry Signal Monitor** | recurring | weekly | marketing (single) | R: signals / W: signals |
| **Due Diligence Summary** | goal | on-demand | research → content | R: competitors, market / W: competitors, signals |

### Operations

| Task Type | Default Mode | Schedule | Process | Domains (R/W) |
|---|---|---|---|---|
| **Meeting Prep Brief** | reactive | on-demand | crm → research | R: relationships, competitors / W: relationships, signals |
| **Stakeholder / Board Update** | recurring | monthly | research → content | R: competitors, market, projects, relationships / W: projects, signals |
| **Relationship Health Digest** | recurring | weekly | crm → content | R: relationships / W: relationships, signals |
| **Project Status Report** | recurring | weekly | research → content | R: projects / W: projects, signals |

### Platform Digests

| Task Type | Default Mode | Schedule | Process | Domains (R/W) |
|---|---|---|---|---|
| **Slack Recap** | recurring | daily | slack_bot (single) | R: signals / W: signals |
| **Notion Sync Report** | recurring | weekly | notion_bot (single) | R: signals / W: signals |

### Content & Communications

| Task Type | Default Mode | Schedule | Process | Domains (R/W) |
|---|---|---|---|---|
| **Content Brief / Blog Draft** | goal | on-demand | research → content | R: content / W: content |
| **Launch / Announcement Material** | goal | on-demand | research → content | R: content, competitors, market / W: content |

### Data & Tracking

| Task Type | Default Mode | Schedule | Process | Domains (R/W) |
|---|---|---|---|---|
| **GTM Tracker** | recurring | weekly | marketing → content | R: competitors, market / W: competitors, signals |

---

## Agent Roster (Default — Pre-Scaffolded at Signup)

| Agent Type | Class | Capabilities | Typical Task Steps | Domain Affinity |
|---|---|---|---|---|
| **Research Agent** | agent | web_search, investigate, chart, mermaid | update-context (research), derive-output | competitors, market, projects |
| **Content Agent** | agent | compose_html, chart, mermaid | derive-output (composition) | reads all, writes none |
| **Marketing Agent** | agent | web_search, read_platforms | update-context (GTM), capture-and-report | competitors, market, signals |
| **CRM Agent** | agent | read_platforms, read_workspace | update-context (relationships) | relationships |
| **Slack Bot** | bot | read_platforms, write_slack | capture-and-report | signals |
| **Notion Bot** | bot | read_platforms, write_notion | capture-and-report | signals |

**Key principle:** Agents carry SKILL (capabilities). Tasks assign agents to DOMAINS. Agent IDENTITY specializes over time through accumulated domain experience.

---

## How It Works Together

### Creating a Task
1. User describes work → TP infers task type from registry
2. Task type defines: process steps (which agents), context_reads/writes (which domains), default schedule/mode
3. Task creation scaffolds: TASK.md, DELIVERABLE.md, memory files
4. Domain folders scaffolded if not yet present (idempotent)

### Running a Task (Recurring Example: Competitive Intel)
1. Scheduler triggers (next_run_at <= now)
2. Pipeline reads `/workspace/context/competitors/` (accumulated context — PRIMARY)
3. Step 1: Research Agent updates context (new signals, entity updates)
4. Step 2: Content Agent derives output (brief emphasizing what changed)
5. Pipeline writes signal to `/workspace/context/signals/`
6. Output saved to `/tasks/{slug}/outputs/`
7. Delivered per TASK.md config

### Accumulation Across Tasks
- Competitive intel writes to `competitors/` → Stakeholder update READS from `competitors/`
- Meeting prep writes to `relationships/` → Relationship health READS from `relationships/`
- ALL tasks write signals → signals/ provides temporal awareness to all tasks
- **Context compounds across tasks. No task is isolated.**

---

## Expansion Guidelines

### Adding a New Context Domain
1. Add entry to `CONTEXT_DOMAINS` in `domain_registry.py`
2. Define entity_structure, synthesis_file, signal_log
3. Update relevant task types with `context_reads`/`context_writes`
4. Update workspace-conventions.md
5. Increment domain registry version

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
/workspace/
├── IDENTITY.md, BRAND.md          # User context
├── documents/                      # User-uploaded references
├── context/                        # ACCUMULATED CONTEXT (domain registry)
│   ├── competitors/                # Managed by: competitive-intel, due-diligence, gtm-tracker
│   ├── market/                     # Managed by: market-research
│   ├── relationships/              # Managed by: meeting-prep, relationship-health
│   ├── projects/                   # Managed by: project-status, stakeholder-update
│   ├── content/                    # Managed by: content-brief, launch-material
│   ├── signals/                    # Managed by: ALL tasks (temporal signal log)
│   └── assets/                     # Cross-domain shared assets
├── notes.md, preferences.md       # TP observations

/agents/{slug}/                     # Agent identity + methodology
├── AGENT.md, memory/reflections.md, memory/feedback.md, playbook-*.md

/tasks/{slug}/                      # Work order + derived output
├── TASK.md, DELIVERABLE.md, memory/, outputs/
```
