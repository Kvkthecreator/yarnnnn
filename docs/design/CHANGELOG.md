# Design Docs — Changelog

Track changes to design documentation structure and active principles.

---

## 2026-04-04 — Agent-centric surface reframe + dedicated chat page

Major surface architecture rewrite. Agents page becomes HOME, tasks dissolve into agent responsibilities, chat becomes a dedicated page.

### Two key shifts
1. **Agent-centric, not task-centric.** The primary working surface lists agents (stable 8-agent roster) with tasks as expandable children. Center panel dispatches by agent class: domain stewards show their directory, synthesizers show deliverables, bots show temporal observations.
2. **Chat as a page, not a drawer.** TP gets its own `/chat` route — full-width, unscoped, strategic. Agent-scoped TP remains as a right panel on the agents page.

### Navigation
`Chat | Agents | Context | Activity` (four-segment toggle bar). Agents is `HOME_ROUTE`.

### Documents updated
- **SURFACE-ARCHITECTURE.md** → v3: full rewrite. Agent-centric page layout, dedicated chat page, four-surface model. Supersedes v2 workfloor + task page.
- **AGENT-PRESENTATION-PRINCIPLES.md** → v2: agents as primary surface (not reference). Class-aware dispatch (domain/deliverable/observations). Tasks as responsibilities.
- **SURFACE-PRIMITIVES-MAP.md** → v2: Chat page + Agents page (agent-scoped + task drill-down) + Context page. Replaces Workfloor + Task Page.
- **TASK-SCOPED-TP.md** → v2: renamed to "Scoped TP". Three scopes: global (chat page), agent-scoped (agents page), task-scoped (drill-down).
- **WORKSPACE-EXPLORER-UI.md** → v2: Tasks folder removed from explorer. Context page shows domains, uploads, settings only.
- **SURFACE-ACTION-MAPPING.md** → updated surface mapping for v3 architecture.

### Documents archived
- **WORKFLOOR-LIVENESS.md** → `archive/` (workfloor dissolved into agents page)
- **WORKSPACE-LAYOUT-NAVIGATION.md** → `archive/` (superseded by SURFACE-ARCHITECTURE.md v3)

### Active docs (10 docs)
| Doc | Purpose |
|-----|---------|
| `SURFACE-ARCHITECTURE.md` | Master layout spec: Chat + Agents + Context + Activity (v3) |
| `AGENT-PRESENTATION-PRINCIPLES.md` | Agent as primary surface, class-aware dispatch (v2) |
| `SURFACE-PRIMITIVES-MAP.md` | Primitive/action mapping per surface (v2) |
| `TASK-SCOPED-TP.md` | Scoped TP: global, agent, task (v2) |
| `WORKSPACE-EXPLORER-UI.md` | Context page explorer (v2, tasks removed) |
| `SURFACE-ACTION-MAPPING.md` | Design principle: directives → chat, config → drawer |
| `INLINE-PLUS-MENU.md` | Verb taxonomy for + menu actions |
| `SHARED-CONTEXT-WORKFLOW.md` | Context update workflow |
| `TP-NOTIFICATION-CHANNEL.md` | FAB badge + notification queueing |
| `FEEDBACK-WORKFLOW-REDESIGN.md` | Feedback collection UX |

### Deferred docs (retained, not updated)
| Doc | Status |
|-----|--------|
| `DELIVERABLE-FIRST-USER-FLOW.md` | Still valid — task creation flow unchanged |
| `TASK-SURFACE-REDESIGN.md` | Task detail views reused in agent drill-down |
| `ONBOARDING-TP-AWARENESS.md` | Cold-start moves to chat page empty state |
| `QUALITY-GATE-DESIGN.md` | Quality gates unchanged |
| `SKILLS-REFRAME.md` | Skills architecture unchanged |
| `FRONTEND-UX-BACKLOG.md` | Needs full review against v3 |

---

## 2026-04-02 — Workfloor explorer shell + mixed file previews

