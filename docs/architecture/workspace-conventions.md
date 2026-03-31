# Architecture: Workspace Conventions

**Status:** Canonical (v8 — ADR-152 unified directory registry)
**Date:** 2026-03-31
**Related:**
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — folder conventions, lifecycle, versioning
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md) — agents own tasks directly
- [ADR-142: Unified Filesystem Architecture](../adr/ADR-142-unified-filesystem-architecture.md) — four roots, document pipeline, /knowledge/ dissolved
- ADR-149 — DELIVERABLE.md quality contract, task memory files, agent reflections
- ADR-151 — /workspace/context/ accumulated context domains, domain registry
- ADR-152 — Unified directory registry, documents/ → uploads/ rename, output categories
- [Naming Conventions](naming-conventions.md) — broader naming system
- [Agent Execution Model](agent-execution-model.md) — how agents interact with workspace

---

## Overview

YARNNN's workspace is a **virtual filesystem of human-readable files** backed by Postgres (`workspace_files` table). Path conventions are the schema. New capabilities extend paths, not database tables.

**Four top-level roots** (ADR-142):

| Root | Scope | Owner | Purpose |
|------|-------|-------|---------|
| `/workspace/` | User-level | User + TP | Identity, preferences, user uploads, accumulated context domains, promoted outputs (PERMANENT) |
| `/platforms/` | Cross-agent | Platform sync | Distilled platform content (OWN LIFECYCLE) |
| `/agents/{slug}/` | Per-agent | Agent + system | WHO — persistent domain identity + memory |
| `/tasks/{slug}/` | Per-task | Agent + system | WHAT — work definition + quality contract + outputs + run memory |

**Dissolved** (ADR-142): `/knowledge/` (absorbed into `/platforms/` + `/tasks/`), `/memory/` (merged into `/workspace/`), `/user_shared/` (absorbed into session-scoped uploads).

---

## `/workspace/` — User Context + Uploads + Accumulated Context + Outputs

Everything the workspace "knows" — user identity, learned preferences, reference material the user explicitly uploaded, accumulated context domains built up by agents over time, and promoted agent outputs.

> **ADR-152:** `documents/` renamed to `uploads/` for clarity. "documents" was ambiguous (user uploads vs system-produced). "uploads" = user-contributed. "outputs" = system-produced.

```
/workspace/
├── IDENTITY.md                    # Who the user is (name, role, company, industry)
├── BRAND.md                       # Output identity (tone, style, visual preferences)
├── CONTEXT.md                     # Inferred context (from documents + onboarding)
├── preferences.md                 # Learned preferences (from user edit feedback)
├── notes.md                       # TP-extracted standing instructions (nightly cron)
├── uploads/                       # User-uploaded reference material (was: documents/)
│   ├── ir-deck-march-2026.md      # Extracted text from uploaded PDF
│   └── product-roadmap.md         # Extracted text from uploaded DOCX
├── outputs/                       # Agent-produced deliverables promoted from tasks
│   ├── reports/                   # Reports, analyses, digests
│   ├── briefs/                    # Briefs, summaries, prep docs
│   └── content/                   # Blog drafts, comms, launch material
└── context/                       # Accumulated context domains (ADR-151)
    ├── competitors/               # Per-competitor entity folders
    │   ├── _landscape.md          # Cross-entity synthesis
    │   └── {company-slug}/
    │       ├── profile.md, signals.md, product.md, strategy.md
    │       └── assets/
    ├── market/
    ├── relationships/
    ├── projects/
    ├── content/
    ├── signals/                   # Cross-domain temporal signal log
    └── assets/                    # Cross-domain shared assets
```

### User Uploads (`/workspace/uploads/`)

When a user uploads a PDF/DOCX/TXT/MD via the "Upload file" action:
1. Backend extracts text
2. Writes to `/workspace/uploads/{slugified-name}.md` (permanent)
3. Creates chunks + embeddings in `filesystem_chunks` (for search)
4. Optionally triggers inference to update CONTEXT.md

**TP always knows** about uploaded documents — they're listed in working memory with filenames and upload dates. TP can read them via `Read(ref="workspace:uploads/{name}.md")`.

**Distinction from chat uploads:** Pasting/dropping files directly in the chat input creates ephemeral session attachments (inline images, temporary text extraction). These never persist to `/workspace/`. "Upload file" via the plus menu = permanent shared document. Paste in chat = ephemeral session context.

### Promoted Outputs (`/workspace/outputs/`)

Agent-produced deliverables promoted from tasks. Organized by output category:
- `reports/` — Reports, analyses, digests, intel briefs
- `briefs/` — Summaries, prep docs, stakeholder updates
- `content/` — Blog drafts, launch material, communications

Output categories are defined in the directory registry (`WORKSPACE_DIRECTORIES` in `directory_registry.py`). Tasks declare their `output_category` — when outputs are promoted to workspace scope, they land in the corresponding subfolder.

### Accumulated Context Domains (`/workspace/context/`) — ADR-151

