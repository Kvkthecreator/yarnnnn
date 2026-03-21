# Architecture: Workspace Conventions

**Status:** Canonical (v2)
**Date:** 2026-03-20
**Related:**
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — folder conventions, lifecycle, versioning
- [ADR-122: Project Type Registry](../adr/ADR-122-project-type-registry.md) — project scaffolding
- [ADR-124: Project Meeting Room](../adr/ADR-124-project-meeting-room.md) — project surface
- [ADR-127: User-Shared File Staging](../adr/ADR-127-user-shared-file-staging.md) — `user_shared/` convention
- [Naming Conventions](naming-conventions.md) — broader naming system
- [Agent Execution Model](agent-execution-model.md) — how agents interact with workspace

---

## Overview

YARNNN's workspace is a **virtual filesystem of human-readable files** backed by Postgres (`workspace_files` table). Path conventions are the schema. New capabilities extend paths, not database tables.

Four top-level namespaces:

| Namespace | Scope | Owner | Purpose |
|-----------|-------|-------|---------|
| `/agents/{slug}/` | Per-agent | Agent + system | Agent identity, memory, outputs, scratch |
| `/projects/{slug}/` | Per-project | PM + contributors | Coordination, contributions, assembly |
| `/knowledge/` | Global (shared) | Agents (at delivery) | Agent-produced knowledge artifacts |
| `/memory/` | Global (user) | User + system | User identity, preferences, notes |

Additionally, `/user_shared/` (global) and `/projects/{slug}/user_shared/` (project-scoped) serve as ephemeral staging areas for user-contributed files (ADR-127).

---

## Industry Alignment

YARNNN's workspace conventions deliberately mirror Claude Code's filesystem model where applicable.

| Purpose | Claude Code | YARNNN | Rationale |
|---------|------------|--------|-----------|
| Identity + instructions | `CLAUDE.md` | `AGENT.md` | Capitalized, root-level, discoverable |
| Memory directory | `.claude/memory/` | `memory/` | Topic-scoped, unbounded |
| Default memory | `.claude/memory/MEMORY.md` | `memory/observations.md` | Semantic name > generic name |
| Topic memory | `.claude/memory/{topic}.md` | `memory/{topic}.md` | Same pattern |
| Settings/config | `.claude/settings.json` | DB columns (not workspace) | Config ≠ intelligence |

**YARNNN-unique files** (no Claude Code equivalent):
- `thesis.md` — self-evolving domain understanding. Core differentiator: agents that build persistent theses.
- `outputs/{date}/` — dated output folders with `manifest.json`. Atomic output packaging.
- `working/{topic}.md` — intermediate research notes that persist across tool rounds within a run.

---

## Agent Workspace

```
/agents/{slug}/
│
├── AGENT.md                        # Identity + behavioral instructions
│                                   # Like CLAUDE.md — the entry point
│                                   # User-writable, agent-readable
│
├── thesis.md                       # Agent's current domain understanding
│                                   # Self-evolving — agent updates after each run
│
├── memory/                         # Topic-scoped persistent memory
│   ├── observations.md             # Timestamped observations from review passes
│   ├── preferences.md              # Learned preferences from user edit patterns (ADR-117)
│   ├── projects.json               # Project memberships list (ADR-119 Phase 2)
│   ├── goal.md                     # Assigned goal and milestones
│   ├── state.md                    # Operational state metadata
│   └── {topic}.md                  # Agent-created topic files (unbounded)
│
├── outputs/                        # Dated output folders (ADR-119 Phase 1)
│   └── {date}/                     # e.g., outputs/2026-03-18T1500/
│       ├── output.md               # Primary text output (feedback surface)
│       ├── manifest.json           # Run metadata, file list, delivery status
│       └── {rendered_files}        # Binary artifacts from RuntimeDispatch (ADR-118)
│
├── working/                        # Intermediate research (ephemeral scratch)
│   └── {topic}.md                  # Research notes, saved queries, evidence
│
├── duties/                         # Multi-duty portfolio (ADR-117 Phase 3)
│   └── {duty_name}.md              # Per-duty definition and instructions
│
├── history/                        # Version archives (ADR-119 Phase 3)
│   └── {filename}/                 # e.g., history/AGENT.md/
│       └── v{N}.md                 # Previous versions (max 5 kept)
│
├── references/                     # Cross-agent references (ADR-116)
│   └── {agent-slug}.md             # Cached identity/thesis from referenced agent
│
└── agent-card.json                 # Auto-generated agent identity card (ADR-116 Phase 4)
```

### Evolving Files (Auto-Versioned)

These files are archived to `/history/{filename}/v{N}.md` on overwrite (max 5 versions):
- `AGENT.md`, `thesis.md`
- All files under `memory/`
- All files under `duties/`

---

## Project Workspace

