# Design Docs — Changelog

Track changes to design documentation structure and active principles.

---

## 2026-04-26 — ADR-215 Phase 7: ADR-219 narrative absorption (doc-only)

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — adopts [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) (Implemented 2026-04-25/26).

SURFACE-CONTRACTS.md bumped to v1.7. ADR-219 (Invocation + Narrative) ratified FOUNDATIONS Axiom 9 across six implementation commits and merged to main on 2026-04-26 (commits `1007869` → `e67abd6`). The canon doc is catching up so it agrees with what live code already does — no code change in this phase.

**Conceptual shift (from the conversation that triggered this):**
ADR-219 demoted "task" from substrate-layer noun to channel/legibility wrapper. The atom of action is now **invocation**; the operator-facing log is **narrative**; tasks attach a nameplate + pulse + contract to recurring categories of invocations. `/chat` is the narrative surface; `/work` is the same narrative filtered by `metadata.task_slug`. Inline actions are first-class; tasks earn their keep when they carry a pulse. SURFACE-CONTRACTS v1.6 still described Chat as "conversation" — that framing is from before ADR-219 and was due to drift.

**Doc updates landed:**
- **Header / Grounded-in / Related docs** — ADR-219 added; FOUNDATIONS bumped to v6.8; `invocation-and-narrative.md` linked.
- **Chat contract** — Archetype rewritten: "Stream — **the narrative surface**. The universal log of every invocation." New "Narrative semantics" subsection names Identity widening (`user | assistant | system | reviewer | agent | external`), weight gradient (`material | routine | housekeeping`), pulse vocabulary, deep-linkable filter chips, and the `/work`-as-filter framing. Stream-mode bullet expanded to include `agent` / `system` / `external` Identity entries with the surfaces that render them.
- **Chat affordances** — Inline-to-task graduation ("Make this recurring") added as a stream-row affordance per ADR-219 D6.
- **Work contract** — "Narrative semantics" subsection added: list-row headlines source from `GET /api/narrative/by-task` (ADR-219 Commit 4); WorkDetail's run-history continues to read `agent_runs` per ADR-219 D7. Reads list updated.
- **Affordance cookbook** — three new rows: Graduate inline action → Task (Chat / R5), Filter narrative stream (Direct), Expand housekeeping digest rollup (Direct).
- **Implementation status — Phase 7** — added with deferred follow-ups explicitly named: Cockpit zone (BriefingStrip on /work) hasn't migrated to narrative yet; D6 "Archive task (keep history)" belongs on WorkDetail, deferred; pulse + time-range filters deferred (richer UI than chips).

**Code change:** none. ADR-219 Commits 1–6 already shipped; this is the canon-doc catch-up.

