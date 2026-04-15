# Registry Matrix — Domains, Tasks, Agents

**Status:** Canonical  
**Date:** 2026-04-13 (ADR-176 universal specialist roster)
**Related:** ADR-176 (Work-First Agent Model), ADR-145 (Task Type Registry), ADR-151 (Context Domains), ADR-152 (Unified Directory Registry), ADR-164 (Back Office Tasks), ADR-166 (Registry Coherence)

---

## Three Registries, One System

YARNNN has three registries that work together:

| Registry | Governs | File | Key constant |
|---|---|---|---|
| **Directory Registry** | Workspace structure + context domains | `directory_registry.py` | `WORKSPACE_DIRECTORIES` |
| **Agent Templates** (v5 universal specialists — ADR-176) | Who does the work — 6 specialists + 3 platform bots | `agent_framework.py` | `AGENT_TEMPLATES` |
| **Task Types** (v6 — ADR-166) | How work gets done — classified by `output_kind` | `task_types.py` | `TASK_TYPES` |

**Read direction:** Domains are upstream → context-accumulating tasks WRITE to domains → deliverable-producing tasks READ from domains → agent types execute task steps. External-action and system-maintenance tasks sit alongside, governed by the same pipeline.

## Two Axes of Organization (ADR-166)

After ADR-166 every task is described by exactly two axes:

| Axis | Where it lives | Values | Used for |
|---|---|---|---|
| **`mode`** (temporal posture) | TASK.md `**Mode:**` + `tasks.mode` column | `recurring \| goal \| reactive` | TP management posture: auto-deliver vs. evaluate-and-steer-to-completion vs. dispatch-and-done. |
| **`output_kind`** (work shape) | TASK.md `**Output:**` + task_types registry | `accumulates_context \| produces_deliverable \| external_action \| system_maintenance` | Pipeline routing: which playbooks load, where output goes, who consumes it, what UI treatment to use. |

**Dropped (ADR-166):** the redundant `category` field on task types and the related `TASK_TYPE_CATEGORIES` constant. Categorization was overlapping shorthand for owner agent + output_kind; both already exist explicitly elsewhere.

**Renamed (ADR-166):** `task_class` → `output_kind`. The old two-value enum (`context | synthesis`) couldn't express external actions (slack-respond, notion-update) or back office work (system_maintenance). The 4-value enum is the clean carve.

---

## Domain ↔ Task ↔ Agent Matrix

