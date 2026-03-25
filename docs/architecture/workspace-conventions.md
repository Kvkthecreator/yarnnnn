# Architecture: Workspace Conventions

**Status:** Canonical (v4 — ADR-142 unified filesystem)
**Date:** 2026-03-25
**Related:**
- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md) — governing ADR
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md) — folder conventions, lifecycle, versioning
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md) — agents own tasks directly
- [ADR-142: Unified Filesystem Architecture](../adr/ADR-142-unified-filesystem-architecture.md) — four roots, document pipeline, /knowledge/ dissolved
- [Naming Conventions](naming-conventions.md) — broader naming system
- [Agent Execution Model](agent-execution-model.md) — how agents interact with workspace

---

## Overview

YARNNN's workspace is a **virtual filesystem of human-readable files** backed by Postgres (`workspace_files` table). Path conventions are the schema. New capabilities extend paths, not database tables.

**Four top-level roots** (ADR-142):

| Root | Scope | Owner | Purpose |
|------|-------|-------|---------|
| `/workspace/` | User-level | User + TP | Identity, preferences, curated documents (PERMANENT) |
| `/platforms/` | Cross-agent | Platform sync | Distilled platform content (OWN LIFECYCLE) |
| `/agents/{slug}/` | Per-agent | Agent + system | WHO — persistent domain identity + memory |
| `/tasks/{slug}/` | Per-task | Agent + system | WHAT — work definition + outputs + run memory |

**Dissolved** (ADR-142): `/knowledge/` (absorbed into `/platforms/` + `/tasks/`), `/memory/` (merged into `/workspace/`), `/user_shared/` (absorbed into session-scoped uploads).

---

## `/workspace/` — User Context + Curated Documents

Everything the workspace "knows" — user identity, learned preferences, and reference material the user explicitly shared.

```
/workspace/
├── IDENTITY.md                    # Who the user is (name, role, company, industry)
├── BRAND.md                       # Output identity (tone, style, visual preferences)
├── CONTEXT.md                     # Inferred context (from documents + onboarding)
├── preferences.md                 # Learned preferences (from user edit feedback)
├── notes.md                       # TP-extracted standing instructions (nightly cron)
└── documents/                     # User-uploaded reference material
    ├── ir-deck-march-2026.md      # Extracted text from uploaded PDF
    └── product-roadmap.md         # Extracted text from uploaded DOCX
```

### Uploaded Documents (`/workspace/documents/`)

When a user uploads a PDF/DOCX/TXT/MD via the "Upload file" action:
1. Backend extracts text
2. Writes to `/workspace/documents/{slugified-name}.md` (permanent)
3. Creates chunks + embeddings in `filesystem_chunks` (for search)
4. Optionally triggers inference to update CONTEXT.md

**TP always knows** about uploaded documents — they're listed in working memory with filenames and upload dates. TP can read them via `Read(ref="workspace:documents/{name}.md")`.

**Distinction from chat uploads:** Pasting/dropping files directly in the chat input creates ephemeral session attachments (inline images, temporary text extraction). These never persist to `/workspace/`. "Upload file" via the plus menu = permanent shared document. Paste in chat = ephemeral session context.

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
│   ├── observations.md            # Timestamped observations from runs
│   ├── preferences.md             # Learned from user edit patterns (ADR-117) — taste
│   ├── self_assessment.md         # Rolling 5-entry self-eval (ADR-128)
│   ├── directives.md              # User guidance from chat (ADR-128)
│   ├── methodology-outputs.md     # How to produce deliverables (ADR-143) — craft
│   ├── methodology-{topic}.md     # Additional craft knowledge (research, formats)
│   └── {topic}.md                 # Agent-created topic files (unbounded)
├── working/                       # Ephemeral scratch (24h TTL)
└── history/                       # Version archives (ADR-119)
    └── {filename}/v{N}.md
```

### Evolving Files (Auto-Versioned)

Archived to `/history/{filename}/v{N}.md` on overwrite (max 5 versions):
- `AGENT.md`, `thesis.md`, all `memory/*.md`

---

## `/tasks/{slug}/` — Task Definition + Outputs

Each task's work definition, execution history, and output artifacts.

```
/tasks/{slug}/
├── TASK.md                        # Work definition: objective, criteria, process
├── memory/
│   └── run_log.md                 # Append-only: date, outcome, confidence, criteria eval
└── outputs/{date}/
    ├── output.md                  # Primary text output
    ├── output.html                # Composed HTML output
    └── manifest.json              # Metadata: sources, delivery status, files
```

---

## Three File-Sharing Contexts

| Context | Example | Lifecycle | Stored where | TP sees? |
|---------|---------|-----------|--------------|----------|
| **Shared document** | "Here's our IR deck" | Permanent | `/workspace/documents/` | Yes — file list in working memory |
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
| `permanent` | User-curated, never auto-cleaned | `/workspace/documents/` uploads |
| `ephemeral` | Temporary — auto-cleaned after TTL | `/working/` (24h) |
| `platform` | Platform-synced — own retention rules | `/platforms/` content |
| `delivered` | Output that has been delivered | Delivery pipeline |
| `archived` | Previous version kept for history | Version archival |

---

## Conventions for New Files

1. **Use existing directories first.** Don't create new top-level roots.
2. **Use `.md` extension.** All content is Markdown. Exception: `manifest.json`, `agent-card.json`.
3. **Use lowercase-kebab-case** for user/agent-created files.
4. **Capitalize identity files** (`AGENT.md`, `TASK.md`, `IDENTITY.md`).
5. **Date-stamp temporal content** (`2026-03-25.md` for daily, `2026-03-25T1500` for output folders).
6. **Prefer folders as boundaries.** New coordination needs → new subfolder, not new table.

---

## References

- [ADR-106: Agent Workspace Architecture](../adr/ADR-106-agent-workspace-architecture.md)
- [ADR-119: Workspace Filesystem Architecture](../adr/ADR-119-workspace-filesystem-architecture.md)
- [ADR-138: Agents as Work Units](../adr/ADR-138-agents-as-work-units.md)
- [ADR-142: Unified Filesystem Architecture](../adr/ADR-142-unified-filesystem-architecture.md)
- [ADR-128: Multi-Agent Coherence Protocol](../adr/ADR-128-multi-agent-coherence-protocol.md)

---

## Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-03-18 | v1 | Initial — agent workspace, knowledge, memory conventions |
| 2026-03-21 | v2 | ADR-128: cognitive files (self_assessment.md, directives.md) |
| 2026-03-25 | v3 | ADR-138: task workspace, /tasks/{slug}/ added |
| 2026-03-25 | v4 | ADR-142: unified filesystem. Four roots (/workspace/, /platforms/, /agents/, /tasks/). /knowledge/ dissolved into /platforms/ + /tasks/. /memory/ merged into /workspace/. /user_shared/ dissolved into session-scoped uploads. Document upload pipeline to /workspace/documents/. Three file-sharing contexts (shared docs, chat uploads, platform syncs). |
| 2026-03-25 | v5 | ADR-143: methodology files in memory/ (methodology-outputs.md, methodology-research.md, methodology-formats.md). Taste (preferences.md) vs craft (methodology-*.md) distinction. Seeded from AGENT_TYPES registry at creation. |