- **Workfloor shifted toward Finder / Windows Explorer mental model** — left panel is now a real hierarchical explorer, center panel is a file/folder browser with breadcrumbs, and TP remains a scoped right drawer.
- **Synthetic explorer roots** — workfloor no longer presents separate semantic surfaces for domains vs. uploads vs. settings. The page synthesizes one explorer root with `Tasks`, `Domains`, `Uploads`, and `Settings` folders while preserving existing visibility rules.
- **Domain browser removed from workfloor** — context domains now open as normal folders/files instead of bespoke entity cards, eliminating the dual navigation model.
- **Details-style directory listing** — folder view now shows `Name`, `Kind`, and `Modified` columns rather than card stacks.
- **Mixed file previews** — file viewer now supports markdown, HTML reports, images/SVG, PDF, CSV, and download-first binary files. `output.html` is previewed inline rather than treated like markdown.
- **Task explorer behavior corrected** — tasks are treated as normal folders inside Workfloor. Clicking task files or outputs now previews them inline in the explorer instead of redirecting into `/tasks/{slug}`.
- **Task page compacted** — `/tasks/{slug}` remains the task management surface, but raw spec and run-log content are collapsed by default and redundant output header duplication was removed.
- **Show/hide behavior preserved** — left explorer collapse and right TP drawer collapse remain intact; the refactor changes navigation semantics, not the panel affordances.
- Updated: `WORKSPACE-EXPLORER-UI.md`, `TASK-SCOPED-TP.md`, `workspace-conventions.md`.

---

## 2026-03-30 — Workfloor overlay layout + button consolidation

- **Habbo-style overlay layout** — Isometric room fills viewport as ambient backdrop. Tasks/Context panel and Chat panel float as semi-transparent overlapping windows (`bg-background/90 backdrop-blur-md`). Both collapsible. Everything visible in one screen — no vertical stacking.
- **Bottom action bar** — Centered, always visible: `+ New Task`, `Update Context`, plus toggle buttons for collapsed panels.
- **Button consolidation** — Separate "Update my identity" and "Update my brand" merged into single "Update context" across: bottom action bar, PlusMenu, suggestion chips. TP decides which target via `UpdateContext(target=...)` primitive (ADR-146).
- **WorkspaceLayout removed** from workfloor — page now manages its own overlay layout instead of using the shared two-column WorkspaceLayout component.
- Updated: `SURFACE-ARCHITECTURE.md` (workfloor section), `SHARED-CONTEXT-WORKFLOW.md` (button consolidation + layout).

---

## 2026-03-22 — Dashboard collapsed into Orchestrator

- **Dashboard page deleted** — `/dashboard` route, backend endpoint (`/api/dashboard/summary`), and API client method removed.
- **Orchestrator is the single landing page** — `HOME_ROUTE = "/orchestrator"`. Post-login and post-OAuth redirects land here.
- **Cold-start onboarding integrated** — Orchestrator empty state shows platform connect cards (Slack, Notion) when no platforms connected, with "or" divider to "New Project" card.
- **Sessions tab removed** — Sessions are infrastructure, not product. Orchestrator panel: Projects + Platforms only.
- **Navigation simplified** — Dropdown: Orchestrator (home) + Projects. Dashboard entry removed. `ORCHESTRATOR_ROUTE` alias deleted — `HOME_ROUTE` is the canonical reference.
- Updated: `WORKSPACE-LAYOUT-NAVIGATION.md` (v4).

### Active docs (6 docs)
| Doc | Purpose |
|-----|---------|
| `SURFACE-ACTION-MAPPING.md` | Design principle: directives → chat, configuration → drawer |
| `INLINE-PLUS-MENU.md` | Verb taxonomy (show/execute/prompt/attach) for + menu actions |
| `WORKSPACE-LAYOUT-NAVIGATION.md` | Canonical layout architecture (WorkspaceLayout, scoped chat, WorkfloorView) |
| `AGENT-PRESENTATION-PRINCIPLES.md` | Agent frontend: source-first grouping, card anatomy, creation flow, cognitive state |
| `PROJECTS-PRODUCT-DIRECTION.md` | Projects as product direction, settled decisions |
| `COGNITIVE-DASHBOARD-DESIGN.md` | ADR-128 Phase 6: cognitive state surfacing on Workfloor + Team panel |