| Context Domain | Tasks that WRITE (accumulates_context) | Tasks that READ (produces_deliverable) | Agent (ADR-176 specialist) |
|---|---|---|---|
| **competitors/** | track-competitors | competitive-brief, market-report, meeting-prep, launch-material | Researcher + Tracker (write), Analyst + Writer (read) |
| **market/** | track-market | market-report, launch-material | Researcher + Tracker (write), Analyst + Writer (read) |
| **relationships/** | track-relationships | meeting-prep, stakeholder-update | Tracker (write), Analyst + Writer (read) |
| **projects/** | track-projects | project-status, stakeholder-update | Tracker (write), Analyst + Writer (read) |
| **content_research/** | research-topics | content-brief, launch-material | Researcher (write), Analyst + Writer (read) |
| **signals/** | slack-digest, notion-digest, github-digest, ALL track-* | ALL deliverable-producing tasks | Tracker + bots (write), all specialists (read) |
| **slack/** (temporal) | slack-digest | (TP awareness only) | Slack Bot |
| **notion/** (temporal) | notion-digest | (TP awareness only) | Notion Bot |
| **github/** (temporal) | github-digest | (TP awareness only) | GitHub Bot |
| **customers/** (canonical, ADR-183) | commerce-digest | revenue-report, daily-update | Commerce Bot (write), Analyst + Writer (read) |
| **revenue/** (canonical, ADR-183) | commerce-digest | revenue-report, daily-update | Commerce Bot (write), Analyst + Writer (read) |
| **(cross-domain)** | — | daily-update, stakeholder-update, market-report | Analyst + Writer (deliverables TP-assembled) |

> **Note (ADR-176):** Domain context directories are created by work demand, not pre-scaffolded at signup. Only `signals/` and platform bot directories exist at signup. Other domains (competitors/, market/, etc.) are created by TP when the first task needing them is created. Domain names come from user language — these are the known archetypes, not the only possible domains.
>
> **Note (ADR-183):** Commerce domains (`customers/`, `revenue/`) are created when a commerce provider is connected, not at signup. Commerce Bot is scaffolded at the same time. See [commerce-substrate.md](commerce-substrate.md).

External-action tasks (`slack-respond`, `notion-update`) read from the domains in their `context_reads` but produce no workspace artifact — their effect is the platform write. System-maintenance tasks (`back-office-*`) touch no domains; they emit hygiene signals only.

---

## Task Type Catalog (v6 — ADR-166)

Task types are organized by `output_kind`. There are exactly four:

1. **`accumulates_context`** — writes to a workspace context domain. Produces no user-visible artifact this run; the run's value is what it adds to the domain.
2. **`produces_deliverable`** — writes a user-visible output to `/tasks/{slug}/outputs/`. The "synthesis tasks" of prior versions.
3. **`external_action`** — takes an action on an external platform via API write. No workspace artifact; the effect lives on the third-party surface.
4. **`system_maintenance`** — TP-owned, deterministic, no LLM. Emits orchestration signals (paused agents, cleaned-up files) into activity_log.

For full intelligence coverage, pair an `accumulates_context` task with a `produces_deliverable` task — e.g., `track-competitors` (Mon) + `competitive-brief` (Fri).

### Accumulates Context — Track & Research

Maintain workspace knowledge domains. Run on schedule, update domain folders, produce no report output.

| Type Key | Display Name | Mode | Schedule | Bootstrap | Domains (writes) |
|---|---|---|---|---|---|
| **track-competitors** | Track Competitors | recurring | weekly | 3 entities, profile | competitors, signals |
| **track-market** | Track Market | recurring | monthly | 2 entities, analysis | market, signals |
| **track-relationships** | Track Relationships | recurring | weekly | 3 entities, profile | relationships, signals |
| **track-projects** | Track Projects | recurring | weekly | 2 entities, status | projects, signals |
| **research-topics** | Research Topics | goal | on-demand | 1 entity, research | content_research |
| **slack-digest** | Slack Digest | recurring | daily | — | slack, signals |
| **notion-digest** | Notion Digest | recurring | weekly | — | notion, signals |
| **github-digest** | GitHub Digest | recurring | daily | — | github, signals |
| **commerce-digest** | Commerce Digest | recurring | daily | — | customers, revenue, signals |

All `track-*` tasks read both their domain AND the `signals/` domain — same shape across the board (ADR-166 normalization).

`commerce-digest` (ADR-183) follows the same pattern — reads from the commerce provider API, writes to `customers/` and `revenue/` domains. Created when commerce provider is connected, not at signup.

### Produces Deliverable — Reports & Outputs

Read from accumulated context, write a finished artifact to `/tasks/{slug}/outputs/`.

| Type Key | Display Name | Mode | Schedule | Reads From | Notes |
|---|---|---|---|---|---|
| **daily-update** ⭐ | Daily Update | recurring | daily | ALL domains | **ESSENTIAL ANCHOR (ADR-161)** — scaffolded at signup, cannot be archived. Empty workspaces produce a deterministic template (zero LLM cost). The user-facing heartbeat artifact. |
| **competitive-brief** | Competitive Brief | recurring | weekly | competitors, signals | briefs |
| **market-report** | Market Report | recurring | monthly | market, competitors, signals | Absorbs former `gtm-report`. Single market+competitive+GTM intelligence brief (ADR-166). |
| **meeting-prep** | Meeting Prep | **goal** | on-demand | relationships, competitors, signals | Has clear completion (the meeting). Goal-shaped, not reactive (ADR-166). |
| **stakeholder-update** | Stakeholder Update | recurring | monthly | ALL domains | reports |
| **project-status** | Project Status Report | recurring | weekly | projects, signals | reports |
| **content-brief** | Content Brief | goal | on-demand | content_research, competitors, signals | content_output |
| **launch-material** | Launch Material | goal | on-demand | content_research, competitors, market, signals | content_output |
| **revenue-report** | Revenue Report | recurring | weekly | revenue, customers, signals | reports |

### External Action — Platform Writes

Take an action on an external platform via API write. The user's workspace gets no artifact; the effect lives on the third-party surface.

| Type Key | Display Name | Mode | Schedule | Reads From | Writes To |
|---|---|---|---|---|---|
| **slack-respond** | Slack Post | reactive | on-demand | slack, signals | Slack channel/thread |
| **notion-update** | Notion Update | reactive | on-demand | notion, signals | Notion page |
| **commerce-create-product** | Create Product | reactive | on-demand | task output folder | Commerce provider (LS) |
| **commerce-update-product** | Update Product | reactive | on-demand | task output folder | Commerce provider (LS) |

### System Maintenance — Back Office (ADR-164)

TP-owned, deterministic, no LLM. Run through the same task pipeline as user-facing tasks. Visible to users at `/work` (essential, cannot be archived).

| Type Key | Display Name | Mode | Schedule | Owner | Effect |
|---|---|---|---|---|---|
| **back-office-agent-hygiene** ⭐ | Agent Hygiene | recurring | daily | TP | Pauses agents whose approval rate has decayed below threshold. |
| **back-office-workspace-cleanup** ⭐ | Workspace Cleanup | recurring | daily | TP | Sweeps ephemeral files past TTL, prunes orphaned outputs. |

### Outputs — Tasks Own Their Outputs (ADR-154)

`/workspace/outputs/` directory and `output_category` field **REMOVED**. Tasks own their outputs directly at `/tasks/{slug}/outputs/`. Users access outputs by clicking tasks in the nav. Context-accumulating tasks write to `/workspace/context/{domain}/`. External-action and system-maintenance tasks emit no workspace files at all.

---

## Agent Roster (Default — Pre-Scaffolded at Signup)

9 agents at signup (ADR-176 universal specialists + ADR-164 TP as agent).

| Agent | Role | Class | Capabilities | Phase | Playbooks |
|---|---|---|---|---|---|
| **Researcher** | `researcher` | specialist | web_search, investigate, read_workspace, search_knowledge, produce_markdown | Accumulation | outputs, research |
| **Analyst** | `analyst` | specialist | read_workspace, search_knowledge, produce_markdown | Accumulation | outputs |
| **Writer** | `writer` | specialist | read_workspace, produce_markdown | Accumulation | outputs, formats |
| **Tracker** | `tracker` | specialist | read_slack, read_notion, read_github, read_workspace, produce_markdown | Accumulation | outputs |
| **Designer** | `designer` | specialist | chart, mermaid, image, video_render, compose_html | Production | visual |
| **Thinking Partner** | `thinking_partner` | meta-cognitive | read_workspace, write_workspace, search_knowledge, produce_markdown | Orchestration | — |
| **Slack Bot** | `slack_bot` | platform-bot | read_slack, write_slack | Accumulation | outputs |
| **Notion Bot** | `notion_bot` | platform-bot | read_notion, write_notion | Accumulation | outputs |
| **GitHub Bot** | `github_bot` | platform-bot | read_github | Accumulation | outputs |
| **Commerce Bot** *(on connect)* | `commerce_bot` | platform-bot | read_commerce, write_commerce | Accumulation | outputs |

> **Commerce Bot (ADR-183):** NOT scaffolded at signup. Created when user connects a commerce provider. Owns `customers/` and `revenue/` context domains. See [commerce-substrate.md](commerce-substrate.md).

**Key principles (ADR-176):**
- **Universal specialists, not ICP-specific personas.** Researcher, Analyst, Writer, Tracker, Designer — names that pass the instinct test for any user in any industry.
- **Capability split:** Accumulation agents (Researcher, Analyst, Writer, Tracker) accumulate knowledge and produce markdown. Production agent (Designer) generates visual assets. These phases never overlap within a single agent.
- **No domain ownership.** Specialists are assigned to tasks; tasks read/write context domains. The same Researcher can work on competitors one task and market another. Domain expertise develops through accumulated work, not through a pre-assigned label.
- **Hospital principle:** The 9-agent roster is fixed and non-configurable. These are the roles that all knowledge work requires. The roster grows from observed work patterns, not user preference.
- **Playbooks** are agent-level methodology. Loaded selectively by task `output_kind` (ADR-166). See `docs/features/agent-playbook-framework.md`.
- Templates are bootstrapping — AGENT.md is the runtime source of truth.
- **Thinking Partner (TP)** is the meta-cognitive agent (ADR-164). Two runtime modes: chat (user-present conversation) and task (back office execution). TP owns no context domain; its domain is orchestration itself.

### Context Domain Assets (ADR-157)

Each entity-bearing context domain has a visible `assets/` subfolder for visual assets:
```
/workspace/context/{domain}/assets/{entity-slug}-favicon.png
```

Favicons fetched automatically via ManageDomains when entities have a `url` field. Available to all agents reading the domain during synthesis.

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
2. Researcher gathers fresh intelligence (workspace context, web search, task-scoped source reads)
3. Tracker maintains entity profiles in `/workspace/context/competitors/` (entity files, analysis)
4. Tracker appends signal to `/workspace/context/signals/`
5. No output produced — context accumulates silently

### Running a Synthesis Task (Example: Competitive Brief)
1. Scheduler triggers (next_run_at <= now)
2. Analyst reads from `/workspace/context/competitors/` and `/workspace/context/signals/`, synthesizes patterns
3. Writer composes a deliverable from the synthesized context
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
├── style.md                        # Learned output style (visible in Settings)
├── _playbook.md                    # TP methodology (HIDDEN — system file)
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
│   ├── customers/                  # Managed by: commerce-digest (ADR-183, on connect)
│   ├── revenue/                    # Managed by: commerce-digest (ADR-183, on connect)
│   └── signals/                    # Temporal signal log (HIDDEN — no user browse)

/agents/{slug}/                     # WHO — identity only (HIDDEN — all of it)
├── AGENT.md                        # Identity + behavioral instructions
└── playbook-*.md                   # Type-seeded methodology

/tasks/{slug}/                      # HOW — task infrastructure (HIDDEN — accessed via task UI)
├── TASK.md, DELIVERABLE.md, awareness.md, memory/, outputs/
```
