# Surface Contracts

**Version:** v2.2 (2026-04-29 — ADR-235 UpdateContext dissolution alignment)
**Status:** Canonical
**Governed by:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Surface Contracts and CRUD Principles
**Grounded in:** [ADR-198](../adr/ADR-198-surface-archetypes.md) surface archetypes · [ADR-214](../adr/ADR-214-agents-page-consolidation.md) four-tab nav · [ADR-209](../adr/ADR-209-authored-substrate.md) authored substrate · [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) invocation + narrative · [ADR-231](../adr/ADR-231-task-abstraction-sunset.md) task abstraction sunset · [ADR-235](../adr/ADR-235-update-context-dissolution.md) UpdateContext dissolution (lifecycle → `ManageRecurrence`; substrate writes → `WriteFile(scope='workspace')`; identity/brand merges → `InferContext` / `InferWorkspace`) · [ADR-168](../architecture/primitives-matrix.md) primitive matrix · [ADR-225](../adr/ADR-225-compositor-layer.md) compositor (Phase 3 — unified seam) · [FOUNDATIONS v6.8](../architecture/FOUNDATIONS.md) Axiom 6 (Channel) + Axiom 9 (Invocation + Narrative)
**Supersedes:** `archive/SURFACE-ARCHITECTURE.md`, `archive/SURFACE-ACTION-MAPPING.md`, `archive/SURFACE-DISPLAY-MAP.md`, `archive/SURFACE-PRIMITIVES-MAP.md`

---

## Purpose

This is the single design reference for YARNNN's cockpit. It answers five questions, in order:

0. **How does the kernel/program seam work for surfaces?** (composition layer)
1. **What does each tab do?** (per-tab contract)
2. **How is mutation expressed?** (CRUD matrix + 6 rules)
3. **What affordances live where?** (affordance cookbook)
4. **In what order do we harden the tabs?** (sequencing)

When a design decision spans two tabs (e.g. "deep-link from Work to Files"), both tabs' contracts must allow it. When a CRUD decision arises (e.g. "how do we let the operator refine a task's deliverable?"), the matrix picks the shape. When the answer would require branching FE code on `program_slug`, the contract is wrong — programs specialize via composition manifest (Part 0), never via FE conditionals.

---

## Part 0 — Composition Layer

Every tab's contract describes the **kernel surface**. Bundles (program manifests at `docs/programs/{slug}/SURFACES.yaml`) extend kernel surfaces declaratively via the compositor seam ([ADR-225](../adr/ADR-225-compositor-layer.md), Phase 3 Implemented 2026-04-27).

**The single mental model:** every compositor-resolved slot has the same shape — bundle declaration → kernel default fallback → library component dispatch by `kind`. There is no "kernel render path" and "bundle render path"; there is one path, where kernel defaults are themselves library components registered in `LIBRARY_COMPONENTS` alongside bundle components.

The architecture-level reference for the seam is [docs/architecture/compositor.md](../architecture/compositor.md). This contract names which slots on which tabs are bundle-shapeable; the architecture doc names how they get rendered.

### Compositor-resolved slots, by tab

| Tab | Slot | Bundle declaration | Kernel default | Phase |
|---|---|---|---|---|
| Work | List pinned tasks | `tabs.work.list.pinned_tasks: [slug, ...]` | No pinning | 3 |
| Work | List banner | `tabs.work.list.banner: "..."` (or via `phase_overlays`) | No banner | 2 |
| Work | List cockpit (four faces) | `tabs.work.list.cockpit: { mandate, money_truth, performance, tracking }` | Mandate · Money truth · Performance · Tracking, fixed order | ADR-228 |
| Work | Detail middle (content) | `tabs.work.detail.middles[]` (4-tier match) | DeliverableMiddle / TrackingEntityGrid / ActionMiddle / MaintenanceMiddle | 2 |
| Work | Detail chrome (metadata + actions) | `tabs.work.detail.middles[].chrome` (optional) | Per-output_kind kernel chrome (`KernelDeliverableMetadata`, etc.) | 3 |
| Agents | List featured agents | `tabs.agents.list.featured: [slug, ...]` | No featuring | (Phase 2 backend; FE consumer pending) |
| Files (Context) | List featured domains | `tabs.context.list.featured_domains: [...]` | No featuring | (Phase 2 backend; FE consumer pending) |
| Files (Context) | List pinned shortcuts | `tabs.context.list.pinned_shortcuts: [...]` | No pinning | (Phase 2 backend; FE consumer pending) |
| Chat | Empty-state chips | `chat_chips: ["...", ...]` | Four kernel-default chips | (Phase 2 backend; FE consumer pending) |
| Chat | Overview surface bands | `tabs.chat.bands[]` | (Currently hardcoded ChatEmptyState) | (Future) |

Slots marked "FE consumer pending" mean the backend resolver returns the field but no FE component reads it yet. They'll wire incrementally as bundles need them. The Work tab is fully bundle-shapeable end-to-end after Phase 3.

### Refuses (composition-layer-wide)

- **No FE branch on `program_slug`.** Specialization happens via composition manifest, never via FE conditionals. If a tab feels it needs to know which program is active, the answer is to declare the variation in SURFACES.yaml.
- **No bundle-supplied executable logic.** SURFACES.yaml carries declarations only. The resolver inspects strings; it never `eval`s anything.
- **No kernel-only dual paths.** Per Singular Implementation, kernel defaults are library components dispatched through the same registry as bundle components. Don't ever introduce a "kernel render branch" that bypasses the resolver.

### Contract authority

When this doc and `docs/architecture/compositor.md` disagree, the architecture doc wins on *how the seam works* (resolver pattern, binding taxonomy, library registry). This doc wins on *what each tab should look like* (per-tab contracts, archetype assignments, refuses lists). When [ADR-225](../adr/ADR-225-compositor-layer.md) and either of these disagree, the ADR wins on decisions; the docs adjust.

---

## Part 1 — Per-Tab Surface Contracts

Four tabs, four contracts. Each contract has seven fixed sections: **Archetype · Reads · List mode · Detail mode · `+` menu · Deep-links out · Refuses.**

### Tab: Files

**Route:** `/context` (legacy slug retained; operator label "Files" per ADR-180)

