# ADR-215: Surface Contracts and CRUD Principles

**Status:** Phase 1 + Phase 2 Implemented — Phases 3–5 Proposed
**Date:** 2026-04-24
**Dimensional classification:** **Channel** (primary, Axiom 6) + **Purpose** (Axiom 3) — establishes per-surface contracts and the CRUD shape matrix that governs all affordances

## Context

ADR-214 (2026-04-23) collapsed cockpit nav to four tabs: **Chat | Work | Agents | Files**. That decision settled the *destinations*. It did not settle, per-tab:

1. **What each tab reads, renders, and refuses to do** (the surface contract). Design has accumulated ad-hoc — `/work` gained a Briefing strip via ADR-205 F2, `/agents` absorbed Reviewer via ADR-214, `/context` (now Files) sprouted a `ManageContextModal`, `/chat` grew suggestion chips and artifact cards. Each addition was individually defensible; collectively they leave the four tabs without a written contract. Recent thrash on `/work` layout (cockpit-stack vs. tab-ify) traces to this gap: without a contract for Files and Agents, the Work composition keeps re-opening.

2. **How mutation is expressed** (CRUD shape). Current state has four distinct shapes with no rule for which to use when:
   - **Direct buttons** on detail pages (`Pause`, `Archive`, `Approve proposal`) — `WorkDetail.tsx`
   - **Modals** (`CreateTaskModal`, `ManageContextModal`) — `/work`, `/context`
   - **Chat redirects** with seeded prompts — `WorkDetail.tsx:123` "Edit via chat", `PrinciplesPane.tsx:55` "Edit via YARNNN", `ContentViewer.tsx:128/253` "Edit via chat"
   - **Substrate-native editing** (filesystem files edited through the file view)

   The drift is visible in the labels alone: three phrasings for the same affordance ("Edit via chat" / "Edit via YARNNN" / "Edit via yarnnn"). Behind the labels the drift is deeper: `ManageContextModal` edits `/workspace/context/_shared/IDENTITY.md` — a file — through a modal, bypassing the revision chain (ADR-209) and the substrate-native edit path. `PrinciplesPane` routes edits through chat but edits `principles.md`, also a file, also substrate. Same kind of thing, three different UIs, and one of them (the modal) silently skips Authored Substrate attribution.

3. **What the `+` menu does, per tab.** Currently inconsistent — some `+` menus launch modals, others seed chat prompts.

Prior design docs try to answer these questions and have gone stale:
- `SURFACE-ARCHITECTURE.md` v15 (2026-04-20) describes five destinations (Overview | Team | Work | Context | Review) — superseded by ADR-214 four-tab nav but the doc still stands as v15 "Canonical."
- `SURFACE-ACTION-MAPPING.md` (2026-03-10, updated 2026-04-15) frames mutation as a two-surface dichotomy (chat/drawer) with "TP" and `agent_instructions`-column vocabulary, both retired.
- `SURFACE-DISPLAY-MAP.md` (2026-04-15) is a pre-ADR-214 code-snapshot of `/work` and `/context` that still references a three-surface user journey.
- `SURFACE-PRIMITIVES-MAP.md` (2026-04-04) duplicates `docs/architecture/primitives-matrix.md` (the ADR-168 canonical doc).

The user-facing effect: four tabs without written contracts, CRUD expressed four different ways with no rule, and four overlapping-but-divergent design docs attempting to describe the same thing. Every `/work` design iteration has been doing implicit Files and Agents design alongside it because the contracts for those tabs aren't written down.

## Decision

**Write per-tab surface contracts. Codify a four-shape CRUD matrix. Unify the design substrate into a single canonical doc (`SURFACE-CONTRACTS.md`) governed by this ADR.**

### Decisions locked in

1. **Four surface contracts, one per tab** (Files · Agents · Work · Chat). Each contract specifies: ADR-198 archetype(s), substrate read, list-mode layout, detail-mode layout, `+` menu contents, outbound deep-links, and what the surface explicitly refuses to do.

