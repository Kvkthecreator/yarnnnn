# Workspace Explorer UI — Unified Navigation + Scoped Chat

**Status:** Implemented (v1 explorer shell)  
**Date:** 2026-04-02  
**Depends on:** ADR-152 (directory registry), ADR-149 (task lifecycle), Agent Templates v4

---

## Overview

Three-panel layout inspired by Finder / Windows Explorer:

- **Left Panel:** Workspace file explorer (unified tree, no tabs)
- **Main Panel:** Context-dependent content viewer (directory listing + type-aware file preview)
- **Right Panel:** Scoped chat (TP with navigation-aware context)

The explorer now uses one navigation model. No separate domain-card browser, no dashboard-vs-explorer split. The filesystem is presented as browseable folders/files, with a synthetic root that preserves user-facing visibility rules.

---

## Left Panel: Workspace Explorer

Unified file tree with synthetic roots:

```
yarnnn
├── Tasks/
│   ├── Market Landscape Tracking/
│   │   ├── TASK.md
│   │   ├── DELIVERABLE.md
│   │   ├── outputs/
│   │   └── awareness.md
│   └── ...
├── Domains/
│   ├── Competitors/
│   │   ├── _landscape.md
│   │   ├── anthropic/
│   │   │   ├── profile.md
│   │   │   └── signals.md
│   │   └── ...
│   └── ...
├── Uploads/
└── Settings/
    ├── IDENTITY.md
    ├── BRAND.md
    └── AWARENESS.md
```

**Behavior:**
- Click folder → main panel shows directory listing
- Click file → main panel shows file viewer
- Folder expand/collapse for navigation
- Top-level folders preserve current visibility rules rather than exposing every raw system path
- Tasks are relabeled from slug → title in the explorer
- Context domains are relabeled from key → display name in the explorer
- Left panel collapse/expand behavior is unchanged from the prior workfloor shell

### Task folder behavior

`/tasks` is treated like any other directory in the explorer:

- Click a task folder → open that folder in the main panel
- Click task files like `TASK.md`, `DELIVERABLE.md`, or output artifacts → preview those files inline
- Task files are not special launch targets inside Workfloor

This preserves one consistent rule:
- Workfloor = Explorer/Finder for all surfaced files and folders

---

## Main Panel: Content Viewer

Depends on what's selected in the explorer:

### Directory Listing View
When a folder is selected. Shows a details-style list with:
- File name
- Kind
- Last modified timestamp
- Preview summary when available

### File Viewer
When a file is selected. Type-aware preview:
- `.md` → rendered markdown
- `.html` → inline iframe preview
- `.png/.jpg/.svg/.gif/.webp` → image preview
- `.pdf` → inline PDF preview when URL-backed
- `.csv` → table preview
- `.xlsx/.pptx` and other binary outputs → open/download affordance
- `.txt/.json` and fallback types → text preview

### Breadcrumb Header
- The top bar shows the current explorer path as clickable breadcrumbs
- Current selection kind or item count appears at the far right
- Back-navigation is path-based, not a separate domain browser mode

---

## Right Panel: Scoped Chat

TP chat with navigation-aware context injection.

### Navigation Context

Frontend sends `navigation_context` with each chat message:

```typescript
interface NavigationContext {
  path: string;           // "/workspace/context/competitors/acme-corp/profile.md"
  type: "file" | "directory" | "task" | "agent" | "workspace";
  domain?: string;        // "competitors" (if within a context domain)
  entity?: string;        // "acme-corp" (if viewing an entity)
  task_slug?: string;     // "track-competitors" (if viewing a task)
  agent_slug?: string;    // "competitive-intelligence" (if viewing an agent)
}
```

### TP Scope Behavior

| Navigation state | TP receives | Scoped suggestions |
|---|---|---|
| `/explorer` root | "User at explorer root" | Workspace overview, task suggestions |
| `/explorer/domains` | "Browsing context domains" | Domain health, create tracking task |
| `/workspace/context/competitors/anthropic/profile.md` | "Viewing Anthropic profile" | Update entity, research, compare |
| `/tasks/track-competitors` | "Viewing a task folder" | Browse task artifacts, inspect outputs |
| `/tasks/track-competitors/outputs/.../output.html` | "Viewing a task output file" | Evaluate, repurpose, export |
| `/workspace/IDENTITY.md` | "Viewing identity" | Update identity, inference |

### Prompt Injection

Navigation context added to TP system prompt:

```
## Current Navigation
The user is currently viewing: /workspace/context/competitors/acme-corp/profile.md
Type: file (entity profile within competitors domain)
Domain: competitors
Entity: acme-corp

Scope your responses to this context. Suggest actions relevant to what the user is looking at.
```

### Plus Menu (Context-Dependent Actions)

The chat's "+" menu shows actions relevant to the current view:

| View | Plus Menu Actions |
|---|---|
| Task detail | Run Now, Evaluate, Steer, Give Feedback, Adjust Schedule |
| Context domain | Create Entity, Run Tracking Task, Evaluate Domain Health |
| Entity file | Update This Entity, Research This Entity |
| Agent detail | View Tasks, View Domain, Rename |
| Output file | Export PDF, Repurpose, Evaluate |
| Workspace root | Create Task, Connect Platform, Upload File |

---

## Data Flow

### Explorer → API
```
GET /api/workspace/tree          → returns folder/file tree
GET /api/workspace/file?path=... → returns file content
GET /api/tasks/{slug}            → returns task detail (existing)
GET /api/agents/{slug}           → returns agent detail (existing, via routes)
```

### Chat → API
```
POST /api/chat
{
  message: "...",
  navigation_context: { path, type, domain, entity, task_slug, agent_slug }
}
```

### Supporting API Shape
- `GET /api/workspace/tree` — file tree for explorer
- `GET /api/workspace/file?path=...` — file content + content type + content URL
- `PATCH /api/workspace/file?path=...` — edit file inline (existing)

---

## Implementation Priority

| Feature | Effort | Priority |
|---|---|---|
| Left panel: file tree from workspace_files | Medium | P0 |
| Main panel: directory listing view | Small | P0 |
| Main panel: file viewer (markdown) | Small | P0 |
| Main panel: task detail view (existing, adapt) | Medium | P0 |
| Right panel: navigation context in chat | Small | P0 |
| Left panel: folder metadata (counts, freshness) | Small | P1 |
| Main panel: IDE tabs | Medium | P1 |
| Main panel: agent detail view | Medium | P1 |
| Main panel: output viewer (HTML) | Small (exists) | P1 |
| Plus menu: context-dependent actions | Medium | P1 |
| Main panel: inline editing | Medium | P2 |
| Main panel: media viewer | Small | P2 |
| New API: /workspace/tree, /workspace/file | Medium | P0 (required) |
