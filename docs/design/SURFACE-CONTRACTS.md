# Surface Contracts

**Version:** v1.7 (2026-04-26)
**Status:** Canonical
**Governed by:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Surface Contracts and CRUD Principles
**Grounded in:** [ADR-198](../adr/ADR-198-surface-archetypes.md) surface archetypes · [ADR-214](../adr/ADR-214-agents-page-consolidation.md) four-tab nav · [ADR-209](../adr/ADR-209-authored-substrate.md) authored substrate · [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) invocation + narrative · [ADR-168](../architecture/primitives-matrix.md) primitive matrix · [FOUNDATIONS v6.8](../architecture/FOUNDATIONS.md) Axiom 6 (Channel) + Axiom 9 (Invocation + Narrative)
**Supersedes:** `archive/SURFACE-ARCHITECTURE.md`, `archive/SURFACE-ACTION-MAPPING.md`, `archive/SURFACE-DISPLAY-MAP.md`, `archive/SURFACE-PRIMITIVES-MAP.md`

---

## Purpose

This is the single design reference for YARNNN's cockpit. It answers four questions, in order:

1. **What does each tab do?** (per-tab contract)
2. **How is mutation expressed?** (CRUD matrix + 5 rules)
3. **What affordances live where?** (affordance cookbook)
4. **In what order do we harden the tabs?** (sequencing)

When a design decision spans two tabs (e.g. "deep-link from Work to Files"), both tabs' contracts must allow it. When a CRUD decision arises (e.g. "how do we let the operator refine a task's deliverable?"), the matrix picks the shape. When either answer is unclear, the doc is wrong and gets updated — not the code.

---

## Part 1 — Per-Tab Surface Contracts

Four tabs, four contracts. Each contract has seven fixed sections: **Archetype · Reads · List mode · Detail mode · `+` menu · Deep-links out · Refuses.**

### Tab: Files

**Route:** `/context` (legacy slug retained; operator label "Files" per ADR-180)

- **Archetype:** Dashboard (primary, per ADR-198 §3) — live substrate slice, read-primary. Detail view of a file is a Document archetype when the file is a composed output.
- **Reads:** `workspace_files` (entire filesystem), `workspace_file_versions` (revision chain per ADR-209), `workspace_blobs` indirectly via revision reads.
- **List mode** (no `?path=`): filesystem tree grouped by ADR-152 directory registry:
  - `_shared/` — workspace-wide authored rules (IDENTITY · BRAND · CONVENTIONS · MANDATE)
  - `context/{domain}/` — accumulated intelligence per domain, including `_performance.md` (ADR-195) and `_tracker.md`
  - `tasks/{slug}/` — per-task charter, DELIVERABLE, feedback, outputs, memory
  - `agents/{slug}/` — per-domain-agent AGENT.md, memory, style
  - `review/` — Reviewer substrate (IDENTITY · principles · decisions — read-only here, edited from Agents tab or via Review flow)
  - `uploads/` — operator-contributed documents (ADR-197)
  - `memory/` — YARNNN working memory (conversation summaries, workspace state)
  - `outputs/` — promoted task outputs per `output_category` (ADR-152)
- **Detail mode** (`?path=/workspace/...`):
  - Rendered file content (markdown, HTML, or binary via `content_url`)
  - Inference-meta caption (ADR-162 sub-phase D) when present
  - Revision history panel (ADR-209 P4) — `authored_by` trail, diff, restore
  - Substrate-native edit affordance when `authored_by=operator` is appropriate (IDENTITY, BRAND, CONVENTIONS, principles, MANDATE, uploaded documents)
- **`+` menu:** UploadFileModal (operator uploads a document into `/workspace/uploads/`). No other modals. No chat seeders.
- **Deep-links out:** every file path is a stable URL (`/context?path=...`) linked from Work task-detail (`DELIVERABLE.md`, `feedback.md`, `outputs/`), Agents detail (`AGENT.md`, `memory/`, `style.md`), Chat artifacts, and the Briefing strip on Work.
- **Refuses:**
  - Task orchestration, agent authoring, proposal approval — those are Work/Agents/Work respectively
  - "Edit in chat" buttons on substrate files (per R3) — Files is where substrate gets edited; Chat would invoke `UpdateContext` and produce the same write with less clear provenance
  - Duplicate rendering of task outputs (outputs exist in one canonical place — under the owning task; Files links rather than embeds per ADR-198 I2)

### Tab: Agents

