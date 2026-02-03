# Implementation Plan: ADR-023 Supervisor Desk Architecture

**Date:** 2026-02-03
**Status:** Ready for execution

---

## Overview

Transform the frontend from a tab-based navigation model to a **single-desk, multi-surface** architecture where:

1. One surface is displayed at a time (the "desk")
2. Surfaces can show any data domain (deliverables, work, context, documents, projects)
3. TP is always present as a floating input bar
4. An attention queue shows items needing review
5. A domain browser provides escape hatch navigation

---

## Phase 1: Foundation

### 1.1 Type Definitions

Create shared types for the desk system:

```typescript
// web/types/desk.ts

export type DeskSurface =
  // Deliverables
  | { type: 'deliverable-review'; deliverableId: string; versionId: string }
  | { type: 'deliverable-detail'; deliverableId: string }
  // Work
  | { type: 'work-output'; workId: string; outputId?: string }
  | { type: 'work-list'; filter?: 'active' | 'completed' | 'all' }
  // Context
  | { type: 'context-browser'; scope: 'user' | 'deliverable' | 'project'; scopeId?: string }
  | { type: 'context-editor'; memoryId: string }
  // Documents
  | { type: 'document-viewer'; documentId: string }
  | { type: 'document-list'; projectId?: string }
  // Projects
  | { type: 'project-detail'; projectId: string }
  | { type: 'project-list' }
  // Idle
  | { type: 'idle' };

export interface AttentionItem {
  type: 'deliverable-staged';
  deliverableId: string;
  versionId: string;
  title: string;
  stagedAt: string;
}

export interface TPMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolResults?: ToolResult[];
  timestamp: Date;
}

export interface Chip {
  label: string;
  prompt: string;
}
```

### 1.2 DeskContext

```typescript
// web/contexts/DeskContext.tsx

interface DeskState {
  surface: DeskSurface;
  surfaceData: Record<string, unknown> | null;
  attention: AttentionItem[];
  isLoading: boolean;
  error: string | null;
}

const initialState: DeskState = {
  surface: { type: 'idle' },
  surfaceData: null,
  attention: [],
  isLoading: true,
  error: null,
};

// Actions
type DeskAction =
  | { type: 'SET_SURFACE'; surface: DeskSurface }
  | { type: 'SET_SURFACE_DATA'; data: Record<string, unknown> }
  | { type: 'SET_ATTENTION'; items: AttentionItem[] }
  | { type: 'CLEAR_SURFACE' }
  | { type: 'NEXT_ATTENTION' }
  | { type: 'SET_LOADING'; isLoading: boolean }
  | { type: 'SET_ERROR'; error: string | null };

// Reducer and provider...
```

### 1.3 TPContext

```typescript
// web/contexts/TPContext.tsx

interface TPState {
  messages: TPMessage[];
  isLoading: boolean;
  error: string | null;
}

// Reuse chat logic from existing useChat hook
// Messages are ephemeral, cleared on surface change (configurable)
```

### 1.4 Desk Container

```typescript
// web/components/desk/Desk.tsx

export function Desk() {
  const { surface, attention, isLoading } = useDesk();

  // On mount: load attention items, check URL params for deep link
  useEffect(() => {
    loadAttentionItems();
    handleDeepLink();
  }, []);

  return (
    <div className="h-full flex flex-col">
      {/* Main surface area */}
      <div className="flex-1 overflow-hidden">
        <SurfaceRouter surface={surface} />
      </div>

      {/* Attention bar (if items exist) */}
      {attention.length > 0 && <AttentionBar items={attention} />}

      {/* TP floating bar */}
      <TPBar />
    </div>
  );
}
```

### 1.5 Surface Router