2. **The CRUD Matrix: four operation shapes, one rule per verb-object pair.** Every mutation in the cockpit picks exactly one shape. No verb-object pair uses two shapes.

   | Shape | When | Surface | Example |
   |---|---|---|---|
   | **Direct** | High-precision, well-specified, one-step, reversible | In-place button on the object's own detail page | Pause task · Archive file · Approve proposal |
   | **Modal** | High-precision, multi-field, **creation flow**, operator arrives with a blueprint | Modal launched from `+` menu or page header | CreateTaskModal · UploadFileModal |
   | **Chat** | Judgment-shaped, ambiguous, needs YARNNN's context | Redirect to `/chat` with seeded prompt | Refine a task's deliverable · Rewrite a mandate · Author an agent |
   | **Substrate** | Operator-authored content that IS a file | Edit the file on Files tab; revision chain records attribution | IDENTITY.md · BRAND.md · principles.md · CONVENTIONS.md |

3. **The five CRUD rules.** These are the discipline that keeps the four shapes from blurring back together.

   - **R1 — One verb, one shape per object.** "Edit a task" is always Chat. "Edit a file" is always Substrate. "Approve a proposal" is always Direct. No mixing across the cockpit.
   - **R2 — Create is always Modal. Update/Delete is Direct or Chat, never Modal.** Modals exist for the moment of creation where the operator arrives with a blueprint (title + type + schedule). After creation, mutation is single-click Direct or judgment-shaped Chat. No "edit modal."
   - **R3 — Substrate operations bypass Chat.** If the thing being edited IS a file, the edit surface is Files, with the revision panel (ADR-209 P4) showing `authored_by=operator`. No "Edit in chat" button on substrate files — Chat would invoke `UpdateContext` anyway, and the operator editing directly produces the same substrate write with clearer provenance.
   - **R4 — The `+` menu is a modal launcher. Never a chat seeder.** Each tab's `+` menu lists only Modal creation flows (creation is Modal per R2). Chat-shaped mutations live on the object's own detail page as "Edit in chat" (the R5 label).
   - **R5 — One label: "Edit in chat".** All existing phrasings ("Edit via chat" / "Edit via YARNNN" / "Edit via yarnnn") converge on "Edit in chat" (lowercase, no YARNNN branding — chat is the tab; YARNNN is the agent; the operator is editing *in a surface*, not *through an agent*). Single `<EditInChatButton prompt={...} />` component across the cockpit.

4. **`ManageContextModal` is retired.** It edits `/workspace/context/_shared/IDENTITY.md`, `BRAND.md`, `CONVENTIONS.md` — three substrate files — through a modal, which violates R3 (substrate) and R2 (modals are for create only). Those files become substrate-editable on Files. The `+` menu on Files no longer launches this modal. Implementation follows in a subsequent commit; this ADR locks the direction.

5. **`PrinciplesPane.tsx` label updates.** `"Edit via YARNNN"` (line 55) and `"Click Edit via YARNNN to set them up."` (line 72) change to `"Edit in chat"` per R5. But R3 eventually retires this button entirely — `principles.md` is substrate; its edit path will move to Files in the same sweep as decision 4. Until that move, the label fixes R5 drift without inventing a new CRUD shape.

6. **`SURFACE-CONTRACTS.md` is the single canonical design doc for cockpit surfaces and CRUD.** It absorbs the live content of `SURFACE-ARCHITECTURE.md`, `SURFACE-ACTION-MAPPING.md`, `SURFACE-DISPLAY-MAP.md`, and `SURFACE-PRIMITIVES-MAP.md`. Those four docs are archived with redirect pointers.

7. **The tab-hardening sequence is Files → Agents → Work → Chat.** Each tab's design depends on the substrate and deep-link targets its predecessors expose. Files has zero inbound dependencies; Chat has the most. Working in this order prevents the redesign ping-pong of the last two weeks. SURFACE-CONTRACTS spells this out per tab; this ADR records the commitment.

### Supersedes

- `docs/design/SURFACE-ARCHITECTURE.md` v15 (2026-04-20) — five-destination cockpit framing (retired by ADR-214 nav collapse; content replaced by SURFACE-CONTRACTS)
- `docs/design/SURFACE-ACTION-MAPPING.md` (2026-03-10) — two-surface chat/drawer dichotomy with retired TP/agent_instructions vocabulary
- `docs/design/SURFACE-DISPLAY-MAP.md` (2026-04-15) — pre-ADR-214 three-surface code snapshot
- `docs/design/SURFACE-PRIMITIVES-MAP.md` (2026-04-04) — duplicate of `docs/architecture/primitives-matrix.md`