**Route:** `/agents` (canonical per ADR-214, reverses ADR-201)

- **Archetype:** List (list mode) + Dashboard (detail mode, per ADR-167 v2). Reviewer decisions stream is a Stream archetype embed inside Reviewer detail.
- **Reads:** `agents` table filtered to principals (YARNNN `thinking_partner` + user-authored domain agents, per ADR-189 origin filter + ADR-214 synthesized Reviewer pseudo-agent), plus each agent's filesystem home (`/workspace/agents/{slug}/*` or `/workspace/review/*` for Reviewer).
- **List mode** (no `?agent=`): two sections, always in this order:
  - **Systemic** — exactly two cards: YARNNN and Reviewer. Unconditional. Rendered even on cold-start workspaces.
  - **Domain** — user-authored instance agents, zero-to-many. This is the authored-team moat (ADR-189); empty state is a real product state, not an error.
- **Detail mode** (`?agent={slug}`): dispatches on `agent_class` per ADR-214:
  - `thinking_partner` (YARNNN) → IDENTITY card + health card + memory substrate panes (AGENT.md edits flow through primitives — judgment-shaped per R1)
  - `reviewer` → ReviewerDetailView: identity card + principles pane (Dashboard read + "Edit on Files" deep-link per R3) + decisions stream (Stream archetype, append-only)
  - domain agents → IDENTITY card + health card + AGENT.md + memory/style substrate panes (AGENT.md edits flow through primitives)
- **`+` menu:** none. Authoring a domain agent is **judgment-shaped** (operator describes a gap; YARNNN proposes the agent shape; substrate gets written) — this is Chat territory per R1 + R2. The Agents tab's header carries an "Author in chat" button (R5 phrasing: "Edit in chat") seeding the prompt. No `AuthorAgentModal`.
- **Deep-links out:** each agent's files on Files (`/context?path=/workspace/agents/{slug}/AGENT.md`), the agent's tasks filtered on Work (`/work?agent={slug}`), and Chat with the agent preselected (`/chat?agent={slug}`).
- **Refuses:**
  - Task management (tasks live on Work; this tab shows agent *identity*, not agent *work*)
  - Editing production roles or platform integrations as if they were agents (ADR-212 — those are Orchestration, not Agents)
  - Principles/IDENTITY modal editing (ADR-215 R3 — substrate edit goes to Files)

### Tab: Work

**Route:** `/work`

