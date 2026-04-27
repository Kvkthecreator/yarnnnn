# Work Surface Audit — 2026-04-27

**Status:** Archived 2026-04-27 — observations absorbed into [ADR-225 Phase 3](../../adr/ADR-225-compositor-layer.md), [SURFACE-CONTRACTS.md v2.0](../SURFACE-CONTRACTS.md), and [docs/architecture/compositor.md](../../architecture/compositor.md). Preserved here for the trail but not canonical. The audit's observation #3 (kind switch fires three times in one detail-page render) was the load-bearing pressure point that motivated Phase 3.

**Method:** Read-only observation. No proposals, no opinions.

---

## 1. Component Inventory

### Page-level (list + detail modes)

[page.tsx](/web/app/(authenticated)/work/page.tsx:75-409)
- Root entry point for `/work`. Maintains mode toggle (list vs detail via `?task={slug}` param), task detail fetch, action state (run/pause/refresh), breadcrumb context, and chat sidebar integration.
- List mode: renders BriefingStrip (cockpit zone) + WorkListSurface. Detail mode: renders WorkDetail.
- Data sources: `useAgentsAndTasks()` (returns tasks[], agents[], narrativeByTask per ADR-219 Commit 4), `useTaskDetail()` (fetches selected task detail).
- Notable: breadcrumb logic (lines 118-165) distinguishes between `?agent=` deep-links (traces Agents surface navigation) vs. standard Work navigation (task-first per ADR-167 v5).

### List-mode components

[WorkListSurface.tsx](/web/components/work/WorkListSurface.tsx:250-453)
- Full-width list with three tabs: "My Work" (grouped by output_kind), "Connectors" (grouped by platform), "System" (flat).
- Renders WorkRow for each task; emits onSelect(slug) to parent page, which pushes router state.
- Data sources: tasks[], agents[], narrativeByTask Map (ADR-219 Commit 4); partitions into tab buckets (myWork, connectors, system).
- Search + agent filter apply independently within active tab. `includeHistorical` checkbox filters out archived/completed in "My Work" only.
- Notable conditional: group headers hidden when tab has ≤1 group (line 324, flattenMyWork).

[WorkRow](/web/components/work/WorkListSurface.tsx:457-579)
- Individual task row. Renders: status dot + kind icon, title + metadata (schedule, assigned agents), time signal (next-run or last narrative headline), clickable button surface.
- Narrative integration (lines 492-511): replaces legacy last_run_at timestamp. Shows `Next: X ago` for active scheduled tasks; for inactive tasks, shows most-recent narrative headline if available, else no headline (per ADR-219 Commit 4 discipline rule 1).

[BriefingStrip.tsx](/web/components/work/briefing/BriefingStrip.tsx:50-74)
- Four-pane cockpit zone rendered above list-mode. Mounts only when no agent filter active (line 381 in page.tsx).
- Composition order per ADR-206 (deliverables-first): NeedsMePane (proposals) → SnapshotPane (money-truth) → SinceLastLookPane (temporal changes) → IntelligenceCard (synthesis).
- Child components: NeedsMePane, SnapshotPane, SinceLastLookPane, IntelligenceCard (all in `/work/briefing/`).

[NeedsMePane.tsx](/web/components/work/briefing/NeedsMePane.tsx)
- Pending approval proposals queue (most urgent per ADR-206). Filterable by signal class.

[SnapshotPane.tsx](/web/components/work/briefing/SnapshotPane.tsx)
- Dashboard snippets (portfolio, P&L, risk gauge). Includes "money-truth" tile pulling from `_performance.md` headline.

[SinceLastLookPane.tsx](/web/components/work/briefing/SinceLastLookPane.tsx)
- Recent activity summaries (task runs, context updates) since last session.

[IntelligenceCard.tsx](/web/components/work/briefing/IntelligenceCard.tsx)
- Synthesis artifact (e.g., daily briefing summary). May embed TaskOutputCard for rendering.

### Detail-mode components

[WorkDetail.tsx](/web/components/work/WorkDetail.tsx:407-515)
- Center panel for selected task. Sticky chrome: SurfaceIdentityHeader (title + per-kind metadata strip + per-kind actions), ObjectiveBlock (collapsed). Scrollable body: MiddleResolver (ADR-225 Phase 2, kind-dispatch) + FeedbackStrip.
- Metadata strips (lines 139-305): DeliverableMetadata, TrackingMetadata, ActionMetadata, MaintenanceMetadata. Each kind renders distinct metadata + action affordances.
- Action flows: hardcoded per-kind action clusters (DeliverableActions, TrackingActions, ActionActions, MaintenanceActions). ActionActions includes explicit "Fire" button for external_action tasks (line 340-364).
- OverflowMenu (lines 71-134): Pause/Resume + Edit in chat (always shown for non-terminal tasks). Edit invokes `onOpenChat()` with task-specific prompt.

