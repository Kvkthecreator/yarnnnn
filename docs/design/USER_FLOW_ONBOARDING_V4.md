# User Flow: Project-Native Onboarding (v6)

> **Status**: Current
> **Date**: 2026-03-20
> **Supersedes**: [Onboarding V5](archive/) (2026-03-16)
> **Related**: ADR-057 (Streamlined Onboarding), ADR-110 (Onboarding Bootstrap), ADR-113 (Auto Source Selection), ADR-119 (Workspace Filesystem), ADR-122 (Project Type Registry), ADR-124 (Project Meeting Room)

---

## What Changed Since V5

V5 was agent-centric: bootstrap created standalone agents, Orchestrator cards created agents, the dashboard supervised agents. With ADR-122 (Project Type Registry) and ADR-124 (Project Meeting Room), the model is now **project-native**:

1. **Projects are the primary unit, not agents.** Bootstrap creates projects (with member agents inside). Orchestrator cards create projects. Users supervise projects.

2. **Orchestrator empty state is 3+1 cards.** Three platform project cards (Slack Recap, Gmail Recap, Notion Recap) backed 1:1 by the project type registry, plus one "New Project" card for custom projects. No aspirational cards without registry backing.

3. **Bootstrap creates projects, not standalone agents.** OAuth → sync → `scaffold_project(type_key)` creates a project with member agent + PM agent. Bootstrap banner links to the project Meeting Room, not an agent page.

4. **Meeting Room is the project surface.** After project creation, users interact in `/projects/{slug}` — a group chat where PM and contributor agents are participants (ADR-124). This is where objective refinement and context collection happen.

5. **Orchestrator is thin for project creation.** TP creates the project and routes the user to the Meeting Room. Deep context collection happens project-side, not in TP chat.

---

## User Personas

| Type | Description | Optimal path |
|------|-------------|--------------|
| **Platform-first** | Has Slack/Gmail/Notion/Calendar; wants recurring summaries from existing work data | Connect platforms → auto-created project → Meeting Room |
| **Topic-first** | Has a research question or monitoring need; doesn't need platform data | Orchestrator → "New Project" card → describe intent → project created → Meeting Room |
| **Explorer** | Curious about AI agents; wants to see what's possible before committing | Dashboard → connect one platform → see first project result |

---

## User Journey

```
OPEN  →  CONNECT  →  AUTO-SYNC  →  FIRST PROJECT  →  FIRST DELIVERY  →  SUPERVISION
 │          │           │              │                 │                  │
 ▼          ▼           ▼              ▼                 ▼                  ▼
Dashboard  OAuth      Smart defaults  Bootstrap         Output in          Dashboard
empty      (direct)   + background    scaffolds         inbox/channel      shows project
state                 sync starts     project + PM      or in-app          health
```

---

## Stage 1: First Open (Dashboard Empty State)

### User state
- Authenticated via Supabase Auth
- No connected platforms
- No projects

### Experience

Dashboard shows a clean welcome with **two paths**:

```
┌──────────────────────────────────────────────────────┐
│              Welcome to YARNNN                       │
│                                                      │
│  Connect your work platforms and YARNNN will create  │
│  projects that deliver recurring insights.           │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐                    │
│  │ [Slack]      │  │ [Gmail]      │  ← OAuth direct  │
│  │  Slack       │  │  Gmail       │                   │
│  ├─────────────┤  ├─────────────┤                    │
│  │ [Notion]     │  │ [Calendar]   │                   │
│  │  Notion      │  │  Calendar    │                   │
│  └─────────────┘  └─────────────┘                    │
│                                                      │
│  ──────────────── or ────────────────                │
│                                                      │
│  [⌘] Ask the Orchestrator                            │
│      Create projects for topics, research, or tasks  │
│      — no platform needed                            │
└──────────────────────────────────────────────────────┘
```

### Design decisions

