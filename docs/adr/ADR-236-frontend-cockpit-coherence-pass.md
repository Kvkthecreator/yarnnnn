# ADR-236: Frontend Cockpit Coherence Pass — Umbrella Scoping

> **Status**: **Proposed** (2026-04-29). Umbrella ADR coordinating a 10-item frontend coherence pass. No implementation lands in this ADR — it scopes, tiers, and sequences the work, and codifies the doc-radius rules every sub-ADR + hygiene commit in this pass must follow.
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Channel** (Axiom 6) primary — every item touches a cockpit surface (Chat, Work, Agents, Files, Settings) or the conventions that govern them. Secondary **Identity** (Axiom 2) for the chat role-based design system, **Mechanism** (Axiom 5) for the autonomy-mode FE consumption layer.
> **Coordinates** (does not amend): ADR-163 (Surface Restructure), ADR-198 (Surface Archetypes), ADR-201 (Review surface — reversed by ADR-214), ADR-205 (Workspace Primitive Collapse), ADR-206 (Operation-First Scaffolding), ADR-214 (Agents Page Consolidation), ADR-215 (Surface Contracts), ADR-217 (Workspace Autonomy Substrate), ADR-225 (Compositor Layer), ADR-226 (Reference-Workspace Activation), ADR-228 (Cockpit as Delegation Posture), ADR-231 (Task Abstraction Sunset).
> **Anticipates** (sub-ADRs spawned by this umbrella): ADR-237 (Chat Role-Based Design System), ADR-238 (Autonomy-Mode FE Consumption), ADR-239 (Trader Cockpit Re-Write), ADR-240 (Onboarding-as-Activation). Numbers reserved at umbrella time; final assignments confirmed when each sub-ADR drafts.
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-141 (execution layers), ADR-156 (single intelligence layer), ADR-176 (universal specialist roster), ADR-194 v2 (Reviewer substrate), ADR-209 (Authored Substrate), ADR-216 (orchestration vs judgment), ADR-231 (recurrence-walker substrate, natural-home paths).

---

## Context

The frontend has accumulated coordinated debt across roughly the last six months of ADRs (163, 201, 205, 214, 217, 225, 228, 231). Each ADR was correct in isolation; together they shipped a cockpit whose surfaces were touched piecemeal without a coordinating frame. Concrete symptoms surfaced in a 2026-04-29 audit:

