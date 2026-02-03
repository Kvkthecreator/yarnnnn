# ADR-023: Supervisor Desk Architecture

> **✅ CURRENT ARCHITECTURE**
> This is the active UI architecture as of 2026-02-03.
> All new development should follow this pattern.

**Status:** Implemented (Current)
**Date:** 2026-02-03
**Supersedes:** ADR-021 (Review-First), ADR-022 (Tab-Based)

## Context

We've iterated through multiple UI architectures:
- ADR-013: Conversation + Surfaces (drawers layer on chat)
- ADR-020: Deliverable-Centric Chat (floating chat globally)
- ADR-021: Review-First (land on what needs attention)
- ADR-022: Tab-Based (IDE-like tabs for multiple open items)

Each iteration added mechanisms without achieving simplicity. The codebase accumulated:
- `TabContext` + `TabBar` + `TabContent`
- `FloatingChatContext` + `FloatingChatPanel`
- `SurfaceContext` + multiple surface components

**The core problem:** We kept implementing navigation paradigms (pages, tabs, drawers) when the supervision model doesn't require navigation.

### The Factory Supervisor Insight

A factory supervisor doesn't navigate. They:
1. Stand in **one place** (their desk/station)
2. Things **come to them** (items needing attention arrive)
3. They can **glance at the queue** without leaving their spot
4. They **speak and things happen** (communication is ambient)
5. They can **pull things onto their desk** to review proactively
6. They can **intervene directly** — edit reports, update records, manage context

The supervisor doesn't have separate "modes" — they're always in the same place, and things flow through. But they also have agency to act directly, not just respond to what arrives.

### Data Domains

YARNNN operates on multiple data domains, each with TP tools and UI needs:

| Data Domain | TP Tools | User Actions |
|-------------|----------|--------------|
| **Deliverables** | `list_deliverables`, `get_deliverable`, `create_deliverable`, `run_deliverable`, `update_deliverable` | Review versions, edit settings, view history |
| **Deliverable Versions** | (via deliverable tools + API) | Edit content, refine with TP, approve/reject |
| **Work** | `create_work`, `list_work`, `get_work`, `update_work`, `delete_work` | View outputs, track progress |
| **Context/Memory** | `list_memories`, `get_memory`, `create_memory`, `update_memory`, `delete_memory` (NEW) | Browse context, edit memories, manage what TP knows |
| **Documents** | (upload via API) | View documents, see extracted content |
| **Projects** | `list_projects`, `create_project`, `rename_project`, `update_project` | Browse projects, edit settings |

The desk must support **all domains**, not just deliverables.

## Decision

### The Desk Model

One persistent workspace. One thing "on the desk" at a time. Any data domain can be surfaced. User can act directly or through TP.

```
┌─────────────────────────────────────────────────────────────────┐
│ YARNNN                                              [Browse ≡]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                                                         │   │
│   │   THE DESK (current surface)                            │   │
│   │                                                         │   │
│   │   Any data domain:                                      │   │
│   │   • Deliverable version review                          │   │
│   │   • Deliverable detail                                  │   │
│   │   • Work output                                         │   │
│   │   • Context/memory browser                              │   │
│   │   • Document viewer                                     │   │
│   │   • Idle (nothing on desk)                              │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
│     ATTENTION: 2 deliverables staged                            │
│   │ [Weekly Report ▸] [Client Update ▸]                    │   │
│   └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ TP: floating input bar                                  │    │
│  │ [contextual chips] [_________________________] [Send]   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Surface Type System

The desk displays **surfaces** — typed views into data domains:

```typescript
type DeskSurface =
  // === Deliverables Domain ===
  | {
      type: 'deliverable-review';
      deliverableId: string;
      versionId: string;
    }
  | {
      type: 'deliverable-detail';
      deliverableId: string;
    }

  // === Work Domain ===
  | {
      type: 'work-output';
      workId: string;
      outputId?: string;  // specific output, or latest
    }
  | {
      type: 'work-list';
      filter?: 'active' | 'completed' | 'all';
    }

  // === Context Domain ===
  | {
      type: 'context-browser';
      scope: 'user' | 'deliverable' | 'project';
      scopeId?: string;  // deliverableId or projectId
    }
  | {
      type: 'context-editor';
      memoryId: string;
    }

  // === Documents Domain ===
  | {
      type: 'document-viewer';
      documentId: string;
    }
  | {
      type: 'document-list';
      projectId?: string;
    }

  // === Projects Domain ===
  | {
      type: 'project-detail';
      projectId: string;
    }
  | {
      type: 'project-list';
    }

  // === Idle State ===
  | {
      type: 'idle';
    };
