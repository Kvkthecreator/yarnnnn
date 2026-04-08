# Design Docs — Changelog

Track changes to design documentation structure and active principles.

---

## 2026-04-08 — ADR-165 v5: Workspace state surface (single-component, TP-directed)

- **ADR-165 rewritten to v5** and renamed: `ADR-165-chat-artifact-surface.md` → `ADR-165-workspace-state-surface.md`. Same ADR number, same in-doc revision history (v1→v5), new file name to reflect the corrected concept.
- **Design doc renamed**: `CHAT-ARTIFACT-SURFACE.md` → `WORKSPACE-STATE-SURFACE.md`. Full rewrite — the v4 model (four sibling artifacts in a tab strip) is replaced by one component with four lead views.
- **Conceptual inversion**: v4 was "always-on tab strip + 38vh card with four sibling artifacts." v5 is "TP chat is the page; workspace state is one on-demand surface that opens when TP or the user asks." Three of the four v4 artifacts (Daily Briefing, Recent Work, Context Gaps) collapse into facets of one component because they read from the same data and answer adjacent questions. The fourth (Onboarding) is the gate path of the same component.
- **TP becomes the surface opener** (single intelligence layer per ADR-156). New marker pattern: TP appends `<!-- workspace-state: {"lead":"...","reason":"..."} -->` as the LAST line of an assistant message. Same parser philosophy as ADR-162's `inference-meta` marker — frontend strips before display, parses for directive, opens the surface.
- **New file**: `web/lib/workspace-state-meta.ts` — `parseWorkspaceStateMeta()` + `stripWorkspaceStateMeta()`.
- **New file**: `web/components/chat-surface/WorkspaceStateView.tsx` — single component with four lead views (`empty | briefing | recent | gaps`) as internal state branches, lens switcher, header with reason/close.
- **Rewrote**: `web/components/chat-surface/ChatSurface.tsx` — owns surface open state, watches `messages` for TP markers, injects "Update my context" plus-menu action, renders `WorkspaceStateView` as `ChatPanel`'s `topContent` only when open.
- **Touched**: `web/components/tp/ChatPanel.tsx` — strips marker before display via `stripWorkspaceStateMeta`, accepts new `inputRowAddon` prop for the workspace-state toggle icon.
- **Touched**: `web/components/tp/InlineToolCall.tsx` — strips marker from `MessageBlocks` text-block render path.
- **Touched**: `web/app/(authenticated)/chat/page.tsx` — passes only first-party plus-menu actions (Create a task), removes the no-op `update-context`/`web-search`/`upload-file` stubs (cleanup of dead code).
- **TP prompt update**: `api/agents/tp_prompts/onboarding.py` gains a "Workspace State Surface (ADR-165 v5)" section under `CONTEXT_AWARENESS`. Tight initial ruleset — at most one marker per message, steady-state silence is correct. See `api/prompts/CHANGELOG.md` entry `[2026.04.08.3]`.
- **Chat column width fix** (independent, landed in same commit): `/chat` page wrapper changes from `max-w-5xl` (1024px) to `max-w-3xl` (768px). Claude Code parity. The textarea inherits the cap.
- **Files DELETED** (singular implementation, no parallel paths):
  - `web/components/chat-surface/ChatArtifactCard.tsx`
  - `web/components/chat-surface/ChatArtifactTabs.tsx`
  - `web/components/chat-surface/chatArtifactTypes.ts`
  - `web/components/chat-surface/artifacts/ContextGapsArtifact.tsx`
  - `web/components/chat-surface/artifacts/DailyBriefingArtifact.tsx`
  - `web/components/chat-surface/artifacts/OnboardingArtifact.tsx`
  - `web/components/chat-surface/artifacts/RecentWorkArtifact.tsx`
  - `web/components/chat-surface/artifacts/` directory itself
- **SURFACE-ARCHITECTURE.md** Chat section updated with the new file map and the renamed ADR pointer.

---

## 2026-04-08 — ADR-167 v2: Breadcrumb collapse into PageHeader

