# ADR-013 Implementation Plan: Conversation + Surfaces

> **Status**: Planning
> **Parent ADR**: [ADR-013: Conversation + Surfaces](./ADR-013-conversation-plus-surfaces.md)
> **Date**: 2025-01-30

---

## Executive Summary

This document details the implementation plan for migrating YARNNN's frontend from a **page-based, tab-navigation architecture** to a **conversation-first, drawer-based surfaces architecture** as specified in ADR-013.

**Scope**: Complete frontend restructure affecting routing, layout, state management, and component architecture.

**Risk Level**: High - This is a significant refactor touching most frontend code.

---

## Current State Analysis

### Architecture Overview

```
CURRENT (Page-Based):
┌─────────────────────────────────────────────────────┐
│ Sidebar │ Page Content                              │
│         │ ┌─────────────────────────────────────┐   │
│ Projects│ │ [Chat] [Context] [Work]  ← Tabs     │   │
│ List    │ │                                     │   │
│         │ │ Tab Content (one visible at a time) │   │
│         │ │                                     │   │
│         │ └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘

TARGET (Conversation + Surfaces):
┌─────────────────────────────────────────────────────┐
│                                                     │
│  CONVERSATION (always visible)                      │
│                                                     │
├─────────────────────────────────────────────────────┤
│ ▼ Surface Drawer (summoned by TP or user)           │
│   [Output | Context | Schedule | Export]            │
└─────────────────────────────────────────────────────┘
```

### Key Files Affected

| Category | Files | Impact |
|----------|-------|--------|
| **Routing** | `app/(authenticated)/*`, `middleware.ts` | Delete/restructure |
| **Layout** | `AuthenticatedLayout.tsx`, `Sidebar.tsx` | Major rewrite |
| **Chat** | `Chat.tsx`, `useChat.ts` | Moderate changes |
| **State** | New `SurfaceProvider`, modify hooks | New code |
| **Components** | New Surface components | New code |
| **Types** | `types/index.ts` | Extensions |

### What Can Be Reused

- ✅ `useChat.ts` - Streaming logic, message handling
- ✅ `Chat.tsx` - Core chat UI (with height adjustments)
- ✅ `api/client.ts` - All API endpoints
- ✅ Auth infrastructure - Supabase auth unchanged
- ✅ `DocumentList.tsx` - For context surface
- ✅ UI primitives - Button, Input, Card, etc.
- ✅ Tailwind styling system

### What Must Be Rebuilt

- 🔄 Routing structure (pages → single /app route)
- 🔄 Layout system (sidebar+tabs → conversation+drawer)
- 🔄 Navigation (page links → surface triggers)
- 🆕 Surface state management
- 🆕 Drawer component with gestures
- 🆕 Surface components (Output, Context, Schedule, Export)
- 🆕 TP surface trigger system

---

## Implementation Phases

### Phase 0: Preparation (1-2 days)

**Objective**: Set up foundation without breaking existing functionality.

#### 0.1 Create Feature Flag
```typescript
// lib/features.ts
export const FEATURES = {
  CONVERSATION_SURFACES: process.env.NEXT_PUBLIC_FEATURE_SURFACES === 'true',
};
```

#### 0.2 Install Dependencies
```bash
# Gesture support for drawer
npm install @use-gesture/react

# Animation (if not already installed)
npm install framer-motion
```

#### 0.3 Create Type Definitions
```typescript
// types/surfaces.ts
export type SurfaceType = 'output' | 'context' | 'schedule' | 'export';

export interface SurfaceState {
  isOpen: boolean;
  type: SurfaceType | null;
  data: SurfaceData | null;
  position: 'bottom' | 'side';  // Mobile vs desktop
  expandLevel: 'peek' | 'half' | 'full';
}

export interface SurfaceData {
  // For output surface
  outputId?: string;
  ticketId?: string;

  // For context surface
  projectId?: string;
  memoryId?: string;

  // For schedule surface
  scheduleId?: string;

  // For export surface
  exportType?: 'pdf' | 'docx' | 'email';
  content?: any;
}

export interface SurfaceAction {
  type: 'OPEN_SURFACE' | 'CLOSE_SURFACE' | 'SET_EXPAND' | 'SET_DATA';
  payload?: Partial<SurfaceState>;
}
```

