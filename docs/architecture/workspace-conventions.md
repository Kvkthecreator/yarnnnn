# Architecture: Workspace Conventions

**Status:** Canonical (v12 — ADR-156 naming convention)
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

**Three top-level roots** (ADR-142, updated ADR-153):

| Root | Scope | Owner | Purpose |
|------|-------|-------|---------|
| `/workspace/` | User-level | User + TP | Identity, preferences, user uploads, accumulated context domains, promoted outputs (PERMANENT) |
| `/agents/{slug}/` | Per-agent | Agent + system | WHO — persistent domain identity + memory |
| `/tasks/{slug}/` | Per-task | Agent + system | WHAT — work definition + quality contract + outputs + run memory |

**Dissolved** (ADR-142, ADR-153): `/knowledge/` (absorbed into `/platforms/` + `/tasks/`), `/memory/` (merged into `/workspace/`), `/user_shared/` (absorbed into session-scoped uploads), `/platforms/` (ADR-153: platform data now flows through tracking tasks into `/workspace/context/` domains).

---

## `/workspace/` — User Context + Uploads + Accumulated Context + Outputs

Everything the workspace "knows" — user identity, learned preferences, reference material the user explicitly uploaded, accumulated context domains built up by agents over time, and promoted agent outputs.

> **ADR-152:** `documents/` renamed to `uploads/` for clarity. "documents" was ambiguous (user uploads vs system-produced). "uploads" = user-contributed. "outputs" = system-produced.

```
/workspace/
├── IDENTITY.md                    # Who the user is (name, role, company, industry)
├── BRAND.md                       # Output identity (tone, style, visual preferences)
├── AWARENESS.md                   # TP's situational notes (shift handoff, cross-session)
├── _playbook.md                   # System: TP orchestration playbook (hidden)
├── _style.md                      # System: inferred style from edit patterns (hidden)
├── notes.md                       # TP-written facts and standing instructions
├── uploads/                       # User-uploaded reference material (was: documents/)
│   ├── ir-deck-march-2026.md      # Extracted text from uploaded PDF
│   └── product-roadmap.md         # Extracted text from uploaded DOCX
├── outputs/                       # Agent-produced deliverables promoted from tasks
│   ├── reports/                   # Reports, analyses, digests
│   ├── briefs/                    # Briefs, summaries, prep docs
│   └── content/                   # Blog drafts, comms, launch material
└── context/                       # Accumulated context domains (ADR-151)
    ├── competitors/               # Per-competitor entity folders
    │   ├── _tracker.md            # System: entity registry + freshness (hidden)
    │   ├── landscape.md           # Content: cross-entity synthesis (agent-written, visible)
    │   └── {company-slug}/
    │       ├── profile.md, signals.md, product.md, strategy.md
    │       └── assets/
    ├── market/                    # Same pattern: _tracker.md + overview.md + entities
    ├── relationships/
    ├── projects/
    ├── content/
    ├── signals/                   # Cross-domain temporal signal log (no tracker)
    └── assets/                    # Cross-domain shared assets
```

### Agent OS Visibility (ADR-154)

The workfloor explorer preserves structured visibility rules, but presents them as a single filesystem-style surface. The left pane synthesizes a root with four browseable folders: `Tasks`, `Domains`, `Uploads`, and `Settings`. Users navigate one hierarchy, not separate domain cards vs. upload lists vs. settings panels.

Visibility rules:

### File Naming Convention (ADR-156)

Three tiers, one glance tells you ownership:

| Convention | Meaning | Writer | Visible in explorer? |
|---|---|---|---|
| **UPPERCASE.md** | Charter/identity — defines who/what/why | User + TP | Yes |
| **lowercase.md** | Content — user knowledge, notes, feedback, synthesis | User + TP + agents | Yes |
| **_prefixed.md** | System infrastructure — derived, pipeline-managed | Pipeline/system | **No** (hidden) |

**Frontend rule:** Any file whose name starts with `_` is hidden from the explorer. One rule, no exceptions.