- **Archetype:** Briefing + Queue (list-mode composition) → Document/Dashboard/Stream (detail mode, per output_kind).
- **Narrative semantics** (ADR-219 D4): `/work` **is the narrative filtered by `metadata.task_slug`**. The list-row recent-activity headline reads from the narrative via `GET /api/narrative/by-task` (ADR-219 Commit 4) — the legacy `task.last_run_at` timestamp source was retired; tasks with no narrative entries simply render no headline (singular implementation). WorkDetail's per-task run-history continues to read `agent_runs` per ADR-219 D7 — that's the audit ledger view, separate consumer.
- **Reads:** `tasks` table, `/workspace/tasks/{slug}/*` (TASK.md, DELIVERABLE.md, feedback.md, outputs, memory), `/workspace/review/decisions.md` (for the SinceLastLook pane), `/workspace/context/_performance_summary.md` (for the Snapshot pane per ADR-195 Phase 3), `agent_runs` (for WorkDetail's per-task run-history view), **`GET /api/narrative/by-task`** (for WorkListSurface row headlines per ADR-219 Commit 4).
- **List mode** (no `?task=`): single vertical scroll with two visually-distinct zones per ADR-215 Phase 4.
  - **Cockpit zone** (`<BriefingStrip>`) — section label "Cockpit", subtle tint, Briefing+Queue archetypes. Panes in ADR-206 deliverables-first order:
    1. NeedsMe — Queue (pending proposals)
    2. Snapshot — Dashboard tiles (book / workforce / context)
    3. SinceLastLook — Briefing (temporal changes)
    4. Workspace Intelligence — synthesis card. Silent-degrade per ADR-198 §3 Briefing invariant: 404 / missing output / transient error all collapse into "Synthesis pending" empty state. No Retry box inside the list surface.
  - **Work zone** (`<WorkListSurface>`) — section label "Work". Task list grouped by output_kind (Reports · Tracking · Connected · Actions), with My Work / Connectors / System tab switcher for scope.
  - Zones share one vertical scroll (ADR-205 F2 — deliberate: glance-then-drill mental model; tab-ify was considered and rejected because it would force proposals behind a click).
- **Detail mode** (`?task={slug}`): ADR-167 v2 four kind-aware middles. Middles are content-only — edit affordances live in `WorkDetail` header row (Run/Pause = Direct; Edit in chat = Chat per R1+R5):
  - `produces_deliverable` → DeliverableMiddle (rendered output + quality contract panel)
  - `accumulates_context` → TrackingMiddle (domain folder link + CHANGELOG)
  - `external_action` → ActionMiddle (fire history + platform link-out)
  - `system_maintenance` → MaintenanceMiddle (hygiene log + run history)
- **`+` menu:** `TaskSetupModal` (singular creation modal across the cockpit — ADR-178 two-route rich intake; forwards to YARNNN via `sendMessage` which calls `ManageTask(action="create")` in the same turn). Per ADR-215 Phase 4 singular-implementation, `CreateTaskModal` was retired — one creation modal across `/chat`, `/work`, `/agents`, `/context`.
- **Deep-links out:** task files on Files (`/context?path=/workspace/tasks/{slug}/DELIVERABLE.md`), assigned agents on Agents (`/agents?agent={slug}`), Chat with task preselected for "Edit in chat" (`/chat?task={slug}`).
- **Refuses:**
  - File browsing outside task scope (goes to Files)
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
- **Writes:** through primitives (`UpdateContext`, `ManageTask`, `ManageAgent`, `ProposeAction`, etc. per ADR-168). Chat never writes substrate directly; it writes through YARNNN's primitive invocations. Every primitive invocation also emits a narrative entry via `services.narrative.write_narrative_entry` (ADR-219 Commit 2 single write path; ADR-219 Commit 6 final coverage gate enforces this).
- **Stream mode** (default, conversation active): append-only message log. Reviewer verdicts appear as `role='reviewer'` messages per ADR-212; agent task completions appear as `role='agent'` entries with task-slug envelope; back-office digests appear as `role='system'` cards with `system_card='narrative_digest'` (collapsed-by-default with expand-to-list). MCP foreign-LLM calls land as `role='external'` entries (ADR-219 Commit 6) with `metadata.mcp_tool` + `metadata.mcp_client` provenance. Artifact cards render inline when a primitive's response carries one. "Edit in chat" entries from other tabs open Chat with a seeded first message.
- **Empty state** (cold start per ADR-205 F1): `<ChatEmptyState>` — deterministic client-side landing with four suggestion chips (Upload a doc, Paste a URL, Track something recurring, Build a recurring report). Zero LLM cost on first load. The only surface in the cockpit that overrides its archetype for first-run guidance.
- **`+` menu:** exactly one entry per ADR-215 Phase 5 — "Start new work" → `TaskSetupModal` (R4 modal launcher). The prior "Update workspace" entry was retired — it violated R2 (update is never Modal) and R3 (identity/brand/conventions are substrate, edited on Files).
- **Deep-links out:** any file YARNNN cites (`/context?path=...`), any task ManageTask creates or updates (`/work?task=...`), any agent ManageAgent touches (`/agents?agent=...`). Reviewer verdict cards (role='reviewer' messages per ADR-212) link to `/agents?agent=reviewer` (ADR-214 canonical route). Artifacts carry links, not embeds.
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

  **Identity-empty states** degrade gracefully — a missing MANDATE.md renders "Not yet declared" with an "Edit in chat" button seeding "Help me author my mandate"; same pattern for missing principles.md. R3 is preserved (substrate-file edits would happen on Files, but this overlay never *edits* substrate — it only seeds the conversation that eventually writes via UpdateContext/inference).
- **Reviewer verdict thread** (ADR-212): `role='reviewer'` session messages render as `<ReviewerCard>` inline in the stream — verdict + occupant + reasoning + deep-link to `/agents?agent=reviewer`. Stream archetype invariant: append-only; verdict cards are historical entries, never mutated inline.
- **Inline-to-task graduation** (ADR-219 D6): material-weight operator messages that have no `metadata.task_slug` (i.e. inline actions per FOUNDATIONS Axiom 9) carry an inline **"Make this recurring"** affordance. Click opens `TaskSetupModal` pre-filled with `Recurring intent: <message-prefix>` so YARNNN turns it into `ManageTask(action='create')` on submit. Reversible: a task can be archived later (deferred to WorkDetail per Phase-7+) and the same shape returns to inline. The atom of action (the invocation) is the same throughout — only the legibility wrapper rotates.
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

### The five rules

- **R1 — One verb, one shape per object.** "Edit a task" is always Chat. "Edit a file" is always Substrate. "Approve a proposal" is always Direct. No mixing across the cockpit.
- **R2 — Create is always Modal. Update/Delete is Direct or Chat, never Modal.** Modals exist for the moment of creation where the operator arrives with a blueprint. After creation, mutation is single-click Direct or judgment-shaped Chat. No "edit modal" anywhere in the cockpit.
- **R3 — Substrate operations bypass Chat.** If the thing being edited IS a file, the edit surface is Files. The revision panel (ADR-209 P4) shows `authored_by=operator`. No "Edit in chat" button on substrate files — Chat would invoke `UpdateContext` anyway, and direct substrate edit produces the same write with clearer provenance.
- **R4 — The `+` menu is a modal launcher. Never a chat seeder.** Each tab's `+` menu lists only Modal creation flows. Chat-shaped mutations live on the object's own detail page as the R5 label.
- **R5 — One label: "Edit in chat".** All existing phrasings ("Edit via chat" / "Edit via YARNNN" / "Edit via yarnnn") converge on **"Edit in chat"**. Lowercase. No YARNNN branding — chat is the tab; YARNNN is the agent; the operator is editing *in a surface*, not *through an agent*. Single `<EditInChatButton prompt={...} />` component across the cockpit.

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

- **Phase 5 — Chat hardening** — **Implemented 2026-04-24**.
  - `OnboardingModal` + `ContextSetup` retired. Auto-trigger was already retired by ADR-190 (onboarding is conversational); the manual "Update workspace" `+` menu entry violated R2 (update is never Modal) and R3 (identity/brand/conventions are substrate). `WorkspaceStateView` identity-empty CTAs now seed chat prompts — YARNNN infers identity/brand from the conversation and writes via `UpdateContext`.
  - `/chat` `+` menu now has exactly one built-in entry: "Start new work" → `TaskSetupModal`. R4 fully enforced on Chat.
  - `ChatSurface.onContextSubmit` prop removed (orphan after OnboardingModal retirement); `/chat` page simplified.
  - `ReviewerCard` deep-link migrated `/review` → `/agents?agent=reviewer` (ADR-214 canonical route). Docstring updated with Stream archetype invariants.
  - `parseOnboardingMeta` export removed (dead code). `stripOnboardingMeta` retained — display hygiene for historical messages that may still carry the retired marker.
  - `ChatEmptyState` + 4-chip cold-start landing retained as-is — already R-compliant (seed composer text or open file picker).
  - Stale doc comments cleaned in `auth/callback/page.tsx`, `ComposerInput.tsx`, `TaskSetupModal.tsx`, `WorkspaceStateView.tsx`, `workspace-state-meta.ts`.
  - TypeScript pass. `grep -rn "Edit via" web/`: zero live hits. Full R1–R5 compliance across all four tabs.

---

## Related docs

- [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — governs this doc
- [ADR-198](../adr/ADR-198-surface-archetypes.md) — archetype vocabulary (Document · Dashboard · Queue · Briefing · Stream)
- [ADR-214](../adr/ADR-214-agents-page-consolidation.md) — four-tab nav + Reviewer-inside-Agents
- [ADR-167 v2](../adr/ADR-167-list-detail-surfaces.md) — list/detail pattern per tab
- [ADR-209](../adr/ADR-209-authored-substrate.md) — revision chain, `authored_by`, substrate attribution
- [ADR-219](../adr/ADR-219-invocation-narrative-implementation.md) — invocation as atom; `/chat` is the narrative surface; `/work` is the narrative filtered by task slug
- [invocation-and-narrative.md](../architecture/invocation-and-narrative.md) — canonical narrative vocabulary (invocation · pulse · narrative · task as legibility wrapper)
- [ADR-206](../adr/ADR-206-operation-first-scaffolding.md) — operator-facing three-layer view (Intent · Operation · Deliverables)
- [ADR-168](../architecture/primitives-matrix.md) — canonical primitive matrix (not a design doc, but the authority for what verbs exist)
- [FOUNDATIONS v6.8](../architecture/FOUNDATIONS.md) — Axiom 6 (Channel), Axiom 9 (Invocation + Narrative), Derived Principle 12 (Channel legibility gates autonomy)
- [INLINE-PLUS-MENU.md](./INLINE-PLUS-MENU.md) — existing plus-menu verb taxonomy; under ADR-215 R4 it is strictly a modal launcher
