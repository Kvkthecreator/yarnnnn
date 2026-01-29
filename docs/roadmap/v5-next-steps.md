# YARNNN v5 Next Steps: Comprehensive Roadmap

**Date:** 2025-01-29
**Status:** Planning
**Context:** Post two-layer memory architecture implementation

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

### Proposed Flow (User-First)
```
Login → Console (ThinkingPartner ready) → Chat immediately OR enter project
              ↓                                    ↓
    Context: user memory                 Context: user + project memory
              ↓                                    ↓
    Can create project from chat         Full project workspace
```

### Key UX Changes

| Current | Proposed | Rationale |
|---------|----------|-----------|
| Dashboard shows project list | Console shows chat + quick actions | Chat is primary, projects are organization |
| Must select project to chat | Can chat without project | User context is always available |
| Context tab in project only | "What YARNNN knows" always visible | Transparency about memory |
| No onboarding flow | First chat = onboarding conversation | Learn about user naturally |

---

## Feature Roadmap (Workflow-Aware)

### Phase 1: Console & User-Level Chat
**Goal:** User can chat with ThinkingPartner without being in a project

#### 1.1 Backend: Global Chat Endpoint
- [ ] New route: `POST /api/chat` (no project_id required)
- [ ] Modify ThinkingPartner to work with user_context only
- [ ] Extraction writes to user_context (no project blocks)
- [ ] Session saved to agent_sessions with project_id = NULL

#### 1.2 Frontend: Console Page
- [ ] New `/console` route (replaces or augments dashboard)
- [ ] ThinkingPartner chat component (full-page, not tab)
- [ ] "What YARNNN knows about you" sidebar panel
- [ ] Quick actions: "New Project", "Import Context", "Settings"
- [ ] Recent projects list (secondary, not primary)