```

### Surface Triggers

Surfaces appear on the desk via three mechanisms:

**1. TP Tool Results**
When TP executes a tool, the result can include a `ui_action` that opens a surface:

```typescript
// Tool result from backend
{
  "success": true,
  "ui_action": {
    "type": "OPEN_SURFACE",
    "surface": "deliverable",
    "data": { "deliverableId": "abc123" }
  }
}

// Maps to DeskSurface
{ type: 'deliverable-detail', deliverableId: 'abc123' }
```

**2. Attention Queue**
Staged deliverable versions appear in the attention bar. Clicking opens review:

```typescript
{ type: 'deliverable-review', deliverableId: '...', versionId: '...' }
```

**3. Domain Browser (Escape Hatch)**
User explicitly browses and selects an item:

```typescript
// User clicks "Weekly Status Report" in deliverables section
{ type: 'deliverable-detail', deliverableId: '...' }

// User clicks "About Me" in context section
{ type: 'context-browser', scope: 'user' }
```

### TP Tool → Surface Mapping

```typescript
function mapToolActionToSurface(action: UIAction): DeskSurface | null {
  const { surface, data } = action;

  switch (surface) {
    // Deliverables
    case 'deliverable':
      return { type: 'deliverable-detail', deliverableId: data.deliverableId };
    case 'deliverable-review':
      return { type: 'deliverable-review', deliverableId: data.deliverableId, versionId: data.versionId };

    // Work
    case 'output':
    case 'work-output':
      return { type: 'work-output', workId: data.workId, outputId: data.outputId };
    case 'work-list':
      return { type: 'work-list' };

    // Context
    case 'context':
    case 'memory':
      return { type: 'context-browser', scope: data.scope || 'user', scopeId: data.scopeId };
    case 'memory-edit':
      return { type: 'context-editor', memoryId: data.memoryId };

    // Documents
    case 'document':
      return { type: 'document-viewer', documentId: data.documentId };

    // Projects
    case 'project':
      return { type: 'project-detail', projectId: data.projectId };

    default:
      return null;
  }
}
```

### Domain Browser (Escape Hatch)

The `[Browse ≡]` button opens a panel showing all data domains:

```
┌────────────────────────────────────────────────────────────────┐
│ BROWSE                                                    [×]  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│ NEEDS ATTENTION (2)                                            │
│ ├─ ● Weekly Status Report                    staged 2h ago     │
│ └─ ● Client Update                           staged 1d ago     │
│                                                                │
│ ───────────────────────────────────────────────────────────── │
│                                                                │
│ DELIVERABLES                                                   │
│ ├─ Weekly Status Report                      Mon 9am           │
│ ├─ Client Update                             15th monthly      │
│ ├─ Competitor Brief                          Paused            │
│ └─ + Create new deliverable                                    │
│                                                                │
│ RECENT WORK                                                    │
│ ├─ Market Analysis                           completed 2h ago  │
│ ├─ Competitor Research                       completed 1d ago  │
│ └─ → View all work                                             │
│                                                                │
│ CONTEXT                                                        │
│ ├─ About Me                                  12 memories       │
│ ├─ Weekly Status Report context              8 memories        │
│ └─ → Manage all context                                        │
│                                                                │
│ DOCUMENTS                                                      │
│ ├─ Q4_Report.pdf                             uploaded Jan 15   │
│ ├─ Competitor_Analysis.docx                  uploaded Jan 10   │
│ └─ → View all documents                                        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