```typescript
// web/components/desk/SurfaceRouter.tsx

export function SurfaceRouter({ surface }: { surface: DeskSurface }) {
  switch (surface.type) {
    case 'deliverable-review':
      return <DeliverableReviewSurface {...surface} />;
    case 'deliverable-detail':
      return <DeliverableDetailSurface {...surface} />;
    case 'work-output':
      return <WorkOutputSurface {...surface} />;
    case 'work-list':
      return <WorkListSurface {...surface} />;
    case 'context-browser':
      return <ContextBrowserSurface {...surface} />;
    case 'context-editor':
      return <ContextEditorSurface {...surface} />;
    case 'document-viewer':
      return <DocumentViewerSurface {...surface} />;
    case 'document-list':
      return <DocumentListSurface {...surface} />;
    case 'project-detail':
      return <ProjectDetailSurface {...surface} />;
    case 'project-list':
      return <ProjectListSurface {...surface} />;
    case 'idle':
    default:
      return <IdleSurface />;
  }
}
```

---

## Phase 2: Core Surfaces

### 2.1 DeliverableReviewSurface

Adapt from `VersionTabView.tsx`:

- Editable content area
- Refinement chips (Shorter, More detail, etc.)
- Custom TP input
- Discard / Skip / Mark as Done actions
- Learning insights banner
- Next/All navigation in header

```typescript
// web/components/surfaces/DeliverableReviewSurface.tsx

interface Props {
  deliverableId: string;
  versionId: string;
}

export function DeliverableReviewSurface({ deliverableId, versionId }: Props) {
  // Load deliverable and version data
  // Reuse logic from VersionTabView
  // Connect to TP for refinements
  // Handle approve/reject actions
}
```

### 2.2 DeliverableDetailSurface

Adapt from `DeliverableDetail.tsx`:

- Deliverable metadata (title, type, schedule)
- Quality metrics and trend
- Latest version preview
- Version history list
- Run Now action
- Edit Settings action

### 2.3 IdleSurface

New component:

- "All caught up" message if no staged items
- Summary of upcoming deliverables
- Onboarding prompts if no deliverables exist
- Quick action chips

### 2.4 AttentionBar

```typescript
// web/components/desk/AttentionBar.tsx

interface Props {
  items: AttentionItem[];
}

export function AttentionBar({ items }: Props) {
  const { setSurface } = useDesk();

  return (
    <div className="shrink-0 border-t bg-muted/30 px-4 py-2">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">
          {items.length} need{items.length === 1 ? 's' : ''} review
        </span>
        <div className="flex gap-2 overflow-x-auto">
          {items.map((item) => (
            <button
              key={item.versionId}
              onClick={() => setSurface({
                type: 'deliverable-review',
                deliverableId: item.deliverableId,
                versionId: item.versionId,
              })}
              className="px-3 py-1 text-xs border rounded-full hover:bg-background whitespace-nowrap"
            >
              {item.title}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Phase 3: TP Bar

### 3.1 TPBar Component

```typescript
// web/components/tp/TPBar.tsx