---

### Phase 1: Surface Infrastructure (3-4 days)

**Objective**: Build the drawer system that can be used alongside existing UI.

#### 1.1 SurfaceProvider Context

```typescript
// contexts/SurfaceContext.tsx
'use client';

import { createContext, useContext, useReducer, ReactNode } from 'react';
import { SurfaceState, SurfaceAction, SurfaceType, SurfaceData } from '@/types/surfaces';

const initialState: SurfaceState = {
  isOpen: false,
  type: null,
  data: null,
  position: 'bottom',
  expandLevel: 'half',
};

function surfaceReducer(state: SurfaceState, action: SurfaceAction): SurfaceState {
  switch (action.type) {
    case 'OPEN_SURFACE':
      return {
        ...state,
        isOpen: true,
        type: action.payload?.type ?? state.type,
        data: action.payload?.data ?? state.data,
        expandLevel: action.payload?.expandLevel ?? 'half',
      };
    case 'CLOSE_SURFACE':
      return { ...state, isOpen: false };
    case 'SET_EXPAND':
      return { ...state, expandLevel: action.payload?.expandLevel ?? state.expandLevel };
    case 'SET_DATA':
      return { ...state, data: action.payload?.data ?? state.data };
    default:
      return state;
  }
}

interface SurfaceContextValue {
  state: SurfaceState;
  openSurface: (type: SurfaceType, data?: SurfaceData) => void;
  closeSurface: () => void;
  setExpand: (level: 'peek' | 'half' | 'full') => void;
}

const SurfaceContext = createContext<SurfaceContextValue | null>(null);

export function SurfaceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(surfaceReducer, initialState);

  const openSurface = (type: SurfaceType, data?: SurfaceData) => {
    dispatch({ type: 'OPEN_SURFACE', payload: { type, data } });
  };

  const closeSurface = () => {
    dispatch({ type: 'CLOSE_SURFACE' });
  };

  const setExpand = (level: 'peek' | 'half' | 'full') => {
    dispatch({ type: 'SET_EXPAND', payload: { expandLevel: level } });
  };

  return (
    <SurfaceContext.Provider value={{ state, openSurface, closeSurface, setExpand }}>
      {children}
    </SurfaceContext.Provider>
  );
}

export function useSurface() {
  const context = useContext(SurfaceContext);
  if (!context) {
    throw new Error('useSurface must be used within SurfaceProvider');
  }
  return context;
}
```

#### 1.2 Drawer Component

```typescript
// components/surfaces/Drawer.tsx
'use client';

import { useSurface } from '@/contexts/SurfaceContext';
import { useDrag } from '@use-gesture/react';
import { useSpring, animated } from 'framer-motion';
import { X, Maximize2, Minimize2 } from 'lucide-react';

const EXPAND_HEIGHTS = {
  peek: '30vh',
  half: '50vh',
  full: '90vh',
};

export function Drawer({ children }: { children: React.ReactNode }) {
  const { state, closeSurface, setExpand } = useSurface();

  // Drag gesture for swipe-to-dismiss / expand
  const bind = useDrag(({ movement: [, my], last, velocity: [, vy] }) => {
    if (last) {
      // Swipe down fast = close
      if (vy > 0.5) {
        closeSurface();
        return;
      }
      // Snap to nearest expand level based on position
      if (my > 100) {
        state.expandLevel === 'full' ? setExpand('half') : closeSurface();
      } else if (my < -100) {
        state.expandLevel === 'half' ? setExpand('full') : setExpand('half');
      }
    }
  });

  if (!state.isOpen) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 -z-10"
        onClick={closeSurface}
      />

      {/* Drawer */}
      <animated.div
        {...bind()}
        className="bg-background border-t rounded-t-xl shadow-lg"
        style={{ height: EXPAND_HEIGHTS[state.expandLevel] }}
      >
        {/* Handle */}
        <div className="flex justify-center py-2">
          <div className="w-12 h-1 bg-muted-foreground/30 rounded-full" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 pb-2 border-b">
          <span className="font-medium capitalize">{state.type}</span>
          <div className="flex gap-2">
            <button onClick={() => setExpand(state.expandLevel === 'full' ? 'half' : 'full')}>
              {state.expandLevel === 'full' ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>
            <button onClick={closeSurface}>
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-auto" style={{ height: 'calc(100% - 60px)' }}>
          {children}
        </div>
      </animated.div>
    </div>
  );
}
```