Clicking any item opens the appropriate surface on the desk.

### Surface Components

Each surface type has a dedicated component:

```
web/components/surfaces/
├── DeliverableReviewSurface.tsx    # Edit, refine, approve version
├── DeliverableDetailSurface.tsx    # View deliverable, history, settings
├── WorkOutputSurface.tsx           # View work result
├── WorkListSurface.tsx             # List work items
├── ContextBrowserSurface.tsx       # Browse memories
├── ContextEditorSurface.tsx        # Edit a memory
├── DocumentViewerSurface.tsx       # View document content
├── DocumentListSurface.tsx         # List documents
├── ProjectDetailSurface.tsx        # Project settings
├── ProjectListSurface.tsx          # List projects
└── IdleSurface.tsx                 # Empty state, onboarding
```

### Example Surfaces

**Deliverable Review Surface:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Weekly Status Report                              [→ Next] [All]│
│ Review draft v4                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Hi Sarah,                                                     │
│                                                                 │
│   Here's this week's update for Project Alpha...                │
│   [Editable content area]                                       │
│                                                                 │
│   ─────────────────────────────────────────────────────────     │
│   ✨ YARNNN noticed: You often add metrics. Include them?       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [Discard]                           [Skip] [Mark as Done ✓]    │
└─────────────────────────────────────────────────────────────────┘
```

**Context Browser Surface:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Context: About Me                                    [+ Add]    │
│ What YARNNN knows about you                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   PREFERENCES                                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • Prefers concise bullet points over paragraphs         │   │
│   │ • Uses "we" not "I" in status reports                   │   │
│   │ • Always includes next steps section                    │   │
│   └─────────────────────────────────────────────────────────┘   │
│   [Edit] [Delete]                                               │
│                                                                 │
│   COMPANY INFO                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ • Company: Acme Corp                                    │   │
│   │ • Role: Engineering Manager                             │   │
│   │ • Team size: 8 engineers                                │   │
│   └─────────────────────────────────────────────────────────┘   │
│   [Edit] [Delete]                                               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  12 memories total • Last updated 2 days ago                    │
└─────────────────────────────────────────────────────────────────┘
```

**Work Output Surface:**
```
┌─────────────────────────────────────────────────────────────────┐
│ Market Analysis                                    [Copy] [↓]   │
│ Research • Completed 2 hours ago                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ## Key Findings                                               │
│                                                                 │
│   1. Market is growing at 15% YoY                               │
│   2. Top 3 competitors control 60% share                        │
│   3. Opportunity in enterprise segment                          │
│                                                                 │
│   ## Detailed Analysis                                          │
│   ...                                                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Task: "Analyze the AI assistant market trends"                 │
└─────────────────────────────────────────────────────────────────┘
```

**Idle Surface:**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                        All caught up.                           │
│                                                                 │
│        Next deliverable: Weekly Status Report (Mon 9am)         │
│                                                                 │
│        ─────────────────────────────────────────────────        │
│                                                                 │
│        What recurring work do you produce?                      │
│        [Weekly report] [Monthly update] [Meeting notes]         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### TP: Floating Input Bar

TP is always present at the bottom. Chips adapt to current surface:

