# Workspace Explorer UI — Unified Navigation + Scoped Chat

**Status:** Proposed  
**Date:** 2026-04-01  
**Depends on:** ADR-152 (directory registry), ADR-149 (task lifecycle), Agent Templates v4

---

## Overview

Three-panel layout inspired by IDE + file explorer:

- **Left Panel:** Workspace file explorer (unified tree, no tabs)
- **Main Panel:** Context-dependent content viewer (directory listing, file viewer, task detail, output viewer)
- **Right Panel:** Scoped chat (TP with navigation-aware context)

The filesystem IS the navigation. No artificial separation between context, tasks, and agents. Everything is a path in the workspace.

---

## Left Panel: Workspace Explorer

Unified file tree mirroring `workspace_files` paths. No distinction tabs.

```
/workspace/
├── IDENTITY.md
├── BRAND.md
├── WORKSPACE.md
├── uploads/
├── context/
│   ├── competitors/
│   │   ├── _landscape.md
│   │   └── acme-corp/
│   ├── market/
│   ├── relationships/
│   ├── projects/
│   ├── content/
│   └── signals/
└── outputs/
    ├── reports/
    ├── briefs/
    └── content/

/agents/
├── competitive-intelligence/
│   ├── AGENT.md
│   └── memory/
├── market-research/
└── ...

/tasks/
├── track-competitors/
│   ├── TASK.md
│   ├── DELIVERABLE.md
│   └── memory/
├── competitive-brief/
└── ...
```

**Behavior:**
- Click folder → main panel shows directory listing
- Click file → main panel shows file viewer
- Click task folder → main panel shows task detail view
- Folder expand/collapse for navigation
- File counts shown on folders (e.g., "competitors/ (5 entities)")
- Last-updated timestamps on folders for freshness signal
- Color coding: context/ (blue), outputs/ (green), tasks/ (orange), agents/ (purple)

---

## Main Panel: Content Viewer

Depends on what's selected in the explorer:

### Directory Listing View
When a folder is selected. Shows files as a list with:
- File name
- Last updated timestamp
- Preview (first line of content)
- File type icon

### File Viewer
When a `.md` file is selected. Shows:
- Rendered markdown
- Edit button (inline editing for IDENTITY.md, BRAND.md, TASK.md, DELIVERABLE.md)
- Metadata: path, last updated, updated by (agent/user)

### Task Detail View
When a task folder or TASK.md is selected. Shows:
- **Header:** Task title, mode badge (recurring/goal/reactive), status, schedule
- **Tabs:** Output | Task | Deliverable | Context | Schedule | Process
  - **Output:** Latest output rendered (HTML iframe or markdown)
  - **Task:** TASK.md content (objective, process, agents)
  - **Deliverable:** DELIVERABLE.md content (quality spec, expected assets, inferred preferences)
  - **Context:** Which domains this task reads/writes, with entity counts and freshness
  - **Schedule:** Run history, next run, evaluation history, steering notes
  - **Process:** Process steps with agent assignments

### Agent Detail View
When an agent folder or AGENT.md is selected. Shows:
- Agent title, role, status, domain owned
- AGENT.md content (identity, instructions)
- Memory: reflections, feedback, playbooks
- Domain health: entity count, freshness of owned domain
- Task assignments: which tasks this agent handles

### Output Viewer
When an `.html` output file is selected. Shows:
- Rendered HTML in iframe
- Repurpose actions (PDF, XLSX, etc.)
- Evaluation summary if available

### Media Viewer
When an image/SVG/chart is selected. Shows:
- Image preview
- Metadata (source task, generation date)

### IDE-Style Tabs
- Multiple items can be open simultaneously
- Tab bar above main panel
- Close button on each tab
- Click in explorer opens new tab (or focuses existing)

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
| `/workspace/` root | "User at workspace root" | Workspace overview, task suggestions |
| `/workspace/context/competitors/` | "Browsing competitor context" | Track Competitors status, create entity, evaluate health |
| `/workspace/context/competitors/acme-corp/` | "Viewing Acme Corp entity" | Update Acme, research Acme, create brief about Acme |
| `/tasks/track-competitors/` | "Viewing Track Competitors task" | Trigger, evaluate, steer, schedule, feedback |
| `/tasks/competitive-brief/` (output tab) | "Viewing competitive brief output" | Evaluate quality, give feedback, re-run |
| `/agents/competitive-intelligence/` | "Viewing CI agent" | Agent health, reflections, task list |
| `/workspace/IDENTITY.md` | "Viewing identity" | Update identity, inference |
| `/workspace/outputs/reports/` | "Browsing reports" | Create report task, search outputs |

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

### New API Endpoints Needed
- `GET /api/workspace/tree` — file tree for explorer (paths, types, updated_at)
- `GET /api/workspace/file?path=...` — file content by path
- `PATCH /api/workspace/file?path=...` — edit file inline (for IDENTITY.md, DELIVERABLE.md, etc.)

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