- **ADR-167 amended in place** with a "V2 Amendment — Breadcrumb collapse into PageHeader" section. Same intent (the breadcrumb-as-navigation thesis from b033513 + ADR-167's surface mode collapse), now landing the visual simplification: the breadcrumb moves out of the global layout and into the first row of each surface as a `<PageHeader />` component.
- **SURFACE-ARCHITECTURE.md → v9.1**: Top Bar now described as just logo + toggle + avatar. New "Page header" section documents the in-page breadcrumb pattern. Work/Agents detail-mode diagrams updated. Component map updated with `PageHeader.tsx` (new) and removes `GlobalBreadcrumb.tsx` (deleted).
- **New file**: `web/components/shell/PageHeader.tsx` — consumes `BreadcrumbContext`, renders segments inline with optional `subtitle` and `actions` slots.
- **Deleted file**: `web/components/shell/GlobalBreadcrumb.tsx` — replaced entirely.
- **Deleted bands**: `WorkDetail`'s internal `<WorkHeader>` (title + status row + Next/Last) and `<ActionsRow>` (Run/Pause/Edit-via-chat). Both move UP into PageHeader. WorkDetail is now content-only: Objective + KindMiddle + AssignedAgent footer.
- **Deleted bands**: `AgentContentView`'s internal `<AgentHeader>` (avatar + name + mandate + class · domain · task count). Same move — metadata strip becomes PageHeader subtitle. AgentContentView is now content-only: IdentityCard + HealthCard.
- **Removed visual**: `★ Essential` badge next to task titles. The `essential` flag stays in the schema and DB (load-bearing for archive guard); only the visual badge is gone. Users discover it functionally when archive is rejected.
- **Bug fix included**: `meta-cognitive` class label was missing from `CLASS_LABELS` in `AgentContentView` and `agents/page.tsx` (introduced by ADR-164). TP was rendering as the raw `meta-cognitive` key. Added.

---

## 2026-04-08 — ADR-167: List/detail surfaces with kind-aware detail

- **New ADR**: `ADR-167-list-detail-surfaces.md` — collapses `/work` and `/agents` from master-detail (left list + center detail + chat) into single surfaces with two URL-driven modes: list mode (full-width filterable list / roster) and detail mode (kind-aware detail).
- **SURFACE-ARCHITECTURE.md → v9**: documents the list/detail collapse, the four kind-aware middle components in `web/components/work/details/`, and the deletion of `WorkList`/`AgentTreeNav`/`ThreePanelLayout.leftPanel` requirement.
- **Component map updated** with `WorkListSurface`, `AgentRosterSurface`, and the four `details/*Middle.tsx` files.
- **Migration note added**: when adding a new way to render a task in detail mode, add a new middle component dispatched from `WorkDetail`'s switch on `task.output_kind` — do not branch inside an existing middle component.
- Auto-select-first behavior on `/work` and `/agents` is GONE. Landing on either page shows the list/roster, never someone else's task or agent by accident. The breadcrumb (commit b033513) drives navigation between modes — its promise of "click `Work` to go back to overview" is now deliverable.

---

## 2026-04-08 — Chat artifact surface

- **Breadcrumb scope bar**: `BreadcrumbContext` now supports route-backed `href` segments; `GlobalBreadcrumb` renders a centered linkable scope path under the four-toggle nav. Work, Agents, and Context emit deeper linkable paths, and Context supports `?path=` deep-linking.
- **New design doc**: `CHAT-ARTIFACT-SURFACE.md` — documents `/chat` as one TP chat surface with a tab-selected structured artifact.
- **New ADR**: `ADR-165-chat-artifact-surface.md` — keeps ADR-163's four top-level surfaces intact while changing only the internal layout methodology of `/chat`.
- **First implementation**: `/chat` now uses `web/components/chat-surface/`; the earlier `command-desk` window package was removed after the multi-window layout proved visually unintuitive.
- **SURFACE-ARCHITECTURE.md** updated with an ADR-165 active-decision pointer and v8.1 revision-history entry.

---

## 2026-04-05b — Onboarding scaffold + daily briefing + Home page

- **New design doc**: `ONBOARDING-SCAFFOLD-AND-BRIEFING.md` — onboarding scaffolds everything (directories → entities → tasks → trigger → briefing), daily briefing as persistent collapsible header, Home page rename, agent work rhythm framing.
- **Chat → Home rename**: Nav label changes from "Chat" to "Home". Route stays `/chat`. Home page shows daily briefing (what happened, coming up, needs attention, workspace signals) above TP chat. Briefing is persistent — auto-collapses after first message but never disappears.
- **Onboarding scaffold sequence**: After entity confirmation gate, TP auto-creates default tasks for populated domains and triggers immediate execution. Synthesis tasks trigger after context tasks complete. All orchestrated via existing primitives (CreateTask, ManageTask trigger).
- **Agent work rhythm**: UI framing shift — "Works weekly" not "Scheduled weekly." Display-only, no data model change. Schedule stays on tasks table.
- **SURFACE-ARCHITECTURE.md** updated: Home page section, route map, navigation bar.

### Active docs (11 docs)
| Doc | Purpose |
|-----|---------|
| `SURFACE-ARCHITECTURE.md` | Master layout spec (v4, three-tab + Home page) |
| `AGENT-PRESENTATION-PRINCIPLES.md` | Knowledge-first agent view (v3) |
| `ONBOARDING-SCAFFOLD-AND-BRIEFING.md` | Onboarding scaffold, daily briefing, Home page (NEW) |
| `SURFACE-PRIMITIVES-MAP.md` | Primitive/action mapping per surface (v2) |
| `TASK-SCOPED-TP.md` | Scoped TP: global, agent, task (v2) |
| `WORKSPACE-EXPLORER-UI.md` | Context page explorer (v2) |
| `ONBOARDING-TP-AWARENESS.md` | /chat as onboarding home (v2) |
| `SURFACE-ACTION-MAPPING.md` | Directives → chat, config → drawer |
| `INLINE-PLUS-MENU.md` | Verb taxonomy for + menu actions |
| `SHARED-CONTEXT-WORKFLOW.md` | Context update workflow |
| `DELIVERABLE-FIRST-USER-FLOW.md` | Task creation flow |

---

## 2026-04-05 — Three-tab center panel + knowledge-first agent view

Major center panel redesign. Agent tab shows knowledge as hero, task metadata collapses to a single status line. Setup tab for task configuration. Settings tab for identity/history/feedback.

### Key shifts from v3
1. **Knowledge is the hero.** Agent tab default shows domain browser (stewards), output viewer (synthesizers), or observations (bots) — filling 90% of the space. Task cards removed from default view.
2. **Three-tab center panel.** Agent / Setup / Settings replaces the vertical stack (header → task cards → domain files). Each tab serves a distinct user intent at decreasing frequency.
3. **Task naming convention.** Task names are freeform — never include frequency, agent name, or type classification. Schedule is config, not identity.
4. **TP-mediated actions.** Setup tab uses action buttons (Run Now, Pause) and "Edit via TP →" links rather than inline CRUD forms.
5. **Left panel simplified.** Section labels renamed: Your Team / Cross-Team / Integrations. Filter pills removed (roster is fixed).

### Documents updated
- **SURFACE-ARCHITECTURE.md** → v4: three-tab center panel, task naming convention, updated implementation sequence.
- **AGENT-PRESENTATION-PRINCIPLES.md** → v3: knowledge-first, three-tab model, 8 principles rewritten.

### Documents superseded
- **FRONTEND-UX-BACKLOG.md** → SUPERSEDED (workfloor + /tasks/[slug] concepts dissolved)
- **TASK-SURFACE-REDESIGN.md** → SUPERSEDED (task detail tabs absorbed into agent Setup/Settings tabs)

### Active docs (10 docs)
| Doc | Purpose |
|-----|---------|
| `SURFACE-ARCHITECTURE.md` | Master layout spec: Chat + Agents + Context + Activity (v4, three-tab center panel) |
| `AGENT-PRESENTATION-PRINCIPLES.md` | Knowledge-first agent view, three-tab model (v3) |
| `SURFACE-PRIMITIVES-MAP.md` | Primitive/action mapping per surface (v2) |
| `TASK-SCOPED-TP.md` | Scoped TP: global, agent, task (v2) |
| `WORKSPACE-EXPLORER-UI.md` | Context page explorer (v2, tasks removed) |
| `ONBOARDING-TP-AWARENESS.md` | /chat as onboarding home (v2) |
| `SURFACE-ACTION-MAPPING.md` | Design principle: directives → chat, config → drawer |
| `INLINE-PLUS-MENU.md` | Verb taxonomy for + menu actions |
| `SHARED-CONTEXT-WORKFLOW.md` | Context update workflow |
| `DELIVERABLE-FIRST-USER-FLOW.md` | Task creation flow (still valid) |

---

## 2026-04-04b — Onboarding consolidated on /chat + navigation cleanup

- **Onboarding migrated to /chat**: ContextSetup renders as chat page empty state. New users (0 tasks) redirected from auth callback to `/chat` instead of `/agents`.
- **Context page cleanup**: setup-phase hero removed (ContextSetup no longer renders on context page). Context page is pure browsing.
- **Agents page cleanup**: ContextSetup removed from chat empty state. Simple prompt text instead.
- **NAVIGATE ui_actions**: `/tasks/{slug}` → `/agents` in CreateTask and ManageTask primitives.
- **Hardcoded /tasks links fixed**: activity page, AuthenticatedLayout surface handler, orchestrator redirect all point to `/agents`.
- **Middleware**: `/chat` added to protected route prefixes.
- Updated: `ONBOARDING-TP-AWARENESS.md` (v2 — /chat as onboarding home), `SURFACE-ARCHITECTURE.md` (cold-start section).

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