| File/Directory | Visible? | Where shown |
|---|---|---|
| Task folders + task outputs (`/tasks/{slug}/...`) | Yes | `Tasks/` explorer subtree |
| Context domain entity files (`{entity}/profile.md`, `signals.md`, etc.) | Yes | `Domains/` explorer subtree |
| Domain synthesis files (`landscape.md`, `overview.md`, etc.) | Yes | Domain folder root |
| Uploads (`/workspace/uploads/*`) | Yes | `Uploads/` explorer subtree |
| IDENTITY.md, BRAND.md, AWARENESS.md, notes.md | Yes | `Settings/` explorer subtree |
| `_tracker.md`, `_style.md`, `_playbook.md`, `_awareness.md`, `_run_log.md` | No | System infrastructure (hidden) |
| `/agents/` (all files) | No | Agent identity = system |
| `/workspace/context/signals/` root | No | Temporal log, not user-browseable |

### User Uploads (`/workspace/uploads/`)

When a user uploads a PDF/DOCX/TXT/MD via the "Upload file" action:
1. Backend extracts text
2. Writes to `/workspace/uploads/{slugified-name}.md` (permanent)
3. Creates chunks + embeddings in `filesystem_chunks` (for search)
4. Optionally triggers inference to update CONTEXT.md

**TP always knows** about uploaded documents — they're listed in working memory with filenames and upload dates. TP can read them via `Read(ref="workspace:uploads/{name}.md")`.

**Distinction from chat uploads:** Pasting/dropping files directly in the chat input creates ephemeral session attachments (inline images, temporary text extraction). These never persist to `/workspace/`. "Upload file" via the plus menu = permanent shared document. Paste in chat = ephemeral session context.

### Outputs — Tasks Own Their Outputs (ADR-154)

> **`/workspace/outputs/` directory REMOVED (ADR-154).** Tasks own their outputs directly at `/tasks/{slug}/outputs/`. No promotion layer, no output categories. Users access outputs by browsing task folders in the explorer. This eliminates the dual-location problem and the never-implemented promotion pipeline.

### Accumulated Context Domains (`/workspace/context/`) — ADR-151

Workspace-scoped accumulated context that agents build up over time. Unlike task outputs (which live in `/tasks/{slug}/outputs/`), context domains are **shared across all tasks and agents** — any agent can read from them, and agents write to them as they discover and synthesize information.

A **domain registry** governs the structure. Each domain (competitors, market, relationships, etc.) has its own folder with domain-specific conventions for entity subfolders, synthesis files, and assets. Cross-entity synthesis files use the `_landscape.md` naming convention (underscore prefix = synthesized, not entity-specific).

**Key properties:**
- **Workspace-scoped, not task-scoped** — accumulated context benefits all agents, not just one task
- **Domain registry governs structure** — new domains added to the registry, not ad-hoc folders
- **Entity folders within domains** — e.g., `/workspace/context/competitors/{company-slug}/` with standardized files (profile.md, signals.md, etc.)
- **Cross-domain files** — `signals/` for temporal signal logs, `assets/` for shared binary/visual assets

**Entity source tagging** (ADR-155): Entity files carry a source tag in an HTML comment on line 1:
- `<!-- source: inferred | date: YYYY-MM-DD -->` — TP-inferred from identity, not yet researched. Sections marked `[Needs research]`.
- `<!-- source: researched -->` — agent-validated via WebSearch/platform data. Full content.
- No tag — manually created or pre-ADR-155 entity.

Inferred stubs are created by the TP via `ScaffoldDomains` primitive during onboarding. Research tasks validate and upgrade them. Re-scaffolding is idempotent: researched entities are never overwritten, inferred stubs are replaced.

---

## `/platforms/` — DEPRECATED (ADR-153)

> **Deprecated.** Platform data now flows through tracking tasks into `/workspace/context/` domains. The `/platforms/` root is no longer written to or read from. Agents call platform APIs (Slack, Notion, GitHub) live during task execution and write structured context to `/workspace/context/` domains. Connect a platform, create a monitoring task, and accumulated context builds organically.

---

## `/agents/{slug}/` — WHO: Agent Identity Only