---

## 2026-03-21 — ADR-128 Phase 6: Cognitive Dashboard Design

- New active doc: `COGNITIVE-DASHBOARD-DESIGN.md`
- **Workfloor evolution**: pulse-only agent cards → pulse + cognitive state. Contributor cards show 4-bar assessment (mandate/fitness/context/output) with level indicators. PM card shows 5-layer constraint indicator (commitment → readiness). "All dimensions healthy" compression when everything is fine.
- **InlineProfileCard enrichment**: Self-assessment section + confidence trajectory sparkline (5-square) added between developmental state and thesis.
- **Backend**: `get_project()` enrichment loop now parses `self_assessment.md` → `cognitive_state` per contributor, `project_assessment.md` → `project_cognitive_state`.
- **Types**: `CognitiveAssessment`, `PMCognitiveState` added to `web/types/index.ts`.
- Updated: `AGENT-PRESENTATION-PRINCIPLES.md` (Principle 8), `WORKSPACE-LAYOUT-NAVIGATION.md` (v3), `PROJECTS-PRODUCT-DIRECTION.md` (settled decision #9).
- Related: ADR-128 (governing ADR, Phases 0-5 built the data substrate, Phase 6 builds the view)

### Active docs (6 docs)
| Doc | Purpose |
|-----|---------|
| `SURFACE-ACTION-MAPPING.md` | Design principle: directives → chat, configuration → drawer |
| `INLINE-PLUS-MENU.md` | Verb taxonomy (show/execute/prompt/attach) for + menu actions |
| `WORKSPACE-LAYOUT-NAVIGATION.md` | Canonical layout architecture (WorkspaceLayout, scoped chat, WorkfloorView) |
| `AGENT-PRESENTATION-PRINCIPLES.md` | Agent frontend: source-first grouping, card anatomy, creation flow, cognitive state |
| `PROJECTS-PRODUCT-DIRECTION.md` | Projects as product direction, settled decisions |
| `COGNITIVE-DASHBOARD-DESIGN.md` | ADR-128 Phase 6: cognitive state surfacing on Workfloor + Team panel |

---

## 2026-03-13 — ADR-110 & ADR-111: Onboarding Bootstrap + Agent Composer (Proposed)

- **ADR-110**: Deterministic agent auto-creation post-platform-connection. Targets <60s time-to-first-value. Bootstrap service creates matching digest agent on first sync completion (Slack→Recap, Gmail→Digest, Notion→Summary). `origin=system_bootstrap`.
- **ADR-111**: Agent Composer — assessment + scaffolding layer. Unifies Write/CreateAgent into single `CreateAgent` primitive (chat + headless). Introduces substrate assessment pipeline. Makes knowledge/research/autonomous agents discoverable through substrate matching.
- Updated docs: primitives.md, agents.md (new origin values), agent-framework.md (bootstrap templates), agent-execution-model.md (planned unification notes), agent-types.md, CLAUDE.md
- **Implication**: Agent creation gains two new paths: bootstrap (automatic, high-confidence) and composed (substrate-assessed, medium-confidence via TP). CreateAgent primitive planned to replace Write for agent creation.

---

## 2026-03-13 — Agent Presentation Principles

- New active doc: `AGENT-PRESENTATION-PRINCIPLES.md`
- Defines first-principled frontend presentation rules for agents as the portfolio grows
- **Core insight**: Users think source-first (platform), not skill-first (processing verb)
- **7 principles**: Source-first mental model, progressive disclosure, card anatomy (source → routine → status), source-affinity grouping, skills as behavioral labels, taxonomy-expansion resilience, chat as long-term creation surface
- **Creation flow**: Source → Job → Configure (inverts current type-first picker)
- **Grouping**: Platform icons as primary visual, source-affinity sections at 6+ agents
- **Template-driven**: Creation options derive from backend config, not hardcoded grids
- Related: agent-framework.md (Scope × Skill × Trigger), SURFACE-ACTION-MAPPING.md, ADR-105

### Active docs (4 docs)
| Doc | Purpose |
|-----|---------|
| `SURFACE-ACTION-MAPPING.md` | Design principle: directives → chat, configuration → drawer |
| `INLINE-PLUS-MENU.md` | Verb taxonomy (show/execute/prompt/attach) for + menu actions |
| `WORKSPACE-LAYOUT-NAVIGATION.md` | Canonical layout architecture (WorkspaceLayout, scoped chat) |
| `AGENT-PRESENTATION-PRINCIPLES.md` | Agent frontend: source-first grouping, card anatomy, creation flow |

---

## 2026-03-12 — Context page: knowledge-first landing + file CRUD + versioning

- Default landing changed from `platforms` to `knowledge` (context page + sidebar)
- Knowledge files now clickable with full-content detail view (back-nav pattern)
- User-contributed file creation: title + content class + markdown content
- **ADR-107 Phase 2: Version management** — `KnowledgeBase.write()` auto-archives existing content as `v{N}.md` before overwrite; version history in detail view; `v*.md` excluded from main list
- Backend: `GET /api/knowledge/files/read` + `POST /api/knowledge/files` + `GET /api/knowledge/files/versions`
- Frontend types: `KnowledgeFileDetail`, `KnowledgeFileCreateInput`, `KnowledgeVersion`, `KnowledgeVersionsResponse`
- API client: `knowledge.readFile(path)`, `knowledge.createFile(data)`, `knowledge.listVersions(path)`
- Related: ADR-107 (knowledge filesystem), ADR-106 (workspace architecture)

---

## 2026-03-11 — Archive shipped specs, establish active/archive structure

### Structure
- Created `archive/` subfolder for implemented and superseded design specs
- Active docs remain in `docs/design/` root

### Active (3 docs)
| Doc | Purpose |
|-----|---------|
| `SURFACE-ACTION-MAPPING.md` | Design principle: directives → chat, configuration → drawer |
| `INLINE-PLUS-MENU.md` | Verb taxonomy (show/execute/prompt/attach) for + menu actions |
| `WORKSPACE-LAYOUT-NAVIGATION.md` | Canonical layout architecture (WorkspaceLayout, scoped chat) |

### Archived (9 docs → `archive/`)
| Doc | Reason |
|-----|--------|
| `ACTIVITY-PAGE-POLISH.md` | Implemented 2026-03-05 |
| `CHAT-FILE-UPLOAD-IMPROVEMENTS.md` | Partially implemented (drag-drop, paste shipped) |
| `DELIVERABLE-CREATE-FLOW-FIX.md` | Implemented 2026-03-05 |
| `DELIVERABLES-LIST-CREATE-OVERHAUL.md` | Implemented 2026-03-05 |
| `DELIVERABLES-WORKSPACE-OVERHAUL.md` | Implemented 2026-03-05 |
| `WORKSPACE-DRAWER-REFACTOR.md` | Implemented 2026-03-05 |
| `SURFACE-LAYOUT-PHASE3-HISTORY.md` | Superseded by WORKSPACE-LAYOUT-NAVIGATION |
| `USER_FLOW_ONBOARDING_V2.md` | Implemented (content is V3 despite filename) |
| `LANDING-PAGE-NARRATIVE-V2.md` | Draft, never implemented |

### Cross-reference updates
- `SURFACE-ACTION-MAPPING.md`: updated link to archived WORKSPACE-DRAWER-REFACTOR
- `INLINE-PLUS-MENU.md`: updated link to archived CHAT-FILE-UPLOAD-IMPROVEMENTS
- `WORKSPACE-LAYOUT-NAVIGATION.md`: updated link to archived SURFACE-LAYOUT-PHASE3-HISTORY