```
/projects/{slug}/
│
├── PROJECT.md                      # Project charter (ADR-119 Phase 2, ADR-123)
│                                   # Title, type_key, objective, contributors,
│                                   # assembly_spec, delivery
│                                   # Mutable by: User, Composer, TP (not PM)
│
├── contributions/                  # Per-agent contribution folders
│   └── {agent-slug}/              # Scoped to each contributor
│       ├── {filename}              # Contribution files (any format)
│       └── brief.md                # PM steering directive (ADR-121)
│                                   # Focus areas, gaps to address
│                                   # Written by PM, read by contributor
│
├── assembly/                       # Composed outputs (ADR-120 Phase 2)
│   └── {date}/                     # Dated assembly folder
│       ├── output.md               # Assembled text output
│       ├── manifest.json           # Assembly metadata, sources, delivery status
│       └── {rendered_files}        # Binary artifacts from RuntimeDispatch
│
├── memory/                         # Project-level state and coordination
│   ├── pm_agent.json               # PM agent reference (pm_agent_id, pm_title)
│   ├── project_assessment.md       # PM's layered project evaluation (PM cognitive model v1.0)
│   │                               # 5-layer: commitment → structure → context → quality → readiness
│   │                               # Rewritten every PM pulse — evolving cognitive state
│   ├── work_plan.md                # PM's operational plan (ADR-120 Phase 4)
│   │                               # Intentions, focus areas, budget status
│   ├── quality_assessment.md       # PM's contribution quality scoring (ADR-121)
│   ├── preferences.md              # Project-level preferences/conventions
│   └── progress.md                 # Progress tracking
│
├── user_shared/                    # User-contributed files (ADR-127)
│   └── {filename}                  # Ephemeral staging — 30-day TTL
│                                   # PM triages: promote or let expire
│
├── working/                        # Ephemeral scratch space
│   └── {topic}.md                  # Temporary working files
│
└── history/                        # Version archives (ADR-119 Phase 3)
    └── {filename}/
        └── v{N}.md
```

### Key Relationships

- **PROJECT.md** is the charter — defines the project's north star (objective) and structure
- **`contributions/{agent_slug}/`** is where agents deposit their work for assembly
- **`contributions/{agent_slug}/brief.md`** is PM's steering mechanism — written by PM, read by contributors during context gathering
- **`assembly/{date}/`** is the composed output from multiple contributions
- **`user_shared/`** is the user's staging area — PM triages files into contributions, knowledge, or lets them expire
- **`memory/project_assessment.md`** is PM's layered evaluation — rewritten every pulse, encodes which prerequisite layer is the current constraint
- **`memory/work_plan.md`** is PM's operational plan — separate from the charter, PM-owned

---

## Knowledge Filesystem (Shared)

```
/knowledge/
├── digests/                        # Platform-specific recaps (role: digest)
│   └── {source}-{date}.md         # e.g., slack-engineering-2026-03-11.md
│
├── research/                       # Deep research outputs (role: research)
│   └── {topic-slug}/
│       ├── latest.md               # Current version (canonical)
│       └── v1.md, v2.md            # Historical versions (opt-in)
│
├── analyses/                       # Cross-platform synthesis (role: synthesize)
│   └── {topic-slug}.md
│
├── briefs/                         # Event-driven preparation (role: prepare)
│   └── {event-slug}.md
│
├── insights/                       # Proactive findings (role: monitor)
│   └── {topic-slug}.md
│
├── custom/                         # Fallback for custom roles
│   └── {slug}-{date}.md
│
└── history/                        # Version archives
    └── {filename}/
        └── v{N}.md
```

Agent outputs enter `/knowledge/` at delivery time (not generation). Only approved/delivered outputs are written. Directory placement communicates content class, versioning, and provenance.

**External platform data** (Slack, Gmail, Notion, Calendar) stays in `platform_content` table — flat, TTL-managed, sync-pipeline-written. `/knowledge/` is for agent-produced knowledge only.

---

## User Memory (Global)

```
/memory/
├── MEMORY.md                       # Identity: name, role, company, timezone, bio
├── preferences.md                  # Communication and content preferences
└── notes.md                        # Standing instructions, observed facts
```

Replaces `user_memory` key-value table (ADR-059). See [ADR-108](../adr/ADR-108-user-memory-filesystem-migration.md).

---

## User-Shared Staging (ADR-127)

```
/user_shared/                       # TP-level: global, not project-scoped
    {filename}

/projects/{slug}/user_shared/       # Project-level: scoped to project
    {filename}
```

**Purpose:** Ephemeral staging area where users share files with agents. Preserves workspace sovereignty — users contribute to a clearly delineated area, agents (PM) decide what gets promoted.

**Lifecycle:** `ephemeral` (30-day TTL). PM triages by promoting files to `contributions/`, `knowledge/`, or `memory/`, or lets them expire.