Each agent's persistent identity. ADR-154: thinned to identity + methodology only. Execution state (reflections, feedback, working notes) lives on tasks. Domain knowledge lives in `/workspace/context/`.

```
/agents/{slug}/
├── AGENT.md                       # Identity + behavioral instructions (like CLAUDE.md)
└── memory/
    ├── playbook-outputs.md        # How to produce deliverables (ADR-143) — craft methodology
    └── playbook-{topic}.md        # Additional craft knowledge (research, formats)
```

**Dissolved files (ADR-154):** `thesis.md` (redundant with domain synthesis files), `memory/reflections.md` (→ task awareness.md), `memory/feedback.md` (→ task feedback.md), `memory/tasks.json` (dead), `memory/goal.md` (dead), `memory/observations.md` (dead), `memory/review-log.md` (dead), `memory/created-agents.md` (dead), `memory/state.md` (dead), `working/` (→ task working/).

---

## `/tasks/{slug}/` — HOW: Work Order + Execution State + Outputs

Each task's work definition, quality contract, cycle-to-cycle awareness, execution history, and output artifacts.

```
/tasks/{slug}/
├── TASK.md                        # Charter: objective, process, type_key, mode
├── DELIVERABLE.md                 # Quality contract: output spec + assets + inferred preferences (ADR-149)
├── awareness.md                   # Cycle-to-cycle execution state (ADR-154, pipeline-maintained)
├── memory/
│   ├── run_log.md                 # Execution history (append-only audit trail)
│   ├── feedback.md                # User corrections + TP evaluations (ADR-149) — sole feedback location
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

## Two File-Sharing Contexts

| Context | Example | Lifecycle | Stored where | TP sees? |
|---------|---------|-----------|--------------|----------|
| **Shared document** | "Here's our IR deck" | Permanent | `/workspace/uploads/` | Yes — file list in working memory |
| **Chat upload** | "Look at this screenshot" | Session TTL (4h) | Inline session attachment | Yes — current conversation only |

---

## TP Awareness Model

TP's understanding of the workspace comes from three layers. Full architecture documented in [TP-DESIGN-PRINCIPLES.md](TP-DESIGN-PRINCIPLES.md#awareness-architecture).

**Layer 1: Ground truth** — `context_readiness` dict computed fresh at session start from actual workspace state. Identity/brand richness, task count, document count, domain health. Disposable — dies at session end.

**Layer 2: Workspace files** — IDENTITY.md (user facts), BRAND.md (output style), AWARENESS.md (TP's situational notes), notes.md (standing instructions), preferences.md (output preferences). Persistent, written by TP and system hooks. AWARENESS.md is TP-specific — its shift handoff for cross-session continuity.

**Layer 3: Behavioral guidance** — `CONTEXT_AWARENESS` prompt (always injected). Priorities, judgment rules, task catalog.

**Task-level awareness** (headless, ADR-154) — pipeline writes `awareness.md` to task workspace after execution. Contains: last cycle metadata, entities touched, domain health, next cycle focus. Agent reads on next run via `gather_task_context()`. Domain `_tracker.md` also injected for context tasks.

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
| `platform` | DEPRECATED (ADR-153) — was platform-synced content | Legacy `/platforms/` content |
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
| 2026-03-31 | v9 | ADR-153: platform_content sunset. /platforms/ deprecated — platform data flows through tracking tasks into /workspace/context/ domains. Four roots → three roots. Platform sync file-sharing context removed. |
| 2026-04-01 | v10 | TP Awareness Model hardened — three-layer architecture (ground truth, workspace files, behavioral guidance), agent-level hooks documented. Cross-ref TP-DESIGN-PRINCIPLES.md. AWARENESS.md added to /workspace/ as TP's persistent situational notes. |
| 2026-04-01 | v11 | ADR-154: Execution boundary reform. Agent workspace thinned to identity only (AGENT.md + playbooks). Dissolved: thesis.md, reflections.md, feedback.md, working/, 6 dead files. Task awareness.md added (cycle-to-cycle state). Domain _tracker.md added (entity registry, pipeline-maintained). context_reads fixed for track-relationships/track-projects. Tool round budget increased. |
