# YARNNN v5 Next Steps: Comprehensive Roadmap

**Date:** 2025-01-29
**Status:** Planning
**Context:** Post two-layer memory architecture implementation
**Approach:** Singular, streamlined - restructure Dashboard into Console

---

## The Core Insight

Current YARNNN forces users into projects before they can chat. This contradicts:
1. **ADR-004**: User context should be available *before* project context
2. **Brand promise**: "Your AI understands YOUR world" - not "your project's world"
3. **Industry benchmark** (Claude Cowork): Chat is user-level, projects are optional organization

**The fix isn't just adding features - it's restructuring the user journey.**

---

## User Journey Redesign

### Current Flow (Project-First)
```
Login → Dashboard (project list) → Select Project → Chat Tab → Start talking
                                                              ↓
                                          Context: project blocks only
```

### Target Flow (User-First)
```
Login → Dashboard (chat-first) → Chat immediately OR select project
              ↓                            ↓
    Context: user memory         Context: user + project memory
```

**Single approach:** Transform existing `/dashboard` - no new routes, no duplication.

---

## Implementation Plan

### Phase 1: Dashboard Transformation
**Goal:** Dashboard becomes chat-first with projects in sidebar

#### 1.1 Backend: Global Chat Endpoint
- [ ] New route: `POST /api/chat` (no project_id required)
- [ ] `load_user_context_only(user_id)` function
- [ ] Extraction writes to user_context only (no project blocks when no project)
- [ ] Session saved to agent_sessions with project_id = NULL

#### 1.2 Frontend: Dashboard Restructure
- [ ] Replace project grid with chat-first layout
- [ ] ThinkingPartner chat as primary content area
- [ ] Projects list in left sidebar (collapsible)
- [ ] "About You" panel in right sidebar (user context)
- [ ] Quick actions row: "New Project", "Import"

#### 1.3 Shared Chat Component
- [ ] Extract chat logic from project page into reusable component
- [ ] Props: `projectId?: string` (optional = user-level chat)
- [ ] Conditional context loading based on projectId presence

### Phase 2: Context Visibility & Management
**Goal:** User can see and manage what YARNNN knows

#### 2.1 User Context Panel (Dashboard Sidebar)
- [ ] "About You" section grouped by category
- [ ] Edit/delete individual items
- [ ] Confidence indicator

#### 2.2 Project Context Enhancement
- [ ] Filter by semantic type in Context tab
- [ ] Importance/recency sorting
- [ ] Inline editing

### Phase 3: Work Agents
**Goal:** Execute structured work

#### 3.1 Activation
- [ ] Uncomment work/agents routes in main.py
- [ ] Basic research, content, reporting agents
- [ ] Status tracking in UI

#### 3.2 Output Delivery
- [ ] Outputs tab in project view
- [ ] Download/export functionality

### Phase 4: External Context
**Goal:** Ingest from other sources

- [ ] Document upload + parsing (PDF, DOCX)
- [ ] Claude/ChatGPT export import
- [ ] MCP connectors (Notion, Linear)

### Phase 5: Proactive Features
**Goal:** YARNNN reaches out

- [ ] Weekly digest emails (Render cron + Resend)
- [ ] Stale context detection

---

## UI/UX: Dashboard Layout (Chat-First)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  YARNNN                                              [Settings] [User]  │
├────────────────┬──────────────────────────────────────┬─────────────────┤
│                │                                      │                 │
│  [+ New Project]  ✨ What's on your mind?            │  ABOUT YOU      │
│                │                                      │  ───────────    │
│  ───────────── │  ┌────────┐ ┌────────┐ ┌────────┐   │  Business:      │
│  PROJECTS      │  │New proj│ │Import  │ │Settings│   │  B2B SaaS       │
│                │  └────────┘ └────────┘ └────────┘   │                 │
│  Project A     │                                      │  Goal:          │
│  Project B     │  ─────────────────────────────────  │  Series A       │
│  Project C     │                                      │                 │
│                │  [Chat messages area]                │  Style:         │
│                │                                      │  Bullet points  │
│                │                                      │                 │
│                │                                      │  [Edit →]       │
│                │  ─────────────────────────────────  │                 │
│                │  [Type a message...]          [Send] │                 │
└────────────────┴──────────────────────────────────────┴─────────────────┘
```

**Key changes from current:**
- Chat is center stage, not hidden in project tabs
- Projects are sidebar navigation, not the main content
- User context visible at all times (right panel)
- Quick actions for common tasks

---

## Technical Changes

### Backend
| Change | File | Notes |
|--------|------|-------|
| Global chat endpoint | `routes/chat.py` | `POST /api/chat` (no project_id) |
| User-only context loader | `routes/chat.py` | New function |
| Nullable project in sessions | Already supported | - |

### Frontend
| Change | File | Notes |
|--------|------|-------|
| Dashboard restructure | `app/dashboard/page.tsx` | Chat-first layout |
| Shared chat component | `components/Chat.tsx` | Extract from project page |
| User context panel | `components/UserContextPanel.tsx` | New component |
| Project sidebar | `components/ProjectSidebar.tsx` | New component |

### Database
No changes needed - schema already supports nullable project_id.

---

## Execution Order

1. **Backend: Global chat endpoint** - Enables user-level chat
2. **Frontend: Extract chat component** - Reusable for dashboard + project
3. **Frontend: Dashboard restructure** - The main UX change
4. **Frontend: User context panel** - Visibility into what YARNNN knows
5. **Polish: Onboarding detection** - First-time user experience

---

## References

- [ADR-004: Two-Layer Memory Architecture](../adr/ADR-004-two-layer-memory-architecture.md)
- Claude Cowork UI (benchmark)
- Current dashboard: `web/app/dashboard/page.tsx`