```typescript
function getChipsForSurface(surface: DeskSurface): Chip[] {
  switch (surface.type) {
    case 'deliverable-review':
      return [
        { label: 'Shorter', prompt: 'Make this more concise' },
        { label: 'More detail', prompt: 'Add more detail' },
        { label: 'More formal', prompt: 'Make the tone more formal' },
      ];

    case 'deliverable-detail':
      return [
        { label: 'Run now', prompt: 'Generate a new version now' },
        { label: 'Show history', prompt: 'Show me the version history' },
        { label: 'Edit settings', prompt: 'I want to change the settings' },
      ];

    case 'context-browser':
      return [
        { label: 'Add memory', prompt: 'I want to tell you something to remember' },
        { label: 'What do you know?', prompt: 'What do you know about me?' },
      ];

    case 'work-output':
      return [
        { label: 'Summarize', prompt: 'Give me the key points' },
        { label: 'Save as memory', prompt: 'Remember the key findings from this' },
      ];

    case 'idle':
      return [
        { label: 'Weekly report', prompt: 'I need a weekly status report' },
        { label: 'Research task', prompt: 'I need you to research something' },
        { label: 'Show context', prompt: 'Show me what you know about me' },
      ];

    default:
      return [];
  }
}
```

TP responses appear inline above the input. The focus remains on the desk content.

### TP Tool + Conversation Blending

TP uses a "tool-first" model where every response is a tool call. But tools can (and often should) be combined:

**Pattern:** Navigation tool → ALWAYS `respond()` with contextual follow-up

Navigation tools MUST be followed by `respond()`. This message becomes the "handoff" shown at the top of the new surface, providing continuity between conversation and content.

```
User: "show me my memories"

TP calls: list_memories()
→ TPBar shows: "Pulling up your memories..."

TP then calls: respond("Here's everything I remember about you. Want to add something new?")
→ Surface opens to context browser
→ HandoffBanner shows TP's message at top of surface
→ Conversation continues naturally
```

**Implementation:**
- `TPContext` tracks pending navigation and follow-up respond message
- Navigation executes AFTER all tool results processed
- If there's a respond message, it's passed as `handoffMessage` to `setSurfaceWithHandoff()`
- `HandoffBanner` component displays the message at top of surface, auto-dismisses after 8s

**Ambiguous requests → clarify():**

```
User: "create a task"

TP calls: clarify("What kind of task?", [
  "One-time work item",
  "Recurring deliverable (like a weekly report)",
  "Just a reminder/note"
])
→ TPBar shows the question with option buttons
→ User clicks option → TP proceeds with appropriate tool
```

**Domain vocabulary mapping in system prompt:**
- "task", "work", "job" → Could be `work` OR `deliverable` (clarify)
- "report", "update", "document" → Usually `deliverable`
- "note", "remember this" → Usually `memory`
- "project", "workspace" → `project`

**Surface "Add/New" buttons:**
All surfaces with creation actions wire their buttons to TP rather than custom forms:
- ContextBrowserSurface "Add" → `sendMessage("I'd like to add something to my memory")`
- ProjectListSurface "New Project" → `sendMessage("I'd like to create a new project")`
- DeliverableListSurface "New" → `sendMessage("I'd like to create a new recurring deliverable")`

This keeps TP as the primary interaction point while providing UI affordances for discoverability.

### New Context/Memory Tools

To complete the context domain, add these TP tools:

