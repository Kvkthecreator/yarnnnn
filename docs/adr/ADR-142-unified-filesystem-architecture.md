# ADR-142: Unified Filesystem Architecture

> **Status**: Proposed
> **Date**: 2026-03-25
> **Authors**: KVK, Claude
> **Supersedes**: ADR-107 (Knowledge Filesystem — `/knowledge/` concept dissolved), ADR-127 (User-Shared File Staging — absorbed into session-scoped uploads)
> **Evolves**: ADR-106 (Workspace Architecture), ADR-119 (Workspace Filesystem Conventions)
> **Requires update**: FOUNDATIONS.md (Axiom 2), CLAUDE.md, workspace-conventions.md, SURFACE-ARCHITECTURE.md

---

## Context

### The problem: three content stores, fragmented awareness

The current system has three separate content stores that should feel like one:

| Store | Table | What's in it | TP sees? | Agents see? |
|-------|-------|-------------|----------|-------------|
| Workspace files | `workspace_files` | Agent workspaces, task outputs, IDENTITY.md | Partial (profile keys) | Own workspace only |
| Documents | `filesystem_documents` + `filesystem_chunks` | User-uploaded PDFs, DOCXs | **No** | **No** (manual search only) |
| Platform content | `platform_content` | Synced Slack/Notion raw data | Connection status only | Via Search primitive |

Additionally, the filesystem has five top-level namespaces (`/workspace/`, `/agents/`, `/tasks/`, `/knowledge/`, `/memory/`) that create false ontological distinctions. A user uploading a PDF doesn't think "is this knowledge or workspace?" — it's just "stuff my team should know."

### Three file-sharing contexts with different lifecycles

User file interactions fall into exactly three categories:

1. **Shared documents** — "Here's our IR deck, use it for investor updates." Permanent reference material. User implies importance. Should trigger inference to update workspace context.

2. **Chat uploads** — "Look at this screenshot, what's wrong?" Ephemeral, session-scoped. Same lifecycle as the chat session (4h TTL). Never persists to workspace. Same architecture for TP chat and task chat.

3. **Platform syncs** — Slack messages, Notion pages. Own lifecycle (14d/90d TTLs). Own sync cadence. Available to agents, deprioritized for TP.

### The `/knowledge/` confusion

`/knowledge/` currently holds distilled platform content (summaries written by platform sync) and agent-produced outputs (via `KnowledgeBase.write()`). But:

- Platform summaries belong with platform data, not in a generic "knowledge" bucket
- Agent outputs already live in `/tasks/{slug}/outputs/` — the `/knowledge/` write is a redundant cross-reference
- The name "knowledge" is vague — users don't think in terms of "knowledge base" vs "workspace"

---

## Decision

### Four filesystem roots (reduced from five)

```
/workspace/                       ← user context + curated documents (PERMANENT)
├── IDENTITY.md                   ← who the user is
├── BRAND.md                      ← output identity
├── CONTEXT.md                    ← inferred context (from documents + onboarding)
├── preferences.md                ← learned preferences (from edit feedback)
├── notes.md                      ← TP-extracted standing instructions
└── documents/                    ← user-uploaded reference material
    ├── ir-deck-march-2026.md     ← extracted text from PDF
    └── product-roadmap.md        ← extracted text from DOCX

/platforms/                       ← distilled platform content (OWN LIFECYCLE)
├── slack/
│   ├── general/2026-03-25.md     ← daily channel summary
│   └── engineering/2026-03-25.md
└── notion/
    └── product-roadmap/2026-03-25.md

/agents/{slug}/                   ← agent identity + memory (PER-AGENT)
├── AGENT.md
├── memory/
│   ├── observations.md
│   ├── preferences.md
│   ├── self_assessment.md
│   └── directives.md
├── working/                      ← ephemeral scratch (24h TTL)
└── history/

/tasks/{slug}/                    ← task definition + outputs (PER-TASK)
├── TASK.md
├── memory/
│   └── run_log.md
└── outputs/{date}/
    ├── output.md
    ├── output.html
    └── manifest.json
```

### What dissolved

| Old | New | Rationale |
|-----|-----|-----------|
| `/knowledge/` | Dissolved | Platform summaries → `/platforms/`. Agent outputs stay in `/tasks/{slug}/outputs/`. No redundant cross-reference. |
| `/memory/` | Merged into `/workspace/` | `notes.md` moves to `/workspace/notes.md`. TP-scoped memory is workspace-level context. |
| `/user_shared/` | Dissolved | Absorbed into session-scoped chat uploads (ephemeral, never written to workspace). |
| `filesystem_documents` table | Dissolved | Upload → extract text → write to `/workspace/documents/{name}.md`. Chunks/embeddings kept in `filesystem_chunks` for search, but canonical content is in workspace_files. |

### Three file-sharing architectures

#### 1. Shared documents (`/workspace/documents/`)