**Why this matters:** SURFACE-CONTRACTS is the single design reference for the cockpit. When it disagrees with live code, the doc is wrong (per ADR-215's own discipline rule). Closing the canon-vs-code drift here keeps the design discipline intact and makes the next surface decision (whether to migrate Cockpit zone to narrative reads) an explicit, scoped question rather than an emergent one.

**Phase 8 candidates** (named here so they don't drift):
- Migrate `SinceLastLookPane` to consume `GET /api/narrative/by-task` directly. Most natural narrative consumer in Cockpit zone — answers "what happened while I was away," which is literally the narrative.
- "Archive task (keep history)" affordance on WorkDetail. Pairs cleanly with task-lifecycle work.
- Pulse filter + time-range filter on `/chat`. Adds two more dimensions to the deep-linkable filter bar.

---

## 2026-04-24 — ADR-215 Phase 6: Snapshot overlay reframe (Workspace modal → Snapshot)

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — amends ADR-165 v8 (Workspace State Surface).

SURFACE-CONTRACTS.md bumped to v1.6. Chat tab's overlay contract rewritten as **Snapshot** — a Briefing archetype in its purest form: pure read, zero LLM at open, stay-in-chat. The prior four-tab `WorkspaceStateView` (Readiness / Attention / Last session / Activity) reframed as three-tab `SnapshotModal` (Mandate / Review standard / Recent). Part 4 Phase 6 marked Implemented.

**Conceptual shift (from the conversation):**
The prior overlay had drifted into a mini-dashboard — stat cards with outbound links, "Production Roles" counts linking to `/work`, "Identity — Empty — Add now" CTAs opening a form. That made it a nav hub, not a glance. The reframe answers one question: *what does the operator need in mind before speaking to YARNNN?* Three things — what they've committed to (Mandate), how judgment happens (Reviewer standard), what's unresolved (Recent) — each rendered in place. No outbound links per row; Close returns to typing.

**Cost contract:** zero LLM at modal open. Every tab reads substrate files (3 HTTP GETs: MANDATE.md, principles.md, decisions.md, awareness.md — 4 files, but parallelized) and neutral audit ledgers (2 Supabase SELECTs: `action_proposals` pending, tasks with `last_run_at`). No summarization, no reasoning, no cross-referencing commentary. Every byte rendered was persisted by an earlier conversational turn.

**Code landed:**
- `web/components/chat-surface/SnapshotModal.tsx` (new) — three tabs, pure reads, per-tab `<EditInChatButton>` seed. Close returns to typing.
- `web/components/chat-surface/WorkspaceStateView.tsx` — **deleted** (1063 lines).
- `web/lib/snapshot-meta.ts` (new) — `parseSnapshotMeta`, `stripSnapshotMeta`, `SnapshotLead` (`mandate | review | recent`). Retains `stripOnboardingMeta` for historical message hygiene.
- `web/lib/workspace-state-meta.ts` — **deleted**. Old `WorkspaceStateLead` (`overview | flags | recap | activity`) gone.
- `web/lib/reviewer-decisions.ts` (new) — shared parser extracted from `DecisionsStreamPane`. Consumed by both `/agents?agent=reviewer` (full stream) and Snapshot's Recent tab (last 3 verdicts). Singular implementation — no duplicate parser.
- `web/components/agents/reviewer/DecisionsStreamPane.tsx` — 80-line in-file parser block deleted; imports from shared lib.
- `web/components/chat-surface/ChatSurface.tsx` — state renamed `overviewOpen` → `snapshotOpen`, header button "Workspace" → "Snapshot", mounts `<SnapshotModal>` instead of `<WorkspaceStateView>`. `agents` + `dataLoading` props dropped (overlay only needs tasks for the Recent tab).
- `web/app/(authenticated)/chat/page.tsx` — caller simplified to pass just `tasks`.
- `web/components/tp/ChatPanel.tsx` + `web/components/tp/InlineToolCall.tsx` — import `stripSnapshotMeta` instead of the retired `stripWorkspaceStateMeta`.
- `web/components/chat-surface/TaskSetupModal.tsx` — docstring pointer to retired `WorkspaceStateView` cleaned.

**Prompts:**
- `api/agents/yarnnn_prompts/onboarding.py` — marker emission guidance rewritten. Retired lead enum (overview/flags/recap/activity); new enum (mandate/review/recent). Stale ADR-203 `/overview` cold-start guidance removed (HOME is `/chat` per ADR-205 F1). `api/prompts/CHANGELOG.md` entry `[2026.04.24.10]` added.

**Docs:**
- `docs/design/WORKSPACE-STATE-SURFACE.md` — **archived** with supersession banner. Canonical contract lives in SURFACE-CONTRACTS.md under the Chat tab's "Snapshot overlay" subsection.

**R-compliance check after Phase 6:**
- R1 preserved. Snapshot overlay is pure-read; only mutation is chat seeding via the shared `<EditInChatButton>` (R5 label).
- R2–R4 unchanged from prior phases.
- R5 preserved. Every tab's "Edit in chat" button uses the shared component.
- New cost invariant: **zero LLM at modal open**, documented in SURFACE-CONTRACTS.md.

**TypeScript:** `tsc --noEmit` passes.

---

## 2026-04-24 — Settings > Memory tab retirement (ADR-215 Phase 2 follow-up closed)

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) R3 — substrate operations edit on Files.

SURFACE-CONTRACTS.md bumped to v1.5. The Phase 2 follow-up flagged in earlier CHANGELOG entries (MemorySection on `/settings` as a parallel IDENTITY/BRAND edit mouth) is now closed: the Memory tab is retired, and Files is the singular substrate edit surface.

**What /settings keeps, and why:**
`/settings` is retained as **account-scoped infrastructure that isn't cockpit substrate** — Billing, Usage, System (diagnostics), Connectors (OAuth), Account (notification prefs + Danger Zone). None of these fit cleanly into the four-tab cockpit (Chat / Work / Agents / Files); they're the account plumbing every SaaS keeps out of the main surface. The separation is clean, not redundant.

**Memory tab retired:**
Identity / Brand / Profile / preferences editing moves to Files with `authored_by=operator` revision attribution via `<SubstrateEditor>`. One edit surface per substrate per R3.

**Code landed:**
- `web/components/settings/MemorySection.tsx` — **deleted**. 709 lines of parallel IDENTITY/BRAND edit UI retired.
- `web/app/(authenticated)/settings/page.tsx` — Memory tab removed: `SettingsTab` union narrowed (`billing | usage | system | connectors | account`), tab button removed, render case removed, `Brain` icon import removed, `MemorySection` import removed. Added `useEffect` redirect for legacy `?tab=memory` → Files IDENTITY.md.
- `web/app/(authenticated)/memory/page.tsx` — redirect target updated from `/settings?tab=memory` → `/context?path=/workspace/context/_shared/IDENTITY.md`. Bookmark-safety stub preserved.
- `web/components/workspace/ContentViewer.tsx` — wires `<InferenceContentView>` for IDENTITY.md + BRAND.md so ADR-162 Sub-phase D inference-meta (source caption + gap banner) still surfaces on Files. No rendering regression from the MemorySection retirement.
- `web/components/context/InferenceContentView.tsx` — docstring updated (MemorySection reference replaced with ContentViewer mount).

**Singular-implementation check:**
- `grep -rn "MemorySection" web/` — only comments explaining the retirement.
- `grep -rn "tab=memory" web/` — zero live callers (redirects in place for bookmarks).
- `InferenceContentView` preserved with new Files mount — inference provenance caption + gap banner continue to surface alongside the substrate edit path.

**TypeScript:** `tsc --noEmit` passes.

---

## 2026-04-24 — ADR-215 Phase 5: Chat hardening (onboarding modal retired, R-compliance complete)

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Chat hardening (Phase 5). **ADR closed**.

SURFACE-CONTRACTS.md bumped to v1.4. Chat contract in Part 1 rewritten with Workspace overlay + Reviewer verdict thread documented; empty state clarified; `+` menu codified at exactly one entry. Part 4 Phase 5 marked Implemented; ADR-215 closed.

**Code landed:**
- `web/components/chat-surface/OnboardingModal.tsx` — **deleted**. Auto-trigger was already retired by ADR-190 (conversational onboarding); the manual "Update workspace" `+` menu entry violated R2 (update is never Modal) and R3 (identity/brand/conventions are substrate, edited on Files).
- `web/components/chat-surface/ContextSetup.tsx` — **deleted**. Only consumer was `OnboardingModal`.
- `web/components/chat-surface/ChatSurface.tsx` — removed OnboardingModal mount, `handleOpenOnboarding`, `handleOnboardingSubmit`, `SlidersHorizontal` import. `+` menu now has exactly one built-in entry: "Start new work" → `TaskSetupModal`. `onContextSubmit` prop removed (orphan after retirement).
- `web/app/(authenticated)/chat/page.tsx` — simplified to drop the orphaned `onContextSubmit` wiring.
- `web/components/chat-surface/WorkspaceStateView.tsx` — `onOpenOnboarding` prop removed (root + OverviewTab + FlagsTab). Identity-empty CTAs seed chat prompts via `onAskTP` — YARNNN infers identity from the conversation per ADR-190, writes IDENTITY.md via `UpdateContext`. R3-compliant substrate path preserved.
- `web/components/tp/ReviewerCard.tsx` — deep-link migrated `/review` → `/agents?agent=reviewer` (ADR-214 canonical route). Docstring updated with Stream archetype invariants (append-only, verdict cards are historical, never mutated inline).
- `web/lib/workspace-state-meta.ts` — dead `parseOnboardingMeta` export removed. `stripOnboardingMeta` retained for display hygiene on historical messages that may still carry the retired marker. File header updated.
- Stale doc comments cleaned: `web/app/auth/callback/page.tsx`, `web/components/chat-surface/ComposerInput.tsx`, `web/components/chat-surface/TaskSetupModal.tsx`.

**R-compliance across all four tabs after Phase 5:**
- **R1** — one verb, one shape per object. Clean across Chat · Work · Agents · Files.
- **R2** — Create is Modal (exactly one: `TaskSetupModal`, used by all four tabs). Update/Delete is Direct or Chat. Zero edit-modals remain anywhere in the cockpit.
- **R3** — substrate-editable paths (IDENTITY · BRAND · CONVENTIONS · MANDATE · principles.md) edit on Files with `authored_by=operator` revision attribution. Chat never edits substrate.
- **R4** — `+` menu is modal launcher only. `/chat` has one entry, `/work` has one, `/context` has two (both modal/web-search), `/agents` has one or two (modal + conditional run action).
- **R5** — single label "Edit in chat". `grep -rn "Edit via" web/` returns zero live hits.

**ADR-215 close-out:**
All five phases implemented. Four surface contracts + four-shape CRUD matrix + five rules govern the cockpit. Future cockpit additions consume `SURFACE-CONTRACTS.md` as the contract doc; phase structure is historical reference.

**TypeScript:** `tsc --noEmit` passes.

---

## 2026-04-24 — ADR-215 Phase 4: Work hardening (silent-degrade + cockpit zone + modal unification)

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Work hardening (Phase 4).

SURFACE-CONTRACTS.md bumped to v1.3. Work contract in Part 1 rewritten to document the two-zone ("Cockpit" / "Work") list-mode layout and the singular TaskSetupModal creation path. Affordance cookbook entry for Create-Task updated. Part 4 Phase 4 marked Implemented.

**Code landed:**
- `web/components/work/briefing/IntelligenceCard.tsx` — silent-degrade fix per ADR-198 §3 Briefing invariant. The `maintain-overview` task isn't scaffolded at signup (ADR-206), so `GET /api/tasks/maintain-overview/outputs/latest` 404s on fresh workspaces. That 404 (and any transient HTTP failure) now collapses into the "Synthesis pending" empty state instead of rendering an "API Error: 404" + Retry box. Briefing archetype never sprouts error chrome inside a list surface.
- `web/components/work/briefing/BriefingStrip.tsx` — wrapped in a `<section>` with zone header "Cockpit" + subtle tint (`bg-muted/20`) + zone description ("What needs you · book · since last look · intelligence"). Single vertical scroll preserved per ADR-205 F2.
- `web/components/work/WorkListSurface.tsx` — matching "Work" zone header added above the toolbar. Zones are legible without tabs.
- `web/app/(authenticated)/work/page.tsx` — `/work` now uses `TaskSetupModal` like `/chat`, `/agents`, `/context`. Singular creation flow across the cockpit.
- `web/components/work/CreateTaskModal.tsx` — **deleted**. R2 is satisfied by `TaskSetupModal` alone across all four tabs.
- `web/lib/api/client.ts` — `api.tasks.create` method removed (zero frontend consumers). Backend POST `/api/tasks` endpoint preserved — it now only serves `ManageTask(action="create")` invocations from YARNNN. `TaskType` / `TaskTypesResponse` imports retained for update/list typing.

**Tab-ify vs single-scroll decision:**
The operator's initial feedback was "should we tab-ify the cockpit vs the list?" Considered and rejected. Reasons: (1) tab-ify forces proposals behind a click, which undoes ADR-206 deliverables-first ordering; (2) ADR-205 F2 deliberately merged Overview into Work to collapse a click; tabs would reverse that; (3) ADR-198 §3 allows one surface to host multiple archetypes (Briefing + Queue on top of List). The fix is visual zone separation, not navigation restructure. "Cockpit" zone tinted and labeled above "Work" zone — glance-then-drill.

**R-compliance check after Phase 4:**
- R1 (one verb, one shape): preserved. Task lifecycle verbs route Direct (Pause/Run/Archive on WorkDetail) or Chat (Edit in chat for judgment-shaped edits).
- R2 (create is Modal, update/delete never Modal): **clean**. `TaskSetupModal` is the one creation modal. The prior parallel path (`CreateTaskModal` on `/work`) is deleted.
- R3 (substrate bypasses Chat): preserved from Phase 2+3.
- R4 (`+` menu is modal launcher): preserved. `/work` `+` menu has exactly one entry (Start new work → `TaskSetupModal`).
- R5 (one label "Edit in chat"): preserved. `grep -rn "Edit via" web/` remains zero live hits.

**Other invariants checked:**
- ADR-198 §3 Briefing I2 (no error chrome inside a list surface): restored by IntelligenceCard fix.
- ADR-205 F2 (single vertical scroll on /work merged surface): preserved by zone approach.
- ADR-206 deliverables-first ordering (NeedsMe → Snapshot → SinceLastLook → Intelligence): preserved inside Cockpit zone.
- ADR-167 v2 kind-middles (four content-only middles): audited clean.

**TypeScript:** `tsc --noEmit` passes.

---

## 2026-04-24 — ADR-215 Phase 3: Agents hardening (principles.md → substrate, PrinciplesPane retired)

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Agents hardening (Phase 3).

SURFACE-CONTRACTS.md bumped to v1.2. Agents contract in Part 1 updated to reflect principles pane is Dashboard-read with deep-link to Files (R3-compliant); affordance cookbook row for principles.md updated; Part 4 Phase 3 marked Implemented + Phase 4 scope amended to include CreateTaskModal/TaskSetupModal reconciliation.

**Code landed:**
- `web/components/agents/reviewer/PrinciplesPane.tsx` — full rewrite. No more chat-seeder button. Renders the file read-only with an "Edit on Files" link (`/context?path=/workspace/review/principles.md`). Props surface simplified from `{ onOpenChatDraft }` to `{}`.
- `web/components/agents/reviewer/ReviewerDetailView.tsx` — drops the `onOpenChatDraft` prop (no consumer after PrinciplesPane retirement). The existing call site in `AgentContentView.tsx` already mounted `<ReviewerDetailView />` without the prop — dead wire confirmed and cleaned.
- `web/components/workspace/SubstrateEditor.tsx` — `SHARED_EDITABLE_PATHS` gains `/workspace/review/principles.md`. Docstring updated to document Phase 3 scope expansion.
- `api/routes/workspace.py` — `editable_prefixes` gains `/workspace/review/principles.md`. Same `write_revision(authored_by="operator")` path as the four `_shared/` rules.

**Behavior shift:** operator edits to Reviewer principles now go through the Files tab (substrate editor + revision chain) instead of seeding YARNNN chat. This means principles edits get `authored_by=operator` on their revisions — important for the audit trail on a file the AI Reviewer reads during judgment (ADR-194 v2 Phase 3).

**R-compliance check after Phase 3:**
- R1 (one verb, one shape): preserved. Reviewer substrate (IDENTITY, principles) → Substrate. AGENT.md for domain/YARNNN agents → Chat (via primitives, judgment-shaped).
- R2 (create is Modal, update/delete never Modal): still clean from Phase 2. Known gray area: `TaskSetupModal` on `/agents` seeds chat (hybrid) — targeted for Phase 4 reconciliation.
- R3 (substrate bypasses Chat): enforced — principles.md joins the `_shared/` rules on the substrate edit path. No chat seeder remains for any operator-authored substrate file.
- R4 (`+` menu is modal launcher): `/agents` `+` menu has "Assign a new task" (modal launcher) and conditional "Run task" (chat seeder) — the run-task entry is an execution action, not an edit, and R4 governs edit authorship. Documenting as intentional.
- R5 (one label "Edit in chat"): clean. `grep -rn "Edit via" web/` returns zero. PrinciplesPane replaces its prior "Edit via YARNNN" with "Edit on Files" (deep-link verb, not the R5 chat label — they are different affordances, different destinations).

**TypeScript:** `tsc --noEmit` passes.

---

## 2026-04-24 — ADR-215 Phase 2: Files hardening (substrate edits + EditInChatButton)

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Files hardening (Phase 2).

SURFACE-CONTRACTS.md bumped to v1.1. Phase 2 implementation status added to Part 4 alongside the tab-hardening sequence.

**Code landed:**
- `web/components/shared/EditInChatButton.tsx` (new) — the unified R5 affordance. Two variants: `default` (full button) and `compact` (icon-only for toolbars). One label: "Edit in chat".
- `web/components/workspace/SubstrateEditor.tsx` (new) — inline substrate editor for `/workspace/context/_shared/{IDENTITY,BRAND,CONVENTIONS,MANDATE}.md`. Exports `isSubstrateEditable(path)` predicate. Writes through `api.workspace.editFile()` → `write_revision(authored_by="operator")` per ADR-209.
- `web/components/workspace/ContentViewer.tsx` — refactored. `onEditViaChat` prop renamed `onOpenChatDraft` (R5 vocabulary); new `onSubstrateSaved` prop for reload-after-save. `FileView` now gates the chat-draft button on `!isSubstrateEditable(file.path)` (R3 — substrate files get inline editor instead). Empty-file short-circuit loosened so empty substrate-editable files still render the editor (lets MANDATE.md be authored from scratch).
- `web/components/agents/reviewer/PrinciplesPane.tsx` — "Edit via YARNNN" button replaced with `<EditInChatButton>`. Interim: principles.md retires to substrate-editable on Files in Phase 3.
- `web/components/work/WorkDetail.tsx` — overflow menu item "Edit via chat" → "Edit in chat". Compact icon button aria-label + title updated.
- `web/components/shell/PageHeader.tsx` — doc comment vocabulary normalized.
- `web/app/(authenticated)/context/page.tsx` — `ManageContextModal` import + state + `+` menu entry removed. ContentViewer wired to new prop names + `onSubstrateSaved`.
- `web/components/context/ManageContextModal.tsx` — **deleted** (violated R2 by being an edit-modal and R3 by bypassing the revision chain for substrate writes).
- `api/routes/workspace.py` — `editable_prefixes` gained `/workspace/context/_shared/MANDATE.md`. Same revision-chain write path as the other three authored rules.

**Decisions locked in for Phase 3+:**
- `PrinciplesPane` inline chat path retires in Phase 3 — principles.md joins `SHARED_EDITABLE_PATHS` and becomes substrate-editable on Files. The decisions pane stays as a Stream embed per ADR-198.
- `MemorySection` on `/settings` retains a parallel IDENTITY/BRAND edit path. Known follow-up: retire in a later sweep so Files is the one and only edit surface for `_shared/` rules. Not blocking Phase 3.

**R-compliance check after Phase 2:**
- R1 (one verb, one shape): preserved. Substrate files route to Substrate; non-substrate files route to Chat.
- R2 (create is Modal, update/delete never Modal): now clean — the last edit-modal (`ManageContextModal`) is deleted.
- R3 (substrate bypasses Chat): enforced via `isSubstrateEditable()` gate in `FileView`.
- R4 (`+` menu is modal launcher): Files tab's `+` menu now has no chat-seeders; only `TaskSetupModal` (legacy — CreateTaskModal migration out of scope for Phase 2) and `Web search`. The "Edit identity / brand / conventions" chat-seeder entry was deleted.
- R5 (one label "Edit in chat"): clean across `web/` — `grep -rn "Edit via"` returns no live hits.

**TypeScript:** `tsc --noEmit` passes.

---

## 2026-04-24 — ADR-215: SURFACE-CONTRACTS unification + four-shape CRUD matrix

**Governing ADR:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Surface Contracts and CRUD Principles.

**New canonical doc**: `SURFACE-CONTRACTS.md` — single design reference for the four cockpit tabs (Chat · Work · Agents · Files). Four sections: per-tab contracts (archetype · reads · list mode · detail mode · `+` menu · deep-links out · refuses), the four-shape CRUD matrix (Direct · Modal · Chat · Substrate) with five rules, the affordance cookbook (verb-object → shape lookup), and the tab-hardening sequence (Files → Agents → Work → Chat).

**Archived to `docs/design/archive/`** (all superseded by `SURFACE-CONTRACTS.md` per ADR-215):
- `SURFACE-ARCHITECTURE.md` v15 (2026-04-20) — five-destination cockpit framing retired by ADR-214's four-tab nav collapse.
- `SURFACE-ACTION-MAPPING.md` (2026-03-10) — two-surface chat/drawer dichotomy with retired TP/agent_instructions vocabulary; replaced by the four-shape CRUD matrix.
- `SURFACE-DISPLAY-MAP.md` (2026-04-15) — pre-ADR-214 three-surface code snapshot; display catalog absorbed into SURFACE-CONTRACTS per-tab sections.
- `SURFACE-PRIMITIVES-MAP.md` (2026-04-04) — duplicated `docs/architecture/primitives-matrix.md` (ADR-168 canonical); surface→action layer absorbed into SURFACE-CONTRACTS Part 3 (Affordance Cookbook).

**Cross-references updated** in active docs: `AGENT-AND-TASK-SURFACE-PATTERNS.md`, `INLINE-PLUS-MENU.md` (notes ADR-215 R4 — `+` menu is strictly a modal launcher), `ONBOARDING-TP-AWARENESS.md`, `TP-NOTIFICATION-CHANNEL.md`, `TASK-OUTPUT-SURFACE-CONTRACT.md`, `WORKSPACE-STATE-SURFACE.md`.

**Decisions locked in** (full detail in ADR-215): four surface contracts, one per tab; four CRUD shapes with R1–R5 discipline; "Edit in chat" as the single label (retires "Edit via chat" / "Edit via YARNNN" / "Edit via yarnnn" drift); `ManageContextModal` to be retired in the Files hardening phase (substrate files edit directly on Files per R3); tab hardening proceeds Files → Agents → Work → Chat.

**Code changes:** none in this commit (docs-only). Follow-on phases land with code + contract update in the same commit per ADR-215 Phase 2–5 plan.

---

## 2026-04-15 — SURFACE-DISPLAY-MAP.md: ground-truth component matrix

**New doc**: `SURFACE-DISPLAY-MAP.md` — single reference for what each surface actually renders. Covers Work (list mode + detail mode per output_kind) and Context/Files (tree roots + center panel dispatch per node type). Ground-truth from code (`WorkDetail.tsx`, `*Middle.tsx`, `context/page.tsx`, `WorkspaceTree.tsx`, `ContentViewer.tsx`), not narrative docs. Establishes the three-surface user journey (Work → judgment gap → Context), cross-surface correspondence table (which output_kinds have Context representation vs. not), and component inventory. Documents known gaps (no FeedbackStrip yet, ObjectiveBlock renders for all kinds in code vs. spec saying produces_deliverable only).

---

## 2026-04-15 — Design folder cleanup: archive pass + route alignment

**Archived to `docs/design/archive/`** (content superseded by current ADRs and docs):
- `QUALITY-GATE-DESIGN.md` — designed for ADR-137 (PM-tier quality gates), which was superseded by ADR-138 (project layer collapse). Evaluation model now lives in ADR-149 + `docs/architecture/execution-loop.md`.
- `TASK-SCOPED-TP.md` — three-scope TP model (global/agent/task). Superseded by ADR-163 four-surface nav + SURFACE-PRIMITIVES-MAP.md which covers scope-aware primitives.
- `ONBOARDING-SCAFFOLD-AND-BRIEFING.md` — proposed onboarding task scaffold + daily briefing header. Architecture diverged: briefing dissolved into Workspace modal (ADR-165 v8), task scaffold moved to TP judgment. Superseded by USER-JOURNEY.md + ONBOARDING-TP-AWARENESS.md.
- `WORKSPACE-EXPLORER-UI.md` — three-panel Files explorer spec from v3 architecture. Superseded by ADR-163 Files surface and SURFACE-ARCHITECTURE.md v12 (nav label "Files", `/context` route, left tree nav retained).

**Updated (route/primitive alignment to v12):**
- `SURFACE-ACTION-MAPPING.md` — route table: /work added, /activity deleted, "Context page" → "Files". Changelog entry added.
- `SURFACE-PRIMITIVES-MAP.md` — `TriggerTask` → `ManageTask(action="trigger")` (ADR-168 Commit 2); `/activity` section deleted; navigate targets fixed to `/work?task=` (was `/agents?agent=&task=`); Context page renamed Files; `/work` task-detail section added.
- `SHARED-CONTEXT-WORKFLOW.md` — `/workfloor` → `/chat`; button consolidation section rewritten with current v12 surface model; stale ContextSetup inline-embed references removed; onboarding dissolution updated to reference ADR-176 roster and Onboarding modal pattern.

---

## 2026-04-14 — ADR-179 + USER-JOURNEY.md v1.2: system event cards pattern

- **New ADR**: `ADR-179-system-event-cards.md` — system events produce pre-composed assistant messages in the TP chat stream, zero LLM cost. Three defined cards: `workspace_init_complete` (seeded from auth callback), `task_triggered` (TP's response text covers this), `task_complete` (scheduler → realtime → card). No progress tracking — two bookend cards per significant action. Chat is the event log. Scopes first implementation of TP-NOTIFICATION-CHANNEL.md.
- **USER-JOURNEY.md v1.2** — added system event cards decision table, explicit two-Clarify sequence in Stage 2A (post-inference gap check + accuracy gate), chat-visible guarantee on ContextSetup dismiss, ADR-179 reference.
- **TP-NOTIFICATION-CHANNEL.md** — added scope clarification header: ADR-179 implements the first phase; FAB ambient state and queued notifications remain as future extension; in-progress task state explicitly out of scope.

---

## 2026-04-14 — USER-JOURNEY.md v1.1: workspace init explicit, tighter format

- **New canonical doc**: `USER-JOURNEY.md` — single source of truth for the full user journey from sign-up through onboarding, returning use, and starting new work. Covers all four paths (sign-up, cold-start, returning user, TaskSetup) with value-add per step. Governed by ADR-138, 141, 144, 161, 163, 176, 178.
- **Archived**: `DELIVERABLE-FIRST-USER-FLOW.md` → `archive/` — superseded by TASK-SETUP-FLOW.md + USER-JOURNEY.md. Referenced old workfloor routes, ADR-145 pipeline visualisation, "deliverables" terminology.
- **Archived**: `AGENT-PRESENTATION-PRINCIPLES.md` → `archive/` — three-tab agent model superseded by ADR-163. File itself acknowledged the content was historical.
- **SURFACE-PRIMITIVES-MAP.md**: Added redirect note to `docs/architecture/primitives-matrix.md` as canonical primitive reference (ADR-168). Surface→action mapping content retained.
- **SHARED-CONTEXT-WORKFLOW.md**: Replaced stale "Workfloor Surface (v4)" section header with current "Chat Surface (ADR-163)" equivalent.
- **FEEDBACK-WORKFLOW-REDESIGN.md**: Replaced "Workfloor chat" entry point label with "Chat surface (`/chat`)".

---

## 2026-04-13 — TASK-SETUP-FLOW.md: Structured intent capture for task creation

- **New design doc**: `TASK-SETUP-FLOW.md` — defines the `TaskSetup` component, the task creation equivalent of `ContextSetup`. Two-route flow: Route B (context-driven: "track something") and Route A (output-driven: "get a deliverable"). Both routes share the same material injection layer (links → entity seed, files → DELIVERABLE.md shape, notes → `focus`). Composed message gives TP a complete intent statement it can act on in one turn without clarifying. Governs ADR-178 task creation routes.
- **`web/components/chat-surface/TaskSetup.tsx`** — component built. Screen 0 = route selection cards. Screen 1B = domain chip + cadence + source toggles + material injection. Screen 1A = surface chip + mode chip + cadence + delivery toggle + material injection.
- **`web/components/chat-surface/TaskSetupModal.tsx`** — modal shell wrapping TaskSetup, same pattern as OnboardingModal.
- **`web/components/chat-surface/ChatSurface.tsx`** — TaskSetupModal added as third sibling modal. Built-in "Start new work" plus-menu action prepended to any page-supplied actions. `handleOpenTaskSetup(initialNotes)` is the entry point.
- **`web/app/(authenticated)/chat/page.tsx`** — simplified: no longer owns plus-menu action definition (ChatSurface owns it).
- **`web/components/chat-surface/WorkspaceStateView.tsx`** — Heads Up idle-agents flag updated: "Suggest work for them" (→ blank TP prompt) replaced by "Set up work for them" (→ opens TaskSetupModal pre-filled with idle agent names).

---

## 2026-04-09 — Agent surface patterns: broader shell / empty-state rules

- **New design doc**: `AGENT-AND-TASK-SURFACE-PATTERNS.md` — broader-scoped surface guidance layered on top of ADR-167. Defines the rendering split: `agent_class` chooses the agent shell, `output_kind` chooses the task shell, assigned-work cards stay shared, and `role` is limited to bounded add-on modules when the data genuinely differs.
- **New proposed design doc**: `TASK-OUTPUT-SURFACE-CONTRACT.md` — defines the next data-layer step for `/work`: one normalized run-centric packet per output folder, returned from existing task output routes, so the frontend stops parsing raw manifests and starts rendering from typed `output_kind`-aware surface data.
- Documents that **no-task states must differ by class**: specialists, reporting, integration bots, and Thinking Partner each have different absence semantics and should not share a generic empty card.
- Clarifies the implementation boundary: **do not build one page per agent type**. Use class-specific shells + empty states, then add role-specific modules only when the data model warrants it.
- `SURFACE-ARCHITECTURE.md` updated to reference the new doc and note class-specific no-task states on the canonical `/agents?agent={slug}` surface.

---

## 2026-04-09 — ADR-167 v5 follow-up: Chat surface adopts the pattern

Extending v5 to /chat for consistency with /work, /agents, /context. Previously /chat had no PageHeader at all and the workspace-state toggle button was an `inputRowAddon` crammed into the chat input row between the + menu and the textarea (per ADR-165 v5/v6). The user flagged this inconsistency: the header pattern should apply to /chat too, and the stage button belongs in the header alongside the page identity, not in the input row.

- **`web/components/chat-surface/ChatSurface.tsx`** — now renders `<PageHeader defaultLabel="Chat" />` + `<SurfaceIdentityHeader title="Thinking Partner" actions={workspaceStateAction} />` as the first two rows of the surface, matching /work and /agents. The workspace-state toggle moves from `inputRowAddon` to `SurfaceIdentityHeader.actions`. The chat conversation column stays centered at `max-w-3xl` beneath the headers.
- **`web/components/tp/ChatPanel.tsx`** — deleted the `inputRowAddon` prop entirely (it had exactly one caller, now removed). Singular implementation: no dead props. The `+` menu and textarea are now the only elements in the input row's left cluster.
- **`web/app/(authenticated)/chat/page.tsx`** — unchanged. ChatSurface handles everything internally.
- **`SURFACE-ARCHITECTURE.md`** — Chat section rewritten with the v5 header pattern and an updated ASCII diagram showing the PageHeader + SurfaceIdentityHeader stack. Replaced the stale two-panel "Briefing + TP Chat" diagram that predated ADR-165 v5/v6. Updated the breadcrumb lookup table row for Chat.
- **No ADR renumbering** — this is a scope extension of the v5 amendment applied the same day, not a new version.

---

## 2026-04-09 — ADR-167 v5: PageHeader split — chrome vs. surface identity, nested document pattern

User flagged that even v4's chrome-only PageHeader still had metadata + actions inside it, and that the metadata "sitting above the real H1" felt structurally wrong — task metadata and actions describe the task, not the navigation, so they should live with the task content. Plus the output iframe's own H1 was still visually competing with whatever PageHeader showed as the last breadcrumb segment. v5 is the cleanest resolution:

- **`web/components/shell/PageHeader.tsx`** — stripped to breadcrumb-only. Deleted `subtitle` and `actions` props entirely. PageHeader is now pure navigation chrome: one breadcrumb strip, ~60 lines, no content-shaped concerns.
- **`web/components/shell/SurfaceIdentityHeader.tsx`** — NEW primitive. Takes `title` (`h1.text-2xl.font-semibold`), `metadata?`, and `actions?` props. Rendered INSIDE the surface's content area (not in the chrome), where it can sit directly above the content it describes. WorkDetail and AgentContentView both render their own `<SurfaceIdentityHeader />` as the first thing in their content stream.
- **`web/components/work/WorkDetail.tsx`** — now owns the task identity. Renders `<SurfaceIdentityHeader title={task.title} metadata={<TaskMetadata/>} actions={<TaskActions/>} />` as the first thing in its content stream. Accepts `mutationPending`, `onRunTask`, `onPauseTask`, `onOpenChat` as new props. The metadata/actions local building that used to live up in `work/page.tsx` moves down here where it conceptually belongs.
- **`web/components/agents/AgentContentView.tsx`** — mirror treatment. Renders `<SurfaceIdentityHeader title={agent.title} metadata={<AgentMetadata/>} />` (no actions for now — the agents surface doesn't have per-agent actions yet). Absorbs the `CLASS_LABELS` map from `agents/page.tsx` since this is the only place they're rendered now.
- **`web/components/work/details/DeliverableMiddle.tsx`** — applies the nested document pattern. The iframe (or markdown fallback) is wrapped in `<div className="rounded-lg border border-border bg-muted/5 overflow-hidden">`. Whatever H1 lives inside the output (e.g. daily-update's `<h1>Daily Workspace Update — April 8, 2026</h1>`) is now visually framed as "a document this task produced," clearly subordinate to the `SurfaceIdentityHeader` above. The card frame + muted background are the signal that does the hard work.
- **`web/components/work/details/TrackingMiddle.tsx`** — same nested-card treatment on the CHANGELOG markdown block. Consistent with DeliverableMiddle.
- **`web/components/work/details/MaintenanceMiddle.tsx`** — same nested-card treatment on the hygiene log block. Consistent.
- **`web/components/work/details/ActionMiddle.tsx`** — no markdown/HTML output, so no card needed, but padding normalized from `px-5` to `px-6` and outer `border-b` wrapper dropped for consistency with the other three middles (which now use fragment roots since WorkDetail owns section dividers).
- **`web/app/(authenticated)/work/page.tsx`** — deleted the `detailSubtitle` and `detailActions` local variables entirely. Deleted the `assignedAgent` useMemo (moved inside WorkDetail). Simplified PageHeader call to `<PageHeader defaultLabel="Work" />`. WorkDetail now receives the raw callbacks + mutation state.
- **`web/app/(authenticated)/agents/page.tsx`** — deleted the `detailSubtitle` IIFE and the `CLASS_LABELS` constant (moved into AgentContentView). Simplified PageHeader call to `<PageHeader defaultLabel="Agents" />`.
- **`SURFACE-ARCHITECTURE.md`** — Page header section rewritten to v5 with the two-component explanation and the nested document pattern, detail-mode ASCII diagram updated, revision history row added (v9.4).
- **Typographic ramp established**: SurfaceIdentityHeader h1 = `text-2xl font-semibold` (the real page title); section labels = `text-[10px] uppercase tracking-wide text-muted-foreground/40`; nested card content uses default `prose prose-sm`. The card frame + size ramp + position (first-large-thing-after-chrome) together give the surface H1 unambiguous visual primacy over whatever content lives inside the nested card.
- **Applied consistently across all four output kinds** (produces_deliverable, accumulates_context, external_action, system_maintenance) so task type never changes the layout shape — only the middle component's contents differ.
- No schema changes, no API changes. No ADR renumbering — continues the v2/v3/v4/v5 amendment pattern on ADR-167.

---

## 2026-04-09 — ADR-167 v4: PageHeader as chrome, not title (superseded same day by v5)

- `web/components/shell/PageHeader.tsx` — rewritten to treat the page header as pure navigation chrome instead of a content-anchored title. v3's large promoted `h1.text-xl` title in Band 2 is deleted. The breadcrumb is ALWAYS present with the same small muted treatment across all states (list and detail) — list pages render `defaultLabel` as a single-segment breadcrumb instead of suppressing the strip. The metadata + actions row stays as an optional second row but collapses when both are absent.
- **Why**: v3 had two residual problems that the user caught in screenshots. (1) v3 was still conditional: list-mode pages suppressed Band 1 entirely, so the header tone flipped between "compact nav strip + title band" (detail) and "title band only" (list). The user wanted the breadcrumb always present with the same manner. (2) v3's big title band was still competing with content. The daily-update task renders its own `<h1>Daily Workspace Update — April 8, 2026</h1>` as the first thing inside its output iframe, which stacked immediately below PageHeader's big "Daily Update" title — two headers doing the same job. The agents roster has the same issue: PageHeader's "Agents" title stacked above AgentRosterSurface's "Thinking Partner · 1" section header with no breathing room. v4 resolves both: the breadcrumb reads as chrome, always present in the same muted tone; the content owns the real H1.
- Applied uniformly across `/work`, `/agents`, `/context` — one component file change fixes the audit across surfaces. No per-page changes.
- `SURFACE-ARCHITECTURE.md` — Page header section rewritten to v4 (chrome-not-title + why), detail-mode ASCII diagrams updated, revision history row added (v9.3).
- No ADR renumbering — this is a v4 amendment to ADR-167, continuing the v2/v3 amendment pattern.
- No schema changes, no API changes, no new props on PageHeader (same `defaultLabel` / `subtitle` / `actions` contract).

---

## 2026-04-09 — ADR-167 v3: PageHeader two-band layout (superseded same day by v4)

- `web/components/shell/PageHeader.tsx` — restructured from single-band (breadcrumb + metadata + actions above one thin divider) into two visually separated bands. Band 1 is a compact muted nav strip (breadcrumb path only). Band 2 is the content-anchored title header (title + metadata subtitle + inline actions), separated from Band 1 by a divider. List-mode pages (one segment, or `defaultLabel` fallback) suppress Band 1 entirely — the title band stands alone.
- **Why**: v2 crammed navigation chrome with content-specific metadata into one dense strip, which made the *actual* page title ambiguous. Users consistently read the first H1 inside the content (e.g. "Daily Workspace Update — April 8, 2026") as the page title because there was no obvious anchor above the content divider saying "this is the thing you're looking at." v3 separates navigation from the content header: breadcrumb on top as pure nav, title + metadata + actions below as the content anchor.
- Applied uniformly across `/work`, `/agents`, `/context` — they all use the same PageHeader, so the audit is one file.
- `SURFACE-ARCHITECTURE.md` — Page header section rewritten to v3 (two-band layout + why), detail-mode ASCII diagrams updated, revision history row added (v9.2).
- No ADR renumbering — this is a v3 amendment to ADR-167, same pattern as the v2 amendment shipped on 2026-04-08.
- No schema changes, no API changes, no new props on PageHeader (same `defaultLabel` / `subtitle` / `actions` contract). Pages using PageHeader did not change.
- **Superseded same day by v4** — see entry above. v3 still had the residual duplicate-title problem (promoted title in Band 2 vs. content's own H1) and still suppressed the breadcrumb in list mode. v4 deletes the promoted title and makes the breadcrumb always-present.

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
