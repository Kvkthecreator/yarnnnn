# Surface Contracts

**Version:** v1.1 (2026-04-24)
**Status:** Canonical
**Governed by:** [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — Surface Contracts and CRUD Principles
**Grounded in:** [ADR-198](../adr/ADR-198-surface-archetypes.md) surface archetypes · [ADR-214](../adr/ADR-214-agents-page-consolidation.md) four-tab nav · [ADR-209](../adr/ADR-209-authored-substrate.md) authored substrate · [ADR-168](../architecture/primitives-matrix.md) primitive matrix · [FOUNDATIONS v6.1](../architecture/FOUNDATIONS.md) Axiom 6 (Channel)
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
  - `thinking_partner` (YARNNN) → IDENTITY card + health card + memory substrate panes
  - `reviewer` → ReviewerDetailView: identity card + principles pane + decisions stream (the three panes absorbed from the deleted `/review` route)
  - domain agents → IDENTITY card + health card + AGENT.md + memory/style substrate panes
- **`+` menu:** none. Authoring a domain agent is **judgment-shaped** (operator describes a gap; YARNNN proposes the agent shape; substrate gets written) — this is Chat territory per R1 + R2. The Agents tab's header carries an "Author in chat" button (R5 phrasing: "Edit in chat") seeding the prompt. No `AuthorAgentModal`.
- **Deep-links out:** each agent's files on Files (`/context?path=/workspace/agents/{slug}/AGENT.md`), the agent's tasks filtered on Work (`/work?agent={slug}`), and Chat with the agent preselected (`/chat?agent={slug}`).
- **Refuses:**
  - Task management (tasks live on Work; this tab shows agent *identity*, not agent *work*)
  - Editing production roles or platform integrations as if they were agents (ADR-212 — those are Orchestration, not Agents)
  - Principles/IDENTITY modal editing (ADR-215 R3 — substrate edit goes to Files)

### Tab: Work

**Route:** `/work`

- **Archetype:** Briefing + Queue (list-mode composition) → Document/Dashboard/Stream (detail mode, per output_kind).
- **Reads:** `tasks` table, `/workspace/tasks/{slug}/*` (TASK.md, DELIVERABLE.md, feedback.md, outputs, memory), `/workspace/review/decisions.md` (for the SinceLastLook pane), `/workspace/context/_performance_summary.md` (for the Snapshot pane per ADR-195 Phase 3), `agent_runs` (for the SinceLastLook pane's run history).
- **List mode** (no `?task=`): BriefingStrip stacked above the task list.
  - **BriefingStrip** (panes in ADR-206 deliverables-first order):
    1. NeedsMe — Queue (pending proposals)
    2. Snapshot — Dashboard tiles (book / workforce / context)
    3. SinceLastLook — Briefing (temporal changes)
    4. Workspace Intelligence — synthesis card (silent-degrade on absence per ADR-198 §3 I2 — Phase 4 fixes current "API Error 404" leak)
  - **Task list** below the strip, grouped by output_kind (Reports · Tracking · Connected · Actions), with My Work / Connectors / System tab switcher for scope.
- **Detail mode** (`?task={slug}`): ADR-167 v2 four kind-aware middles:
  - `produces_deliverable` → DeliverableMiddle (rendered output + quality contract panel)
  - `accumulates_context` → TrackingMiddle (domain folder link + CHANGELOG)
  - `external_action` → ActionMiddle (fire history + platform link-out)
  - `system_maintenance` → MaintenanceMiddle (hygiene log + run history)
- **`+` menu:** CreateTaskModal (creation is Modal per R2). Title + type_key + mode + schedule + context. No other modals.
- **Deep-links out:** task files on Files (`/context?path=/workspace/tasks/{slug}/DELIVERABLE.md`), assigned agents on Agents (`/agents?agent={slug}`), Chat with task preselected for "Edit in chat" (`/chat?task={slug}`).
- **Refuses:**
  - File browsing outside task scope (goes to Files)
  - Agent identity editing (goes to Agents → Chat)
  - Replacing Files for the `_shared/` authored rules (per R3 — `ManageContextModal` retired)

### Tab: Chat

**Route:** `/chat` (HOME per ADR-205 F1)

- **Archetype:** Stream (append-only conversation) with inline artifact cards. Cold-start empty-state is the one exception — renders a curated landing panel.
- **Reads:** `chat_sessions` + `session_messages` (windowed per ADR-159), compact index (`format_compact_index()` per ADR-186 profile), all substrate indirectly via YARNNN's tool calls.
- **Writes:** through primitives (`UpdateContext`, `ManageTask`, `ManageAgent`, `ProposeAction`, etc. per ADR-168). Chat never writes substrate directly; it writes through YARNNN's primitive invocations.
- **Stream mode** (default, conversation active): append-only message log. Reviewer verdicts appear as `role='reviewer'` messages per ADR-212. Artifact cards render inline when a primitive's response carries one (task preview, file summary, proposal draft). "Edit in chat" entries from other tabs open Chat with a seeded first message.
- **Empty state** (cold start per ADR-205 F1): landing panel with suggestion chips ("Connect a platform" · "Upload a document" · "Describe your work") — the only surface in the cockpit that overrides its archetype for first-run guidance.
- **`+` menu:** none. Chat is the mutation surface for judgment-shaped actions; Chat seeds don't need a `+` entry point.
- **Deep-links out:** any file YARNNN cites (`/context?path=...`), any task ManageTask creates or updates (`/work?task=...`), any agent ManageAgent touches (`/agents?agent=...`). Artifacts carry links, not embeds.
- **Refuses:**
  - Full CRUD forms (modal-shape — those are on other tabs per R2)
  - Heavy data tables (those are Dashboard archetype — other tabs)
  - Replacing direct affordances on other tabs (approve buttons stay on Work; pause buttons stay on Work; no Chat-only paths for Direct-shape operations per R1)

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
| Create | Task | Modal | Work `+` menu → CreateTaskModal | R2 |
| Create | Domain agent | Chat | Agents header → "Edit in chat" | R1 (judgment-shaped) |
| Create | Proposal | Chat | Agent proposes via ProposeAction primitive | Not operator-initiated |
| Upload | Document | Modal | Files `+` menu → UploadFileModal | R2 |
| Edit | Task (DELIVERABLE, team, schedule by judgment) | Chat | Work detail → "Edit in chat" | R1 |
| Edit | Task (mode, pause/resume, run now, archive) | Direct | Work detail → header buttons | R1, R2 |
| Edit | Agent identity (IDENTITY.md, memory/style) | Chat or Substrate | Substrate if file; Chat if judgment-shaped | R1 per field |
| Edit | `_shared/` authored rules (IDENTITY · BRAND · CONVENTIONS · MANDATE) | Substrate | Files detail → inline edit | R3 |
| Edit | Reviewer principles.md | Substrate | Files detail → inline edit | R3 (retires PrinciplesPane edit path in Phase 3) |
| Edit | `feedback.md` on a task | Chat | Work detail → FeedbackStrip → "Edit in chat" | R1 |
| Approve | Proposal | Direct | Work NeedsMe pane → Approve button | R1 |
| Reject | Proposal | Direct | Work NeedsMe pane → Reject button | R1 |
| Archive | Task | Direct | Work detail → header overflow | R1 |
| Archive | File | Direct | Files detail → overflow | R1 (when lifecycle allows) |
| Restore | File revision | Direct | Files revision panel → Restore | R1 |
| Connect | Platform | Modal | Settings `?tab=connectors` → connect flow | R2 (not on the four main tabs) |

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
- **Phase 2 — Files hardening** — **Implemented 2026-04-24**. `<EditInChatButton>` shared component landed at `web/components/shared/EditInChatButton.tsx` (R5 single label). `<SubstrateEditor>` landed at `web/components/workspace/SubstrateEditor.tsx` with `isSubstrateEditable()` predicate covering `/workspace/context/_shared/{IDENTITY,BRAND,CONVENTIONS,MANDATE}.md`. `ManageContextModal.tsx` deleted. `ContentViewer.tsx` refactored — substrate-editable files render inline editor, non-substrate files keep chat-draft affordance. Backend `editable_prefixes` gained `MANDATE.md`. Labels normalized across `WorkDetail.tsx` and `PrinciplesPane.tsx` to R5 ("Edit in chat"). TypeScript pass.
  - **Follow-up (not blocking Phase 3):** `web/components/settings/MemorySection.tsx` retains a parallel IDENTITY/BRAND edit path on `/settings`. It's a second mouth for the same substrate — Files is now canonical. Route to retire in a later sweep so the signed-in UI has one and only one edit surface for `_shared/` rules.
- **Phase 3 — Agents hardening** — Pending. Retires `PrinciplesPane` inline chat path (R3); principles.md becomes substrate-editable on Files (add `/workspace/review/principles.md` to `editable_prefixes` and extend `SHARED_EDITABLE_PATHS`). Reviewer detail + Systemic/Domain split harden.
- **Phase 4 — Work hardening** — Pending. Cockpit-zone treatment on `/work` list mode, IntelligenceCard silent-degrade fix (ADR-198 I2), 4 kind-middles reviewed against contract.
- **Phase 5 — Chat hardening** — Pending. Empty-state, suggestion chips, artifact cards, Reviewer verdict thread reviewed against contract.

---

## Related docs

- [ADR-215](../adr/ADR-215-surface-contracts-and-crud-principles.md) — governs this doc
- [ADR-198](../adr/ADR-198-surface-archetypes.md) — archetype vocabulary (Document · Dashboard · Queue · Briefing · Stream)
- [ADR-214](../adr/ADR-214-agents-page-consolidation.md) — four-tab nav + Reviewer-inside-Agents
- [ADR-167 v2](../adr/ADR-167-list-detail-surfaces.md) — list/detail pattern per tab
- [ADR-209](../adr/ADR-209-authored-substrate.md) — revision chain, `authored_by`, substrate attribution
- [ADR-206](../adr/ADR-206-operation-first-scaffolding.md) — operator-facing three-layer view (Intent · Operation · Deliverables)
- [ADR-168](../architecture/primitives-matrix.md) — canonical primitive matrix (not a design doc, but the authority for what verbs exist)
- [FOUNDATIONS v6.1](../architecture/FOUNDATIONS.md) — Axiom 6 (Channel), Derived Principle 12 (Channel legibility gates autonomy)
- [INLINE-PLUS-MENU.md](./INLINE-PLUS-MENU.md) — existing plus-menu verb taxonomy; under ADR-215 R4 it is strictly a modal launcher