#### 1.3 Surface Router (Content Switching)

```typescript
// components/surfaces/SurfaceRouter.tsx
'use client';

import { useSurface } from '@/contexts/SurfaceContext';
import { Drawer } from './Drawer';
import { OutputSurface } from './OutputSurface';
import { ContextSurface } from './ContextSurface';
import { ScheduleSurface } from './ScheduleSurface';
import { ExportSurface } from './ExportSurface';

export function SurfaceRouter() {
  const { state } = useSurface();

  const renderContent = () => {
    switch (state.type) {
      case 'output':
        return <OutputSurface data={state.data} />;
      case 'context':
        return <ContextSurface data={state.data} />;
      case 'schedule':
        return <ScheduleSurface data={state.data} />;
      case 'export':
        return <ExportSurface data={state.data} />;
      default:
        return null;
    }
  };

  return (
    <Drawer>
      {renderContent()}
    </Drawer>
  );
}
```

---

### Phase 2: Surface Content Components (3-4 days)

**Objective**: Build the content for each surface type.

#### 2.1 Output Surface

Displays work results, documents, drafts with export options.

```typescript
// components/surfaces/OutputSurface.tsx
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { SurfaceData } from '@/types/surfaces';
import { useSurface } from '@/contexts/SurfaceContext';

interface OutputSurfaceProps {
  data: SurfaceData | null;
}

export function OutputSurface({ data }: OutputSurfaceProps) {
  const [output, setOutput] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { openSurface } = useSurface();

  useEffect(() => {
    if (data?.outputId) {
      loadOutput(data.outputId);
    } else if (data?.ticketId) {
      loadTicketOutputs(data.ticketId);
    }
  }, [data]);

  const loadOutput = async (id: string) => {
    // Fetch specific output
    setLoading(true);
    try {
      const result = await api.work.get(id);
      setOutput(result);
    } finally {
      setLoading(false);
    }
  };

  const loadTicketOutputs = async (ticketId: string) => {
    // Fetch all outputs for a ticket
    setLoading(true);
    try {
      const result = await api.work.get(ticketId);
      setOutput(result);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (type: 'pdf' | 'docx' | 'email') => {
    openSurface('export', { exportType: type, content: output });
  };

  if (loading) {
    return <div className="p-4">Loading...</div>;
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">{output?.title}</h2>

      {/* Render output content based on type */}
      <div className="prose prose-sm max-w-none">
        {output?.content}
      </div>

      {/* Export actions */}
      <div className="flex gap-2 mt-6 pt-4 border-t">
        <button
          onClick={() => handleExport('pdf')}
          className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm"
        >
          Export PDF
        </button>
        <button
          onClick={() => handleExport('docx')}
          className="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm"
        >
          Export DOCX
        </button>
        <button
          onClick={() => handleExport('email')}
          className="px-3 py-1.5 bg-secondary text-secondary-foreground rounded text-sm"
        >
          Email
        </button>
      </div>
    </div>
  );
}
```

#### 2.2 Context Surface

Displays memories, documents, project context.

```typescript
// components/surfaces/ContextSurface.tsx
// Adapt existing UserContextPanel + DocumentList for surface format
```

#### 2.3 Schedule Surface

Displays and manages scheduled work.