Workspace-scoped accumulated context that agents build up over time. Unlike task outputs (which live in `/tasks/{slug}/outputs/`), context domains are **shared across all tasks and agents** — any agent can read from them, and agents write to them as they discover and synthesize information.

A **domain registry** governs the structure. Each domain (competitors, market, relationships, etc.) has its own folder with domain-specific conventions for entity subfolders, synthesis files, and assets. Cross-entity synthesis files use the `_landscape.md` naming convention (underscore prefix = synthesized, not entity-specific).

**Key properties:**
- **Workspace-scoped, not task-scoped** — accumulated context benefits all agents, not just one task
- **Domain registry governs structure** — new domains added to the registry, not ad-hoc folders
- **Entity folders within domains** — e.g., `/workspace/context/competitors/{company-slug}/` with standardized files (profile.md, signals.md, etc.)
- **Cross-domain files** — `signals/` for temporal signal logs, `assets/` for shared binary/visual assets

---

## `/platforms/` — Distilled Platform Content

Summaries written by the platform sync pipeline. Each platform gets a subfolder, each source gets dated files.

```
/platforms/
├── slack/
│   ├── general/
│   │   └── 2026-03-25.md          # Daily channel summary
│   └── engineering/
│       └── 2026-03-25.md
└── notion/
    └── product-roadmap/
        └── 2026-03-25.md
```

**Own lifecycle:** Platform content has retention rules (Slack 14d, Notion 90d) separate from workspace files. Raw data stays in `platform_content` table (high-volume, TTL-managed). `/platforms/` holds distilled summaries only.

**Deprioritized for TP:** Working memory says "Slack synced 2h ago (5 channels)" — not full content. Agents search via `Search(scope="platform")`.

**Not nested under `/workspace/`:** Platform data has fundamentally different lifecycle, volume, and metadata characteristics. Keeping it as a separate root maintains data handling clarity.

---

## `/agents/{slug}/` — Agent Identity + Memory

Each agent's persistent workspace. Identity, accumulated domain knowledge, and developmental state.

```
/agents/{slug}/
├── AGENT.md                       # Identity + behavioral instructions (like CLAUDE.md)
├── thesis.md                      # Self-evolving domain understanding
├── memory/
│   ├── feedback.md                # Rolling 10-entry feedback history (ADR-143) — TP writes, agent reads
│   ├── reflections.md             # Rolling 5-entry agent self-reflection (ADR-149) — agent writes, TP reads
│   ├── playbook-outputs.md         # How to produce deliverables (ADR-143) — craft
│   ├── playbook-{topic}.md         # Additional craft knowledge (research, formats)
│   └── goal.md                    # Current goal and milestones
├── working/                       # Ephemeral scratch (24h TTL)
└── history/                       # Version archives (ADR-119)
    └── {filename}/v{N}.md
```

### Evolving Files (Auto-Versioned)

Archived to `/history/{filename}/v{N}.md` on overwrite (max 5 versions):
- `AGENT.md`, `thesis.md`, all `memory/*.md`

---

## `/tasks/{slug}/` — Task Definition + Outputs

Each task's work definition, quality contract, execution history, and output artifacts.

```
/tasks/{slug}/
├── TASK.md                        # Charter: objective, process, type_key, mode
├── DELIVERABLE.md                 # Quality contract: output spec + assets + inferred preferences (ADR-149)
├── memory/
│   ├── run_log.md                 # Execution history (append-only)
│   ├── feedback.md                # Task-level feedback: user corrections + TP evaluations (ADR-149)
│   └── steering.md                # TP management notes for next cycle (ADR-149)
├── outputs/
│   ├── latest/                    # Current deliverable (mode-dependent semantics)
│   │   ├── output.md
│   │   ├── output.html
│   │   └── manifest.json
│   └── {date}/                    # Run history (timestamped folders)
│       ├── output.md
│       ├── output.html
│       └── manifest.json
└── working/                       # Ephemeral scratch (24h TTL)
```

Tasks do NOT have `context/` or `knowledge/` folders — accumulated context lives at `/workspace/context/` (ADR-151). Tasks are thin work units: charter, quality contract, memory, outputs, scratch.

### Mode-Dependent `outputs/` Semantics

The meaning of `latest/` and `{date}/` folders varies by task mode:

| Mode | `latest/` | `{date}/` folders |
|------|-----------|-------------------|
| **Recurring** | Points to most recent run | Accumulate (one per cycle) |
| **Goal** | IS the evolving deliverable (revised each cycle) | Revision snapshots |
| **Reactive** | Last trigger output | Sparse archive |

---

## Three File-Sharing Contexts

| Context | Example | Lifecycle | Stored where | TP sees? |
|---------|---------|-----------|--------------|----------|
| **Shared document** | "Here's our IR deck" | Permanent | `/workspace/uploads/` | Yes — file list in working memory |
| **Chat upload** | "Look at this screenshot" | Session TTL (4h) | Inline session attachment | Yes — current conversation only |
| **Platform sync** | Slack daily digest | Platform TTL | `/platforms/` + `platform_content` | Deprioritized |

