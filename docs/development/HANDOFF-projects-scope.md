# Handoff: Projects — Backend + Frontend Scope

**Context**: This handoff covers implementing projects as a first-class concept per ADR-119 Phase 2 and the design direction in `docs/design/PROJECTS-PRODUCT-DIRECTION.md`.
**Dependencies**: ADR-119 Phase 1 (output folders + lifecycle) ✅ implemented. ADR-118 D.1-D.3 ✅ implemented.
**Parallel work**: Can run alongside ADR-117 Phase 1 (feedback distillation) — different files.

## Settled Decisions (do not re-litigate)

1. Projects are optional, not mandatory. Standalone agents are valid.
2. Agents can contribute to multiple projects.
3. Platform sync is invisible infrastructure; digest agents are visible workers with full feedback loops.
4. Composer manages project assembly (writes to `/assembly/`). No dedicated coordinator agent.
5. Projects are ongoing, not scheduled. Composer assembles when contributions change.
6. Contributing agents read project context (PROJECT.md, memory/preferences.md) via ReadAgentContext.
7. TP/Composer is the single conversational surface for project management.

## Backend Scope (ADR-119 Phase 2)

### New primitives

**CreateProject** — analogous to CreateAgent
- Creates `/projects/{slug}/PROJECT.md` with title, description, contributor list, output expectations
- Creates `/projects/{slug}/memory/` directory
- Returns project metadata
- Available to Composer (chat mode)

**ReadProject** — reads project context
- Returns PROJECT.md content + contributor listing + latest assembly manifest
- Extend ReadAgentContext to handle `/projects/` paths for contributing agents

### Workspace changes

**AgentWorkspace extensions**:
- `contribute_to_project(project_slug, files)` — writes to `/projects/{slug}/contributions/{own-slug}/`
- Validate write permissions: agents can only write to their own contribution subfolder

**New class or methods on workspace.py**:
- `ProjectWorkspace` (analogous to AgentWorkspace, scoped to `/projects/{slug}/`)
- `read_project(slug)` → PROJECT.md content (parsed: intent, contributors, assembly spec, delivery)
- `list_contributors(slug)` → agent slugs with contribution paths + expected contributions
- `assemble(slug, files)` → writes to `/projects/{slug}/assembly/{date}/` with manifest
- `list_assemblies(slug)` → dated assembly folders with manifest data
- `update_project(slug, updates)` → modifies PROJECT.md sections

### PROJECT.md schema

PROJECT.md carries more than AGENT.md — it's a coordination contract:
- **Intent**: what the project produces, who it's for, why (upstream of agent instructions)
- **Contributors**: agent roster with expected contributions per agent
- **Assembly spec**: how contributions combine — ordering, sections, format, skill requirements
- **Delivery**: destination channel, recipients, format preferences

Full schema with examples in `docs/design/PROJECTS-PRODUCT-DIRECTION.md` (PROJECT.md schema section).

### CreateProject flow (requirements propagation)

CreateProject is more complex than CreateAgent because intent creates downstream requirements:

1. Parse intent → extract output format requirements → determine which skills needed
2. Identify/create contributing agents → check existing agents, create missing ones
3. Check skill authorization → contributing agents + output gateway have required skills
4. Write PROJECT.md with full coordination contract
5. Create folder structure (`/memory/`, `/contributions/`, `/assembly/`)
6. Notify contributing agents (project context injected on next run)

**EditProject cascades**: changing intent (e.g., "make it a PPTX deck") changes assembly spec → changes skill requirements → may need contributor skill re-authorization. Adding/removing contributors updates PROJECT.md roster and affects next assembly.

**ArchiveProject**: status → archived, all files lifecycle → archived. Contributing agents NOT affected — they continue standalone.

### Composer changes

**Project creation heuristics** in `api/services/composer.py`:
- In heartbeat assessment, detect cross-agent consumption patterns (agent A's output in agent B's manifest sources)
- When detected, propose project creation as a Composer action
- Composer prompt needs project-awareness: can suggest "combine these agents into a project"
- Intent inference: Composer infers deliverable type, audience, format from agent roles and user context