```typescript
// components/surfaces/ScheduleSurface.tsx
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { SurfaceData } from '@/types/surfaces';
import { Calendar, Clock, Pause, Play, Trash2 } from 'lucide-react';

interface Schedule {
  id: string;
  task: string;
  agent_type: string;
  schedule: string;  // Human readable
  cron: string;
  timezone: string;
  enabled: boolean;
  next_run: string;
  last_run: string | null;
  project_name: string;
}

export function ScheduleSurface({ data }: { data: SurfaceData | null }) {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSchedules();
  }, [data?.projectId]);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      // Call TP tool via API (or direct endpoint)
      const result = await api.chat.send({
        message: '',
        tool_call: { name: 'list_schedules', input: { project_id: data?.projectId } }
      });
      setSchedules(result.schedules || []);
    } finally {
      setLoading(false);
    }
  };

  const toggleSchedule = async (id: string, enabled: boolean) => {
    await api.chat.send({
      message: '',
      tool_call: { name: 'update_schedule', input: { schedule_id: id, enabled: !enabled } }
    });
    loadSchedules();
  };

  const deleteSchedule = async (id: string) => {
    await api.chat.send({
      message: '',
      tool_call: { name: 'delete_schedule', input: { schedule_id: id } }
    });
    loadSchedules();
  };

  if (loading) {
    return <div className="p-4">Loading schedules...</div>;
  }

  if (schedules.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <Calendar className="mx-auto mb-2" size={32} />
        <p>No scheduled work yet.</p>
        <p className="text-sm">Ask TP to schedule recurring work for you.</p>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-semibold mb-4">Scheduled Work</h2>

      <div className="space-y-3">
        {schedules.map((schedule) => (
          <div
            key={schedule.id}
            className="p-3 border rounded-lg"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="font-medium">{schedule.task}</p>
                <p className="text-sm text-muted-foreground">
                  {schedule.project_name} · {schedule.agent_type}
                </p>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => toggleSchedule(schedule.id, schedule.enabled)}
                  className="p-1.5 hover:bg-muted rounded"
                >
                  {schedule.enabled ? <Pause size={16} /> : <Play size={16} />}
                </button>
                <button
                  onClick={() => deleteSchedule(schedule.id)}
                  className="p-1.5 hover:bg-muted rounded text-destructive"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>

            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {schedule.schedule}
              </span>
              {schedule.next_run && (
                <span>Next: {new Date(schedule.next_run).toLocaleString()}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

#### 2.4 Export Surface

Handles export flows (PDF, DOCX, email).

```typescript
// components/surfaces/ExportSurface.tsx
// Integration with backend export endpoints
```

---

### Phase 3: TP Surface Triggers (2-3 days)

**Objective**: Enable TP to open surfaces via tool responses.

#### 3.1 Extend Tool Response Schema

```typescript
// types/chat.ts
export interface TPToolResponse {
  success: boolean;
  // ... existing fields

  // NEW: UI action
  ui_action?: {
    type: 'OPEN_SURFACE' | 'CLOSE_SURFACE' | 'HIGHLIGHT';
    surface?: SurfaceType;
    data?: SurfaceData;
  };
}
```

#### 3.2 Update useChat Hook

```typescript
// hooks/useChat.ts (additions)

import { useSurface } from '@/contexts/SurfaceContext';

// Inside useChat hook:
const { openSurface } = useSurface();

// In stream handler, after parsing tool_result:
if (toolResult.ui_action) {
  switch (toolResult.ui_action.type) {
    case 'OPEN_SURFACE':
      openSurface(toolResult.ui_action.surface!, toolResult.ui_action.data);
      break;
    case 'CLOSE_SURFACE':
      closeSurface();
      break;
  }
}
```

#### 3.3 Update Backend Tool Handlers

```python
# api/services/project_tools.py

# Example: handle_create_work returns ui_action
async def handle_create_work(auth, input: dict) -> dict:
    # ... existing logic ...

    return {
        "success": True,
        "work": { ... },
        # NEW: Tell frontend to open output surface
        "ui_action": {
            "type": "OPEN_SURFACE",
            "surface": "output",
            "data": { "ticketId": ticket_id }
        }
    }