[MiddleResolver.tsx](/web/components/library/MiddleResolver.tsx:130-175)
- Core ADR-225 Phase 2 dispatcher. Tries bundle-supplied middles first (4-tier match resolution via `resolveMiddle()`), falls through to kernel-default kind-middles (lines 150-174).
- Bundle middles: map library component `kind` → renderer (LIBRARY_COMPONENTS dict, lines 52-63). Currently registers: PerformanceSnapshot, PositionsTable, RiskBudgetGauge, TradingProposalQueue (alpha-trader suite).
- Kernel defaults: TrackingEntityGrid (accumulates_context), DeliverableMiddle (produces_deliverable), ActionMiddle (external_action), MaintenanceMiddle (system_maintenance).
- Note: library components kept in `/components/library/` for now; kernel middles remain in `/work/details/` per Phase 2 implementation refinement (ADR-225 §5).

[DeliverableMiddle.tsx](/web/components/work/details/DeliverableMiddle.tsx:295-382)
- Output iframe + markdown renderer (nested-document pattern per ADR-167 v5). Two tabs: "Output" (latest), "History" (past 20 runs).
- SectionProvenanceStrip (lines 82-103): renders section pills from sys_manifest.json when present (ADR-170). Freshness indicator (fresh/stale/unknown) color-coded.
- QualityContractPanel (lines 109-166): collapsible quality criteria + audience + user_preferences from deliverable_spec (ADR-178 Phase 6).
- Data sources: useTaskOutputs(taskSlug, {includeLatest: true, historyLimit: 20, refreshKey}) — API calls /api/tasks/{slug}/outputs/latest + /api/tasks/{slug}/outputs.