- **Archetype:** Dashboard (primary, per ADR-198 §3) — live substrate slice, read-primary. Detail view of a file is a Document archetype when the file is a composed output.
- **Reads:** `workspace_files` (entire filesystem), `workspace_file_versions` (revision chain per ADR-209), `workspace_blobs` indirectly via revision reads.
- **List mode** (no `?path=`): filesystem tree grouped by ADR-152 directory registry + ADR-231 D2 natural-home substrate:
  - `_shared/` — workspace-wide authored rules (IDENTITY · BRAND · CONVENTIONS · MANDATE) + the shared back-office YAML index (`back-office.yaml` per ADR-231 D2) + audit log (`back-office-audit.md`)
  - `context/{domain}/` — accumulated intelligence per domain, including `_performance.md` (ADR-195), `_tracker.md`, `_recurring.yaml` (per-domain ACCUMULATION recurrence declarations per ADR-231 D3), and `_feedback.md` (ADR-181)
  - `reports/{slug}/` — DELIVERABLE-shape recurrences per ADR-231 D2 (`_spec.yaml` declaration · `_run_log.md` · `_feedback.md` · `{date}/output.md` per firing). **Replaces the dissolved `tasks/{slug}/` tree per ADR-231 D2.**
  - `operations/{slug}/` — ACTION-shape recurrences (`_action.yaml` declaration · `_run_log.md`)
  - `agents/{slug}/` — per-domain-agent AGENT.md, memory, style
  - `review/` — Reviewer substrate (IDENTITY · principles · decisions — read-only here, edited from Agents tab or via Review flow)
  - `uploads/` — operator-contributed documents (ADR-197)
  - `memory/` — YARNNN working memory (conversation summaries, workspace state)
- **Detail mode** (`?path=/workspace/...`):
  - Rendered file content (markdown, HTML, or binary via `content_url`)
  - Inference-meta caption (ADR-162 sub-phase D) when present
  - Revision history panel (ADR-209 P4) — `authored_by` trail, diff, restore
  - Substrate-native edit affordance when `authored_by=operator` is appropriate (IDENTITY, BRAND, CONVENTIONS, principles, MANDATE, uploaded documents)
- **`+` menu:** UploadFileModal (operator uploads a document into `/workspace/uploads/`). No other modals. No chat seeders.
- **Deep-links out:** every file path is a stable URL (`/context?path=...`) linked from Work task-detail (`/workspace/reports/{slug}/_spec.yaml` · `_feedback.md` · `{date}/output.md` per ADR-231 D2), Agents detail (`/workspace/agents/{slug}/AGENT.md` · `memory/` · `style.md`), Chat artifacts, and the cockpit faces on Work.
- **Refuses:**
  - Recurrence orchestration, agent authoring, proposal approval — those are Work/Agents/Work respectively
  - "Edit in chat" buttons on substrate files (per R3) — Files is where substrate gets edited; Chat would invoke `WriteFile(scope='workspace', ...)` / `InferContext` and produce the same write with less clear provenance
  - Duplicate rendering of recurrence outputs (outputs exist in one canonical place at the natural-home `/workspace/reports/{slug}/{date}/`; Files links rather than embeds per ADR-198 I2)

### Tab: Agents

**Route:** `/agents` (canonical per ADR-214, reverses ADR-201)

- **Archetype:** List (list mode) + Dashboard (detail mode, per ADR-167 v2). Reviewer decisions stream is a Stream archetype embed inside Reviewer detail.
- **Reads:** `agents` table filtered to principals (YARNNN `thinking_partner` + user-authored domain agents, per ADR-189 origin filter + ADR-214 synthesized Reviewer pseudo-agent), plus each agent's filesystem home (`/workspace/agents/{slug}/*` or `/workspace/review/*` for Reviewer).
- **List mode** — **DELETED by ADR-241** (2026-04-30). Post-ADR-235 D2 (no user-authored agent creation), the roster was always-empty ceremony. `/agents` (no query param) redirects directly to `?agent=thinking-partner`. If a future ADR re-introduces user-authored Agents, the roster reappears.
- **Detail mode** (`?agent={slug}`): dispatches on `agent_class`:
  - `thinking_partner` (YARNNN) → tab-based detail (Identity / Principles / Tasks per ADR-241 D2). The Principles tab renders `/workspace/review/principles.md` — the judgment framework TP applies to verdicts.
  - `reviewer` → **redirects to `?agent=thinking-partner&tab=principles`** per ADR-241 D3. Legacy URL preserved for bookmark + ADR-194 cross-link integrity; substrate (`/workspace/review/`) unchanged.
  - domain agents → IDENTITY card + health card + AGENT.md + memory/style substrate panes (AGENT.md edits flow through primitives). User-authored Agents not currently creatable per ADR-235 D2; existing rows tolerated.
- **Decisions surface** (`/work` Decisions tab) — Stream archetype over `/workspace/review/decisions.md` lives on `/work` per ADR-241 D3, not `/agents`. The actionable consequence of judgment lives where proposals live.
- **`+` menu:** none. Per ADR-235 D2, no chat-surface pathway to create user-authored Agents.
- **Deep-links out:** each agent's files on Files (`/context?path=/workspace/agents/{slug}/AGENT.md`), the agent's tasks filtered on Work (`/work?agent={slug}`), and Chat with the agent preselected (`/chat?agent={slug}`).
- **Refuses:**
  - Task management (tasks live on Work; this tab shows agent *identity*, not agent *work*)
  - Editing production roles or platform integrations as if they were agents (ADR-212 — those are Orchestration, not Agents)
  - Principles/IDENTITY modal editing (ADR-215 R3 — substrate edit goes to Files)

### Tab: Work

**Route:** `/work`