---

## TP Awareness Model

Working memory injection at session start:

```
### Your workspace
- IDENTITY.md: Kevin, Founder at YARNNN
- BRAND.md: set
- preferences.md: 3 learned preferences

### Uploaded documents (2)
- ir-deck-march-2026.md (PDF, 487KB, uploaded 2h ago)
- product-roadmap.md (DOCX, 120KB, uploaded 3d ago)

### Your team (6 agents)
- Research Agent, Content Agent, Marketing Agent, CRM Agent, Slack Bot, Notion Bot

### Connected platforms
- Slack: synced 2h ago (5 channels)
- Notion: synced 1d ago (12 pages)
```

---

## Manifest Files

Task outputs use `manifest.json` for metadata:

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
    {"path": "output.html", "type": "text/html", "role": "composed"}
  ],
  "sources": [],
  "feedback": {},
  "delivery": {"channel": "email", "sent_at": null, "status": "pending"}
}
```

---

## Lifecycle & Versioning (ADR-119)

### `lifecycle` Column

| Value | Meaning | Set by |
|-------|---------|--------|
| `active` | Normal operational file | Default |
| `permanent` | User-curated, never auto-cleaned | `/workspace/uploads/` uploads |
| `ephemeral` | Temporary — auto-cleaned after TTL | `/working/` (24h) |
| `platform` | Platform-synced — own retention rules | `/platforms/` content |
| `delivered` | Output that has been delivered | Delivery pipeline |
| `archived` | Previous version kept for history | Version archival |

---

## Conventions for New Files

1. **Use existing directories first.** Don't create new top-level roots.
2. **Use `.md` extension.** All content is Markdown. Exception: `manifest.json`, `agent-card.json`.
3. **Use lowercase-kebab-case** for user/agent-created files.
4. **Capitalize identity files** (`AGENT.md`, `TASK.md`, `DELIVERABLE.md`, `IDENTITY.md`).
5. **Date-stamp temporal content** (`2026-03-25.md` for daily, `2026-03-25T1500` for output folders).
6. **Prefer folders as boundaries.** New coordination needs → new subfolder, not new table.
7. **Accumulated context goes in `/workspace/context/`.** New context domains must be added to the domain registry (ADR-151). Don't create ad-hoc context folders under `/tasks/` or `/agents/`.

---

## References

- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md)
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md)
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md)
- [ADR-142: Unified Filesystem Architecture](../adr/ADR-142-unified-filesystem-architecture.md)
- [ADR-128: Multi-Agent Coherence Protocol](../adr/ADR-128-multi-agent-coherence-protocol.md)
- ADR-149 — DELIVERABLE.md, task memory files (feedback.md, steering.md), agent reflections
- ADR-151 — /workspace/context/ accumulated context domains, domain registry

---

## Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-18 | v1 | Initial — agent workspace, knowledge, memory conventions |
| 2026-03-21 | v2 | ADR-128: cognitive files (self_assessment.md, directives.md) |
| 2026-03-25 | v3 | ADR-138: task workspace, /tasks/{slug}/ added |
| 2026-03-25 | v4 | ADR-142: unified filesystem. Four roots (/workspace/, /platforms/, /agents/, /tasks/). /knowledge/ dissolved into /platforms/ + /tasks/. /memory/ merged into /workspace/. /user_shared/ dissolved into session-scoped uploads. Document upload pipeline to /workspace/documents/. Three file-sharing contexts (shared docs, chat uploads, platform syncs). |
| 2026-03-25 | v5 | ADR-143: playbook files + feedback consolidation. 3 agent memory files: feedback.md (rolling 10, TP writes), self_assessment.md (rolling 5, agent writes), playbook-*.md (craft). TP gets playbook-orchestration.md at /workspace/. BRAND.md injected into all agent execution contexts. Deleted: preferences.md, observations.md, supervisor-notes.md, review-log.md, directives.md. Renamed: methodology-* → playbook-*. |
| 2026-03-31 | v6 | ADR-149: DELIVERABLE.md quality contract added to /tasks/{slug}/. Task memory expanded: feedback.md (user corrections + TP evaluations), steering.md (TP management notes). outputs/ restructured with latest/ + {date}/ folders and mode-dependent semantics. Agent self_assessment.md renamed to reflections.md. |
| 2026-03-31 | v7 | ADR-151: /workspace/context/ replaces /workspace/knowledge/. Accumulated context is workspace-scoped, shared across tasks. Domain registry governs structure. Task knowledge/ folder removed. |
| 2026-03-31 | v8 | ADR-152: Unified directory registry. /workspace/documents/ renamed to /workspace/uploads/ (clarity: user-contributed vs system-produced). /workspace/outputs/ added (reports/, briefs/, content/ — promoted agent deliverables). Domain registry → directory registry (WORKSPACE_DIRECTORIES in directory_registry.py). |
