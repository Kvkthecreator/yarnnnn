# ADR-127: User-Shared File Staging Area

**Status:** Proposed
**Date:** 2026-03-20
**Related:**
- [ADR-106: Agent Workspace Architecture](ADR-106-agent-workspace-architecture.md) — governing workspace model
- [ADR-119: Workspace Filesystem Architecture](ADR-119-workspace-filesystem-architecture.md) — folder conventions, lifecycle column
- [ADR-124: Project Meeting Room](ADR-124-project-meeting-room.md) — user↔agent conversation surface
- [ADR-123: Project Objective & Ownership](ADR-123-project-objective-ownership.md) — workspace sovereignty model
- [Workspace Conventions](../architecture/workspace-conventions.md) — canonical path reference

---

## Context

YARNNN has three document tiers:

1. **`filesystem_documents` / `filesystem_chunks`** — user-uploaded files (PDF, DOCX, TXT, MD). TP-searchable via Search primitive. No project scoping. No update/replace API. Write-once.
2. **`workspace_files`** — agent workspaces. Path-based, lifecycle-tracked, version-controlled. Agents write, users read + give feedback.
3. **`/knowledge/`** — shared knowledge base. Agent-produced, delivered outputs only.

**The gap:** Users have no fluid way to share files with projects or agents. The only upload path is `POST /documents/upload` (25MB, 4 formats), which lands in `filesystem_documents` — a flat, unscoped, TP-only search pool. There is no:

- Path from user documents to project agents
- File attachment in Meeting Room conversations
- Way for users to share updated versions of files they previously shared
- Way for PM to triage user-contributed files into the right workspace location

Meanwhile, workspace sovereignty (FOUNDATIONS.md Axiom 3) dictates that agents own their workspace. Users don't overwrite agent files directly — the edit→distill→learn pipeline is the feedback mechanism. But users need to *contribute* files (briefs, data, reference docs, edited outputs) without breaking this model.

---

## Decision

Introduce **`user_shared/`** — an ephemeral staging area where users can freely share files. Agents (specifically PM) triage shared files by promoting them to the appropriate workspace location or letting them expire.

### Convention

```
/projects/{slug}/user_shared/       # Project-level: user shares files with a project
    {filename}                       # Any file the user contributes
    {filename}                       # Supports multiple files

/user_shared/                        # TP-level: user shares files in Orchestrator context
    {filename}                       # Global, not project-scoped
```

**Same name at both levels.** Whether a user shares a file in a Meeting Room conversation or in TP chat, it goes to `user_shared/`. The scope differs (project vs global), the convention is identical.

### Lifecycle

- Files in `user_shared/` are written with `lifecycle = 'ephemeral'`
- **30-day TTL** — files auto-expire if not promoted
- PM (or TP for global) triages files:
  - **Promote to contributions**: Copy to `/projects/{slug}/contributions/{agent_slug}/` → `lifecycle = 'active'`
  - **Promote to knowledge**: Copy to `/knowledge/{class}/` → `lifecycle = 'active'`
  - **Promote to agent memory**: Copy to `/agents/{slug}/memory/` → `lifecycle = 'active'`
  - **Let expire**: File stays in `user_shared/`, cleaned up after 30 days
- Original in `user_shared/` is **not deleted** on promotion — it serves as provenance record until TTL expiry

### Version Handling

When a user shares a file with the same name as an existing file in `user_shared/`:
- **Overwrite** the existing file (same path = same file, standard workspace write semantics)
- The `version` column increments automatically
- Previous version archived to `/history/` per ADR-119 Phase 3 convention

When a user shares an updated version of a file that was already promoted:
- PM detects the relationship (same filename, similar content) and updates the promoted location
- The `user_shared/` copy is the latest; the promoted copy gets overwritten with the new version

### Cleanup

A **cleanup cron** sweeps `user_shared/` (and all other `lifecycle = 'ephemeral'` files) on a configurable schedule:

```sql
DELETE FROM workspace_files
WHERE lifecycle = 'ephemeral'
AND updated_at < NOW() - INTERVAL '30 days';
```

This also cleans up `/working/` scratch files that have accumulated beyond their useful life.

**Implementation note:** The `lifecycle = 'ephemeral'` index already exists (ADR-119). The cleanup cron does not — it must be added to `unified_scheduler.py` or run as a periodic maintenance task.

---

## Workspace Sovereignty Preservation

This convention deliberately preserves the workspace sovereignty model:

1. **Users write to `user_shared/`** — a clearly delineated staging area, not agent workspace proper
2. **Agents (PM) decide** what gets promoted and where — the agent controls its own workspace
3. **Promoted files** follow normal workspace write semantics (versioned, lifecycle-tracked)
4. **Expiry is the default** — files that aren't promoted are assumed non-essential