```python
LIST_MEMORIES_TOOL = {
    "name": "list_memories",
    "description": """List user's memories (context).

Memories are what YARNNN knows about the user across conversations.
Use this when user asks "what do you know about X" or wants to see their context.

Scopes:
- "user": Cross-cutting personal context (preferences, company info)
- "deliverable": Context specific to a deliverable
- "project": Context specific to a project (legacy)
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["user", "deliverable", "project"],
                "description": "Which context scope to list"
            },
            "scope_id": {
                "type": "string",
                "description": "For deliverable/project scope, the ID"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by tags (e.g., ['preferences', 'company'])"
            },
            "limit": {
                "type": "integer",
                "description": "Max results. Default: 20"
            }
        },
        "required": []
    }
}

CREATE_MEMORY_TOOL = {
    "name": "create_memory",
    "description": """Store a new memory about the user.

Use when:
- User explicitly tells you to remember something
- You learn something important about the user that should persist
- User provides context that will be useful for future deliverables

Examples:
- "Remember that I prefer bullet points"
- "My manager's name is Sarah Chen"
- "We use React for our frontend"
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "The memory content"
            },
            "scope": {
                "type": "string",
                "enum": ["user", "deliverable"],
                "description": "Where this memory applies. Default: user"
            },
            "scope_id": {
                "type": "string",
                "description": "For deliverable scope, the deliverable ID"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for organization (e.g., ['preferences', 'technical'])"
            }
        },
        "required": ["content"]
    }
}

UPDATE_MEMORY_TOOL = {
    "name": "update_memory",
    "description": "Update an existing memory's content or tags.",
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string"},
            "content": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["memory_id"]
    }
}

DELETE_MEMORY_TOOL = {
    "name": "delete_memory",
    "description": """Delete a memory.

Use when user wants to remove something from context:
- "Forget that old project"
- "Remove the memory about Vue, we use React now"
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string"}
        },
        "required": ["memory_id"]
    }
}
```

### State Management

**DeskContext:**
```typescript
interface DeskState {
  // Current surface on desk
  surface: DeskSurface;

  // Cached data for current surface (avoid re-fetching)
  surfaceData: Record<string, unknown> | null;

  // Attention queue (staged deliverables)
  attention: AttentionItem[];

  // Loading states
  isLoading: boolean;
  error: string | null;
}

interface AttentionItem {
  type: 'deliverable-staged';
  deliverableId: string;
  versionId: string;
  title: string;
  stagedAt: string;
}

type DeskAction =
  | { type: 'SET_SURFACE'; surface: DeskSurface }
  | { type: 'SET_SURFACE_DATA'; data: Record<string, unknown> }
  | { type: 'SET_ATTENTION'; items: AttentionItem[] }
  | { type: 'CLEAR_SURFACE' }  // Go to idle
  | { type: 'NEXT_ATTENTION' }  // Open next attention item
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_ERROR'; error: string | null };
```

**TPContext:**
```typescript
interface TPState {
  messages: TPMessage[];  // Recent messages (ephemeral)
  isLoading: boolean;
  error: string | null;
}

// Messages are contextual to current surface
// Cleared when surface changes (or kept for continuity — TBD)
```

### URL Strategy

Single route with query params for deep linking:

```
/dashboard                                    → Idle or first attention item
/dashboard?surface=deliverable-review&did=X&vid=Y   → Review version
/dashboard?surface=deliverable-detail&did=X         → Deliverable detail
/dashboard?surface=context-browser&scope=user       → User context
/dashboard?surface=work-output&wid=X                → Work output
```

Deep links work (for email notifications, sharing), but users don't navigate via URLs.

### Component Architecture

```
web/
├── app/
│   └── (authenticated)/
│       └── dashboard/
│           └── page.tsx              # Single page
│
├── components/
│   ├── desk/
│   │   ├── Desk.tsx                  # Main container
│   │   ├── SurfaceRouter.tsx         # Routes to surface component
│   │   ├── AttentionBar.tsx          # Staged items indicator
│   │   └── DomainBrowser.tsx         # [Browse] escape hatch
│   │
│   ├── surfaces/
│   │   ├── DeliverableReviewSurface.tsx
│   │   ├── DeliverableDetailSurface.tsx
│   │   ├── WorkOutputSurface.tsx
│   │   ├── WorkListSurface.tsx
│   │   ├── ContextBrowserSurface.tsx
│   │   ├── ContextEditorSurface.tsx
│   │   ├── DocumentViewerSurface.tsx
│   │   ├── DocumentListSurface.tsx
│   │   ├── ProjectDetailSurface.tsx
│   │   ├── ProjectListSurface.tsx
│   │   └── IdleSurface.tsx
│   │
│   ├── tp/
│   │   ├── TPBar.tsx                 # Floating input bar
│   │   ├── TPChips.tsx               # Contextual quick actions
│   │   └── TPMessages.tsx            # Inline responses
│   │
│   └── ui/                           # Keep existing primitives
│
├── contexts/
│   ├── DeskContext.tsx               # Surface state, attention queue
│   └── TPContext.tsx                 # TP conversation state
│
└── hooks/
    ├── useDesk.ts                    # Desk operations
    ├── useTP.ts                      # TP chat operations
    └── useSurface.ts                 # Surface-specific data loading
```

