# ADR-241: Single Cockpit Persona — Reviewer Collapses Into Thinking Partner

> **Status**: **Implemented** (2026-04-30, single commit). Round 5 step of the ADR-236 frontend cockpit coherence pass. Test gate `api/test_adr241_single_cockpit_persona.py` 8/8 passing. TypeScript typecheck clean. Cross-ADR regression check 79/79 across nine gates (231 + 233 P1 + 233 P2 + 234 + 237 + 238 + 239 + 240 + 241) — ADR-239 gate's `WEB_DECISIONS_PANE` path constant updated for the relocated module. CHANGELOG entry `[2026.04.30.N]` recorded. ADR-194 v2 status header amended with the surface-collapse note pointing here. Operator manual smoke required: `/agents` redirects to TP detail; legacy `?agent=reviewer` redirects to TP Principles tab; `/work` Decisions tab shows the verdict stream.
> **Date**: 2026-04-30
> **Authors**: KVK, Claude
> **Dimensional classification**: **Channel** (Axiom 6) primary — collapses two cockpit surfaces (TP card + Reviewer card + Reviewer detail view + Decisions stream split between cockpit faces and Reviewer view) into one canonical cockpit persona. **Identity** (Axiom 2) secondary — re-classifies Reviewer's *operator-facing surface* without amending its substrate role. **Substrate** (Axiom 1) tertiary — `/workspace/review/*.md` substrate paths preserved.
> **Builds on**: ADR-194 v2 (Reviewer Layer + Operator Impersonation — Implemented; substrate semantics preserved), ADR-198 (Surface Archetypes — Implemented; the Stream archetype's correct home for decisions.md is `/work`, not the persona detail view), ADR-214 (Agents Page Consolidation — Implemented; this ADR amends its decision to render Reviewer as a roster card), ADR-216 (Orchestration vs Judgment — Implemented; this ADR refines the operator-facing presentation of that distinction), ADR-235 (UpdateContext Dissolution — Implemented; ManageAgent.create removal is the upstream reason "we only have one agent now"), ADR-236 (Frontend Cockpit Coherence Pass — Round 4 closed), ADR-237 (Chat Role-Based Design System — Implemented; reviewer-verdict shape stays in chat narrative), ADR-238 (Autonomy-Mode FE Consumption — Implemented), ADR-239 (Trader Cockpit Coherence Pass — Implemented; canonical `parseDecisions` lives in `web/lib/reviewer-decisions.ts`), ADR-240 (Onboarding-as-Activation — Implemented).
> **Amends**: ADR-214 (Agents Page Consolidation) — the "Reviewer rendered as systemic roster card" decision is reversed. Single-card roster collapses to direct-detail landing; Reviewer's substrate becomes a tab inside the canonical Thinking Partner detail view. ADR-194 v2 (Reviewer Layer) — operator-facing surface visibility section amended; substrate role + path conventions + audit trail behavior preserved.
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-141 (execution layers), ADR-156 (single intelligence layer), ADR-159 (filesystem-as-memory), ADR-194 v2 substrate (`/workspace/review/IDENTITY.md` + `principles.md` + `decisions.md` paths unchanged; Reviewer audit trail unchanged; reactive dispatch in `services/review_proposal_dispatch.py` unchanged; AI Reviewer logic in `api/agents/reviewer_agent.py` unchanged), ADR-198 archetypes (Decisions stays a Stream archetype, just relocates), ADR-209 (Authored Substrate attribution), ADR-216 (orchestration vs judgment vocabulary stays as backend canon — operator-facing surface collapses).

---

## Context

The original ADR-236 audit recorded operator observations that surfaced after Round 4:

> *"i thought we only have one agent now (Thinking Partner) and thus, no cards needed go straight into agent=reviewer? (but needs rename) and thus, here, i thought we remove the decisions section (said this needs to be migrated to work, or the kernel like consideration), whilst the other information is tab display."*

And from the original assessment's **Agents page** section:

> *"agents theme, until there will be multiple agents (for now, there can't be since we removed the primitive recently), it should just be the command center like page dedicated to the new, unified Thinking Partner Agent."*

> *"Main layout should be tab based. the current two split with decisions is confusion. tabs are the files dedicated to the agent."*

> *"existing Decisions component is actually better treated as some dedicated kernel projects components under work page."*

The audit context: ADR-235 D2 removed `ManageAgent.create` from the chat surface — operators cannot create user-authored Agents. Per ADR-205 + ADR-194 v2, signup scaffolds two systemic Agents (YARNNN + Reviewer seat). Post-ADR-214, both render as roster cards on `/agents`.

But with `ManageAgent.create` gone and no expansion path, the roster is **always exactly two cards forever** (or one + one synthesized pseudo-agent). The Round 5 hygiene commit (`174fd92`, 2026-04-29) collapsed the roster's grouping headers but kept both cards.

The operator's observation is sharper: with one persona-bearing entity, the roster is wasted ceremony. The right shape is direct-detail landing. And the Reviewer substrate isn't structurally a separate "agent" the operator interacts with — it's the **judgment layer** behind YARNNN's posture. Surfacing it as a peer card overstates its agent-ness.

### Why this is correct, not a regression of ADR-194 v2

ADR-194 v2 declared Reviewer as the sole systemic persona-bearing Agent because it owns judgment substrate (IDENTITY.md, principles.md, decisions.md) and ADR-216's orchestration-vs-judgment distinction needs a substrate home. **That substrate role is preserved by this ADR.** What changes is the *operator-facing surface*:

- **Backend canon (unchanged):** `/workspace/review/` substrate stays. `services/reviewer_audit.py` keeps writing `decisions.md`. `api/agents/reviewer_agent.py` keeps running. `services/review_proposal_dispatch.py` keeps dispatching reactive verdicts. ADR-194 v2 Phases 1–3 implementations are preserved bit-for-bit.

- **Operator-facing surface (this ADR):** Reviewer is no longer presented as a separate roster card. Its substrate (Identity + Principles) becomes a **tab inside Thinking Partner's detail view**. `decisions.md` content (the verdict stream) **migrates to `/work`** as the canonical Stream-archetype home for "what the kernel decided about my proposals."

This is consistent with ADR-216's framing: orchestration vs judgment is a **backend/architectural** distinction. The operator interacts with **one cockpit persona** (TP) that internally consults the judgment layer. Surfacing both as peer agents was a leaky abstraction — fine while ADR-235 D2 hadn't shipped, jarring once "one agent" became literally true.

### What ADR-198's Stream archetype says about Decisions

ADR-198 says Stream archetypes (append-only logs read chronologically) live at the surface that hosts the **actionable consequence** of the stream. For Decisions:

- The **proposals** these decisions evaluate are operator work items (action_proposals → "do this trade?").
- The actionable consequence ("approve / reject / observe") happens on `/work` (TrackingFace already shows pending action_proposals).
- A Reviewer detail page rendering decisions has the operator clicking *out* to `/work` to act.

The Stream archetype's natural home is `/work`. Today's ReviewerDetailView placement was correct under ADR-214's "render Reviewer as systemic peer," but once that framing dissolves, Decisions follow the consequence path.

---

## Decision

Three structural changes, all landing in one commit:

### D1 — Collapse `/agents` roster; default to Thinking Partner detail

`/agents` (no query param) **redirects to `/agents?agent=thinking-partner`** instead of rendering a roster surface. With one non-pseudo systemic agent, the roster page is dead UX.

Reviewer's pseudo-agent synthesis on the API side (`api/routes/agents.py::list_agents`) **stays** — it's still cited by other surfaces (e.g., breadcrumb context, future expansibility) and removing it would amend ADR-214 more than necessary. But the FE roster filter that surfaced it as a peer card no longer applies; `AgentRosterSurface.tsx` is **deleted entirely**. The only landing on `/agents` is the TP detail view.

**Future expansibility**: when a future ADR re-introduces user-authored Agents, the roster reappears and `/agents` returns to roster-default. Today's collapse is a temporary canonical shape; the backend stays roster-capable.

### D2 — Thinking Partner detail becomes tab-based

`AgentContentView` for `agent_class === 'meta-cognitive'` (Thinking Partner) renders four tabs:

1. **Identity** — TP's identity card (current TP shell content from `AgentRoleBlock` + `AgentMetadata`). Cites the operator's IDENTITY.md when operator-authored.
2. **Principles** — Renders `/workspace/review/principles.md` (lifted from `ReviewerDetailView`'s `PrinciplesPane`). The judgment framework TP applies to verdicts. Edit-via-Files affordance preserved per ADR-215 R3.
3. **Memory** — Existing `LearnedBlock` content (TP's accumulated learnings), if relevant. Currently meta-cognitive suppresses the LearnedBlock — re-evaluate whether to surface a "Memory" tab here. **Defer** the Memory tab to a follow-up if no meaningful TP-memory substrate exists today (avoid empty tabs).
4. **Tasks** — Lightweight "currently assigned to" list (existing `TasksBlock`).

The tabs replace the current single-page vertical scroll. Tab navigation via URL query param (`?agent=thinking-partner&tab=principles`) so tabs are deep-linkable.

### D3 — Decisions migrate to `/work` entirely

`/workspace/review/decisions.md` substrate is **read-only** (per ADR-194 v2 Phase 2a, append-only audit log). The current rendering split:

- `web/components/agents/reviewer/DecisionsStreamPane.tsx` — full Stream view at `/agents?agent=reviewer`.
- `web/components/library/faces/PerformanceFace.tsx` — calibration aggregate inside `/work` cockpit (post-ADR-239, uses canonical `parseDecisions`).
- `web/components/library/faces/TrackingFace.tsx` — pending action_proposals (different substrate — `action_proposals` table, not `decisions.md`).

Post-ADR-241:

- `DecisionsStreamPane.tsx` **moves** from `web/components/agents/reviewer/` to `web/components/work/details/DecisionsStream.tsx`. Becomes a `/work` surface component.
- A new entry on `/work`'s left list — **Decisions** (or the surface's natural slot) — shows the Stream view. Operator-clickable; renders the full filterable verdict log.
- Calibration aggregate in PerformanceFace **stays** (it's a derived view, not a duplicate).
- ReviewerDetailView **deleted**. Its `ReviewerCardPane` content (Reviewer Identity = the operator's posture toward judgment) folds into TP's Identity tab if the content is non-trivial; otherwise deleted.

### D4 — Naming: "Reviewer" → operator-facing language

Per the operator's "needs rename": the term **Reviewer** stays as backend canon (per ADR-194 v2 the seat is path-named at `/workspace/review/`, the audit log is `decisions.md`, the AI Reviewer module is `reviewer_agent.py`). What changes is **operator-facing presentation**:

- The Principles tab content ships under the label "**Principles**" (no "Reviewer" prefix in the page UI).
- The Decisions surface on `/work` ships as "**Decisions**" or "**Verdicts**" (whichever the implementation finds reads better — implementation-time call per Rule 7).
- The synthesized pseudo-agent's `title` field stays "Reviewer" in the API response for backend coherence (other ADRs reference it), but the FE never surfaces "Reviewer" as a top-level cockpit label.

This honors the operator's intent ("but needs rename") without performing a backend-wide rename that would amend more ADRs than necessary.

---

## What this ADR does NOT do

- **Does not delete `/workspace/review/*.md` substrate.** ADR-194 v2 substrate paths preserved verbatim. Reviewer audit trail keeps writing `decisions.md`. AI Reviewer keeps reading `principles.md`.
- **Does not delete `services/reviewer_audit.py`, `services/review_proposal_dispatch.py`, `api/agents/reviewer_agent.py`.** Backend judgment layer unchanged.
- **Does not change `agent_class='reviewer'` in the API response.** The synthesized pseudo-agent stays in `list_agents()` for future expansibility and ADR-216 vocabulary preservation. FE just stops surfacing it as a roster card.
- **Does not amend ADR-216's orchestration-vs-judgment distinction.** That's backend canon. The distinction's *visibility* on the cockpit collapses; the distinction's *substrate* is unchanged.
- **Does not introduce a JS test runner.** Same regression-script pattern as ADR-237 / ADR-238 / ADR-239 / ADR-240 per ADR-236 Rule 3.
- **Does not delete `web/lib/reviewer-decisions.ts`.** The canonical `parseDecisions` + `aggregateReviewerCalibration` (ADR-239) stay; the new `/work` Decisions surface imports them.
- **Does not change chat-narrative reviewer rendering.** ADR-237's `reviewer-verdict` shape (full-width `ReviewerCard` rendering when `msg.role === 'reviewer'`) stays. Verdicts still appear inline in chat narrative; only the *agents page* surface changes.
- **Does not introduce a Memory tab on TP.** Deferred per D2 unless implementation-time inspection surfaces meaningful TP-memory substrate.

---

## Implementation

### Files created (2)

- `web/components/work/details/DecisionsStream.tsx` — relocated from `web/components/agents/reviewer/DecisionsStreamPane.tsx`. Same logic, same canonical `parseDecisions` import, same operator-visible behavior. Renamed for clarity (no "Pane" suffix; matches the `web/components/work/details/` naming convention for kind-middle components).
- `api/test_adr241_single_cockpit_persona.py` — Python regression gate (8 assertions).

### Files modified (4)

- `web/app/(authenticated)/agents/page.tsx` — when `?agent` query param is absent, **redirect** to `?agent=thinking-partner` (preserves bookmark-safety per ADR-236 Rule R5 redirect-stub policy). Roster rendering branch deleted.
- `web/components/agents/AgentContentView.tsx` — `meta-cognitive` branch becomes tab-based (Identity / Principles / Tasks). `reviewer` branch redirects to `?agent=thinking-partner&tab=principles` (the `?agent=reviewer` URL maps to the Principles tab on TP for backwards-compat with existing breadcrumbs/links).
- `web/lib/routes.ts` — add `THINKING_PARTNER_ROUTE = '/agents?agent=thinking-partner'` constant for cross-surface deep-links.
- `docs/adr/ADR-194-reviewer-layer.md` — small operator-facing surface amendment note in status header (one paragraph) citing ADR-241 as the source of the surface change. Substrate sections preserved verbatim.

### Files deleted (5)

- `web/components/agents/reviewer/ReviewerDetailView.tsx`
- `web/components/agents/reviewer/ReviewerCardPane.tsx` — its content (operator's posture toward judgment) was a duplication of TP identity framing; folds into TP's Identity tab.
- `web/components/agents/reviewer/PrinciplesPane.tsx` — content lifts into a TP Principles tab component (kept structurally similar; just no longer in the `reviewer/` namespace).
- `web/components/agents/reviewer/DecisionsStreamPane.tsx` — moved to `web/components/work/details/DecisionsStream.tsx` (one source of truth; the relocation is the move, not parallel files).
- `web/components/agents/AgentRosterSurface.tsx` — no longer rendered. With direct-detail landing on `/agents`, the roster surface is dead code per Singular Implementation rule.

### Files NOT modified

- `api/routes/agents.py` — `list_agents()` reviewer synthesis preserved.
- `api/services/reviewer_audit.py` + `api/services/review_proposal_dispatch.py` + `api/agents/reviewer_agent.py` — backend judgment layer untouched.
- `web/lib/reviewer-decisions.ts` — canonical parser stays (ADR-239 D1 preserved).
- `web/components/library/faces/PerformanceFace.tsx` — calibration aggregate path unchanged (still consumes `aggregateReviewerCalibration`).
- `web/components/library/faces/TrackingFace.tsx` — pending action_proposals view unchanged (different substrate — `action_proposals` table — not `decisions.md`).
- `web/components/tp/MessageDispatch.tsx` — reviewer-verdict chat shape preserved per ADR-237.
- ADR predecessors except ADR-194 v2's small surface-amendment note — Rule 2 historical preservation.

### Test gate

`api/test_adr241_single_cockpit_persona.py` asserts eight invariants:

1. `web/components/work/details/DecisionsStream.tsx` exists and exports `DecisionsStream`.
2. `web/components/agents/reviewer/` directory does NOT exist (regression guard against re-creation).
3. `web/components/agents/AgentRosterSurface.tsx` does NOT exist (regression guard).
4. `web/app/(authenticated)/agents/page.tsx` redirects to `?agent=thinking-partner` when no agent query param is present.
5. `web/components/agents/AgentContentView.tsx` no longer dispatches to `ReviewerDetailView` (regression guard against the pre-ADR-241 dispatch line).
6. `api/services/reviewer_audit.py` exists and continues to write to `/workspace/review/decisions.md` (substrate preservation regression guard).
7. `web/lib/reviewer-decisions.ts` exports `parseDecisions` and `aggregateReviewerCalibration` (ADR-239 preservation regression guard).
8. `web/components/work/details/DecisionsStream.tsx` imports `parseDecisions` from `@/lib/reviewer-decisions` (Singular Implementation: one parser, one canonical home).

Combined gate target: 8/8 passing.

### Render parity

| Service | Affected | Why |
|---|---|---|
| API (yarnnn-api) | No | FE-only, except `docs/adr/ADR-194-reviewer-layer.md` doc update. |
| Unified Scheduler | No | FE-only. |
| MCP Server | No | FE-only. |
| Output Gateway | No | Untouched. |

**No env var changes. No schema changes. No new services. No DB migrations.**

### Singular Implementation discipline

- One landing on `/agents` — direct-detail to TP. Roster surface dead code, deleted.
- One Decisions stream — `web/components/work/details/DecisionsStream.tsx` is the only FE site that renders the full verdict log. Old `ReviewerDetailView` deleted.
- One canonical parser — `web/lib/reviewer-decisions.ts::parseDecisions` (preserved from ADR-239).
- One TP detail view — tab-based. No legacy single-page-scroll variant coexists.

---

## Risks

**R1 — Breadcrumb / deep-link breakage.** Existing links to `/agents?agent=reviewer` (used by a few internal FE components and by the ADR-194 v2 amendment chain) need to keep working. Mitigation: `?agent=reviewer` redirects to `?agent=thinking-partner&tab=principles` in `AgentContentView`'s reviewer branch. Old URL works; lands on the right tab.

**R2 — Substrate-vs-surface boundary confusion in future ADRs.** ADR-241 makes a sharp distinction between Reviewer substrate (preserved) and Reviewer surface (collapsed). Future ADRs touching judgment substrate need to know not to reintroduce a peer "Reviewer" cockpit surface. Mitigation: ADR-241's status header explicitly amends ADR-214 + notes the surface-vs-substrate boundary; future ADRs that touch the judgment layer will find this ADR via grep on "Reviewer" in `docs/adr/`.

**R3 — Decisions surface placement on `/work`.** Where exactly does Decisions appear? `/work`'s list view groups by output_kind; Decisions isn't a recurrence and doesn't fit the existing groupings. Mitigation: implementation-time decision per Rule 7. Likely candidate: a top-level pseudo-tab or a "System" tab entry surfacing `decisions.md` content (Stream archetype). The exact slot is implementation-time.

**R4 — TP identity tab content.** TP's current `AgentRoleBlock` + `AgentMetadata` content is generic shell — there's no operator-authored TP IDENTITY.md per ADR-216 (TP's voice is platform-fixed). The Identity tab risks being thin. Mitigation: pragmatic — the Identity tab surfaces TP's role + tagline + active-task summary. If thinness becomes a real legibility issue, a future ADR introduces a TP-customization surface; today's collapse is honest about TP's platform-fixed nature.

**R5 — Memory tab deferral.** D2 defers a Memory tab. If implementation-time inspection finds meaningful TP-memory substrate (e.g., `agent_memory` JSONB on the `agents` row, or a `/agents/thinking-partner/memory/*.md` filesystem area), Memory becomes a fourth tab. If not, three tabs (Identity / Principles / Tasks) is the canonical shape.

**R6 — `AgentContentView`'s reviewer branch redirect timing.** When the operator hits `?agent=reviewer`, the redirect fires inside the component's render. React Router handles this cleanly via `router.replace`, but a flash of the legacy view could occur if not gated correctly. Mitigation: redirect happens in a `useEffect` early-return shape; loading state shows during the brief redirect.

---

## Phasing

Single commit, sized medium (~500 LOC delta — net negative, since 5 files delete and 1 moves). Linear:

1. Author `web/components/work/details/DecisionsStream.tsx` by relocating `DecisionsStreamPane.tsx` content (lifted verbatim, import path adjusted).
2. Refactor `AgentContentView.tsx` `meta-cognitive` branch to tab-based; reviewer branch becomes a redirect.
3. Update `web/app/(authenticated)/agents/page.tsx` — default redirect to `?agent=thinking-partner` when no param.
4. Delete the five files listed in §"Files deleted."
5. Add `THINKING_PARTNER_ROUTE` constant to `web/lib/routes.ts`.
6. Surface Decisions on `/work` — exact slot per implementation-time decision.
7. Add ADR-194 v2 small surface-amendment note in its status header.
8. Author `api/test_adr241_single_cockpit_persona.py` — 8 assertions.
9. Run all gates (231 / 233 P1+P2 / 234 / 237 / 238 / 239 / 240 / 241).
10. Manual smoke required: `/agents` redirects to TP detail; `?agent=reviewer` redirects to TP Principles tab; `/work` shows Decisions surface; `/workspace/review/decisions.md` substrate unchanged on disk.
11. Add `[2026.04.30.N]` CHANGELOG entry.
12. Pre-commit `git diff --cached --stat` discipline per ADR-239 recovery note.
13. Atomic commit + push.

---

## Closing

ADR-241 closes the Reviewer-as-peer-agent loop that ADR-235 D2 made structurally inconsistent. With one persona-bearing chat entity (TP) and no expansion path on the cockpit, presenting Reviewer as a separate agent was a leaky abstraction inherited from the pre-ADR-235 era. The right shape — already implicit in ADR-216's orchestration-vs-judgment vocabulary — is one cockpit persona that internally consults a judgment substrate. ADR-241 makes that surface-truth match the substrate-truth. Decisions, being the actionable consequence of judgment, follow to `/work` where the operator decides what to do about them. The Round 5 mop-up that started with operator observations becomes a clean architectural correction, not a hygiene patch.