- **Platform cards trigger OAuth directly** (ADR-113). One click starts the entire flow.
- **Orchestrator is secondary but visible** for topic-first users.
- Both paths lead to the same destination: a project in the Meeting Room.

---

## Stage 2a: Platform Path (Connect → Auto-Sync → Bootstrap Project → Meeting Room)

### Flow

1. **User clicks platform card** → OAuth redirect → callback auto-discovers landscape + auto-selects sources (ADR-113) → kicks off first sync → redirects to `/dashboard?provider={platform}&status=connected`
2. **Dashboard shows transitional state**: platform connected, sync in progress
3. **Onboarding Bootstrap** (ADR-110/122): post-sync, `maybe_bootstrap_project()` calls `scaffold_project(type_key)` which creates:
   - Project folder (`/projects/{slug}/PROJECT.md`)
   - Member agent (e.g., "Slack Agent", role=digest) + seeded `memory/self_assessment.md` (ADR-128)
   - PM agent ("PM: Slack Recap") + seeded `memory/project_assessment.md` (ADR-128)
   - Cognitive files initialized with "awaiting first run/pulse" state — PM sees clean starting signal
   - First agent run executes immediately
4. **Bootstrap banner** appears in Orchestrator: "{Project Title} is ready! → View project"
5. **User clicks through to Meeting Room** at `/projects/{slug}`

### What gets scaffolded (per project type)

| Type Key | Project Title | Member Agent | PM | First Run |
|----------|--------------|-------------|-----|-----------|
| `slack_digest` | Slack Recap | Slack Agent (digest/platform) | PM: Slack Recap | Immediate |
| `gmail_digest` | Gmail Recap | Gmail Agent (digest/platform) | PM: Gmail Recap | Immediate |
| `notion_digest` | Notion Recap | Notion Agent (digest/platform) | PM: Notion Recap | Immediate |

### Source curation (optional)

Users can refine which sources are synced at `/context/{platform}` at any time. This is an escape hatch, not a prerequisite.

---

## Stage 2b: Orchestrator Path (Chat → Create Project → Meeting Room)

### Flow

1. **User clicks a card** in the Orchestrator empty state → message sent to TP
2. **For platform cards**: TP calls `CreateProject(type_key="slack_digest")` → deterministic scaffolding, same as bootstrap
3. **For "New Project" card**: TP calls `CreateProject(title="...", objective={...})` → creates project with PM, user provides contributors/context
4. **Project appears in sidebar** → user navigates to Meeting Room

### Orchestrator empty state cards

```
SET UP A PROJECT
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Slack Recap   │ │ Gmail Recap  │ │ Notion Recap │ │ New Project  │
│ Daily summary │ │ Daily recap  │ │ Daily recap  │ │ Start from   │
│ of channels   │ │ of labels    │ │ of pages     │ │ scratch      │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘

OR ASK DIRECTLY
┌──────────────┐ ┌──────────────┐
│ Search        │ │ Web research │
│ platforms     │ │              │
└──────────────┘ └──────────────┘
```

**Design principles:**
- Platform cards are 1:1 with `PROJECT_TYPE_REGISTRY` entries. No aspirational cards without registry backing.
- "New Project" routes to TP chat which creates the project and points user to the Meeting Room.
- Capability cards (Search, Web research) are orthogonal to project creation — utility actions.
- The plus menu "Create project" action shows the same 4 project cards.

### When to suggest platforms

If a user creates a platform-dependent project via "New Project" but has no platforms connected, TP should:
- Explain that the project needs platform access
- Offer to connect the relevant platform
- Create the project in a pending state

---

## Stage 3: Meeting Room (Post-Creation)

### Project-level onboarding

After project creation, the user lands in the Meeting Room (`/projects/{slug}`). This is where the 60-second magic happens — not in TP chat.

For **platform projects** (bootstrap/template): The project is fully scaffolded. First run is executing or complete. The Meeting Room shows the first output in the timeline.

For **custom projects** (New Project): The Meeting Room is empty. The first-run experience should guide the user to share context and clarify objectives with PM. The conversation IS the onboarding — PM extracts both objective refinement and context from the user's first messages.