## Consequences

### Positive

- **Unified model** — All data domains accessible through same pattern
- **TP tool integration** — Tool results naturally open relevant surfaces
- **Direct manipulation** — User can browse and edit without TP
- **No navigation paradigm** — One place, surfaces flow through
- **Extensible** — New domains just need new surface type + component
- **Significant code reduction** — Remove tabs, floating chat, fragmented surfaces

### Negative

- **Single-item focus** — Can't view two things side-by-side
- **Learning curve** — Not a traditional dashboard
- **Surface proliferation** — Many surface components to build/maintain

### Trade-offs Accepted

- **Simplicity over multi-document** — One thing at a time is enough for supervision
- **Ambient TP over chat history** — TP presence implied, not a chat app
- **Domain browser over navigation** — Escape hatch exists but isn't primary

## Migration Path

### Phase 1: Foundation
1. Create `DeskContext` with surface type system
2. Create `TPContext` for conversation state
3. Create `Desk.tsx` container with `SurfaceRouter`

### Phase 2: Core Surfaces
1. `DeliverableReviewSurface` (adapt from VersionTabView)
2. `DeliverableDetailSurface` (adapt from DeliverableDetail)
3. `IdleSurface` (new)
4. `AttentionBar` component

### Phase 3: Domain Browser
1. `DomainBrowser` component
2. Load data for each section (deliverables, work, context, docs)

### Phase 4: Additional Surfaces
1. `WorkOutputSurface`, `WorkListSurface`
2. `ContextBrowserSurface`, `ContextEditorSurface`
3. `DocumentViewerSurface`, `DocumentListSurface`
4. `ProjectDetailSurface`, `ProjectListSurface`

### Phase 5: Context Tools (Backend)
1. Add `list_memories`, `create_memory`, `update_memory`, `delete_memory` tools
2. Add handlers in `project_tools.py`
3. Update TP system prompt

### Phase 6: Cleanup
1. Delete legacy components (tabs, floating chat)
2. Simplify `AuthenticatedLayout`
3. Remove unused contexts

## What Gets Removed

**Frontend — Delete:**
- `FloatingChatContext.tsx`
- `FloatingChatPanel.tsx`
- `FloatingChatTrigger.tsx`
- `TabContext.tsx`
- `TabBar.tsx`
- `TabContent.tsx`
- `tabs/views/DeliverableTabView.tsx`
- `tabs/views/VersionTabView.tsx`
- `EmbeddedTPInput.tsx`
- `Sidebar.tsx`
- Old surface components (will be replaced)

**Frontend — Keep & Adapt:**
- `ChatView.tsx` → Extract patterns to TPBar
- `VersionReview.tsx` → Adapt to DeliverableReviewSurface
- `DeliverableDetail.tsx` → Adapt to DeliverableDetailSurface
- UI primitives (button, card, input, etc.)

**Backend — Add:**
- Memory tools in `project_tools.py`
- Memory tool handlers

## References

- [ESSENCE.md](../ESSENCE.md) - Core principles
- [ADR-018: Recurring Deliverables](ADR-018-recurring-deliverables.md) - Deliverable data model
- [ADR-022: Tab-Based Architecture](ADR-022-tab-based-supervision-architecture.md) - Superseded
- Factory supervisor mental model (conversation 2026-02-03)