Users can freely share files without worrying about overwriting agent work. Agents can freely ignore files that aren't relevant. The staging area is the buffer that makes both sides comfortable.

---

## Lifecycle Inference Update

`_infer_lifecycle()` in `workspace.py` must be updated:

```python
def _infer_lifecycle(path: str) -> str:
    if "/working/" in path:
        return "ephemeral"
    if "/user_shared/" in path:
        return "ephemeral"
    return "active"
```

---

## UX Surface

### Meeting Room (Project-Level)

- File attachment button in Meeting Room chat input
- Files uploaded via attachment are written to `/projects/{slug}/user_shared/{filename}`
- PM receives a notification/event in the conversation stream: "User shared {filename}"
- PM triages in its next run or inline in conversation

### Orchestrator (TP-Level)

- File attachment in TP chat input (may already exist via document upload)
- Files written to `/user_shared/{filename}`
- TP can search and reference these files
- If user creates a project from TP conversation, relevant `user_shared/` files can be moved to the project's `user_shared/`

### Visibility

- `user_shared/` folder visible in Context tab (Meeting Room) and workspace browser
- Files show creation date, size, and promotion status (if promoted, show destination path)
- Users can delete their own shared files before TTL expiry

---

## Impact on Existing Subfolder Conventions

### `contributions/{agent_slug}/`
Unchanged. PM promotes relevant user files here. The contribution brief (`brief.md`) remains PM-written only.

### `assembly/{date}/`
Unchanged. Assembly reads from contributions, not directly from `user_shared/`.

### `memory/`
PM may promote reference docs to project memory. User files don't go here by default.

### `working/`
Unchanged. Agent-only scratch space. `user_shared/` is the user equivalent.

### `/knowledge/`
TP or PM may promote user-shared reference material to knowledge base. Rare but supported.

---

## Interaction with Document Upload (`filesystem_documents`)

`filesystem_documents` remains the TP-level document upload path for large, permanent reference documents. `user_shared/` is for fluid, conversational file sharing — smaller, more ephemeral, project-scoped.

Future consolidation may merge the two:
- `filesystem_documents` → `/user_shared/` with `lifecycle = 'active'` (permanent) instead of ephemeral
- Or: a "pin" action that converts ephemeral → active for important shared files

This consolidation is out of scope for ADR-127.

---

## Phases

### Phase 1: Convention + Lifecycle (Implemented)
- `_infer_lifecycle()` updated in both `AgentWorkspace` and `ProjectWorkspace` — `user_shared/` → ephemeral
- Cleanup cron in `unified_scheduler.py` split into two-tier TTL: `/working/` = 24h, `/user_shared/` = 30 days
- `workspace-conventions.md` updated to v2 with full project workspace tree + `user_shared/` convention

### Phase 2: PM Triage (Implemented)
- PM prompt v5.0: `user_shared/` context injection + `triage_file` action (promote to contributions/memory/knowledge, or ignore)
- `_load_pm_project_context()` lists `user_shared/` files with content excerpts
- `_handle_pm_decision()` routes `triage_file` action: reads source, writes to destination, logs `project_file_triaged` activity event
- `activity_log.py`: added `project_file_triaged`, `project_contributor_steered`, `project_quality_assessed` event types

### Phase 3: UX Integration (Implemented)
- `POST /projects/{slug}/share` endpoint — writes to `user_shared/{filename}` with sanitized filename
- Frontend API client: `api.projects.shareFile(slug, filename, content)`
- Meeting Room PlusMenu: "Share a file" action → inline form (filename + content) → calls share endpoint
- `project_file_triaged` event rendered in Meeting Room activity timeline
- TP-level file attachment (global `/user_shared/`) — deferred to future work

---

## References

- [Workspace Conventions](../architecture/workspace-conventions.md) — canonical path reference (updated alongside this ADR)
- [ADR-106: Agent Workspace Architecture](ADR-106-agent-workspace-architecture.md) — workspace model
- [ADR-119: Workspace Filesystem Architecture](ADR-119-workspace-filesystem-architecture.md) — folder conventions, lifecycle, versioning
- [ADR-121: PM as Intelligence Director](ADR-121-pm-intelligence-director.md) — PM triage capabilities
- [ADR-124: Project Meeting Room](ADR-124-project-meeting-room.md) — conversation surface where file sharing happens
- [FOUNDATIONS.md](../architecture/FOUNDATIONS.md) — Axiom 3 (workspace sovereignty)