```

---

### Phase 4: Layout Restructure (3-4 days)

**Objective**: Migrate from tab-based to conversation-first layout.

#### 4.1 New App Route Structure

```
app/
├── page.tsx                    # Landing (unchanged)
├── auth/                       # Auth routes (unchanged)
├── (app)/                      # NEW: Authenticated app group
│   ├── layout.tsx              # NEW: Conversation + Surface layout
│   └── page.tsx                # NEW: Main app (conversation)
├── settings/                   # Settings (could become surface)
└── admin/                      # Admin (unchanged)
```

#### 4.2 New App Layout

```typescript
// app/(app)/layout.tsx
'use client';

import { SurfaceProvider } from '@/contexts/SurfaceContext';
import { SurfaceRouter } from '@/components/surfaces/SurfaceRouter';
import { ProjectSelector } from '@/components/ProjectSelector';
import { UserMenu } from '@/components/UserMenu';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SurfaceProvider>
      <div className="h-screen flex flex-col">
        {/* Header */}
        <header className="h-14 border-b flex items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <span className="font-semibold">YARNNN</span>
            <ProjectSelector />
          </div>
          <UserMenu />
        </header>

        {/* Main content (conversation) */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>

        {/* Surface drawer */}
        <SurfaceRouter />
      </div>
    </SurfaceProvider>
  );
}
```

#### 4.3 New App Page (Conversation)

```typescript
// app/(app)/page.tsx
'use client';

import { Chat } from '@/components/Chat';
import { useProjectContext } from '@/contexts/ProjectContext';

export default function AppPage() {
  const { activeProject } = useProjectContext();

  return (
    <Chat
      projectId={activeProject?.id}
      projectName={activeProject?.name}
      includeContext={true}
      heightClass="h-full"
    />
  );
}
```

#### 4.4 Project Context (Not Route)

```typescript
// contexts/ProjectContext.tsx
'use client';

import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '@/lib/api/client';

interface Project {
  id: string;
  name: string;
}