**Upload flow:**
1. User uploads PDF/DOCX/TXT/MD via UI or chat "Upload file" action
2. Backend extracts text (PyPDF2, python-docx, or plain decode)
3. Text written to `/workspace/documents/{slugified-name}.md` as workspace_file
4. Chunks + embeddings written to `filesystem_chunks` (for vector search)
5. Inference triggered: Claude reads document + existing IDENTITY.md → suggests updates to CONTEXT.md
6. TP working memory updated: "You have N uploaded documents: [list]"

**Properties:**
- Permanent (lifecycle='permanent')
- TP-visible in working memory (filename list)
- Searchable by agents via workspace search
- Can trigger context inference (update IDENTITY.md, BRAND.md, CONTEXT.md)

#### 2. Chat uploads (session-scoped)

**Upload flow:**
1. User pastes image / drops file in chat (TP or task-scoped)
2. Images: inline as Claude vision attachments (base64 in message)
3. Documents: extracted text included in current message context
4. Nothing written to workspace filesystem
5. Expires with session (4h inactivity rotation)

**Properties:**
- Ephemeral (session TTL)
- Same architecture for TP chat and task chat
- Never persists to `/workspace/` or `/tasks/`
- "Debug this screenshot" ≠ "Here's our company deck"

**Distinction from shared documents:** The UI makes this clear:
- Plus menu "Upload file" on workfloor → shared document (permanent, triggers inference)
- Paste/drop in chat input → chat upload (ephemeral, session-scoped)
- Plus menu "Upload file" on task page → task-scoped document? Or shared? → **Decision: task page uploads are shared** (they go to `/workspace/documents/`). Chat paste/drop is always ephemeral.

#### 3. Platform content (`/platforms/`)

**Sync flow (unchanged from ADR-077):**
1. Platform sync cron runs per source (channel, page)
2. Raw content → `platform_content` table (with TTLs: Slack 14d, Notion 90d)
3. Distilled summaries → `/platforms/{platform}/{source}/{date}.md` (workspace_files)

**Properties:**
- Own lifecycle (platform-specific TTLs on raw data)
- Distilled summaries in workspace_files have lifecycle='platform'
- Available to agents via search
- Deprioritized for TP — working memory says "Platforms: Slack (synced 2h ago), Notion (synced 1d ago)" but doesn't inject content
- `platform_content` table KEPT (raw data, high-volume, TTL-managed) — not merged into workspace_files

### TP awareness model

Working memory injection (what TP always knows):

```
### Your workspace
- IDENTITY.md: Kevin, Founder at YARNNN (last updated 2d ago)
- BRAND.md: set (last updated 5d ago)
- preferences.md: 3 learned preferences

### Uploaded documents (2)
- ir-deck-march-2026.md (PDF, 487KB, uploaded 2h ago)
- product-roadmap.md (DOCX, 120KB, uploaded 3d ago)
Use Search(scope="workspace") or Read(ref="workspace:documents/ir-deck-march-2026.md") to access.

### Your team (6 agents)
[existing roster display]

### Connected platforms
- Slack: synced 2h ago (5 channels)
- Notion: synced 1d ago (12 pages)
Use Search(scope="platform") to search platform content.
```

### Code changes required

#### Phase 1: Document pipeline → workspace_files

1. **`api/routes/documents.py`**: After upload + text extraction, write extracted text to `/workspace/documents/{slug}.md` via workspace_files (in addition to existing chunk/embed pipeline). `filesystem_documents` table kept for now as metadata index (filename, size, status) but canonical content is workspace_file.

2. **`api/services/working_memory.py`**: Add "Uploaded documents" section. Query workspace_files for `path LIKE '/workspace/documents/%'`. Show filename, type, size, upload date.

3. **`api/services/context_inference.py`**: After document write, trigger inference to suggest CONTEXT.md updates.

#### Phase 2: `/knowledge/` → `/platforms/` migration

4. **`api/services/workspace.py`**: `KnowledgeBase` class → rename to `PlatformKnowledge` or dissolve. Content class paths change: `/knowledge/slack/...` → `/platforms/slack/...`.

5. **`api/workers/platform_worker.py`**: Sync writes distilled summaries to `/platforms/{platform}/{source}/{date}.md` instead of `/knowledge/`.

6. **`api/services/agent_execution.py`** + **`api/services/task_pipeline.py`**: Knowledge write at delivery changes from `/knowledge/{class}/{slug}.md` to `/tasks/{slug}/outputs/` (already happens) — remove the redundant `/knowledge/` cross-write.

7. **`api/services/primitives/workspace.py`**: `QueryKnowledge` scope changes from `/knowledge/` to `/platforms/` + `/workspace/documents/`.

#### Phase 3: `/memory/` merge + cleanup

8. **`api/services/memory.py`**: Nightly extraction writes to `/workspace/notes.md` instead of `/memory/notes.md`.

9. **Existing workspace_files data**: Migration to repath:
   - `/knowledge/*` → `/platforms/*` (for platform content)
   - `/memory/*` → `/workspace/*`
   - `/user_shared/*` → delete (ephemeral, should be expired)

10. **`filesystem_documents` table**: Keep as metadata index for now. Frontend documents list reads from it. Drop in a future cleanup when frontend reads from workspace_files instead.