**Project assembly** in Composer:
- When Composer detects contributions have changed since last assembly, trigger assembly
- Read PROJECT.md intent + assembly spec to understand desired output
- Read all contribution folders for current content
- Invoke output gateway skills as needed (pptx, pdf, chart per assembly spec)
- Write assembled output to `/assembly/{date}/` with manifest
- Update manifest with delivery status after sending
- Assembly reads project memory/preferences.md for learned assembly preferences

### Agent execution changes

**Context injection for contributing agents**:
- During `load_context()`, if agent contributes to projects, inject PROJECT.md (intent section) and project memory/preferences.md
- This gives contributing agents awareness of what the project needs, shaping their outputs
- The intent flows downstream: "this is for an executive audience" influences how the Slack digest agent summarizes

### Routes

**New API routes** (`api/routes/projects.py`):
- `GET /api/projects` — list projects for user (title, status, contributor count, last assembly)
- `GET /api/projects/{slug}` — project detail (PROJECT.md parsed, contributors with health, assemblies)
- `POST /api/projects` — create project (via API, alternative to Composer chat)
- `PATCH /api/projects/{slug}` — update PROJECT.md (intent, contributors, assembly spec, delivery)
- `PATCH /api/projects/{slug}/contributors` — add/remove contributing agents
- `DELETE /api/projects/{slug}` — archive project (soft delete, contributors unaffected)

## Frontend Scope

### New pages

**Project list** (`/projects`):
- Grid of project cards with title, contributor count, last assembly, delivery status
- Empty state: "Projects combine outputs from multiple agents..."
- Create button → navigates to Orchestrator with project creation intent

**Project detail** (`/projects/[slug]`):
- Reuse WorkspaceLayout pattern from agent detail
- Chat area: talk to Composer about this project
- Panel tabs: Assembly (outputs), Contributors (agent list), Instructions (PROJECT.md), Memory, Settings
- See `PROJECTS-PRODUCT-DIRECTION.md` for wireframe

### Dashboard updates

**Add Projects section** above agent grid:
- Project cards: title, contributors (platform icons), last assembly, format badges
- When zero projects: prompt text encouraging creation
- Composer activity feed: include project-related actions (created, assembled, suggested)

### Agent detail updates

**Project membership indicator**:
- If agent contributes to projects, show badges: "Contributing to: Monday Brief, Q2 Review"
- Badge links to project detail page
- Breadcrumb when navigated from project: "← Your Monday Brief / Slack Agent"

### Navigation updates

Add "Projects" to primary nav dropdown (between Orchestrator and Agents).

### Routes file

Add to `web/lib/routes.ts`:
```typescript
export const PROJECTS_ROUTE = '/projects'
export const PROJECT_DETAIL_ROUTE = (slug: string) => `/projects/${slug}`
```

## Design references

- `docs/design/PROJECTS-PRODUCT-DIRECTION.md` — full product direction with wireframes and settled decisions
- `docs/design/SUPERVISION-DASHBOARD.md` — current v1 dashboard (extend, don't replace)
- `docs/design/AGENT-PRESENTATION-PRINCIPLES.md` — source-first mental model (extends to project-first grouping)
- `docs/adr/ADR-119-workspace-filesystem-architecture.md` — project folder conventions, resolved decisions 4-10

## Files NOT to touch

- Bootstrap/onboarding flow — no changes. Projects introduced post-onboarding.
- Agent creation flow — no changes. Standalone agents created as before.
- Platform sync — no changes. Infrastructure layer unaffected.
- ADR-118, ADR-119, agent-framework.md — already updated in this session.

## Suggested implementation order

1. Backend: ProjectWorkspace class + CreateProject primitive + ReadProject primitive
2. Backend: API routes for projects CRUD
3. Backend: Composer project creation heuristics (heartbeat assessment)
4. Backend: Context injection for contributing agents
5. Frontend: Project list page + project detail page
6. Frontend: Dashboard v2 (projects section)
7. Frontend: Agent detail project membership indicator
8. Backend: Composer assembly logic (read contributions, invoke gateway, write assembly)

Steps 1-4 can be done without any frontend. Steps 5-7 can be done against mock data. Step 8 is the integration that makes it end-to-end.
