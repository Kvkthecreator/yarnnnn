# Architecture: Workspace Conventions

**Status:** Canonical (v3)
**Date:** 2026-03-25
**Related:**
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — folder conventions, lifecycle, versioning
- [ADR-127: User-Shared File Staging](../adr/ADR-127-user-shared-file-staging.md) — `user_shared/` convention
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md) — agents own tasks directly, projects dissolved
- [Naming Conventions](naming-conventions.md) — broader naming system
- [Agent Execution Model](agent-execution-model.md) — how agents interact with workspace

---

## Overview

YARNNN's workspace is a **virtual filesystem of human-readable files** backed by Postgres (`workspace_files` table). Path conventions are the schema. New capabilities extend paths, not database tables.

Four top-level namespaces:

| Namespace | Scope | Owner | Purpose |
|-----------|-------|-------|---------|
| `/workspace/` | User-level | User | Identity + brand (stable context that flows into tasks) |
| `/agents/{slug}/` | Per-agent | Agent + system | WHO — persistent domain identity + memory |
| `/tasks/{slug}/` | Per-task | Agent + system | WHAT — work definition + outputs + run memory |
| `/knowledge/` | Global (shared) | Agents (at delivery) | Shared accumulated content corpus |
| `/memory/` | TP-scoped | TP + extraction cron | TP-accumulated knowledge from conversations |

Additionally, `/user_shared/` serves as ephemeral staging (ADR-127).

### `/workspace/` — User Context

Two canonical files. Read by agents at execution time.

| File | Purpose |
|------|---------|
| `IDENTITY.md` | Who you are (name, role, company, industry, timezone, summary) |
| `BRAND.md` | How outputs look and sound (colors, typography, tone, voice) |

### Agent Categories

Two categories with different data access patterns:

| Category | Examples | Reads external? | Reads internal? |
|----------|----------|-----------------|-----------------|
| **Perception** | briefer, monitor, scout | Yes (platforms, web) | Via search_knowledge |
| **Production** | researcher, drafter, analyst, writer, planner | No | Yes (knowledge, workspace) |

Perception agents bridge external data (platforms, web) into the knowledge layer. Production agents work within the knowledge layer, reading processed knowledge rather than raw external data.

### `/memory/` — TP-Accumulated Knowledge

| File | Purpose |
|------|---------|
| `notes.md` | Standing instructions, observed facts (extracted nightly from conversations) |

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
│   ├── self_assessment.md          # Rolling self-assessment history (ADR-128)
│   │                               # 5 most recent entries, newest first
│   │                               # 4 dimensions: mandate, domain fitness, context currency, output confidence
│   │                               # Seeded at creation with "awaiting first run"
│   ├── directives.md               # Accumulated user directives from chat (ADR-128)
│   │                               # Append-only — agent persists durable guidance via WriteWorkspace
│   │                               # Read by agent on next headless run via load_context()
│   ├── goal.md                     # Assigned goal and milestones
│   ├── state.md                    # Operational state metadata
│   └── {topic}.md                  # Agent-created topic files (unbounded)
│
├── working/                        # Intermediate research (ephemeral scratch)
│   └── {topic}.md                  # Research notes, saved queries, evidence
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

---

## Task Workspace (ADR-138)

Each task is a unit of work assigned to an agent. Tasks define what needs to be done, track run history, and store outputs.

```
/tasks/{slug}/
│
├── TASK.md                         # Work definition: objective, criteria, process, output spec
│                                   # The "what" — defines the recurring or one-shot work
│                                   # Written by: User, TP, Composer
│
├── memory/
│   └── run_log.md                  # Append-only run history
│                                   # Each entry: date, outcome, observations
│                                   # Agent writes after each run — accumulates learning
│
└── outputs/{date}/                 # Dated output folders (same convention as agent outputs)
    ├── output.md                   # Primary text output
    ├── output.html                 # Composed HTML output
    └── manifest.json               # Metadata: sources, delivery status, files
```

### Key Relationships

- **TASK.md** is the work definition — defines what the agent produces, for whom, how often, and to what standard
- **`memory/run_log.md`** is the task's accumulated learning — append-only log of outcomes and observations per run
- **`outputs/{date}/`** is where completed work lands — each run produces a dated folder with output files and manifest

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

**External platform data** (Slack, Notion) stays in `platform_content` table — flat, TTL-managed, sync-pipeline-written. `/knowledge/` is for agent-produced knowledge only.

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
/user_shared/                       # TP-level: global
    {filename}