### Amends

- **ADR-167 v2** (list/detail surfaces): surface contracts per tab formalize the list/detail split that ADR-167 established structurally.
- **ADR-198** (surface archetypes): the per-tab contracts in SURFACE-CONTRACTS assign archetypes from ADR-198's vocabulary to each tab's panes. ADR-198 remains the archetype taxonomy; ADR-215 is where those archetypes get bound to concrete destinations.
- **ADR-206** (operation-first scaffolding): ADR-206 introduced the CRUD split (create via modal, update via chat, approve direct) as a decision. ADR-215 is where it gets codified as a matrix with explicit rules, and where the R3 substrate rule retires `ManageContextModal` (which ADR-206 introduced in good faith and R3 now retires).
- **ADR-209** (authored substrate): R3 ("substrate operations bypass chat") is a direct application of ADR-209 — the revision chain is the canonical author trail; modal writes that skip it are drift.

### Preserves

- **ADR-198 archetypes** — the five-archetype vocabulary (Document, Dashboard, Queue, Briefing, Stream) remains unchanged; contracts consume it.
- **ADR-214 four-tab nav** — Chat | Work | Agents | Files stands.
- **ADR-168 primitive matrix** — `docs/architecture/primitives-matrix.md` remains the canonical primitive doc; SURFACE-CONTRACTS references it rather than duplicating.
- **ADR-186 prompt profiles** — surface metadata continues to flow into YARNNN's prompt via `SURFACE_PROFILES` resolver.

## Non-goals

- **No code changes in this ADR.** The docs land first so Files → Agents → Work → Chat implementation can consume a stable contract. Follow-on commits retire `ManageContextModal`, update `PrinciplesPane` labels, and introduce `<EditInChatButton>` as a shared component.
- **No new primitives.** The CRUD matrix expresses itself through existing primitives (ADR-168) — modals write through primitives like operator actions do; substrate edits write through `UpdateContext` or direct file writes with `authored_by=operator`.
- **No new routes.** Four tabs stay four tabs. SURFACE-CONTRACTS maps detail-mode URLs that already exist (`?task=`, `?agent=`, `?path=`).

## Implementation

Phased to match the tab-hardening sequence:

- **Phase 1 (Implemented 2026-04-24, commit `936eacc`).** ADR-215 + SURFACE-CONTRACTS.md + archive supersedes + CHANGELOG entry. Docs-only.
- **Phase 2 (Files hardening) — Implemented 2026-04-24.** `<EditInChatButton>` shared component at `web/components/shared/EditInChatButton.tsx` (R5 single label, two variants). `<SubstrateEditor>` at `web/components/workspace/SubstrateEditor.tsx` with `isSubstrateEditable()` predicate covering `/workspace/context/_shared/{IDENTITY,BRAND,CONVENTIONS,MANDATE}.md`. `ManageContextModal.tsx` deleted. `ContentViewer.tsx` refactored — substrate files render inline editor; non-substrate files keep chat-draft affordance. Backend `api/routes/workspace.py` editable-prefixes gained `MANDATE.md`. `PrinciplesPane.tsx` + `WorkDetail.tsx` + `PageHeader.tsx` doc comment normalized to R5. TypeScript pass. Known follow-up: `web/components/settings/MemorySection.tsx` retains a parallel IDENTITY/BRAND edit path on `/settings` — to retire in a future sweep (not blocking Phase 3).
- **Phase 3 (Agents hardening).** Systemic (YARNNN + Reviewer) and Domain detail shapes finalized. `PrinciplesPane` retired in favor of substrate-native editing on Files (per R3) — the decisions pane stays as a Stream embed.
- **Phase 4 (Work hardening).** Cockpit-zone treatment on `/work` list mode (defer the tab-ify-vs-stack call to this phase with Files + Agents contracts already stable). IntelligenceCard silent-degrade fix (ADR-198 Briefing invariant I2). Four kind-aware detail middles (ADR-167 v2) reviewed against the contract.
- **Phase 5 (Chat hardening).** Empty-state, suggestion chips, artifact card shape, Reviewer verdict thread (ADR-212) reviewed against the contract. Chat converges to the shapes the other three tabs now stably expose.

Each phase lands with code + contract section update + CHANGELOG entry. No phase ships without the written-down contract change — the discipline that prevents this ADR's motivation from recurring.