#### 1.3 Frontend: Navigation Restructure
- [ ] Console as default post-login destination
- [ ] Projects accessible from sidebar (like Claude Cowork's starred items)
- [ ] Breadcrumb: Console → Project Name (when in project)

#### 1.4 Onboarding Flow
- [ ] First-time user detection
- [ ] ThinkingPartner initiates onboarding conversation
- [ ] Extract user context from onboarding chat
- [ ] "Here's what I learned about you" summary

### Phase 2: Enhanced Context Visibility
**Goal:** User can see and manage what YARNNN knows

#### 2.1 User Context Panel
- [ ] "About You" section in Console sidebar
- [ ] Grouped by category (7 categories from ADR-004)
- [ ] Edit/delete individual items
- [ ] Confidence indicator (how sure YARNNN is)

#### 2.2 Project Context Panel
- [ ] Enhanced Context tab (already exists, needs polish)
- [ ] Filter by semantic type
- [ ] Sort by importance, recency
- [ ] Bulk operations (delete, reclassify)

#### 2.3 Context Transparency
- [ ] Show which context items were used in last response
- [ ] "Why did you say that?" explainer (which context informed answer)

### Phase 3: Work Agents Integration
**Goal:** Execute structured work from Console or Project

#### 3.1 Work Ticket Creation
- [ ] "Create work ticket" from Console (creates project if needed)
- [ ] ThinkingPartner can suggest work tickets during chat
- [ ] Quick actions: "Write a report", "Research topic", "Draft content"

#### 3.2 Agent Execution
- [ ] Activate work routes in main.py
- [ ] Implement research, content, reporting agents
- [ ] Output delivery to work_outputs table
- [ ] Status tracking UI

#### 3.3 Output Management
- [ ] Outputs panel in Console (cross-project view)
- [ ] Project-specific outputs in Work tab
- [ ] Export/download functionality

### Phase 4: Documents & External Context
**Goal:** Ingest context from external sources

#### 4.1 Document Upload
- [ ] PDF, DOCX, TXT upload to Supabase Storage
- [ ] Text extraction (pdf-parse, mammoth for docx)
- [ ] Chunking and block creation
- [ ] Associate with project or user-level

#### 4.2 External LLM Import
- [ ] Claude conversation export parser
- [ ] ChatGPT export parser
- [ ] Extract context from imported conversations

#### 4.3 MCP Integrations
- [ ] Notion connector (read pages as context)
- [ ] Linear connector (read issues)
- [ ] Framework for additional connectors

### Phase 5: Scheduled & Proactive Features
**Goal:** YARNNN reaches out, doesn't just respond

#### 5.1 Weekly Digest
- [ ] Implement Render cron job
- [ ] Digest content generation (summary of week's work)
- [ ] Email delivery via Resend
- [ ] Digest preferences UI

#### 5.2 Proactive Suggestions
- [ ] "You might want to..." based on context patterns
- [ ] Stale context detection and refresh prompts
- [ ] Goal progress tracking

---

## UI/UX Specifications

### Console Page Layout (Claude Cowork-Inspired)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  YARNNN                                    [Settings] [Profile]         │
├────────────────┬────────────────────────────────────────────────────────┤
│                │                                                        │
│  [+ New Chat]  │  ✨ What would you like to work on?                   │
│                │                                                        │
│  ───────────── │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  PROJECTS      │  │ Start a chat │ │ New project  │ │ Import text  │   │
│                │  └──────────────┘ └──────────────┘ └──────────────┘   │
│  ★ Project A   │                                                        │
│  ★ Project B   │  ───────────────────────────────────────────────────  │
│                │                                                        │
│  ───────────── │  💬 [Chat input area - full width]                    │
│  RECENT        │                                                        │
│                │  ───────────────────────────────────────────────────  │
│  Project C     │                                                        │
│  Project D     │  Recent chats / activity feed                          │
│                │                                                        │
├────────────────┼────────────────────────────────────────────────────────┤
│                │  📋 ABOUT YOU              [Edit]                      │
│                │  ────────────────────────                              │
│                │  Business: B2B SaaS startup                            │
│                │  Goal: Raising Series A                                │
│                │  Style: Prefers bullet points                          │
│                │  [Show all →]                                          │
└────────────────┴────────────────────────────────────────────────────────┘
```

### Project Page Layout (Enhanced)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Console    Project Name                 [Settings] [Profile]         │
├────────────────┬────────────────────────────────────────────────────────┤
│                │  [Chat] [Context] [Work] [Outputs]                     │
│  PROJECTS      │  ═══════════════════════════════════════════════════  │
│  ...           │                                                        │
│                │  (Tab content area - existing design)                  │
│                │                                                        │
│                │                                                        │
│                │                                                        │
│                │                                                        │
├────────────────┼────────────────────────────────────────────────────────┤
│                │  📋 PROJECT CONTEXT        [Edit]                      │
│                │  ────────────────────────                              │
│                │  Requirements: 3 items                                 │
│                │  Facts: 5 items                                        │
│                │  Assumptions: 2 items                                  │
│                │  [Show all →]                                          │
└────────────────┴────────────────────────────────────────────────────────┘
```

---

## Technical Dependencies

### Backend Changes Required

| Change | Files | Complexity |
|--------|-------|------------|
| Global chat endpoint | `routes/chat.py`, `main.py` | Low |
| User-only context assembly | `routes/chat.py` | Low |
| Nullable project_id in sessions | Already supported | None |
| Work routes activation | `main.py`, `routes/work.py`, `routes/agents.py` | Medium |
| Document parsing | New `services/documents.py` | Medium |
| Cron job | New Render config, `services/digest.py` | Medium |

### Frontend Changes Required

| Change | Files | Complexity |
|--------|-------|------------|
| Console page | New `app/console/page.tsx` | Medium |
| Navigation restructure | `components/Sidebar.tsx`, layouts | Medium |
| User context panel | New component | Low |
| Chat component extraction | Refactor from project page | Medium |
| Onboarding flow | New components, state management | Medium |

### Database Changes Required

| Change | Migration | Complexity |
|--------|-----------|------------|
| None for Phase 1-2 | Schema already supports | None |
| Document metadata | May need enhancement | Low |

---

## Priority Recommendation

### Immediate (This Week)
1. **Console page with user-level chat** - Biggest UX impact
2. **Navigation restructure** - Enables the new flow
3. **User context panel** - Transparency, builds trust

### Next (Following Week)
4. **Onboarding flow** - First-time user experience
5. **Work agents activation** - Core value proposition
6. **Enhanced context visibility** - Polish

### Later (Following Weeks)
7. **Document upload** - Expands context sources
8. **External imports** - Claude/ChatGPT migration
9. **Weekly digest** - Retention feature
10. **MCP integrations** - Power user features

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to first chat | ~30s (create project first) | <5s (immediate) |
| User context items after 1 week | 0 (new feature) | 10+ per user |
| Projects per user | Required | Optional |
| Return rate (week 2) | Unknown | 40%+ |

---

## Open Questions

1. **Console vs Dashboard naming?** - "Console" feels more tool-like, "Dashboard" is generic
2. **Sidebar always visible or collapsible?** - Cowork has it always visible
3. **Mobile experience?** - Console-first design needs mobile consideration
4. **Project creation from chat?** - "Let's start a project for this" flow
5. **Multi-project context?** - Should user context from Project A inform Project B chat? (Currently yes via user_context, but should it be configurable?)

---

## References

- [ADR-004: Two-Layer Memory Architecture](../adr/ADR-004-two-layer-memory-architecture.md)
- [First Principles Analysis](../analysis/memory-architecture-first-principles.md)
- Claude Cowork UI (user-provided screenshot)
- Current YARNNN dashboard implementation