interface ProjectContextValue {
  projects: Project[];
  activeProject: Project | null;
  setActiveProject: (project: Project | null) => void;
  refreshProjects: () => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: React.ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    const result = await api.projects.list();
    setProjects(result);
  };

  return (
    <ProjectContext.Provider value={{
      projects,
      activeProject,
      setActiveProject,
      refreshProjects: loadProjects,
    }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProjectContext() {
  const context = useContext(ProjectContext);
  if (!context) throw new Error('useProjectContext must be used within ProjectProvider');
  return context;
}
```

---

### Phase 5: Migration & Cleanup (2-3 days)

**Objective**: Complete migration, remove old code, redirect routes.

#### 5.1 Route Redirects

```typescript
// middleware.ts (additions)
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Redirect old routes to new /app
  if (pathname === '/dashboard') {
    return NextResponse.redirect(new URL('/app', request.url));
  }
  if (pathname.startsWith('/projects/')) {
    const projectId = pathname.split('/')[2];
    return NextResponse.redirect(new URL(`/app?project=${projectId}`, request.url));
  }

  // ... existing auth logic
}
```

#### 5.2 Query Param Deep Links

```typescript
// app/(app)/page.tsx
'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect } from 'react';
import { useProjectContext } from '@/contexts/ProjectContext';
import { useSurface } from '@/contexts/SurfaceContext';

export default function AppPage() {
  const searchParams = useSearchParams();
  const { projects, setActiveProject } = useProjectContext();
  const { openSurface } = useSurface();

  useEffect(() => {
    // Handle ?project=uuid
    const projectId = searchParams.get('project');
    if (projectId) {
      const project = projects.find(p => p.id === projectId);
      if (project) setActiveProject(project);
    }

    // Handle ?surface=output&id=uuid
    const surface = searchParams.get('surface');
    const id = searchParams.get('id');
    if (surface) {
      openSurface(surface as SurfaceType, { outputId: id });
    }
  }, [searchParams, projects]);

  // ... rest of component
}
```

#### 5.3 Remove Old Code

Files to delete after migration:
- `app/(authenticated)/dashboard/page.tsx`
- `app/(authenticated)/projects/[id]/page.tsx`
- `app/(authenticated)/layout.tsx`
- `components/shell/Sidebar.tsx`
- `components/shell/AuthenticatedLayout.tsx`
- Related tab components

---

### Phase 6: Desktop Enhancement (2-3 days)

**Objective**: Add side-docking for larger screens.

#### 6.1 Responsive Drawer Behavior

```typescript
// components/surfaces/Drawer.tsx (enhanced)

import { useMediaQuery } from '@/hooks/useMediaQuery';

export function Drawer({ children }: { children: React.ReactNode }) {
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const { state, closeSurface, setExpand } = useSurface();

  // Desktop: side panel
  if (isDesktop && state.isOpen) {
    return (
      <div className="fixed top-14 right-0 bottom-0 w-[480px] border-l bg-background z-40">
        <div className="flex items-center justify-between p-4 border-b">
          <span className="font-medium capitalize">{state.type}</span>
          <button onClick={closeSurface}><X size={18} /></button>
        </div>
        <div className="overflow-auto h-[calc(100%-57px)]">
          {children}
        </div>
      </div>
    );
  }

  // Mobile: bottom drawer
  // ... existing drawer code
}
```

#### 6.2 Layout Adjustment for Side Panel

```typescript
// app/(app)/layout.tsx (enhanced)

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { state } = useSurface();
  const isDesktop = useMediaQuery('(min-width: 1024px)');

  return (
    <SurfaceProvider>
      <div className="h-screen flex flex-col">
        <header>...</header>

        <div className="flex-1 flex overflow-hidden">
          {/* Conversation - shrinks when surface open on desktop */}
          <main className={cn(
            "flex-1 overflow-hidden transition-all",
            isDesktop && state.isOpen && "mr-[480px]"
          )}>
            {children}
          </main>
        </div>

        <SurfaceRouter />
      </div>
    </SurfaceProvider>
  );
}
```

---

## Testing Strategy

### Unit Tests
- SurfaceProvider state management
- Drawer gesture behavior
- Surface component rendering

### Integration Tests
- TP tool → surface opening
- Project context switching
- Deep link handling

### E2E Tests
- Full conversation → work → output flow
- Mobile drawer interactions
- Desktop side panel behavior

### Manual Testing Checklist
- [ ] New user onboarding flow
- [ ] Project creation via TP
- [ ] Work execution and output viewing
- [ ] Schedule creation and management
- [ ] Export flows (PDF, DOCX, email)
- [ ] Mobile responsive behavior
- [ ] Desktop side panel docking
- [ ] Deep links working

---

## Rollout Strategy

### Stage 1: Internal Testing
- Deploy behind feature flag
- Team testing for 1 week
- Bug fixes

### Stage 2: Beta Users
- Enable for subset of users
- Collect feedback
- Iterate on UX

### Stage 3: Full Rollout
- Remove feature flag
- Old route redirects active
- Monitor for issues

### Rollback Plan
- Feature flag can disable new UI
- Old routes preserved (redirected) for 30 days
- Database schema unchanged (no migration needed)

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 0: Preparation | 1-2 days | None |
| Phase 1: Surface Infrastructure | 3-4 days | Phase 0 |
| Phase 2: Surface Components | 3-4 days | Phase 1 |
| Phase 3: TP Triggers | 2-3 days | Phase 1, Phase 2 |
| Phase 4: Layout Restructure | 3-4 days | Phase 1 |
| Phase 5: Migration & Cleanup | 2-3 days | Phase 4 |
| Phase 6: Desktop Enhancement | 2-3 days | Phase 5 |

**Total Estimated Duration: 16-23 days**

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing users | Feature flag, gradual rollout |
| Complex state management | Thorough testing, simple reducer |
| Mobile gesture issues | Test on real devices, fallback buttons |
| Performance regression | Profile drawer animations, lazy load surfaces |
| TP trigger edge cases | Comprehensive tool response testing |

---

## Success Criteria

1. **User can complete full workflow without page navigation**
   - Conversation → ask TP → see output in surface → export

2. **TP can surface information proactively**
   - Tool responses trigger appropriate surfaces

3. **Mobile experience is native-feeling**
   - Swipe gestures work, no jank

4. **Desktop users get enhanced experience**
   - Side panel for simultaneous viewing

5. **No regression in existing functionality**
   - All current features accessible via surfaces or conversation