**Same convention at both levels.** Whether sharing in TP chat or a Meeting Room, files land in `user_shared/`.

---

## Manifest Files

Both agent outputs and project assemblies use `manifest.json` for metadata:

### Agent Output Manifest (`outputs/{date}/manifest.json`)

```json
{
  "run_id": "uuid",
  "agent_id": "uuid",
  "version": 1,
  "role": "digest",
  "created_at": "2026-03-20T09:00:00Z",
  "status": "active",
  "files": [
    {"path": "output.md", "type": "text/markdown", "role": "primary"},
    {"path": "report.pdf", "type": "application/pdf", "content_url": "s3://...", "role": "rendered"}
  ],
  "sources": ["platform_content references consumed"],
  "feedback": {},
  "delivery": {"channel": "email", "sent_at": null, "status": "pending"}
}
```

### Project Assembly Manifest (`assembly/{date}/manifest.json`)

```json
{
  "project_slug": "q2-business-review",
  "version": 1,
  "created_at": "2026-03-20T09:00:00Z",
  "status": "active",
  "files": [
    {"path": "output.md", "type": "text/markdown", "role": "primary"},
    {"path": "report.pptx", "content_url": "s3://...", "role": "rendered"}
  ],
  "sources": ["contributions/agent-slug/file.md"],
  "feedback": {},
  "delivery": {"channel": "email", "sent_at": null, "status": "pending"}
}
```

---

## Lifecycle & Versioning (ADR-119)

### `lifecycle` Column

| Value | Meaning | Set by |
|-------|---------|--------|
| `active` | Normal operational file | Default for most paths |
| `ephemeral` | Temporary — auto-cleaned after TTL | `_infer_lifecycle()` for `/working/`, `/user_shared/` |
| `delivered` | Output that has been delivered | Delivery pipeline |
| `archived` | Previous version kept for history | Version archival |

### `version` Column

Integer, auto-incremented on overwrite of the same path. Used for:
- Optimistic concurrency (future)
- Version history tracking
- Detecting stale reads

### Version History Convention

On overwrite of evolving files, previous version is copied to:
```
/history/{original_filename}/v{N}.md
```

Max 5 versions kept per file. Oldest auto-deleted when limit exceeded.

**Evolving file patterns** (triggers auto-versioning):
- Exact: `AGENT.md`, `thesis.md`, `PROJECT.md`
- Directory prefixes: `memory/`, `duties/`

---

## File Semantics

### Identity: AGENT.md / PROJECT.md

Root identity files. `AGENT.md` mirrors `CLAUDE.md`. `PROJECT.md` is the project charter.

| File | Contains | Written by | Read by |
|------|----------|-----------|---------|
| `AGENT.md` | Behavioral instructions, targeting, format preferences | User | Agent |
| `PROJECT.md` | Title, type_key, objective, contributors, assembly, delivery | User/Composer/TP | PM, contributors |

### Domain Understanding: thesis.md

The agent's accumulated understanding of its domain. This is what makes reasoning agents improve with tenure.

**Who writes:** Agent (updated after each generation run)
**Who reads:** Agent (loaded in `load_context()`, used as starting point for investigation)
**No Claude Code equivalent.** This is YARNNN's core intelligence primitive.

### Memory: memory/

Topic-scoped persistent memory. Mirrors Claude Code's `.claude/memory/` directory.

**Why a directory, not a single file:** Single `memory.md` grows unbounded. Topic-scoped files let agents compartmentalize knowledge and create memory on any topic they deem worth remembering.

| File | Written by | Contains |
|------|-----------|----------|
| `observations.md` | Agent (via `record_observation()`) | Timestamped review pass observations |
| `preferences.md` | Feedback engine (system) | Learned preferences from user edit patterns |
| `projects.json` | System (scaffold_project) | Project memberships list |
| `project_assessment.md` | PM agent | Layered evaluation: commitment→structure→context→quality→readiness |
| `work_plan.md` | PM agent | Operational plan, intentions, focus areas |
| `{topic}.md` | Agent (via WriteWorkspace) | Agent-determined topic memory |

### Research: working/

Intermediate research notes. Ephemeral within a run lifecycle — agents write here during investigation, read back during generation.

**Distinction from memory/:** Working notes are process artifacts. Memory is distilled knowledge.

### Outputs: outputs/{date}/

Atomic output packages. Each run produces a dated folder containing the output file(s) and a `manifest.json` with metadata.

**Written by:** Agent pipeline (after generation completes)
**Convention:** `{date}` uses ISO-ish format: `2026-03-18T1500`

### Contributions: contributions/{agent_slug}/

Per-agent scoped contribution folders within a project. Agents deposit work here for PM to assess and assemble.

**Written by:** Agent (via `_write_contribution_to_projects()` after each run)
**Read by:** PM (for quality assessment), Assembly pipeline (for composition)