[TrackingMiddle.tsx](/web/components/work/details/TrackingMiddle.tsx:216-234)
- ActivityTab (lines 93-206): run receipts (date + one-line summary extracted from first non-header paragraph), expandable latest-run log detail.
- DataContractPanel (collapsible, matching DeliverableMiddle's QualityContractPanel).
- PlatformSourcesSection (line 230): channel/page selector for slack-digest, notion-digest tasks (allows inline source editing per ADR-215 R2).

[TrackingEntityGrid.tsx](/web/components/work/details/TrackingEntityGrid.tsx:1-80)
- Entity cards (icon + name + file count + last-updated). Clicking an entity navigates to `/context?path=...` (section-swap feel).
- Data sources: API call (api.contexts.getDomainContext(domain_key)) returns DomainData with entities[], synthesis_files[].
- Run history strip below grid (compact activity log).

[ActionMiddle.tsx](/web/components/work/details/ActionMiddle.tsx:30-168)
- Action Target block (tells operator where the task fires: Slack channel, Notion page, etc., sourced from task.delivery or task.objective.audience).
- Latest Payload: markdown renderer for most recent fire (task output content).
- Action History: list of past fires with status (delivered, failed, etc.), external links if available.
- Data sources: useTaskOutputs(taskSlug, {includeLatest: true, historyLimit: 10, refreshKey}).

[MaintenanceMiddle.tsx](/web/components/work/details/MaintenanceMiddle.tsx:27-132)
- Back Office Task framing (no user feedback loop, TP-owned, deterministic Python).
- Latest hygiene log in nested card + optional run history below.
- Data sources: useTaskOutputs(taskSlug, {includeLatest: true, historyLimit: 10, refreshKey}).

[FeedbackStrip.tsx](/web/components/work/details/FeedbackStrip.tsx:39-59)
- Thin bar below MiddleResolver. Single "Ask TP for changes" button per task.kind (ADR-181 Phase 4a).
- Only rendered when task.last_run_at is set; skipped for system_maintenance.
- Prompts are: produces_deliverable → "I want to make changes to…", accumulates_context → "Adjust what … tracks", external_action → "Change how … works".

### Modals + overlays

[TaskSetupModal.tsx](/web/components/chat-surface/TaskSetupModal.tsx:28-60)
- Launched by "Start new work" plus-menu action (visible only in list mode, line 244 in page.tsx: `selectedTask ? [] : [...]`).
- On submit, passes composed message to page's `sendMessage()` callback (line 404 in page.tsx) with optional chatSurfaceOverride.
- Singular modal across all cockpit tabs (ADR-215 Phase 4); dispatch to YARNNN for ManageTask(action="create").

---

## 2. Route + API Graph

### Frontend call sites → Backend routes

| Frontend call | File:Line | API route | Principal service | Notes |
|---|---|---|---|---|
| `api.tasks.list()` | page.tsx:82 | GET /api/tasks | (service.TBD) | Returns tasks[], used for WorkListSurface; includes status filtering |
| `api.tasks.run(slug)` | page.tsx:173 | POST /api/tasks/{slug}/run | task_pipeline | Triggers immediate run; response reloads task + detail |
| `api.tasks.update(slug, {status})` | page.tsx:196 | PUT /api/tasks/{slug} | (service.TBD) | Pause/resume task (status=active\|paused) |
| `useTaskDetail(slug)` | page.tsx:87-92 | GET /api/tasks/{slug} | (service.TBD) | Fetches TaskDetail with deliverable_spec, run_log |
| `useAgentsAndTasks({includeNarrative: true})` | page.tsx:82 | GET /api/tasks + GET /api/narrative/by-task | narrative resolver | ADR-219 Commit 4: narrative slices keyed by task slug |
| `useTaskOutputs(slug, {includeLatest, historyLimit})` | DeliverableMiddle:305, etc. | GET /api/tasks/{slug}/outputs/latest + GET /api/tasks/{slug}/outputs | (service.TBD) | Paginated output history; latest includes html_content, md_content, sections, manifest |
| `api.contexts.getDomainContext(domain_key)` | TrackingEntityGrid | GET /api/context/domains/{domain_key} | (service.TBD) | Returns DomainData with entities[], synthesis_files[], file counts |
| `fetchWorkspaceSurfaces()` | MiddleResolver via useComposition:49 | GET /api/programs/surfaces | composition_resolver | Returns SurfacesResponse: active_bundles[], composition tree (tabs.work.detail.middles[]) |

### Composition API

[/api/programs/surfaces](/api/routes/programs.py:35-73)
- Returns `SurfacesResponse`: schema_version, active_bundles[], composition (tabs + chat_chips).
- Composition.tabs.work.detail.middles = bundle-declared MiddleDecl[] for detail mode dispatch.
- For alpha-trader: two task-specific middles declared (portfolio-review → dashboard, trading-signal → queue) with bindings + components.
- Resolver calls `resolve_workspace_composition(user_id, client)` (backend service).

### Narrative API (ADR-219 Commit 4)

[/api/narrative/by-task](/api/routes/narrative.py)
- Returns `NarrativeByTaskResponse`: Map<task_slug, NarrativeByTaskSlice>.
- NarrativeByTaskSlice contains: last_material (most-recent material session_message headline) + metadata.
- Consumed by WorkListSurface to render headlines on list rows (line 440, narrativeSlice.last_material.summary).

### SWR keys / hooks

- `useComposition()` (web/lib/compositor/useComposition.ts): per-session cached fetch of /api/programs/surfaces. No auto-refetch; called once on mount.
- `useAgentsAndTasks(opts)` (web/hooks/useAgentsAndTasks.ts): fetches tasks[] + agents[] + optionally narrativeByTask. Cached; reload() callback available.
- `useTaskDetail(slug)` (web/hooks/useTaskDetail.ts): fetches single task detail by slug. Separate from list fetch to allow selective reload.
- `useTaskOutputs(slug, opts)` (web/hooks/useTaskOutputs.ts): fetches output history + latest. historyLimit + refreshKey support.

---

## 3. Operator Action Inventory

| Verb | Location | Kind | CRUD shape (ADR-215) | Primitive | Deep-link |
|---|---|---|---|---|---|
| Click row → open detail | WorkListSurface, WorkRow | List mode | Direct (URL state) | router.push(`/work?task=...`) | Yes, `?task={slug}` |
| Filter by agent | WorkListSurface toolbar | List mode | Direct (URL state) | router.replace (modify sp) | Yes, `?agent={slug}` |
| Clear agent filter | WorkListSurface toolbar | List mode | Direct (URL state) | router.replace (strip sp) | Yes, removes `?agent=` |
| Search (tab-local) | WorkListSurface toolbar | List mode | Client-side (no persist) | setSearch state | No |
| Toggle include historical | WorkListSurface toolbar | List mode | Client-side (no persist) | setIncludeHistorical state | No |
| Run task | WorkDetail header (ActionActions) | Detail, external_action | Direct | api.tasks.run(slug), reload | No |
| Pause/Resume task | WorkDetail overflow menu | Detail (all kinds) | Direct | api.tasks.update(slug, {status}), reload | No |
| Edit in chat | WorkDetail overflow menu + FeedbackStrip | Detail (all kinds except maintenance) | Chat | onOpenChat(editPrompt) → seeds rail composer | No |
| Open entity in Context | TrackingEntityGrid card click | Detail, accumulates_context | Direct (section swap) | router.replace(`/context?path=...`) | Yes, URL preserves path |
| Approve/reject proposal | NeedsMePane (in BriefingStrip) | List, cockpit | Chat | onOpenChatDraft(proposal_context) | No |
| Create new task | Plus menu (list mode) | List, any kind | Modal → Chat | TaskSetupModal → sendMessage(msg, {surface: 'task-detail'}) | No |

Notable: all CRUD shapes align with ADR-215 R1-R5 (Direct = URL or API action; Modal = flow dialog; Chat = seeds composer; Substrate = file edit).

---

## 4. Constraint Inventory

### ADR-167 v5 (List/detail pattern + PageHeader)

Load-bearing:
- Breadcrumb as chrome via PageHeader (no task metadata in chrome).
- SurfaceIdentityHeader in WorkDetail body (task title + metadata + actions colocated with content).
- Two-mode page: list (full-width table) vs detail (two-column: chrome + scrollable body).

Currently free:
- Detail panel scroll position on URL transition (could be saved/restored).

### ADR-198 (Five archetypes)

Load-bearing (Work surface applies):
- Document (DeliverableMiddle output rendering).
- Dashboard (alpha-trader portfolio-review via MiddleResolver bundle middle).
- Queue (NeedsMePane, alpha-trader trading-signal proposal queue).
- Briefing (BriefingStrip four-pane cockpit).
- Stream (not yet used on Work; could apply to run-history feeds).

### ADR-206 (Deliverables-first)

Load-bearing:
- WorkListSurface groups "My Work" tab by output_kind, default order: Reports (produces_deliverable) → Tracking (accumulates_context) → Actions (external_action). Line 98-108 defines MY_WORK_GROUP_ORDER.
- BriefingStrip composition order: NeedsMePane (proposals, most urgent) → SnapshotPane (money-truth) → SinceLastLookPane → IntelligenceCard.

### ADR-213 (Surface-pull composition)

Load-bearing:
- Composition fires once on FE mount (useComposition() in MiddleResolver, line 131). No refetch on route change.
- Bundle middles pulled from /api/programs/surfaces at render time; kernel defaults used if compositor is unreachable (graceful fallback, line 54 in useComposition.ts).

### ADR-215 (CRUD shapes, R1-R5)

Load-bearing:
- R2 (Modal): TaskSetupModal is singular creation path across cockpit.
- R4 (Chat): "Edit in chat" opens composer with task-scoped prompt (onOpenChat callback, line 417 in page.tsx).
- R5 (Direct): Pause/Resume, Run, navigation.

### ADR-219 (Narrative semantics)

Load-bearing:
- WorkListSurface uses narrativeByTask Map to populate list-row headlines (line 440). Forward-looking (next_run_at) for active tasks; backward-looking (last_material.summary) for inactive (line 511).
- ADR-219 Commit 7 deferred: legacy task.last_run_at still used in DeliverableMetadata (line 172), TrackingMetadata (line 216), ActionMetadata (line 267) metadata strips. BriefingStrip does not yet migrate off last_run_at.

Currently free:
- Run history split (narrative vs manifest) pending full Phase 7 rollout.

### ADR-225 (MiddleResolver, 4-tier resolution)

Load-bearing:
- MiddleResolver replaces hardcoded KindMiddle switch. 4-tier match: task_slug → output_kind+condition → output_kind → agent_role/agent_class (resolveMiddle in /lib/compositor/resolver.ts).
- Kernel defaults (TrackingEntityGrid, DeliverableMiddle, ActionMiddle, MaintenanceMiddle) coexist at `/work/details/` (not library-relocated per Phase 2 refinement).
- Library components registered in LIBRARY_COMPONENTS dict (MiddleResolver.tsx line 52-63). Unknown component kind renders amber warning box (line 96-101).

Currently free:
- Bundle middle condition matching (currently only output_kind+condition tested in alpha-trader SURFACES.yaml, but resolver supports arbitrary condition keys, line 82-90 in resolver.ts).
- Archetype use for bundle middles (unused by FE; available for future rendering hints).

---

## 5. Drift / Inconsistency Observations

1. **Narrative not fully adopted (ADR-219 Phase 7 deferred):**
   - WorkListSurface headlines source from narrativeByTask (correct, line 505-511).
   - DeliverableMetadata, TrackingMetadata, ActionMetadata, MaintenanceMetadata still read task.last_run_at for the metadata strip (lines 172, 216, 267, 292 in WorkDetail.tsx).
   - Decision: these strips show deterministic, user-facing time labels (e.g., "Last output: 3h ago"), not historical context, so last_run_at is appropriate here. No drift.

2. **MiddleResolver fires only in detail mode:**
   - MiddleResolver invoked from WorkDetail (line 509 in WorkDetail.tsx), not in list mode.
   - Bundle middles apply only to detail view. List-mode composition (WorkListSurface tab filtering, BriefingStrip panes) not affected by bundle SURFACES.yaml.
   - This is correct per design (detail vs list composition).

3. **Kind middles cleanly mapped to ADR-198 archetypes:**
   - accumulates_context → TrackingEntityGrid (Dashboard/Grid pattern, not Briefing).
   - produces_deliverable → DeliverableMiddle (Document pattern).
   - external_action → ActionMiddle (could be Queue or Reactive; currently shows history, not queued proposals).
   - system_maintenance → MaintenanceMiddle (Document pattern for logs).
   - Bundle middles declare explicit archetype field in SURFACES.yaml (e.g., dashboard, queue), but kernel defaults don't declare archetypes in code. No drift; FE simply doesn't use archetype field yet.

4. **CRUD shapes inconsistent across kinds? No:**
   - Every kind middle has "Edit in chat" (hardcoded in overflow menu for all non-terminal tasks, lines 113-130 in WorkDetail.tsx).
   - ActionMiddle has "Fire" button (line 340-364); others don't (correct per kind).
   - No anomalies.

5. **?agent= filter still wired and clearable:**
   - Agent filter applied in WorkListSurface (line 281-282). Chip rendered with X button (line 400-408). onClearAgentFilter() in page.tsx removes param (lines 228-233).
   - Breadcrumb logic respects ?agent= (lines 125-147 in page.tsx).
   - Fully functional.

6. **FeedbackStrip exists on /work today:**
   - Yes, rendered below MiddleResolver in WorkDetail (line 511 in WorkDetail.tsx).
   - Condition: only when task.last_run_at is set (line 40 in FeedbackStrip.tsx); skipped for system_maintenance (line 33-35).
   - Live and operational.

7. **TaskSetupModal launched from /work is identical to /chat:**
   - Same component (TaskSetupModal from chat-surface).
   - Launches with empty initialNotes (no pre-fill from /work context).
   - On submit, sends message to current surface (detail mode: surface={type: 'task-detail', taskSlug}, line 257; list mode: undefined, line 404).
   - Yes, singular implementation.

8. **Kernel-default middles colocated with library middles? No:**
   - Kernel defaults at `/web/components/work/details/` (DeliverableMiddle, TrackingMiddle, ActionMiddle, MaintenanceMiddle).
   - Library middles imported into MiddleResolver from `/web/components/library/` (PerformanceSnapshot, PositionsTable, RiskBudgetGauge, TradingProposalQueue).
   - This is intentional per ADR-225 Phase 2 implementation refinement (comment line 13-18 in MiddleResolver.tsx): kernel defaults stay where they are; library reorg deferred.

9. **Daily-update task rendered specially?**
   - Daily-update is flagged essential=true in the task registry (ADR-161).
   - No special rendering on /work; treatment would be in workspace navigation (blocking archive, ADR-161 §5).
   - Check: FeedbackStrip, WorkDetail, middles — no special daily-update handling observed.
   - This is not a Work surface concern (essential flag checked at the task-model level elsewhere).

10. **Work-page breadcrumb matches ADR-167 v2 PageHeader pattern:**
    - Breadcrumb set via useBreadcrumb context (lines 125-165 in page.tsx).
    - Rendered by PageHeader component (line 315 in page.tsx).
    - Structure: Work › Task (standard) or Agents › Agent › Task (?agent= deep-link case).
    - Yes, follows pattern.

---

## 6. Files Touched Outside Direct Scope That Are Load-Bearing

### Type definitions

[/web/types/index.ts](portions)
- Task, TaskDetail, TaskCreate (task CRUD shapes).
- NarrativeByTaskResponse, NarrativeByTaskSlice (ADR-219).
- DeskSurface (line 37 in page.tsx: type for chatSurfaceOverride).

### Routes + navigation

[/web/lib/routes.ts](presumed)
- AGENTS_ROUTE, CONTEXT_ROUTE (linked in WorkDetail metadata strips and TrackingEntityGrid).

### Agent identity

[/web/lib/agent-identity.ts](used in WorkListSurface:32, page.tsx:35)
- getAgentSlug() helper for agent slug resolution and breadcrumb label lookup.

### Task-type resolution

[/web/lib/task-types.ts](used in WorkDetail:45)
- resolveTaskSurface(), SURFACE_TYPE_LABELS, resolveDomainWorkspacePath() for task kind labels and domain folder navigation.

### Shell chrome

[/web/components/shell/PageHeader.tsx](referenced page.tsx:33, WorkDetail)
- Renders breadcrumb navigation; no title, no metadata (per ADR-167 v5).

[/web/components/shell/SurfaceIdentityHeader.tsx](referenced WorkDetail:42)
- Task title + metadata + actions header (replaces task metadata in chrome).

### Compositor public API

[/web/lib/compositor/index.ts](/web/lib/compositor/index.ts:1-27)
- Exports useComposition, resolveMiddle, getDetailMiddles, getTab, getActiveBundles.
- Used by MiddleResolver; consumers rely on types (MiddleDecl, Archetype, ComponentDecl, etc.).

### Utilities

[/web/lib/formatting.ts](used throughout)
- formatRelativeTime() for timestamp display.

[/web/lib/utils.ts](used throughout)
- cn() for classname merging.

---

## Summary Stats

- **Components inventoried:** 28 (7 page/container-level; 6 list-mode; 8 detail-mode middles + FeedbackStrip; 4 BriefingStrip panes; 1 MiddleResolver; 2 modals/chrome; other support).
- **ADRs flagged in constraints:** 7 (ADR-167 v5, ADR-198, ADR-206, ADR-213, ADR-215, ADR-219, ADR-225).
- **Drift observations found:** 0 genuine drift (all apparent inconsistencies are design decisions or deferred phases, not bugs).
- **API routes:** 10+ principal (tasks CRUD, outputs, narrative, composition).

---

## Top 5 Striking Facts

1. **Compositor (ADR-225) is live but bundle-middles are spartan.** MiddleResolver stands ready for bundle components, but only alpha-trader SURFACES.yaml declares middles (portfolio-review dashboard, trading-signal queue). Library component registry has 4 slots (PerformanceSnapshot, PositionsTable, RiskBudgetGauge, TradingProposalQueue). No other bundles wired. If alpha-trader ships additional middles, the resolver will dispatch them; if another bundle lands, SURFACES.yaml must be authored first.

2. **Narrative headlines live in list rows but absent from detail-mode metadata.** WorkListSurface shows NarrativeByTaskSlice.last_material summaries (correct per ADR-219 Commit 4). DeliverableMetadata, TrackingMetadata, ActionMetadata still show task.last_run_at (deferred Phase 7 per comment line 80-82 in page.tsx). This is intentional; the metadata strips are operational timestamps, not historical context.

3. **MiddleResolver falls through to kernel defaults gracefully, with no special wiring needed.** The resolver is safe to attach to any task that lacks a bundle middle. New kernel-default middles (if any future output_kind is added) auto-route. The LIBRARY_COMPONENTS dict is the sole registration point; unknown library component kinds render an amber warning (not a hard break).

4. **TaskSetupModal is the singular task-creation path across all cockpit tabs, but launched from /work only via plus-menu in list-mode.** Detail mode hides the plus-menu (line 243-253 in page.tsx: `selectedTask ? [] : [...]`). This ensures the operator can't accidentally create a new task while editing one, a sensible interaction boundary.

5. **BriefingStrip (cockpit zone) is hidden when ?agent= filter is active.** List-mode rendering checks `!agentFilter` (line 381 in page.tsx) before mounting BriefingStrip. When an agent filter is set, the filtered task list becomes the primary focus, replacing the glance-zone (proposals, money-truth, etc.). This is a deliberate focus shift per ADR-206 (deliverables-first when viewing all work, task-list-first when filtering).