#### Phase 4: Frontend

11. **Context page sidebar**: Workspace, Agents, Tasks, Platforms, Documents (matches filesystem roots)

12. **Chat upload UX**: Plus menu "Upload file" → shared document pipeline. Paste/drop in chat → session-scoped (existing behavior, no change needed).

---

## Code Impact Inventory

### High impact (structural changes)
- `api/services/workspace.py` — `KnowledgeBase` class (~270 lines): rename/repath to `/platforms/`, dissolve content class map
- `api/routes/knowledge.py` — entire route file (~266 lines): repath or merge into workspace routes
- `api/services/task_pipeline.py` — knowledge write at delivery: remove `/knowledge/` cross-write (outputs already in `/tasks/`)
- `api/services/agent_execution.py` — knowledge write: same removal
- `api/services/documents.py` — add workspace_file write alongside chunk/embed pipeline
- `api/services/working_memory.py` — add uploaded documents section to working memory

### Medium impact (path updates)
- `api/services/memory.py` — `/memory/notes.md` → `/workspace/notes.md` (8 refs)
- `api/services/primitives/workspace.py` — `QueryKnowledge` scope: `/knowledge/` → `/platforms/` + `/workspace/documents/`
- `api/services/primitives/save_memory.py` — path update (2 refs)
- `api/services/primitives/search.py` — document search scope update
- `api/services/primitives/refs.py` — document resolution path
- `api/services/composer.py` — knowledge queries (4 refs)
- `api/routes/memory.py` — path updates (12 refs)
- `api/jobs/unified_scheduler.py` — cleanup cron: `/user_shared/` → remove (3 refs)
- `api/mcp_server/server.py` — knowledge tool (2 refs)
- `web/lib/api/client.ts` — API endpoints for knowledge + memory
- `web/app/(authenticated)/context/page.tsx` — sidebar sections

### Low impact (comments, types, admin)
- `api/routes/admin.py` — admin queries for filesystem_documents stats
- `api/routes/account.py` — deletion paths
- `api/routes/integrations.py`, `api/routes/system.py` — timezone reads from /memory/
- `api/scripts/verify_schema.py` — schema list
- `web/types/index.ts` — type definitions

### Total: ~29 files across backend + frontend

---

## What stays unchanged

- `platform_content` table — raw perception data with TTLs (high-volume, separate from workspace_files)
- `/agents/{slug}/` — agent identity + memory structure
- `/tasks/{slug}/` — task definition + outputs structure
- `workspace_files` table schema — no schema changes needed
- Agent execution context gathering — reads agent workspace + platform search (paths change but interfaces don't)
- Chat session architecture — session-scoped uploads are already inline attachments

---

## Impact on existing ADRs

| ADR | Impact |
|-----|--------|
| ADR-106 (Workspace Architecture) | Evolves — `/knowledge/` dissolved, `/platforms/` added as top-level |
| ADR-107 (Knowledge Filesystem) | **Superseded** — `/knowledge/` concept dissolved |
| ADR-119 (Filesystem Conventions) | Evolves — four roots instead of five, document path convention added |
| ADR-127 (User-Shared Staging) | **Superseded** — `/user_shared/` dissolved into session-scoped uploads |
| ADR-138 (Agents as Work Units) | Compatible — task filesystem unchanged |
| ADR-140 (Workforce Model) | Compatible — agent filesystem unchanged |

---

## FOUNDATIONS.md changes

### Axiom 2: The Perception Substrate Is Recursive — revision

Update three layers of perception:
1. **External perception** — platform sync fills `platform_content` from Slack and Notion, distilled to `/platforms/` workspace files.
2. **User-contributed perception** — uploaded documents in `/workspace/documents/`. Permanent reference material the user explicitly shares. Triggers inference to update workspace context.
3. **Internal perception** — agent outputs in `/tasks/{slug}/outputs/`. Task outputs ARE the accumulated knowledge — no separate knowledge layer.
4. **Reflexive perception** — user feedback, TP observations, extracted notes in `/workspace/notes.md`.

### Derived Principle 2: Workspace is the shared OS — revision

Four filesystem roots: `/workspace/` (user context + curated documents), `/platforms/` (distilled platform content), `/agents/` (identity + memory), `/tasks/` (work + outputs). The filesystem IS the information architecture. New capabilities extend paths, not tables.

---

## Future considerations

### Multi-workspace

Each workspace gets its own filesystem root. `/workspace/` is unambiguous — it's "this workspace's shared context." Multiple workspaces per user would be separate filesystem trees, each with their own `/workspace/`, `/agents/`, `/tasks/`, `/platforms/`.

### Document versioning

When a user re-uploads the same document (e.g., updated IR deck), the old version could be archived to `/workspace/documents/history/` using the same version history convention as agent files (ADR-119).

### Large document handling

For documents exceeding workspace_files content limits, store extracted text in chunks and assemble on read. The `filesystem_chunks` table already handles this — it becomes the backing store for large `/workspace/documents/` files.