- **Archetype:** Briefing + Queue (list-mode composition) → Document/Dashboard/Stream (detail mode, per output_kind).
- **Narrative semantics** (ADR-219 D4): `/work` **is the narrative filtered by `metadata.task_slug`**. The list-row recent-activity headline reads from the narrative via `GET /api/narrative/by-task` (ADR-219 Commit 4) — the legacy `task.last_run_at` timestamp source was retired; tasks with no narrative entries simply render no headline (singular implementation). WorkDetail's per-task run-history continues to read `agent_runs` per ADR-219 D7 — that's the audit ledger view, separate consumer.
- **Reads:** `tasks` thin scheduling index (per ADR-231 D4 Path B — `next_run_at`, `last_run_at`, `paused`, `declaration_path`), `/workspace/reports/{slug}/*` (DELIVERABLE: `_spec.yaml`, `_feedback.md`, `_run_log.md`, `{date}/output.md`), `/workspace/context/{domain}/*` (ACCUMULATION: `_recurring.yaml`, `_feedback.md`, `_run_log.md`, entity files), `/workspace/operations/{slug}/*` (ACTION: `_action.yaml`, `_run_log.md`), `/workspace/_shared/back-office.yaml` + `back-office-audit.md` (MAINTENANCE), `/workspace/review/decisions.md` (for the SinceLastLook pane), `/workspace/context/_performance_summary.md` (for the Snapshot pane per ADR-195 Phase 3), `agent_runs` (for WorkDetail's per-task run-history view), **`GET /api/narrative/by-task`** (for WorkListSurface row headlines per ADR-219 Commit 4).
- **List mode** (no `?task=`): single vertical scroll with two visually-distinct zones per ADR-215 Phase 4. Both zones are now compositor-resolved (ADR-225 Phase 3, see Part 0 slot table).
  - **Cockpit zone** (`<CockpitRenderer>`, replaces deleted `<BriefingStrip>`) — the operation, rendered. Per ADR-228, the cockpit is **four faces in fixed order**: Mandate (standing intent + autonomy posture), Money truth (where the account stands now, platform-live where applicable), Performance (attribution against mandate + Reviewer calibration), Tracking (pending decisions + operational state + recent outcomes). Bundles fill each face's domain shape via `tabs.work.list.cockpit.{mandate,money_truth,performance,tracking}`; bundles cannot reorder or omit faces. The `cockpit_panes` flat-array shape from ADR-225 Phase 3 was deleted by ADR-228.
    - **Kernel default** (no active program): the four faces render kernel-default substrate-fallback paths (mandate reads `_shared/MANDATE.md` + `_shared/AUTONOMY.md`; money truth reads `_performance_summary.md`; performance reads `_performance_summary.md` + `/workspace/review/decisions.md`; tracking reads pending action_proposals + narrative outcomes).
    - **Bundle override** (e.g., alpha-trader): `tabs.work.list.cockpit` declares per-face bindings (e.g., `cockpit.money_truth.substrate_fallback: /workspace/context/portfolio/_performance.md`). Platform-live bindings for Money truth (Alpaca / commerce providers) are reserved for ADR-228 Commit 3.
    - **Empty states:** each face renders its own empty/skeleton state inside the face. Skeleton MANDATE renders destructive-tinted authoring CTA. The other faces remain readable when MANDATE is absent — the operator can still see balances, recent activity. No whole-cockpit posture switch.
    - **Hidden when `?agent=` filter active** — deliberate focus shift per ADR-206 (filtered list becomes the primary focus). The gate lives in `page.tsx`; `<CockpitRenderer>` doesn't know about the agent filter.
  - **Work zone** (`<WorkListSurface>`) — section label "Work". Task list grouped by output_kind (Reports · Tracking · Connected · Actions), with My Work / Connectors / System tab switcher for scope. **Pinned tasks** (`tabs.work.list.pinned_tasks`) float to the top of their group with a small pin glyph. **Banner** (`tabs.work.list.banner`, including via `phase_overlays`) renders above the task list via `<BundleBanner tab="work" />`.
  - Zones share one vertical scroll (ADR-205 F2 — deliberate: glance-then-drill mental model; tab-ify was considered and rejected because it would force proposals behind a click).
- **Detail mode** (`?task={slug}`): three compositor-resolved layers — chrome (top), middle (content), feedback strip (bottom). Per Part 0, every layer flows through the resolver pattern.
  - **Chrome** (`<ChromeRenderer>`) — single component for the metadata strip + array of components for the actions row. Resolved via `resolveChrome(ctx, middles)`:
    - **Kernel default per output_kind** (`KERNEL_DEFAULT_CHROME` in `kernel-defaults.ts`):
      - `produces_deliverable` → KernelDeliverableMetadata + KernelDeliverableActions
      - `accumulates_context` → KernelTrackingMetadata + KernelTrackingActions
      - `external_action` → KernelActionMetadata + KernelActionActions (Fire button + Edit-in-chat)
      - `system_maintenance` → KernelMaintenanceMetadata + (no actions)
    - **Bundle override** via `tabs.work.detail.middles[].chrome` (optional, partial overrides allowed): bundles override metadata only, actions only, or both. Missing slots inherit kernel default.
    - **Action handlers** thread via `WorkDetailActionsContext` provider in `WorkDetail.tsx`. Kernel and bundle chrome components both consume `useWorkDetailActions()`.
    - **Operational vs historical timestamp rule** (rule made contract-explicit in v2.0): chrome metadata strips show **operational** timestamps that help the operator answer "is this task healthy and current?" Bundle middles whose content area regenerates substrate every run (e.g., a Dashboard reading `_performance.md`) should override the metadata to show *substrate* freshness, not artifact age. Historical context lives in the narrative (`/work` list-row headlines, ADR-219), not in chrome.
  - **Middle** (`<MiddleResolver>`) — content area. Resolved via `resolveMiddle(ctx, middles)` 4-tier match:
    - **Kernel default per output_kind** (kind-specific components at `web/components/work/details/`, retained as the kernel-default fallback per ADR-225 §5):
      - `produces_deliverable` → DeliverableMiddle (rendered output + quality contract panel)
      - `accumulates_context` → TrackingEntityGrid (domain folder + entity cards)
      - `external_action` → ActionMiddle (fire history + platform link-out)
      - `system_maintenance` → MaintenanceMiddle (hygiene log + run history)
    - **Bundle override** via `tabs.work.detail.middles[]` 4-tier match (task_slug → output_kind+condition → output_kind → agent_role/class). First match wins. Bundle middles take full content area; archetype declared via `archetype` field per ADR-198.
  - **FeedbackStrip** — thin bar below the middle. Single "Edit in chat" prompt per kind (ADR-181 Phase 4a). Skipped for system_maintenance (back-office tasks have no user feedback loop).
- **`+` menu:** `TaskSetupModal` (singular creation modal across the cockpit — ADR-178 two-route rich intake; forwards to YARNNN via `sendMessage`. Per ADR-231 D5, YARNNN calls `ManageRecurrence(action='create', shape=..., slug=..., body={...})` in the same turn — `ManageTask` was deleted in ADR-231 Phase 3.7). Per ADR-215 Phase 4 singular-implementation, `CreateTaskModal` was retired — one creation modal across `/chat`, `/work`, `/agents`, `/context`.
- **Deep-links out:** recurrence files on Files (`/context?path=/workspace/reports/{slug}/_spec.yaml` for DELIVERABLE; `/workspace/context/{domain}/_recurring.yaml` for ACCUMULATION; `/workspace/operations/{slug}/_action.yaml` for ACTION; per ADR-231 D2/D3 natural-home paths), assigned agents on Agents (`/agents?agent={slug}`), Chat with recurrence preselected for "Edit in chat" (`/chat?task={slug}` — query-param name preserved per ADR-219 D4 task_slug = declaration slug).
- **Refuses:**
  - File browsing outside recurrence scope (goes to Files)
  - Agent identity editing (goes to Agents → Chat)
  - Replacing Files for the `_shared/` authored rules (per R3 — `ManageContextModal` retired)

### Tab: Chat

**Route:** `/chat` (HOME per ADR-205 F1)

- **Archetype:** Stream — **the narrative surface** per [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) (FOUNDATIONS Axiom 9). The universal log of every invocation in the workspace, of which the operator's own conversation is one thread. Reviewer verdicts (`role='reviewer'`), agent task completions (`role='agent'`), back-office digests (`role='system'`), and external MCP foreign-LLM calls (`role='external'`) all surface here as Identity-tagged entries with weight-driven rendering. Cold-start empty-state is the one exception — renders a curated landing panel.
- **Narrative semantics** (ADR-219):
  - **Identity widening** — `session_messages.role` enum is `user | assistant | system | reviewer | agent | external` (migration 161). Every invocation in the workspace emits exactly one narrative entry into this stream.
  - **Weight-driven rendering** (ADR-219 D5) — `metadata.weight` ∈ `{material, routine, housekeeping}` drives per-row UI density. Material → full card (existing user/assistant/reviewer card path). Routine → collapsed line with chevron + click-to-expand. Housekeeping → dim one-liner; the curated rollup card written by `back-office-narrative-digest` (ADR-219 Commit 3) is the recommended surface for housekeeping clusters. Legacy "no envelope" rows default to material so messages predating ADR-219 Commit 2 don't disappear.
  - **Pulse** = trigger sub-shape attached to each entry. Periodic / reactive / addressed / heartbeat. Carried in `metadata.pulse`.
  - **Filter bar** (`<ChatFilterBar>`) — three deep-linkable query-param dimensions: `?weight=...&identity=...&task=...`. Bar auto-opens when any filter is active. The filter is a Channel-layer slice over the same Stream — never a substrate change.
  - **`/work` is the same narrative filtered by `metadata.task_slug`** — Chat and Work read the same source of truth (ADR-219 D4); Work is the legibility wrapper for task-labeled invocations, Chat is everything.
- **Reads:** `chat_sessions` + `session_messages` (windowed per ADR-159), compact index (`format_compact_index()` per ADR-186 profile), all substrate indirectly via YARNNN's tool calls.
- **Writes:** through primitives (`WriteFile(scope='workspace')`, `InferContext`, `InferWorkspace`, `FireInvocation`, `ManageAgent` (lifecycle-only per ADR-235 D2), `ManageRecurrence`, `ManageDomains`, `ProposeAction`, etc. per ADR-168 + ADR-231 D5 + ADR-235). Chat never writes substrate directly; it writes through YARNNN's primitive invocations. Recurrence lifecycle flows through `ManageRecurrence` (create/update/pause/resume/archive) + `FireInvocation` (manual fire) per ADR-231 D5 + ADR-235 D1.c — the legacy `ManageTask` primitive was deleted in Phase 3.7 and `UpdateContext` was deleted in ADR-235. Every primitive invocation also emits a narrative entry via `services.narrative.write_narrative_entry` (ADR-219 Commit 2 single write path; ADR-219 Commit 6 final coverage gate enforces this).
- **Stream mode** (default, conversation active): append-only message log. Reviewer verdicts appear as `role='reviewer'` messages per ADR-212; agent task completions appear as `role='agent'` entries with task-slug envelope; back-office digests appear as `role='system'` cards with `system_card='narrative_digest'` (collapsed-by-default with expand-to-list). MCP foreign-LLM calls land as `role='external'` entries (ADR-219 Commit 6) with `metadata.mcp_tool` + `metadata.mcp_client` provenance. Artifact cards render inline when a primitive's response carries one. "Edit in chat" entries from other tabs open Chat with a seeded first message.
- **Empty state** (cold start per ADR-205 F1): `<ChatEmptyState>` — deterministic client-side landing with four suggestion chips (Upload a doc, Paste a URL, Track something recurring, Build a recurring report). Zero LLM cost on first load. The only surface in the cockpit that overrides its archetype for first-run guidance.
- **`+` menu:** exactly one entry per ADR-215 Phase 5 — "Start new work" → `TaskSetupModal` (R4 modal launcher). The prior "Update workspace" entry was retired — it violated R2 (update is never Modal) and R3 (identity/brand/conventions are substrate, edited on Files).
- **Deep-links out:** any file YARNNN cites (`/context?path=...`), any recurrence `ManageRecurrence` creates or updates (`/work?task=...` — query-param name preserved per ADR-219 D4 task_slug = declaration slug), any agent `ManageAgent` touches (`/agents?agent=...`). Reviewer verdict cards (role='reviewer' messages per ADR-212) link to `/agents?agent=reviewer` (ADR-214 canonical route). Artifacts carry links, not embeds.
- **Snapshot overlay** (`<SnapshotModal>`): modal opened by YARNNN-emitted `<!-- snapshot: {"lead":"..."} -->` marker OR the surface header "Snapshot" button. **Briefing archetype in its purest form** (ADR-198 §3): pure read, composed by selection, no outbound nav, zero LLM at open time. The overlay is *of* the conversation — Close returns the operator to typing with enriched awareness, not to another tab.

  Three tabs, each rendered in place from substrate files and neutral audit ledgers:

  | Tab | Purpose (the operator's *why*) | What renders in place | Sources | Cost |
  |---|---|---|---|---|
  | **Mandate** | "What have I committed to?" | MANDATE.md rendered as markdown, full. Operator owns keeping it tight (~300 words). | `GET /api/workspace/file?path=/workspace/context/_shared/MANDATE.md` | 1 HTTP GET, 0 LLM |
  | **Review standard** | "How does judgment happen around here?" | Reviewer principles.md rendered as bullets + last 3 entries from decisions.md (Stream tail, parsed) | `GET` principles.md + `GET` decisions.md | 2 HTTP GETs, 0 LLM |
  | **Recent** | "What's unresolved right now?" | Pending proposals (count + titles), last 3 task runs, latest AWARENESS.md snippet | SELECT `action_proposals` + SELECT `agent_runs` + `GET` AWARENESS.md | 2 SELECTs + 1 GET, 0 LLM |

  **Zero LLM cost at modal open**, by contract. No summarization, no reasoning, no cross-referencing commentary. Every byte rendered was persisted by an earlier conversational turn — the overlay reads what already exists.

  **Stay-in-chat invariant** (the defining discipline): every tab renders its content in place. No "Open on Files" links per row, no stat cards that ship the operator to another tab. If the operator wants to browse the full `_shared/` substrate or the roster, the tab bar already carries Files and Agents — the overlay doesn't duplicate those destinations. Close button returns to typing.

  **Permitted affordances per tab:**
  1. Close button — return to conversation.
  2. At most one `<EditInChatButton>` per tab (R5 single label) seeding a tab-contextual prompt ("Revise my mandate", "Evolve the Reviewer's principles", "What should I do about these pending proposals?"). The seed closes the modal and drops the prompt into the composer. Operator still owns pressing Send.

  **Identity-empty states** degrade gracefully — a missing MANDATE.md renders "Not yet declared" with an "Edit in chat" button seeding "Help me author my mandate"; same pattern for missing principles.md. R3 is preserved (substrate-file edits would happen on Files, but this overlay never *edits* substrate — it only seeds the conversation that eventually writes via `WriteFile(scope='workspace')` or `InferContext`).
- **Reviewer verdict thread** (ADR-212): `role='reviewer'` session messages render as `<ReviewerCard>` inline in the stream — verdict + occupant + reasoning + deep-link to `/agents?agent=reviewer`. Stream archetype invariant: append-only; verdict cards are historical entries, never mutated inline.
- **Inline-to-recurrence graduation** (ADR-219 D6 + ADR-231 D1/D5): material-weight operator messages that have no `metadata.task_slug` (i.e. inline invocations per FOUNDATIONS Axiom 9 + ADR-231 D1 invocation-first default) carry an inline **"Make this recurring"** affordance. Per D1 the operator's first invocation already fired and produced its result; this affordance attaches a nameplate + pulse + contract for repeat firings. Click opens `TaskSetupModal` pre-filled with `Recurring intent: <message-prefix>` so YARNNN turns it into `ManageRecurrence(action='create', shape=..., slug=..., body={...})` on submit. Reversible: a recurrence can be archived later via `ManageRecurrence(action='archive', ...)` and the same intent returns to inline. The atom of action (the invocation) is the same throughout — only the legibility wrapper rotates.
- **Refuses:**
  - Full CRUD forms (modal-shape — those are on other tabs per R2)
  - Heavy data tables (those are Dashboard archetype — other tabs)
  - Replacing direct affordances on other tabs (approve buttons stay on Work; pause buttons stay on Work; no Chat-only paths for Direct-shape operations per R1)
  - Onboarding forms — onboarding is conversational per ADR-190; no `OnboardingModal` / `ContextSetup` after ADR-215 Phase 5

---

## Part 2 — The CRUD Matrix

Four shapes. One rule per verb-object pair. Every mutation in the cockpit picks exactly one shape.

| Shape | When | Surface | Example |
|---|---|---|---|
| **Direct** | High-precision, well-specified, one-step, reversible | In-place button/input on the object's own detail page | Pause task · Archive file · Approve proposal · Run task now |
| **Modal** | High-precision, multi-field, **creation flow**, operator arrives with a blueprint | Modal launched from `+` menu or page header | CreateTaskModal · UploadFileModal |
| **Chat** | Judgment-shaped, ambiguous, needs YARNNN's context | Redirect to `/chat` with seeded prompt | Refine a task's deliverable · Rewrite a mandate · Author a domain agent · Define review principles |
| **Substrate** | Operator-authored content that IS a file | Edit the file on Files tab; revision chain records `authored_by=operator` | IDENTITY.md · BRAND.md · CONVENTIONS.md · MANDATE.md · principles.md · uploaded documents |

### The six rules

- **R1 — One verb, one shape per object.** "Edit a task" is always Chat. "Edit a file" is always Substrate. "Approve a proposal" is always Direct. No mixing across the cockpit.
- **R2 — Create is always Modal. Update/Delete is Direct or Chat, never Modal.** Modals exist for the moment of creation where the operator arrives with a blueprint. After creation, mutation is single-click Direct or judgment-shaped Chat. No "edit modal" anywhere in the cockpit.
- **R3 — Substrate operations bypass Chat.** If the thing being edited IS a file, the edit surface is Files. The revision panel (ADR-209 P4) shows `authored_by=operator`. No "Edit in chat" button on substrate files — Chat would invoke `WriteFile(scope='workspace')` or `InferContext` anyway, and direct substrate edit produces the same write with clearer provenance.
- **R4 — The `+` menu is a modal launcher. Never a chat seeder.** Each tab's `+` menu lists only Modal creation flows. Chat-shaped mutations live on the object's own detail page as the R5 label.
- **R5 — One label: "Edit in chat".** All existing phrasings ("Edit via chat" / "Edit via YARNNN" / "Edit via yarnnn") converge on **"Edit in chat"**. Lowercase. No YARNNN branding — chat is the tab; YARNNN is the agent; the operator is editing *in a surface*, not *through an agent*. Single `<EditInChatButton prompt={...} />` component across the cockpit.
- **R6 — Surfaces never branch on `program_slug`.** Specialization happens via composition manifest (Part 0), never via FE conditionals. If a tab's contract feels it needs to know which program is active, the answer is to declare the variation in `SURFACES.yaml`. The compositor seam is the kernel/program boundary at the FE layer; bypassing it for "just one quick conditional" undoes the structural reason the seam exists. Per ADR-225 Phase 3 + ADR-222 Principle 16.

---

## Part 3 — Affordance Cookbook

Quick lookup for common verb-object pairs. When adding a new affordance, add it here in the same commit it lands in code.

| Verb | Object | Shape | Location | Notes |
|---|---|---|---|---|
| Create | Task | Modal | Any tab `+` menu → TaskSetupModal (singular per ADR-215 Phase 4) | R2 |
| Create | Domain agent | Chat | Agents header → "Edit in chat" | R1 (judgment-shaped) |
| Create | Proposal | Chat | Agent proposes via ProposeAction primitive | Not operator-initiated |
| Upload | Document | Modal | Files `+` menu → UploadFileModal | R2 |
| Edit | Task (DELIVERABLE, team, schedule by judgment) | Chat | Work detail → "Edit in chat" | R1 |
| Edit | Task (mode, pause/resume, run now, archive) | Direct | Work detail → header buttons | R1, R2 |
| Edit | Agent identity (IDENTITY.md, memory/style) | Chat or Substrate | Substrate if file; Chat if judgment-shaped | R1 per field |
| Edit | `_shared/` authored rules (IDENTITY · BRAND · CONVENTIONS · MANDATE) | Substrate | Files detail → inline edit | R3 |
| Edit | Reviewer principles.md | Substrate | Files detail → inline edit | R3 (Phase 3 — retired PrinciplesPane chat edit path; PrinciplesPane links to Files) |
| Edit | `feedback.md` on a task | Chat | Work detail → FeedbackStrip → "Edit in chat" | R1 |
| Approve | Proposal | Direct | Work NeedsMe pane → Approve button | R1 |
| Reject | Proposal | Direct | Work NeedsMe pane → Reject button | R1 |
| Archive | Task | Direct | Work detail → header overflow | R1 |
| Archive | File | Direct | Files detail → overflow | R1 (when lifecycle allows) |
| Restore | File revision | Direct | Files revision panel → Restore | R1 |
| Connect | Platform | Modal | Settings `?tab=connectors` → connect flow | R2 (not on the four main tabs) |
| Graduate | Inline action → Task | Chat | Chat → material operator entry → "Make this recurring" → opens TaskSetupModal pre-filled | R5 phrasing; ADR-219 D6 |
| Filter | Narrative stream | Direct | Chat header → Filter icon → ChatFilterBar (weight / identity / task chips) | ADR-219 D5; deep-link query params |
| Expand | Housekeeping digest rollup | Direct | Chat → narrative_digest card → chevron toggle → rolled-up bullet list | ADR-219 Commit 3 + 5 |

---

## Part 4 — Tab-Hardening Sequence

Tabs harden in this order: **Files → Agents → Work → Chat.** The order reflects the dependency graph — each tab's design consumes substrate and deep-link targets from tabs earlier in the sequence.

```
Files  ←── Agents ←── Work ←── Chat
(substrate)  (identity)  (action)    (conductor)
zero inbound   1 inbound   2 inbound   3 inbound
```

- **Files first** — zero inbound dependencies. Every other tab links into Files paths. File detail shape, revision panel, inference-meta rendering, upload UX, directory-type-specific affordances must be stable before any deep-link target is promised.
- **Agents second** — Systemic vs Domain split is fresh (ADR-214) and needs to harden before Work references agents in task-team sections. Reviewer detail (three panes) is the highest-complexity agent type; lock that shape.
- **Work third** — Work detail links to task files (→ Files) and assigned agents (→ Agents). Deciding Work before Files/Agents is the pattern that caused the last two weeks of thrash.
- **Chat last** — Chat mirrors affordances exposed on other tabs. Locking Chat first forces reshapes every time another tab moves. Locking Chat last lets it converge to what's already stable.

Each phase lands with: code changes + this doc's contract section updated in the same commit + `docs/design/CHANGELOG.md` entry. No phase ships without the contract change — that discipline is what prevents ADR-215's motivation from recurring.

### Implementation status

> **Supersession note (2026-04-30, ADR-236 Cluster A + ADR-241):** Phase 2's `<SubstrateEditor>` was deleted by ADR-236 Round 5 Cluster A — every file now routes to chat for edits via `<EditInChatButton>` per the original ADR-236 assessment ("not notion-like, streamline back to edit via Chat"). Phase 3's `PrinciplesPane` and `ReviewerDetailView` were deleted by ADR-241 — Reviewer surface collapsed into Thinking Partner (Principles became a TP tab; Decisions relocated to `/work`). The `editable_prefixes` allowlist on the backend stays — chat's WriteFile primitive uses it server-side. The Phase 2/3 entries below are preserved verbatim per ADR-236 Rule 2 (historical record); for current canonical state see the §"Cockpit nav" topology above + the per-tab contracts.

- **Phase 1 — Contracts + CRUD matrix** — **Implemented 2026-04-24** (commit `936eacc`). ADR-215 + this doc + four archive supersedes + CHANGELOG entry.
- **Phase 2 — Files hardening** — **Implemented 2026-04-24**. `<EditInChatButton>` shared component landed at `web/components/shared/EditInChatButton.tsx` (R5 single label). `<SubstrateEditor>` landed at `web/components/workspace/SubstrateEditor.tsx` with `isSubstrateEditable()` predicate covering `/workspace/context/_shared/{IDENTITY,BRAND,CONVENTIONS,MANDATE}.md`. `ManageContextModal.tsx` deleted. `ContentViewer.tsx` refactored — substrate-editable files render inline editor, non-substrate files keep chat-draft affordance. Backend `editable_prefixes` gained `MANDATE.md`. Labels normalized across `WorkDetail.tsx` and `PrinciplesPane.tsx` to R5 ("Edit in chat"). Phase 2 follow-up (MemorySection on `/settings`) closed same day in the Settings cleanup commit — see CHANGELOG entry "Settings > Memory tab retirement." TypeScript pass.
- **Phase 3 — Agents hardening** — **Implemented 2026-04-24**. `PrinciplesPane` retired from chat-seeded edit path (R3 compliance). `/workspace/review/principles.md` added to both `SHARED_EDITABLE_PATHS` (frontend) and `editable_prefixes` (backend `api/routes/workspace.py`). PrinciplesPane now renders read-only with a deep-link to Files (`/context?path=/workspace/review/principles.md`) — same substrate editor as the four `_shared/` rules. `ReviewerDetailView` prop surface simplified (no `onOpenChatDraft` required; decisions stream was already read-only). `AgentContentView` YARNNN + domain + platform-bot + reviewer dispatch audited clean — no R5 label drift, AGENT.md edits continue to flow through primitives (judgment-shaped per R1). TypeScript pass.
  - **Known follow-ups (not blocking Phase 4):**
    - `web/components/settings/MemorySection.tsx` retains a parallel IDENTITY/BRAND edit path on `/settings`. Files is canonical; Settings mouth retires in a later sweep.
    - `TaskSetupModal` remains as the `/agents` `+` menu entry "Assign a new task" — it's a modal that seeds chat rather than a direct-create API call. R2 gray area. `/work` already uses `CreateTaskModal` for direct-create; Phase 4 reconciles the two creation modals into a single model per ADR-215 R2.
- **Phase 4 — Work hardening** — **Implemented 2026-04-24**.
  - `IntelligenceCard` silent-degrade fix per ADR-198 §3 Briefing invariant. The 404-before-first-run path is a normal empty state (task not scaffolded at signup per ADR-206), not an error. Missing output + transient HTTP failure both collapse to "Synthesis pending" placeholder. Retry box removed — Briefing never sprouts error chrome inside a list surface.
  - `CreateTaskModal` retired; `/work` `+` menu uses `TaskSetupModal` (singular creation flow across all four tabs). `api.tasks.create` client method removed (YARNNN is the sole frontend consumer of task creation via `ManageTask(action="create")`; backend POST `/api/tasks` endpoint preserved for the primitive). R2 singular-implementation achieved.
  - Cockpit-zone visual treatment on `/work` list mode: section labels "Cockpit" + "Work", subtle zone tint on Cockpit, zone padding. Single vertical scroll preserved per ADR-205 F2 — tab-ify was considered and rejected (would force proposals behind a click, undoes ADR-206 deliverables-first).
  - 4 kind-middles audited: zero R1/R3/R5 violations. Middles are content-only; edit affordances live in `WorkDetail` header (Run/Pause = Direct, Edit in chat = Chat) with R5-compliant labels from Phase 2.
- **Phase 6 — Snapshot reframe (2026-04-24)** — **Implemented 2026-04-24**.
  - The four-tab `WorkspaceStateView` overlay (Readiness / Attention / Last session / Activity) reframed as three-tab `SnapshotModal` (Mandate / Review standard / Recent). See the Chat contract's "Snapshot overlay" subsection above for the full shape.
  - Zero LLM at modal open — every tab reads substrate files and neutral audit ledgers; no summarization pass.
  - Stay-in-chat contract: overlay is *of* the conversation, not a nav hub. No outbound links per row. Close returns to typing.
  - Marker renamed `<!-- workspace-state: ... -->` → `<!-- snapshot: {"lead":"mandate|review|recent"} -->`. Header button label renamed "Workspace" → "Snapshot". `parseWorkspaceStateMeta` → `parseSnapshotMeta` (singular implementation, no dual markers).
  - `WORKSPACE-STATE-SURFACE.md` archived — the living contract for this overlay now lives here in SURFACE-CONTRACTS.
  - YARNNN prompts (`yarnnn_prompts/*`) updated to emit the new marker where applicable; `api/prompts/CHANGELOG.md` records the change per ADR-215 discipline rule 7.

- **Phase 7 — ADR-219 narrative absorption (doc-only)** — **Implemented 2026-04-26**.
  - Chat contract reframed as **the narrative surface** per FOUNDATIONS Axiom 9 — every invocation in the workspace surfaces here as an Identity-tagged entry with weight-driven rendering. Identity widening (`user | assistant | system | reviewer | agent | external`), weight gradient (`material | routine | housekeeping`), pulse vocabulary, filter bar, narrative_digest card all named in the contract.
  - Work contract amended: list-row headlines source from `GET /api/narrative/by-task` (ADR-219 Commit 4), not `task.last_run_at`. WorkDetail's run-history stays on `agent_runs` per ADR-219 D7.
  - Affordance cookbook gains three new rows: Make-this-recurring (Chat / R5), narrative filter chip (Direct), housekeeping digest expand (Direct).
  - **No code change in this phase** — ADR-219 Commits 1–6 already shipped (commits `1007869` → `e67abd6`, merged to main 2026-04-26). This is the canon-doc catch-up so SURFACE-CONTRACTS agrees with what live code does.
  - **Known follow-ups (deferred from Phase 7, not blocking):**
    - **Cockpit zone (BriefingStrip on /work) hasn't migrated to narrative.** `NeedsMePane`, `SinceLastLookPane`, `SnapshotPane`, `IntelligenceCard` all read `tasks` / `agents` / workspace files directly; the narrative endpoint is unused there. After a soak period of operator use, evaluate whether `SinceLastLookPane` should consume narrative directly (it most directly answers "what happened while I was away," which is what narrative is for). Two read paths to the same truth is acceptable for alpha — promote to drift if duplication causes operator confusion.
    - **D6 "Archive task (keep history)" affordance** belongs on WorkDetail, not Chat. Pairs with a future task-lifecycle commit. ADR-219 D6 part 2.
    - **Pulse + time-range filters** on Chat — richer UI than chips, deferred.

- **Phase 8 — Unified compositor seam (ADR-225 Phase 3)** — **Implemented 2026-04-27** (commits `3460919` → `[final]`). Bumps doc to v2.0.
  - **New Part 0** added: composition layer preamble + slot inventory + R6 (no FE branch on `program_slug`).
  - **R6 ratified** as the sixth CRUD rule. The compositor seam is the kernel/program boundary at the FE layer; bypassing it for "just one quick conditional" undoes the structural reason the seam exists.
  - **Work tab contract rewritten** around three compositor-resolved layers in detail mode (chrome / middle / feedback strip) and two compositor-resolved zones in list mode (cockpit panes / pinned tasks + banner). Per-kind hardcoded dispatch is gone from this contract — the contract describes what each layer does and where its declarations live.
  - **Operational vs historical timestamp rule** now contract-explicit (was code-implicit per the audit's observation #2). Chrome metadata shows operational signal; narrative carries historical context.
  - Closes the prior Phase 7 deferred follow-up: "Cockpit zone hasn't migrated to narrative." The cockpit zone is now compositor-resolved, which makes the migration question scoped — narrative-shaped panes can register as library components and bundles can swap them in via `cockpit_panes`.
  - **Code changes** absorbed: `WorkDetail.tsx` 515 → 164 lines (per-kind chrome dispatch + OverflowMenu DELETED); `BriefingStrip.tsx` DELETED; new `ChromeRenderer` + `CockpitRenderer` siblings to `MiddleResolver`; new `KERNEL_DEFAULT_CHROME` + `KERNEL_DEFAULT_COCKPIT_PANES` registries; new `WorkDetailActionsContext` + `CockpitContext` providers; alpha-trader SURFACES.yaml extended end-to-end.
  - **Known gaps named in `docs/architecture/compositor.md`** (not blocking):
    - `MiddleResolver` name overfits to "middle" now that `ChromeRenderer` and `CockpitRenderer` are siblings. Rename rejected (too many call sites); clarification at the doc layer is sufficient.
    - Bundle-supplied agent-tab and files-tab chrome are deferred — the resolver pattern is portable; extending to other tabs is incremental as bundles need it.
    - Multi-bundle chrome merge semantics tested on backend (10/10 ADR-225 backend tests still pass) but no real two-active-bundle workspace exists yet to surface FE rendering edge cases.

- **Phase 5 — Chat hardening** — **Implemented 2026-04-24**.
  - `OnboardingModal` + `ContextSetup` retired. Auto-trigger was already retired by ADR-190 (onboarding is conversational); the manual "Update workspace" `+` menu entry violated R2 (update is never Modal) and R3 (identity/brand/conventions are substrate). `WorkspaceStateView` identity-empty CTAs now seed chat prompts — YARNNN infers identity/brand from the conversation and writes via `InferContext` / `InferWorkspace` (post-ADR-235).
  - `/chat` `+` menu now has exactly one built-in entry: "Start new work" → `TaskSetupModal`. R4 fully enforced on Chat.
  - `ChatSurface.onContextSubmit` prop removed (orphan after OnboardingModal retirement); `/chat` page simplified.
  - `ReviewerCard` deep-link migrated `/review` → `/agents?agent=reviewer` (ADR-214 canonical route). Docstring updated with Stream archetype invariants.
  - `parseOnboardingMeta` export removed (dead code). `stripOnboardingMeta` retained — display hygiene for historical messages that may still carry the retired marker.
  - `ChatEmptyState` + 4-chip cold-start landing retained as-is — already R-compliant (seed composer text or open file picker).
  - Stale doc comments cleaned in `auth/callback/page.tsx`, `ComposerInput.tsx`, `TaskSetupModal.tsx`, `WorkspaceStateView.tsx`, `workspace-state-meta.ts`.
  - TypeScript pass. `grep -rn "Edit via" web/`: zero live hits. Full R1–R5 compliance across all four tabs.

- **Phase 9 — ADR-231 substrate-vocabulary alignment** — **Implemented 2026-04-29** (commits `b7e4fd3` Class A · `1a77459` Class B · this commit Class D).
  - **Class A logic fix**: `/context` Reports section deep-links migrated from the dead `/tasks/{slug}/outputs/latest` namespace to the natural-home `/workspace/reports/{slug}` substrate root per ADR-231 D2. Detail-mode dispatcher regex updated; `DeliverableMiddle` consumes via `api.recurrences.listOutputs` already (Phase 3.6/3.8 backend migration).
  - **Class B vocabulary refresh**: `ChatEmptyState` adds primary "Ask for something" chip per ADR-231 D1 invocation-first default — recurrence chips (Track / Build a recurring report) become explicit-graduation affordances at indexes 3-4. `TaskSetupModal` + `ChatSurface` + `client.ts` comment refs to `ManageTask` retired; all docstrings now point at `ManageRecurrence(action='create', ...)` per ADR-231 D5 + ADR-235 D1.c (ManageTask deleted in Phase 3.7; UpdateContext deleted in ADR-235).
  - **Class D doc refresh** (this entry): SURFACE-CONTRACTS.md Files tab list-mode tree, Work tab Reads section, Work `+` menu primitive ref, deep-links out, Chat tab Writes/Deep-links, inline-to-recurrence graduation flow — all aligned with ADR-231 D2/D3 natural-home substrate (`reports/{slug}/`, `context/{domain}/`, `operations/{slug}/`, `_shared/back-office.yaml`) + D5 primitive surface (`ManageRecurrence` + `FireInvocation`).
  - **Refuses preserved** — Class C file renames (`web/components/tasks/` → `recurrences/`, etc.) are pure cosmetic file moves; deferred to a quiet hygiene window once the parallel ADR-233 prompt reorg lands.
  - TypeScript pass. Backend tests 96/96 still green.

---

## Related docs

- [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — governs this doc
- [ADR-198](../adr/ADR-198-surface-archetypes.md) — archetype vocabulary (Document · Dashboard · Queue · Briefing · Stream)
- [ADR-214](../adr/ADR-214-agents-page-consolidation.md) — four-tab nav + Reviewer-inside-Agents
- [ADR-167 v2](../adr/ADR-167-list-detail-surfaces.md) — list/detail pattern per tab
- [ADR-209](../adr/ADR-209-authored-substrate.md) — revision chain, `authored_by`, substrate attribution
- [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) — invocation as atom; `/chat` is the narrative surface; `/work` is the narrative filtered by task slug
- [ADR-225](../adr/ADR-225-compositor-layer.md) — compositor seam (Phase 3 unified — chrome + cockpit + middle through one resolver pattern)
- [docs/architecture/compositor.md](../architecture/compositor.md) — architecture-level reference for the resolver pattern, binding taxonomy, kernel-default registry
- [invocation-and-narrative.md](../architecture/invocation-and-narrative.md) — canonical narrative vocabulary (invocation · pulse · narrative · task as legibility wrapper)
- [ADR-206](../adr/ADR-206-operation-first-scaffolding.md) — operator-facing three-layer view (Intent · Operation · Deliverables)
- [ADR-168](../architecture/primitives-matrix.md) — canonical primitive matrix (not a design doc, but the authority for what verbs exist)
- [FOUNDATIONS v6.8](../architecture/FOUNDATIONS.md) — Axiom 6 (Channel), Axiom 9 (Invocation + Narrative), Derived Principle 12 (Channel legibility gates autonomy)
- [INLINE-PLUS-MENU.md](./INLINE-PLUS-MENU.md) — existing plus-menu verb taxonomy; under ADR-215 R4 it is strictly a modal launcher