export function TPBar() {
  const { surface } = useDesk();
  const { messages, sendMessage, isLoading, clearMessages } = useTP();
  const [input, setInput] = useState('');

  const chips = getChipsForSurface(surface);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    await sendMessage(input, getSurfaceContext(surface));
    setInput('');
  };

  const handleChipClick = (prompt: string) => {
    setInput(prompt);
  };

  return (
    <div className="shrink-0 border-t bg-background">
      {/* Recent TP messages */}
      {messages.length > 0 && (
        <TPMessages messages={messages} onDismiss={clearMessages} />
      )}

      {/* Input area */}
      <div className="p-4">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center gap-2">
            {/* Chips */}
            <TPChips chips={chips} onSelect={handleChipClick} />

            {/* Input */}
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything..."
              className="flex-1 px-4 py-2.5 border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />

            {/* Send */}
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="p-2.5 bg-primary text-primary-foreground rounded-full disabled:opacity-50"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

### 3.2 Chip Configuration

```typescript
// web/lib/tp-chips.ts

export function getChipsForSurface(surface: DeskSurface): Chip[] {
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
      ];

    case 'context-browser':
      return [
        { label: 'Add memory', prompt: 'I want to tell you something to remember' },
        { label: 'What do you know?', prompt: 'Summarize what you know about me' },
      ];

    case 'work-output':
      return [
        { label: 'Summarize', prompt: 'Give me the key points from this' },
        { label: 'Save insight', prompt: 'Remember the key findings from this' },
      ];

    case 'idle':
      return [
        { label: 'Weekly report', prompt: 'I need to send weekly status reports' },
        { label: 'Research', prompt: 'I need you to research something' },
        { label: 'My context', prompt: 'Show me what you know about me' },
      ];

    default:
      return [];
  }
}
```

### 3.3 TP Tool → Surface Integration

```typescript
// web/hooks/useTP.ts

// When TP returns a ui_action, map it to a surface change
function handleToolResult(result: ToolResult) {
  if (result.ui_action?.type === 'OPEN_SURFACE') {
    const surface = mapToolActionToSurface(result.ui_action);
    if (surface) {
      setSurface(surface);
    }
  }
}
```

---

## Phase 4: Domain Browser

### 4.1 DomainBrowser Component

```typescript
// web/components/desk/DomainBrowser.tsx

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function DomainBrowser({ isOpen, onClose }: Props) {
  const { setSurface, attention } = useDesk();
  const [data, setData] = useState<BrowserData | null>(null);

  useEffect(() => {
    if (isOpen) loadBrowserData();
  }, [isOpen]);

  const handleItemClick = (surface: DeskSurface) => {
    setSurface(surface);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />

      {/* Panel */}
      <div className="absolute right-0 top-0 h-full w-80 bg-background border-l shadow-xl overflow-y-auto">
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Browse</h2>
            <button onClick={onClose}><X className="w-4 h-4" /></button>
          </div>

          {/* Needs Attention */}
          {attention.length > 0 && (
            <BrowserSection title={`Needs Attention (${attention.length})`}>
              {attention.map((item) => (
                <BrowserItem
                  key={item.versionId}
                  title={item.title}
                  subtitle={`staged ${formatRelative(item.stagedAt)}`}
                  indicator="staged"
                  onClick={() => handleItemClick({
                    type: 'deliverable-review',
                    deliverableId: item.deliverableId,
                    versionId: item.versionId,
                  })}
                />
              ))}
            </BrowserSection>
          )}

          {/* Deliverables */}
          <BrowserSection title="Deliverables">
            {data?.deliverables.map((d) => (
              <BrowserItem
                key={d.id}
                title={d.title}
                subtitle={d.scheduleDescription}
                onClick={() => handleItemClick({
                  type: 'deliverable-detail',
                  deliverableId: d.id,
                })}
              />
            ))}
            <BrowserAction
              label="+ Create new deliverable"
              onClick={() => {/* Focus TP with prompt */}}
            />
          </BrowserSection>

          {/* Recent Work */}
          <BrowserSection title="Recent Work">
            {data?.recentWork.map((w) => (
              <BrowserItem
                key={w.id}
                title={w.title}
                subtitle={`${w.status} ${formatRelative(w.completedAt)}`}
                onClick={() => handleItemClick({
                  type: 'work-output',
                  workId: w.id,
                })}
              />
            ))}
            <BrowserAction
              label="→ View all work"
              onClick={() => handleItemClick({ type: 'work-list' })}
            />
          </BrowserSection>

          {/* Context */}
          <BrowserSection title="Context">
            <BrowserItem
              title="About Me"
              subtitle={`${data?.userMemoryCount} memories`}
              onClick={() => handleItemClick({
                type: 'context-browser',
                scope: 'user',
              })}
            />
            {data?.deliverableContexts.map((dc) => (
              <BrowserItem
                key={dc.deliverableId}
                title={`${dc.deliverableTitle} context`}
                subtitle={`${dc.memoryCount} memories`}
                onClick={() => handleItemClick({
                  type: 'context-browser',
                  scope: 'deliverable',
                  scopeId: dc.deliverableId,
                })}
              />
            ))}
          </BrowserSection>

          {/* Documents */}
          <BrowserSection title="Documents">
            {data?.recentDocuments.map((doc) => (
              <BrowserItem
                key={doc.id}
                title={doc.filename}
                subtitle={`uploaded ${formatRelative(doc.uploadedAt)}`}
                onClick={() => handleItemClick({
                  type: 'document-viewer',
                  documentId: doc.id,
                })}
              />
            ))}
            <BrowserAction
              label="→ View all documents"
              onClick={() => handleItemClick({ type: 'document-list' })}
            />
          </BrowserSection>
        </div>
      </div>
    </div>
  );
}
```

---

## Phase 5: Additional Surfaces

Build remaining surfaces following the same pattern:

### 5.1 Work Surfaces
- `WorkOutputSurface` - Display work output content, copy/download actions
- `WorkListSurface` - List of work items with filters

### 5.2 Context Surfaces
- `ContextBrowserSurface` - List memories grouped by tags, edit/delete actions
- `ContextEditorSurface` - Edit a single memory

### 5.3 Document Surfaces
- `DocumentViewerSurface` - Display document content/preview
- `DocumentListSurface` - List uploaded documents

### 5.4 Project Surfaces
- `ProjectDetailSurface` - Project info and settings
- `ProjectListSurface` - List projects (legacy, lower priority)

---

## Phase 6: Backend - Memory Tools

### 6.1 Add Memory Tools

```python
# api/services/project_tools.py

# Add to THINKING_PARTNER_TOOLS list:
LIST_MEMORIES_TOOL = {...}
CREATE_MEMORY_TOOL = {...}
UPDATE_MEMORY_TOOL = {...}
DELETE_MEMORY_TOOL = {...}

# Add handlers:
async def handle_list_memories(auth, input: dict) -> dict:
    scope = input.get("scope", "user")
    scope_id = input.get("scope_id")
    tags = input.get("tags", [])
    limit = input.get("limit", 20)

    query = auth.client.table("memories")\
        .select("id, content, tags, source_type, created_at")\
        .eq("user_id", auth.user_id)\
        .order("created_at", desc=True)\
        .limit(limit)

    if scope == "user":
        query = query.is_("project_id", "null")
    elif scope == "deliverable" and scope_id:
        query = query.eq("deliverable_id", scope_id)
    elif scope == "project" and scope_id:
        query = query.eq("project_id", scope_id)

    if tags:
        query = query.contains("tags", tags)

    result = query.execute()

    return {
        "success": True,
        "memories": result.data or [],
        "count": len(result.data or []),
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "context",
            "data": {"scope": scope, "scopeId": scope_id}
        }
    }

async def handle_create_memory(auth, input: dict) -> dict:
    content = input["content"]
    scope = input.get("scope", "user")
    scope_id = input.get("scope_id")
    tags = input.get("tags", [])

    memory_data = {
        "content": content,
        "user_id": auth.user_id,
        "tags": tags,
        "source_type": "user_input",
    }

    if scope == "deliverable" and scope_id:
        memory_data["deliverable_id"] = scope_id
    elif scope == "project" and scope_id:
        memory_data["project_id"] = scope_id

    result = auth.client.table("memories").insert(memory_data).execute()

    return {
        "success": True,
        "memory": result.data[0] if result.data else None,
        "message": "Got it, I'll remember that."
    }

# Similar for update and delete...
```

### 6.2 Update TP System Prompt

Add memory tool instructions to the system prompt:

```python
**Memory Management:**
- `list_memories` - Show what you know about the user
- `create_memory` - Remember something new
- `update_memory` - Correct existing knowledge
- `delete_memory` - Forget something

Use these when:
- User asks "what do you know about me/my company/etc."
- User says "remember that..." or "don't forget..."
- User wants to correct or remove information
```

---

## Phase 7: Cleanup

### 7.1 Delete Legacy Files

```bash
# Contexts
rm web/contexts/FloatingChatContext.tsx
rm web/contexts/TabContext.tsx
rm web/contexts/SurfaceContext.tsx  # Replaced by DeskContext

# Components
rm web/components/FloatingChatPanel.tsx
rm web/components/FloatingChatTrigger.tsx
rm web/components/EmbeddedTPInput.tsx
rm web/components/shell/Sidebar.tsx

# Tab system
rm -rf web/components/tabs/

# Old surfaces (replaced)
rm web/components/surfaces/OutputSurface.tsx
rm web/components/surfaces/ContextSurface.tsx
rm web/components/surfaces/ScheduleSurface.tsx
rm web/components/surfaces/ExportSurface.tsx
rm web/components/surfaces/SurfaceRouter.tsx  # Old one
rm web/components/surfaces/OutputDetailView.tsx
rm web/components/surfaces/OutputsSurface.tsx
rm web/components/surfaces/WorkspacePanel.tsx
rm web/components/surfaces/Drawer.tsx

# Lib
rm web/lib/tabs.ts
```

### 7.2 Update AuthenticatedLayout

```typescript
// web/components/shell/AuthenticatedLayout.tsx

export function AuthenticatedLayout({ children }: { children: ReactNode }) {
  const [browserOpen, setBrowserOpen] = useState(false);

  return (
    <DeskProvider>
      <TPProvider>
        <div className="h-screen flex flex-col bg-background">
          {/* Top bar with browse button */}
          <header className="h-12 border-b flex items-center justify-between px-4">
            <span className="font-semibold">YARNNN</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setBrowserOpen(true)}
                className="p-2 hover:bg-muted rounded"
              >
                <Menu className="w-4 h-4" />
              </button>
              <UserMenu />
            </div>
          </header>

          {/* Main content */}
          <main className="flex-1 overflow-hidden">
            {children}
          </main>

          {/* Domain browser */}
          <DomainBrowser isOpen={browserOpen} onClose={() => setBrowserOpen(false)} />
        </div>
      </TPProvider>
    </DeskProvider>
  );
}
```

### 7.3 Update Dashboard Page

```typescript
// web/app/(authenticated)/dashboard/page.tsx

export default function DashboardPage() {
  return <Desk />;
}
```

---

## Testing Checklist

### Functional Tests

**Surfaces:**
- [ ] Idle surface shows when no attention items
- [ ] Deliverable review surface loads and displays content
- [ ] Content editing works in review surface
- [ ] Approve/reject actions work
- [ ] Skip goes to next attention item
- [ ] Deliverable detail surface shows metadata and history
- [ ] Work output surface displays content
- [ ] Context browser shows memories grouped by tags
- [ ] Context editor allows editing

**Attention Bar:**
- [ ] Shows staged deliverable versions
- [ ] Clicking item opens review surface
- [ ] Updates when items are approved/rejected

**TP Bar:**
- [ ] Chips update based on current surface
- [ ] Sending message works
- [ ] Tool results trigger surface changes
- [ ] Refinement requests update content

**Domain Browser:**
- [ ] Opens when clicking browse button
- [ ] Shows all sections with correct data
- [ ] Clicking items opens correct surfaces
- [ ] Closes on backdrop click

**Deep Links:**
- [ ] URL params open correct surface on load
- [ ] Surface changes update URL

### Edge Cases

- [ ] No deliverables → onboarding prompts
- [ ] No staged items → idle surface
- [ ] Network errors → show error state
- [ ] Empty sections in domain browser

---

## Success Criteria

1. **Simplicity:** User opens app, sees what needs attention, acts, done
2. **No navigation confusion:** One place, surfaces flow through
3. **TP integration:** Tool results naturally open relevant surfaces
4. **Direct access:** User can browse and interact without TP
5. **Code reduction:** ~15+ files deleted, 2+ contexts consolidated
6. **Performance:** Faster initial load, less client-side state

---

## Rollback Plan

If critical issues arise:
1. Git revert the implementation commits
2. Old components remain in git history
3. No database migrations to roll back
