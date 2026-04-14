# Workspace Explorer UI — Unified Navigation + Scoped Chat

**Status:** Implemented (v1 explorer shell)  
**Date:** 2026-04-04 (v2 — tasks removed, agents page owns task browsing)  
**Depends on:** ADR-152 (directory registry), [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md) v3  
**Supersedes:** v1 (2026-04-02, included Tasks folder in explorer)

---

## Overview

Three-panel layout inspired by Finder / Windows Explorer:

- **Left Panel:** Workspace file explorer (unified tree, no tabs)
- **Main Panel:** Context-dependent content viewer (directory listing + type-aware file preview)
- **Right Panel:** Scoped chat (TP with navigation-aware context)

The explorer now uses one navigation model. No separate domain-card browser, no dashboard-vs-explorer split. The filesystem is presented as browseable folders/files, with a synthetic root that preserves user-facing visibility rules.

---

## Left Panel: Workspace Explorer

Unified file tree with synthetic roots. Tasks are NOT in the explorer — they are accessed through the agents page (see [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md) v3).

```
yarnnn
├── Domains/
│   ├── Competitors/
│   │   ├── _landscape.md
│   │   ├── anthropic/
│   │   │   ├── profile.md
│   │   │   └── signals.md
│   │   └── ...
│   ├── Market/
│   ├── Relationships/
│   ├── Projects/
│   ├── Content/
│   └── Signals/
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
- Context domains are relabeled from key → display name in the explorer
- Left panel collapse/expand behavior is unchanged from the prior workfloor shell

### Surface split

The context page is the workspace substrate explorer. It shows accumulated knowledge (domains), user-contributed files (uploads), and workspace settings. Tasks and agent outputs are accessed through the agents page, not through the context explorer. This preserves a clean separation:
- **Agents page** = manage work (agents, tasks, outputs)
- **Context page** = browse knowledge (domains, uploads, settings)

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

| Feature | Effort | Priority | Status |
|---|---|---|---|
| Left panel: file tree from workspace_files | Medium | P0 | Implemented |
| Main panel: directory listing view | Small | P0 | Implemented |
| Main panel: file viewer (markdown, HTML, images) | Small | P0 | Implemented |
| Right panel: navigation context in chat | Small | P0 | Implemented |
| API: /workspace/tree, /workspace/file | Medium | P0 | Implemented |
| Left panel: folder metadata (counts, freshness) | Small | P1 | Pending |
| Plus menu: context-dependent actions | Medium | P1 | Pending |
| Main panel: inline editing | Medium | P2 | Deferred |
| Main panel: media viewer (full) | Small | P2 | Deferred |

**Removed from scope:** Task detail view and agent detail view are no longer in the context explorer — they live on the agents page per [SURFACE-ARCHITECTURE.md](SURFACE-ARCHITECTURE.md) v3.