- **Six redirect stubs** (`/orchestrator`, `/team`, `/overview`, `/workfloor`, `/memory`, `/system`) accumulated across four ADRs with no shared rule for when a redirect is the right answer vs. a stale URL deletion. Stubs are correct as bookmark-safety, but the policy isn't documented.
- **Chat role-based components** (`SystemCard`, `ReviewerCard`, `ProposalCard`, `NotificationCard`, `InlineActionCard`, `InlineToolCall`, `ToolResultCard`) exist but have no shared formal grammar — each was added per ADR (193, 194, 219) with its own padding / icon / metadata strip / action affordances. The vocabulary expanded organically; the design system did not.
- **`ChatFilterBar`** (ADR-219 Commit 5) is wired to URL params and the `NarrativeFilter` consumer in `ChatPanel`, but operator-reported as "doesn't work" — the architecture works in principle; the consumption path needs end-to-end verification.
- **"Make this recurring"** (`ChatSurface.tsx::handleMakeRecurring`) was authored when task creation was the ceremony. Post-ADR-231 D1 (invocation-first default), the inline ask already fired and produced output; the modal is over-built for "graduate to recurrence."
- **ADR-217 Workspace Autonomy Substrate** specifies `_shared/AUTONOMY.md` but no FE consumption path exists. No code reads autonomy state to gate the chat composer, modal confirmations, or grey-outs.
- **Trader cockpit** (`MoneyTruthFace`, `TrackingFace`, `PerformanceFace`) per ADR-228 Phase 2 is implemented in skeleton form; Phases 3–5 (platform-live binding, bundled metrics, doc sync) are deferred. Substrate transitioned from YAML to natural-home `.md` per ADR-231; the trader-specific kernel surface was authored against the older substrate model.
- **Files page** (`/context`) returns `500` from `/api/workspace/tree` ("Failed to load explorer"). Two endpoints (`/api/workspace/tree` legacy, `/api/workspace/nav` ADR-154 structured) coexist; one of them must be canonical.
- **Onboarding** scaffolds zero operational tasks (ADR-206) and forks a program bundle when activated (ADR-226). But platform connection — required for capability-gated mandates per ADR-207 — is not elevated to first-class in the onboarding surface.
- **Agents page** is the unified TP command center per ADR-214; current layout is a two-split with Decisions panel; tab-based layout per file (IDENTITY.md / memory/* / feedback.md) is more discoverable.
- **`/work` cockpit ↔ chat snapshot** share zero components today. The four cockpit faces flow through `CockpitRenderer` only; `SnapshotModal` (chat-side briefing) has its own three-tab implementation. ADR-198 Briefing archetype admits convergence; no ADR has authorized it.

The pattern is clear: items addressed piecemeal across 5+ ADRs, no coordinating document, no shared doc-radius rule. The umbrella ADR is the response.

---

## Decision

**This ADR is a coordinator, not an implementor.** It does three things:

1. **Inventories the 10 items** with verified scope and existing-ADR linkage.
2. **Tiers the items** (architectural / hygiene / mid-scope) with a stated rationale for each tier.
3. **Codifies the doc-radius rules** every sub-ADR + hygiene commit in this pass must follow.

The umbrella ADR does NOT specify implementation details for any item. Tier 1 items get their own sub-ADRs. Tier 2 items land as single commits referencing this ADR. Tier 3 items get scoping memos under `docs/analysis/` first; sub-ADRs follow if the memo surfaces architectural questions.

---

## The 10-Item Inventory

Each item lists: **what it is**, **verified state in code**, **existing ADR linkage**, **scope estimate**.

### Item 1 — Chat role-based design system

- **What**: Establish a shared formal grammar for chat-message components by role (system, user, YARNNN/orchestration, agent, reviewer, external). Each role gets a defined surface contract: padding, icon position, metadata strip shape, action affordances.
- **Verified state**: 7 components exist in `web/components/tp/` (`SystemCard`, `ReviewerCard`, `ProposalCard`, `NotificationCard`, `InlineActionCard`, `InlineToolCall`, `ToolResultCard`). Each defines its own visual rules. Dispatch lives in `TPMessages.tsx`.
- **Existing ADRs**: ADR-193 (proposal cards), ADR-194 v2 (Reviewer substrate), ADR-219 (narrative weights), ADR-216 (orchestration vs judgment vocabulary).
- **Scope**: medium. Frames Items 8 + 10 — both depend on a settled role grammar.

### Item 2 — Autonomy-mode FE consumption

- **What**: FE layer that reads `_shared/AUTONOMY.md` and gates UI affordances accordingly (composer disabling, double-check modals, in-component edits permitted in DIRECT mode).
- **Verified state**: `_shared/AUTONOMY.md` exists as substrate per ADR-217. No FE code reads it. `MandateFace.tsx` reads MANDATE.md but not AUTONOMY.md.
- **Existing ADRs**: ADR-217 (Workspace Autonomy Substrate — defines the substrate, defers FE consumption).
- **Scope**: small-to-medium. Self-contained; does not block other items.

### Item 3 — Trader cockpit re-write

- **What**: Audit + re-write of the trader-workspace-specific cockpit. Convergence opportunities: `/work` cockpit faces ↔ chat snapshot modal, Tracking unification (Reviewer Decisions ↔ TrackingFace), Portfolio time-series component (today: substrate fallback only).
- **Verified state**: ADR-228 Phase 2 implemented (4 face components at `web/components/library/faces/`). Phases 3–5 deferred (platform-live MoneyTruth binding, bundled metrics, doc sync). Substrate moved YAML→md per ADR-231; trader kernel surface authored against earlier model.
- **Existing ADRs**: ADR-225 (Compositor Layer), ADR-226 (Reference-Workspace Activation), ADR-228 (Cockpit as Delegation Posture), ADR-231 (Task Abstraction Sunset).
- **Scope**: large. Largest item in the pass. Requires scoping memo before sub-ADR.

### Item 4 — Onboarding-as-activation

- **What**: Promote platform connection from optional refinement to first-class onboarding step. Reframe onboarding around ADR-226 program activation rather than form-shaped data capture.
- **Verified state**: `workspace_init.py` Phase 5 forks bundle on `program_slug`. Activation overlay prompt exists at `prompts/chat/activation.py`. No FE flow surfaces program selection at signup. Platform connection lives in `/integrations/[provider]/` and `/settings`.
- **Existing ADRs**: ADR-205 (Workspace Primitive Collapse), ADR-206 (Operation-First Scaffolding), ADR-207 (Primary-Action-Centric Workflow — capability gating), ADR-226 (Reference-Workspace Activation).
- **Scope**: medium. Touches ADR-226 Phase 2 (deferred FE work).

### Item 5 — Redirect-stub cleanup

- **What**: Apply a single coordinated rule to the six existing redirect stubs. Verify each target is current; document the redirect policy in `web/lib/routes.ts` so future ADRs follow it.
- **Verified state**: Six stubs verified clean: `/orchestrator → /chat`, `/team → /agents`, `/overview → /work`, `/workfloor → /chat`, `/memory → /context?path=...IDENTITY.md`, `/system → /settings?tab=system`. All redirect to current canonical routes. **No code-level slop** — the "slop" is the absence of a documented policy.
- **Existing ADRs**: ADR-163, ADR-201, ADR-205 F1, ADR-214.
- **Scope**: small. Hygiene only — comments + policy doc.

### Item 6 — Files page 500 root cause + nav/tree duality

- **What**: Resolve the production `500` on `/api/workspace/tree`. Decide canonical between `/api/workspace/tree` (legacy) and `/api/workspace/nav` (ADR-154 structured).
- **Verified state**: `web/app/(authenticated)/context/page.tsx:293` catches the error. Backend route at `api/routes/workspace.py:392` labeled "legacy, used by file viewer." `/api/workspace/nav` referenced at `api/routes/workspace.py:4`.
- **Existing ADRs**: ADR-154 (structured nav), ADR-180 (Files canonical label).
- **Scope**: small-to-medium. Depends on root-cause analysis before scoping the consolidation.

### Item 7 — Settings ↔ /integrations consolidation — **Deferred** (2026-04-29)

- **What**: Collapse the duplication between `/settings` (ConnectedIntegrationsSection) and `/integrations/[provider]/` (OAuth callback route). Settings becomes the single canonical surface for platform connection management.
- **Verified state**: `/integrations/[provider]/page.tsx` is the OAuth callback handler — **not** a duplicate of settings. **Original audit overstated this**: there is no settings/integrations duplication at the route level; the consolidation question is narrower — should `ConnectedIntegrationsSection` be embeddable on Chat (snapshot) and elsewhere as a reusable read-only summary?
- **Existing ADRs**: ADR-153 (Platform Sync sunset), ADR-205 (Workspace Primitive Collapse).
- **Scope**: small. Reframed: extraction of a reusable read-only ConnectedIntegrationsSummary, not a full consolidation.
- **Deferral rationale (2026-04-29)**: ConnectedIntegrationsSection currently has exactly one consumer (`/settings`). Extracting a read-only summary now would ship a component looking for a consumer — anti-Singular-Implementation per Rule 7. Item 1 (chat role-based design system) and Item 4 (onboarding-as-activation) are likely to surface the first real consumer of an integrations summary. Item 7 is **deferred** and re-picked up alongside whichever Tier 1 sub-ADR first needs it. The deferral records a coordination point: when Item 1 / 3 / 4's sub-ADR drafts and identifies a need for an integrations summary, the extraction lands as part of that sub-ADR's commit, not as a standalone refactor.

### Item 8 — ChatFilterBar verification + "Make this recurring" rework

- **What**: End-to-end verify ChatFilterBar filters messages as advertised. Re-evaluate the "Make this recurring" graduation flow under ADR-231 D1 invocation-first default.
- **Verified state**: ChatFilterBar parses URL params correctly; `NarrativeFilter` is passed to `ChatPanel`; the filter render path was not verified in audit. `handleMakeRecurring` opens RecurrenceSetupModal pre-filled with operator's original message.
- **Existing ADRs**: ADR-219 Commit 5 (filter chips), ADR-231 D1 (invocation-first default).
- **Scope**: small (verification) + medium (recurring rework). Depends on Item 1's role grammar.

### Item 9 — Agents page tab refactor

- **What**: Replace the current two-split layout with file-per-tab navigation (IDENTITY.md / memory/* / feedback.md tabs).
- **Verified state**: `AgentContentView.tsx` is 736 LOC with multiple shell registries (`AGENT_SHELL_REGISTRY`, `ROLE_GUIDANCE_REGISTRY`, `AGENT_EMPTY_STATE_REGISTRY`). Reviewer Decisions panel renders inside this view via `web/components/agents/reviewer/DecisionsStreamPane.tsx`.
- **Existing ADRs**: ADR-214 (Agents Page Consolidation).
- **Scope**: medium. Depends on Item 1's role grammar (agent tabs follow chat-role conventions).

### Item 10 — Cockpit ↔ snapshot convergence

- **What**: Converge `/work` cockpit faces and chat-side `SnapshotModal` onto shared components. ADR-198 Briefing archetype already supports the framing.
- **Verified state**: `SnapshotModal` has three independent tabs (Mandate / Review / Recent). `CockpitRenderer` imports `MandateFace`, `MoneyTruthFace`, `PerformanceFace`, `TrackingFace` directly. Zero shared components today.
- **Existing ADRs**: ADR-198 (Surface Archetypes), ADR-225 (Compositor Layer), ADR-228 (Cockpit as Delegation Posture).
- **Scope**: medium. Depends on Items 1 + 3.

---

## Tier Classification

### Tier 1 — Architectural (sub-ADR required)

Items whose decision-shape is non-obvious and whose outcome constrains other items.

| Item | Anticipated sub-ADR | Reason |
|---|---|---|
| 1. Chat role-based design system | ADR-237 | Frames role grammar; constrains 8, 9, 10. |
| 2. Autonomy-mode FE consumption | ADR-238 | New FE consumption layer; substrate exists, contract doesn't. |
| 3. Trader cockpit re-write | ADR-239 (after memo) | Largest scope; multiple convergence questions. |
| 4. Onboarding-as-activation | ADR-240 | Touches ADR-226 deferred Phase 2; capability-gating reshapes flow. |

### Tier 2 — Hygiene (single commit, no new ADR)

Items whose decision is already implicit in existing ADRs; the commit references this umbrella.

| Item | Why no new ADR |
|---|---|
| 5. Redirect-stub cleanup | All six stubs already correct. Pass adds policy doc only. |
| 6. Files page 500 + nav/tree | Root cause first; consolidation decided by what root cause reveals. If new architectural decision surfaces, escalates to Tier 1. |
| 7. Settings ↔ /integrations | Reframed in inventory: extraction pattern, not a consolidation. Standard refactor. |

### Tier 3 — Mid-scope (scoping memo first)

Items where the question shape is unsettled and a memo precedes any sub-ADR.

| Item | Why memo first |
|---|---|
| 8. ChatFilterBar + recurring rework | Verification first; rework scope depends on what verification reveals. |
| 9. Agents page tab refactor | Tab grammar depends on Item 1's outcome; memo confirms compatibility. |
| 10. Cockpit ↔ snapshot convergence | Convergence shape depends on Items 1 + 3; memo confirms timing. |

---

## Doc Radius Rules

Every sub-ADR + hygiene commit in this pass MUST follow these rules. They are codified here so the rules outlive this pass.

### Rule 1 — Active canon rewrites in place

The following docs describe **current state**. Sub-ADRs in this pass rewrite them in place. History lives in git.

- `CLAUDE.md` (current-canon section + File Locations table)
- `docs/design/SURFACE-CONTRACTS.md`
- `docs/architecture/primitives-matrix.md` (only if a primitive's mode availability changes)
- `docs/architecture/SERVICE-MODEL.md` (only if a Frame is materially altered)
- `docs/features/{chat,work,agents,files,settings}.md` (where they exist)

### Rule 2 — Historical ADR summaries preserved verbatim

Per CLAUDE.md project discipline, historical ADR summary blocks are not rewritten. Sub-ADRs in this pass add `Amends: ADR-XXX` headers; they do NOT edit the historical body of the amended ADR.

### Rule 3 — Test gates required for Tier 1, optional for Tier 2/3

- **Tier 1 sub-ADRs** ship with `api/test_adrXXX_*.py` or `web/__tests__/adrXXX_*.test.ts` test gate. Combined gate must pass.
- **Tier 2 hygiene commits** must not regress existing gates but do not require their own.
- **Tier 3 memos** do not have test gates; the sub-ADR (if spawned) does.

### Rule 4 — CHANGELOG entries

`api/prompts/CHANGELOG.md` gets one entry per sub-ADR (Tier 1) when prompts change. Hygiene commits that don't touch prompts don't add entries.

### Rule 5 — CLAUDE.md ADR-summary block updates batch at end

CLAUDE.md's ADR summary list updates **once at the end of the pass**, not per sub-ADR. Otherwise the file churns 4–5 times. Each sub-ADR amends only the File Locations table + current-canon section if needed; the summary block is written in the closing commit.

### Rule 6 — Dimensional classification declared per sub-ADR

Every sub-ADR in this pass declares its primary + secondary dimensional classification per FOUNDATIONS v6.0 Axioms 1–8.

### Rule 7 — Singular Implementation honored per sub-ADR

Each sub-ADR replaces the legacy code it touches in the same commit. No parallel implementations, no transitional shims. If a Tier 1 sub-ADR's surface is too large for a single commit, it splits into named phases — never into "old way still works."

### Rule 8 — Drafted-pair sequencing (just-in-time ADR drafting)

Sub-ADRs in this pass are drafted **just-in-time, not all up-front**. The pattern:

1. **Draft sub-ADR N** as `Proposed`.
2. **Implement sub-ADR N** in the same or next session — the implementation stress-tests the design.
3. **Land sub-ADR N** with status flipped to `Implemented`.
4. **Then draft sub-ADR N+1** — the new ADR cites real code from sub-ADR N's implementation, not predicted code, AND explicitly addresses how it composes with N's surface.

This rule resolves a tension between two legitimate options. **Option A** (draft all sub-ADRs first, then execute) front-loads design but produces stale ADRs by the time later items implement. **Option B** (draft + implement strictly one at a time) ships fast but risks Item N painting Item N+1 into a corner. **Rule 8 (Option C)** keeps the just-in-time virtue of B while requiring each new sub-ADR to explicitly cite predecessors — preserving cross-cutting awareness without paying A's up-front cost.

**Why this works for YARNNN:** the 230-series ADRs in this repo have shipped at sustained quality precisely because they were drafted close to their implementation (each cites real code it just touched, not speculation). Rule 8 codifies the existing successful pattern as policy for this pass and any future multi-sub-ADR pass that follows.

**Concrete shape per sub-ADR draft:**
- Header section explicitly lists `Builds on: ADR-XXX (Implemented YYYY-MM-DD)` for each prerequisite.
- The `Decision` section names how this sub-ADR composes with predecessors — e.g., ADR-237's role grammar accepting ADR-238's autonomy-mode as a row property.
- If a predecessor's implementation surfaced realities that change this sub-ADR's scope, the sub-ADR records it in the `Context` section rather than retroactively editing predecessors.

**Failure mode this rule prevents:** a future session drafting all four sub-ADRs (237, 238, 239, 240) in one go, then implementing them in sequence three weeks later only to find that ADR-237's design assumptions don't survive ADR-238's implementation. Rule 8 forbids that pattern.

---

## Sequencing

The 10 items have real dependencies. Sequenced execution prevents merge thrash and honors Singular Implementation. **Rule 8 governs the inner loop**: each Tier 1 sub-ADR drafts → implements → lands before the next one drafts.

The pass moves in **named rounds**. Rounds are not parallel; later rounds may interleave Tier 3 items between Tier 1 sub-ADRs as dependencies allow.

### Round 0 — Foundations (Implemented 2026-04-29)

| Step | Output | Status |
|---|---|---|
| 0.1 | Umbrella ADR (this document) | Implemented (commit `74b6f2f`) |
| 0.2 | Item 5 — Redirect-stub policy + docblock alignment | Implemented (commit `9aacd09`) |
| 0.3 | Item 6 — `/api/workspace/nav` 500 root cause fix | Implemented (commit `ca53c53`) |
| 0.4 | Item 7 — Settings extraction deferral recorded | Deferred (commit `9969aa4`) |

Tier 2 hygiene block closed. Validates the doc-radius rules end-to-end.

### Round 1 — Independent Tier 1 sub-ADR

| Step | Output | Blocker | Sequencing |
|---|---|---|---|
| 1.1 | Draft ADR-238 (Item 2 — Autonomy-mode FE consumption) as `Proposed` | None | Independent of ADR-235 + ADR-237 + ADR-239 + ADR-240. |
| 1.2 | Implement ADR-238 | 1.1 | Same session if scope fits; else next. |
| 1.3 | Flip ADR-238 to `Implemented`, land | 1.2 | — |

### Round 2 — Chat design system (gated on ADR-235)

| Step | Output | Blocker |
|---|---|---|
| 2.1 | Draft ADR-237 (Item 1 — Chat role-based design system) as `Proposed` — explicitly cites ADR-235's primitive surface + ADR-238's autonomy-mode gates | ADR-235 Implemented + Round 1 complete |
| 2.2 | Implement ADR-237 | 2.1 |
| 2.3 | Flip ADR-237 to `Implemented`, land | 2.2 |

### Round 3 — Trader cockpit (memo + sub-ADR)

| Step | Output | Blocker |
|---|---|---|
| 3.1 | Item 3 scoping memo at `docs/analysis/trader-cockpit-rewrite-{YYYY-MM-DD}.md` | Round 2 — memo cites ADR-237 role grammar |
| 3.2 | Draft ADR-239 (Item 3 — Trader cockpit re-write) as `Proposed` | 3.1 |
| 3.3 | Implement ADR-239 (likely phased per Rule 7) | 3.2 |
| 3.4 | Flip ADR-239 to `Implemented` (or final phase Implemented), land | 3.3 |

### Round 4 — Onboarding-as-activation

| Step | Output | Blocker |
|---|---|---|
| 4.1 | Draft ADR-240 (Item 4 — Onboarding-as-activation) as `Proposed` — cites ADR-237 (chat role grammar for first-conversation surface) + ADR-238 (autonomy gates on first run) | Round 2 + Round 3 |
| 4.2 | Implement ADR-240 | 4.1 |
| 4.3 | Flip ADR-240 to `Implemented`, land | 4.2 |

### Round 5 — Tier 3 mop-up

| Step | Output | Blocker |
|---|---|---|
| 5.1 | Item 9 — Agents page tab refactor | ADR-237 |
| 5.2 | Item 8 — ChatFilterBar verification + recurring rework | ADR-237 |
| 5.3 | Item 10 — Cockpit ↔ snapshot convergence | ADR-237 + ADR-239 |

Tier 3 items get their own scoping memos at execution time if they surface architectural questions; otherwise they ship as commits referencing this umbrella ADR.

### Round 6 — Closing

| Step | Output |
|---|---|
| 6.1 | CLAUDE.md ADR-summary block updated once with all sub-ADR entries (Rule 5) |
| 6.2 | This umbrella ADR's status flips to `Implemented` |
| 6.3 | Final test gates green, no console.error in production explorer load |

Sessions execute one round-step at a time. If a step uncovers cross-round friction, the session pauses and updates this umbrella ADR's sequencing section before continuing.

---

## Scope Guards

What this pass does **NOT** do, declared explicitly so future-me doesn't drift:

1. **No backend work beyond Item 6's 500 root cause.** Backend is downstream of ADR-235 (in flight in another session). Mixing concerns risks merge collisions.
2. **No new compositor primitives.** ADR-225 + ADR-228 already define the compositor; this pass uses what exists. New compositor primitives = a separate ADR after this pass closes.
3. **No vocabulary-shaped renames** unless a sub-ADR explicitly motivates one. Vocabulary churn (Task→Recurrence per ADR-231, Specialist→Production Role per ADR-216) has been heavy; let it settle.
4. **No new database migrations.** This is a frontend pass.
5. **No platform-integration additions** (no new OAuth providers, no new platform bots).
6. **No new MCP tools.** ADR-169's three-tool surface is preserved.
7. **No documentation outside the doc-radius register** (defined per sub-ADR via Rule 1).

---

## Definition of Done

This umbrella ADR's status flips to **Implemented** when:

- [x] Round 0 — Tier 2 hygiene block closed (Items 5, 6 Implemented; Item 7 Deferred).
- [x] Round 1 — ADR-238 reaches **Implemented** (commit `c769e64`; test gate 6/6 passing).
- [x] **Round 0 + Round 1 validation checkpoint** authored at [docs/analysis/adr236-validation-checkpoint-2026-04-29.md](../analysis/adr236-validation-checkpoint-2026-04-29.md), walked, and closed. Code-side 25/25 + cross-ADR 50/50 + operator browser smoke confirmed. Results: [docs/analysis/adr236-validation-results-2026-04-29.md](../analysis/adr236-validation-results-2026-04-29.md). Round 0 + Round 1 definitively validated 2026-04-29.
- [x] Round 2 — ADR-237 reaches **Implemented** (test gate 7/7; cross-ADR 57/57; ADR-235 prerequisite met by commit `9156db9`).
- [x] Round 3 — ADR-239 reaches **Implemented** (test gate 6/6; cross-ADR 63/63). Memo found scope smaller than predicted: Q5 path audit clean, MessageRenderer composition not applicable to cockpit list views; net work is parser unification (Q2) which fixed a bug in `PerformanceFace`'s decision-format reading.
- [x] Round 4 — ADR-240 reaches **Implemented** (test gate 8/8; cross-ADR 71/71). FE consumption layer for ADR-226 Phase 1 backend: two-step OnboardingModal at `/auth/callback` (program pick → optional platform connect). YARNNN activation overlay extended with capability-gap awareness paragraph (D6). Modal mount gated on activation_state + active_program_slug substrate signals (idempotent across re-signin).
- [x] Round 5 step (ADR-241) — Reviewer surface collapses into Thinking Partner. Test gate 8/8; cross-ADR 79/79 across 9 gates. Operator-facing roster on `/agents` redirects directly to TP detail (tab-based: Identity / Principles / Tasks). Decisions stream relocates to `/work` Decisions tab. Backend judgment substrate (ADR-194 v2) preserved verbatim — ADR-194 status header amended with the surface-collapse note. Closes operator observation: "we only have one agent now... should just be the command center page dedicated to the new, unified Thinking Partner Agent."
- [x] Round 5 Cluster B (partial) — two FE-only items closed; two backend/architectural items deferred to follow-up sub-ADRs:
  - **TP-edit notification (Closed)**: head-revision authorship surfaced on the Files header. Reads existing `/api/workspace/revisions?limit=1` (ADR-209 Phase 4 endpoint) — no new backend. `formatHeadAuthor()` maps ADR-209 `authored_by` taxonomy ('operator' / 'yarnnn:*' / 'agent:*' / 'specialist:*' / 'reviewer:*' / 'system:*') to operator-facing labels ('You' / 'YARNNN' / 'Agent (slug)' / etc.). Falls back silently on read error. Touches `web/components/workspace/ContentViewer.tsx`.
  - **Autonomy chip clickability (Closed, Shape β-lite)**: ADR-237 R3 anticipated routing the autonomy chip click to a posture modal. ADR-236 Cluster B fulfills this as **navigation, not modal** — chip becomes a link to `/context?path=AUTONOMY.md` where the substrate file IS the posture explainer. Edits continue to flow through chat (ADR-235 D1.b WriteFile scope='workspace'). Touches `web/components/tp/ChatPanel.tsx`.
  - **MoneyTruth platform-live (Deferred → ADR-242)**: backend-touching work — new endpoint `/api/cockpit/money-truth/{workspace_id}` reading Alpaca live + fallback to substrate. Per ADR-236 scope guard 1 ("no backend work beyond Item 6 500 fix") and ADR-239 memo Q3, this is its own sub-ADR. Today's MoneyTruthFace renders substrate-fallback-only correctly; live binding is upgrade work, not a regression.
  - **Cockpit ↔ snapshot convergence (Item 10, Deferred → memo + sub-ADR)**: Item 10 was originally Tier 3 (memo recommended). Post-ADR-241, structural simplification: Decisions stream is now on `/work` only; SnapshotModal's "Review" tab and TP's Principles tab share the same `/workspace/review/principles.md` substrate. The convergence work (sharing components between SnapshotModal and CockpitRenderer) is its own sub-ADR. Substrate-truth holds; surface-truth alignment is a coordination pass.
- [x] Round 5 Cluster A — three operator-assessment items closed in one commit:
  - **Item 8.2 — Make Recurring rework**: graduation moves from user ask to assistant output (ADR-231 D1 invocation-first default — by the time operator considers scheduling, the ask already fired and produced output). Affordance now reads "Run this on a schedule" (operator language). Modal pre-fill replaced with chat-mediated graduation — clicking sends a chat message, YARNNN proposes recurrence shape conversationally and calls ManageRecurrence(create) per ADR-235 D1.c. Modal stays accessible via plus-menu for explicit creation. Touches `web/components/tp/MessageRow.tsx` + `web/components/chat-surface/ChatSurface.tsx`.
  - **Files page user-edit removal**: SubstrateEditor.tsx deleted entirely. Per the assessment ("not notion-like, streamline back to edit via Chat"), every file now routes to chat for edits via EditInChatButton. Empty-file state gains "Chat with YARNNN to author content" guidance. RevisionHistoryPanel revert affordance preserved (substrate recovery is not editing). PATCH /api/workspace/file route stays available — chat's WriteFile primitive uses it server-side.
  - **Item 7 closure verification — Settings Connectors**: audit confirmed `/settings?tab=connectors` already centralizes all five platforms (Slack, Notion, GitHub, Lemon Squeezy, Alpaca). Zero redirects to other connection surfaces. The assessment's "revamp" framing was about completeness; the surface is structurally complete. Item 7's deferral converts to verified-closed; no extraction needed because the centralized tab IS the canonical consumer.
- [ ] Round 3 — ADR-239 reaches **Implemented** (or final phase, per Rule 7) — preceded by scoping memo.
- [ ] Round 4 — ADR-240 reaches **Implemented**.
- [ ] Round 5 — Items 8, 9, 10 reach **Implemented** OR **Deferred** with rationale recorded here.
- [ ] Round 6 — CLAUDE.md ADR-summary block updated once with all sub-ADR entries (Rule 5).
- [ ] Each sub-ADR's `Builds on:` header cites only predecessors with `Implemented` status (Rule 8 conformance).
- [ ] CI test gates green; combined regression suite passing.
- [ ] No `console.error` in production explorer load.
- [ ] Per-tab feature docs (`docs/features/*.md`) reflect the post-pass state.

---

## Risks

**R1 — Pass duration drift.** A 10-item coordinated pass risks dragging across many sessions, during which other ADRs (in flight: ADR-235) land and interact. Mitigation: Tier 2 items execute first as proof of velocity; Tier 1 sub-ADRs are sized to one session each per Singular Implementation rule.

**R2 — Cross-pass interaction with ADR-235.** ADR-235 dissolves `UpdateContext` into `InferContext` + `WriteFile` + `ManageRecurrence`. The chat role-based design system (Item 1, ADR-237) will surface `WriteFile` invocations in chat narrative — must compose with ADR-235's vocabulary, not predate it. Mitigation: per Rule 8 + the Round structure, ADR-237 (Round 2) waits until ADR-235 is **Implemented** before it drafts. Round 1 (ADR-238 — autonomy-mode FE) is independent of ADR-235's primitive surface and proceeds without that gate. Round 0 (Tier 2 hygiene) shipped before this risk applied.

**R3 — Trader cockpit scope creep.** Item 3 has the largest surface and could absorb time better spent elsewhere. Mitigation: scoping memo gates the sub-ADR; if the memo reveals scope > 3 sessions, the sub-ADR splits into phases at memo time, not mid-implementation.

**R4 — Frontend test infrastructure.** YARNNN's frontend test coverage is thin compared to backend. Tier 1 sub-ADRs requiring `web/__tests__/*` may need infrastructure scaffolding first. Mitigation: each Tier 1 sub-ADR declares its test surface; if scaffolding is needed, it's named as a sub-phase, not skipped.

**R5 — Scope guard violations under pressure.** A genuine architectural question may surface mid-pass that a scope guard rules out. Mitigation: violation is allowed only by amending this umbrella ADR explicitly — no silent expansion.

---

## What this ADR does NOT decide

- Specific component shapes for any of the 10 items.
- Specific test gate counts or assertion lists for sub-ADRs.
- Whether ADR-237 / 238 / 239 / 240 final numbers hold (numbers reserved; final assignment per sub-ADR drafting).
- Whether deferred items become future-pass scope or pure deferrals.

---

## Closing

The pass exists because the cockpit was built ADR-by-ADR with no coordinator. The umbrella ADR is the coordinator. Future passes of this shape (multi-item, multi-surface, multi-tier) should follow the same pattern — name the items, tier them, sequence them, codify the doc-radius rules — rather than landing each item as its own ADR with no shared frame.

The 10 items are not novel architectural decisions in aggregate; they are coherence work on top of decisions already made. This ADR's job is to make that coherence work legible and bounded.