### Briefs: contributions/{agent_slug}/brief.md

PM's steering directive for a specific contributor. Tells the contributor what to focus on, what gaps to address.

**Written by:** PM (via `steer_contributor` action, ADR-121)
**Read by:** Contributor agent (during context gathering)

### User Shared: user_shared/

Ephemeral staging area for user-contributed files (ADR-127).

**Written by:** User (via file upload in Meeting Room or TP chat)
**Read by:** PM (for triage), agents (if relevant)
**Lifecycle:** Ephemeral — 30-day TTL, auto-cleaned

---

## Access Patterns

### Agent → Workspace (via primitives)

| Primitive | Operation | Typical paths |
|-----------|-----------|---------------|
| ReadWorkspace | Read file content | `AGENT.md`, `thesis.md`, `memory/observations.md` |
| WriteWorkspace | Create/overwrite file | `thesis.md`, `memory/{topic}.md`, `working/{topic}.md` |
| SearchWorkspace | Full-text search | Query across all workspace files |
| ListWorkspace | Directory listing | `memory/`, `working/`, `outputs/` |
| QueryKnowledge | Search knowledge base | `/knowledge/` (shared, cross-agent) |

### System → Workspace (via AgentWorkspace / ProjectWorkspace classes)

| Caller | Operation | Path |
|--------|-----------|------|
| `agent_execution.py` | Write output folder | `outputs/{date}/output.md` + `manifest.json` |
| `agent_execution.py` | Write contribution | `/projects/{slug}/contributions/{agent_slug}/` |
| `proactive_review.py` | Append observation | `memory/observations.md` |
| `feedback_distillation.py` | Write preferences | `memory/preferences.md` |
| `scaffold_project()` | Write PROJECT.md | `/projects/{slug}/PROJECT.md` |
| PM agent | Write brief | `/projects/{slug}/contributions/{slug}/brief.md` |
| PM agent | Write project assessment | `/projects/{slug}/memory/project_assessment.md` |
| PM agent | Write work plan | `/projects/{slug}/memory/work_plan.md` |
| Assembly pipeline | Write assembled output | `/projects/{slug}/assembly/{date}/` |
| Cleanup cron | Delete expired ephemeral | `working/`, `user_shared/` (lifecycle=ephemeral, >30d) |

---

## Conventions for New Files

When extending the workspace with new file types:

1. **Use existing directories first.** Don't create new top-level directories unless the content doesn't fit existing folders.
2. **Use `.md` extension.** All workspace content is Markdown. Exception: structured data files (`manifest.json`, `agent-card.json`, `projects.json`).
3. **Use lowercase-kebab-case** for user/agent-created files (`competitive-landscape.md`).
4. **Capitalize identity files** (`AGENT.md`, `PROJECT.md`). These signal "this is an entry point."
5. **Date-stamp temporal content** (`2026-03-11.md` for daily snapshots, `2026-03-18T1500` for output folders).
6. **Prefer folders as boundaries.** New coordination needs → new subfolder convention, not new table.

---

## References

- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR with convention spec
- [ADR-107: Knowledge Filesystem Architecture](../adr/ADR-107-knowledge-filesystem-architecture.md) — `/knowledge/` shared filesystem
- [ADR-108: User Memory Filesystem Migration](../adr/ADR-108-user-memory-filesystem-migration.md) — `/memory/` global user state
- [ADR-116: Agent Identity & Inter-Agent Knowledge](../adr/ADR-116-agent-identity-inter-agent-knowledge.md) — agent discovery, cross-agent reading, agent cards
- [ADR-117: Agent Feedback Substrate](../adr/ADR-117-agent-feedback-substrate.md) — preferences.md, duties, seniority
- [ADR-118: Skills as Capability Layer](../adr/ADR-118-skills-capability-layer.md) — output gateway, rendered files
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — output folders, project folders, version history, lifecycle
- [ADR-120: Project Execution & Work Budget](../adr/ADR-120-project-execution-work-budget.md) — PM, assembly, work budget
- [ADR-121: PM as Intelligence Director](../adr/ADR-121-pm-intelligence-director.md) — contribution briefs, quality assessment
- [ADR-122: Project Type Registry](../adr/ADR-122-project-type-registry.md) — project scaffolding, type_key
- [ADR-123: Project Objective & Ownership](../adr/ADR-123-project-objective-ownership.md) — objective model, work plan
- [ADR-124: Project Meeting Room](../adr/ADR-124-project-meeting-room.md) — project conversation surface
- [ADR-127: User-Shared File Staging](../adr/ADR-127-user-shared-file-staging.md) — `user_shared/` convention
- [Naming Conventions](naming-conventions.md) — broader YARNNN naming system
- [Agent Execution Model](agent-execution-model.md) — how orchestration invokes agents