### Three-tab architecture (ADR-124)

- **Meeting Room**: Chat with PM + contributor agents, activity timeline
- **Context**: Workspace file browser
- **Settings**: Objective, contributors, delivery, schedule

---

## Stage 4: Supervision (Returning User)

### Dashboard states (progressive)

| State | Condition | Display |
|-------|-----------|---------|
| **Empty** | No platforms, no projects | Two-path welcome (OAuth cards + Orchestrator) |
| **Transitional** | Platforms connected, no projects yet | Connected platforms + syncing + connect more |
| **Active** | 1+ projects | Supervision dashboard (project health, stats, Composer activity) |

### What the active dashboard shows

See [SUPERVISION-DASHBOARD.md](SUPERVISION-DASHBOARD.md) for full specification.

---

## Technical Components

### Frontend

| Component | Location | Purpose |
|-----------|----------|---------|
| Dashboard | `web/app/(authenticated)/dashboard/page.tsx` | Empty + transitional + supervision |
| Orchestrator | `web/components/desk/ChatFirstDesk.tsx` | 3+1 project cards + capability cards + bootstrap banner |
| Meeting Room | `web/app/(authenticated)/projects/[slug]/page.tsx` | Project surface (ADR-124) |
| Projects list | `web/app/(authenticated)/projects/page.tsx` | All projects |
| Context pages | `web/app/(authenticated)/context/` | Source refinement (optional) |

### Backend

| Component | Purpose |
|-----------|---------|
| `scaffold_project()` | Unified project creation (ADR-122) — all flows use this |
| `maybe_bootstrap_project()` | Post-sync bootstrap check + scaffold (ADR-110/122) |
| `CreateProject` primitive | TP/headless project creation → delegates to `scaffold_project()` |
| `PROJECT_TYPE_REGISTRY` | Curated project type definitions (ADR-122) |
| Composer heartbeat | Assesses substrate, suggests/creates projects (ADR-111/120) |

### Data flow

```
Dashboard (empty state)
  ├─ Path A: Platform → OAuth → callback → auto-sync
  │    → /dashboard (transitional) → sync completes
  │    → maybe_bootstrap_project() → scaffold_project(type_key)
  │    → project + member agent + PM + first run
  │    → Orchestrator bootstrap banner → "View project →"
  │    → Meeting Room (/projects/{slug})
  │
  └─ Path B: Orchestrator → click card → TP chat
       → CreateProject(type_key or custom) → scaffold_project()
       → project appears in sidebar → Meeting Room
```

---

## Differences from V5

| Aspect | V5 | V6 (ADR-122/124) |
|--------|----|----|
| Primary unit | Agents | Projects (agents are members inside) |
| Bootstrap creates | Standalone digest agent | Project with member agent + PM |
| Bootstrap banner links to | `/agents/{id}` | `/projects/{slug}` (Meeting Room) |
| Orchestrator cards | 6 project templates (3 aspirational) + 3 capability | 3 registry-backed + 1 blank + 2 capability |
| Post-creation surface | Agent drawer | Meeting Room (group chat with agents) |
| Context/objective refinement | TP chat | Meeting Room (PM conversation) |
| Dashboard supervision | Agent health grid | Project health |
| Composer actions | Creates agents | Creates projects (ADR-120 Phase 5) |

---

## References

- [Supervision Dashboard](SUPERVISION-DASHBOARD.md)
- [ADR-110: Onboarding Bootstrap](../adr/ADR-110-onboarding-bootstrap.md)
- [ADR-113: Auto Source Selection](../adr/ADR-113-auto-source-selection.md)
- [ADR-119: Workspace Filesystem](../adr/ADR-119-workspace-filesystem.md)
- [ADR-122: Project Type Registry](../adr/ADR-122-project-type-registry.md)
- [ADR-124: Project Meeting Room](../adr/ADR-124-project-meeting-room.md)