```

**Purpose:** Ephemeral staging area where users share files with agents. Preserves workspace sovereignty — users contribute to a clearly delineated area, agents decide what gets promoted.

**Lifecycle:** `ephemeral` (30-day TTL). Files are promoted to `knowledge/` or `memory/`, or left to expire.

---

## Manifest Files

Task outputs use `manifest.json` for metadata:

### Task Output Manifest (`outputs/{date}/manifest.json`)

```json
{
  "run_id": "uuid",
  "agent_id": "uuid",
  "task_slug": "weekly-slack-recap",
  "version": 1,
  "role": "briefer",
  "created_at": "2026-03-25T09:00:00Z",
  "status": "active",
  "files": [
    {"path": "output.md", "type": "text/markdown", "role": "primary"},
    {"path": "output.html", "type": "text/html", "role": "composed"},
    {"path": "report.pdf", "type": "application/pdf", "content_url": "s3://...", "role": "rendered"}
  ],
  "sources": ["platform_content references consumed"],
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
- Exact: `AGENT.md`, `thesis.md`, `TASK.md`
- Directory prefixes: `memory/`

---

## File Semantics

### Identity: AGENT.md

Root identity file. Mirrors `CLAUDE.md` — the entry point for an agent's workspace.

| File | Contains | Written by | Read by |
|------|----------|-----------|---------|
| `AGENT.md` | Behavioral instructions, targeting, format preferences | User | Agent |

### Work Definition: TASK.md

The task's work definition — objective, success criteria, process, output specification.

| File | Contains | Written by | Read by |
|------|----------|-----------|---------|
| `TASK.md` | Objective, criteria, process, output spec, cadence, delivery | User/Composer/TP | Agent |

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
| `self_assessment.md` | Agent (post-generation, ADR-128) | Rolling history (5 recent) of mandate/fitness/currency/confidence |
| `directives.md` | Agent-via-chat (WriteWorkspace, ADR-128) | Accumulated user directives from chat |
| `{topic}.md` | Agent (via WriteWorkspace) | Agent-determined topic memory |

### Run Log: memory/run_log.md (task workspace)

Append-only log of task execution outcomes. Each entry records the date, outcome (generate/observe/wait), and key observations from that run.

**Who writes:** Agent pipeline (after each run completes)
**Who reads:** Agent (loaded during next run for continuity)

### Research: working/

Intermediate research notes. Ephemeral within a run lifecycle — agents write here during investigation, read back during generation.

**Distinction from memory/:** Working notes are process artifacts. Memory is distilled knowledge.

### Outputs: outputs/{date}/

Atomic output packages. Each run produces a dated folder containing the output file(s) and a `manifest.json` with metadata.

**Written by:** Agent pipeline (after generation completes)
**Convention:** `{date}` uses ISO-ish format: `2026-03-18T1500`

### User Shared: user_shared/

Ephemeral staging area for user-contributed files (ADR-127).

**Written by:** User (via file upload in TP chat)
**Read by:** Agents (if relevant)
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

### System → Workspace (via AgentWorkspace class)

| Caller | Operation | Path |
|--------|-----------|------|
| `agent_execution.py` | Write output folder | `/tasks/{slug}/outputs/{date}/output.md` + `manifest.json` |
| `agent_execution.py` | Append run log | `/tasks/{slug}/memory/run_log.md` |
| `agent_execution.py` | Append self-assessment (ADR-128) | `memory/self_assessment.md` |
| Agent-via-chat | Persist directive (ADR-128) | `memory/directives.md` |
| `feedback_distillation.py` | Write preferences | `memory/preferences.md` |
| Cleanup cron | Delete expired ephemeral | `working/`, `user_shared/` (lifecycle=ephemeral, >30d) |

---

## Conventions for New Files

When extending the workspace with new file types:

1. **Use existing directories first.** Don't create new top-level directories unless the content doesn't fit existing folders.
2. **Use `.md` extension.** All workspace content is Markdown. Exception: structured data files (`manifest.json`, `agent-card.json`).
3. **Use lowercase-kebab-case** for user/agent-created files (`competitive-landscape.md`).
4. **Capitalize identity files** (`AGENT.md`, `TASK.md`). These signal "this is an entry point."
5. **Date-stamp temporal content** (`2026-03-11.md` for daily snapshots, `2026-03-18T1500` for output folders).
6. **Prefer folders as boundaries.** New coordination needs → new subfolder convention, not new table.

---

## References

- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR with convention spec
- [ADR-107: Knowledge Filesystem Architecture](../adr/ADR-107-knowledge-filesystem-architecture.md) — `/knowledge/` shared filesystem
- [ADR-108: User Memory Filesystem Migration](../adr/ADR-108-user-memory-filesystem-migration.md) — `/memory/` global user state
- [ADR-116: Agent Identity & Inter-Agent Knowledge](../adr/ADR-116-agent-identity-inter-agent-knowledge.md) — agent discovery, cross-agent reading, agent cards
- [ADR-117: Agent Feedback Substrate](../adr/ADR-117-agent-feedback-substrate.md) — preferences.md, feedback distillation
- [ADR-118: Skills as Capability Layer](../adr/ADR-118-skills-capability-layer.md) — output gateway, rendered files
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — output folders, version history, lifecycle
- [ADR-127: User-Shared File Staging](../adr/ADR-127-user-shared-file-staging.md) — `user_shared/` convention
- [ADR-128: Multi-Agent Coherence Protocol](../adr/ADR-128-multi-agent-coherence-protocol.md) — cognitive files, self-assessment
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md) — tasks replace projects, agents own work directly
- [Naming Conventions](naming-conventions.md) — broader YARNNN naming system
- [Agent Execution Model](agent-execution-model.md) — how orchestration invokes agents
