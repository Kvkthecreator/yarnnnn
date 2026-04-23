# ADR-214: Agents Page Consolidation — Four-Tab Nav, Systemic Agents Inside

**Status:** Proposed (implementation in same commit)
**Date:** 2026-04-23
**Dimensional classification:** **Channel** (primary, Axiom 6) + **Identity** (Axiom 2)

## Context

Post-ADR-212 (LAYER-MAPPING correction, 2026-04-23), "Agent" in YARNNN canon is strictly a judgment-bearing entity with standing intent. Three members: **YARNNN** (systemic meta-cognitive), **Reviewer** (systemic judgment seat), and **user-authored domain Agents** (instance). Production roles and platform integrations are **Orchestration**, not Agents. The cockpit navigation today does not reflect this taxonomy:

- **Five nav tabs** (`Chat | Work | Files | Team | Review` per ADR-205 F1 + ADR-180), one per systemic Agent layer plus substrate and work. Review is a standalone tab pointing at Reviewer substrate; Team conflates Agents with Orchestration in its roster (Production Roles + Integrations appear as co-equal groups alongside YARNNN and user-authored Agents).
- **Reviewer has no agent-detail entry point.** `/review` renders one monolithic composition (`ReviewerCardPane` + `PrinciplesPane` + `DecisionsStreamPane`) reading `/workspace/review/IDENTITY.md` + `principles.md` + `decisions.md`. Operationally it *is* an agent detail view — the filesystem substrate, the identity card, the principles (configuration), the decisions (run log) — but structurally it's a separate tab.
- **The Team page groups Production Roles and Integrations as if they were Agent groups** (per `AgentRosterSurface.tsx:40-62`), which post-ADR-212 is an architectural inconsistency: they are orchestration capability bundles, not principals.

The user-facing effect: an operator looking at the cockpit sees five top-level destinations where four would suffice, and the Agents surface mixes two kinds of things it shouldn't.

## Decision

**Collapse to four nav tabs.** Merge Reviewer into the Agents surface as a systemic agent detail. Drop Orchestration groups from the Agents roster. Rename the route `/team` → `/agents` (reverse ADR-201).

### Decisions locked in

1. **Nav is `Chat | Work | Agents | Files`.** Four tabs, one per cockpit concern. The dropped tab (Review) collapses into Agents; Reviewer is still reachable via `/agents?agent=reviewer`.

2. **Agents page = Agents only.** Roster shows exactly two sections: **Systemic** (YARNNN + Reviewer, always two cards, unconditional) and **Domain** (user-authored instance Agents, zero-to-many). Production Roles, Reporting, and Integrations no longer appear as groups on this surface. They are Orchestration per ADR-212; their setup lives at `/settings?tab=connectors` (integrations) and their composition is visible on `/work` task-detail `## Team` sections (per-task, display-only, already implicit).

3. **Reviewer is a pseudo-agent in the list response.** `api/routes/agents.py::list_agents()` synthesizes a Reviewer envelope in every list response. No DB row — Reviewer substrate stays filesystem-first (`/workspace/review/*.md`) per ADR-194 v2. Backend synthesis (not frontend-only) because the same shape will later carry Reviewer's approval/decision metrics without a second round-trip; this keeps the list/detail contract uniform across Agent kinds.

4. **Reviewer detail view absorbs `ReviewSurface` composition.** New `web/components/agents/ReviewerDetailView.tsx` carries the identity card, principles pane, and decisions stream. `components/review/*` deleted after move (singular implementation, no dual path). `AgentContentView` dispatches on agent kind: `yarnnn` → existing YARNNN detail, `reviewer` → new ReviewerDetailView, `domain` → existing user-authored detail.

5. **Route rename `/team` → `/agents`.** Reverses ADR-201 at the URL level. ADR-201's layered-naming principle (operator vocabulary in UI, substrate vocabulary in code) is preserved — "Agents" is now both the operator label and the substrate-aligned path. `TEAM_ROUTE` constant deleted; `AGENTS_ROUTE` added. `/team` retains a redirect stub for bookmark symmetry (mirrors how the old ADR-201 kept `/agents` → `/team`); `/review` is deleted outright with no redirect (its composition moved into `/agents?agent=reviewer`).

### Why Reviewer inside Agents and not its own tab

Reviewer and YARNNN are both systemic Agents by ADR-212. Treating one as a first-class tab and the other as an agent detail is an internal inconsistency. The operator's mental model is cleaner when both systemic Agents + all domain Agents live on a single surface with uniform list/detail shape (ADR-167 v2). The existing `ReviewSurface` panes (identity + principles + decisions) map naturally onto the agent detail contract (identity card + config + run history).

### Why drop Orchestration from the Agents page

ADR-212 is explicit: only judgment-bearing entities are Agents. Production roles and platform integrations are capability bundles. Showing them in an "Agents" roster is a vocabulary leak — it implies operator parity where none exists (production roles have no standing intent, no memory-across-runs, no workspace of their own per ADR-205). Surfacing them contextually where they matter (task-detail Team section for production roles; Settings for integrations) preserves access without conflating ontology.

### Why backend synthesis for Reviewer, not a real agents row

Creating a `reviewer`-role row would require (a) an agent lifecycle (hygiene, pulsing, versioning) that Reviewer doesn't participate in, (b) a new role enum constraint update, (c) data-migration of existing workspaces. Reviewer substrate is filesystem-first by ADR-194 v2 Axiom 1; the list-response synthesis is a read-side adapter that keeps the substrate authoritative without polluting the `agents` table.

## Consequences

### Preserved

- ADR-212 taxonomy. This ADR is the cockpit implementation of ADR-212's vocabulary.
- ADR-194 v2 Reviewer substrate. No changes to `/workspace/review/*.md` or to the reviewer audit pipeline.
- ADR-167 v2 list/detail surfaces pattern. `/agents` follows the same URL-state + auto-select-deleted shape.
- ADR-205 F1 chat-first landing. `HOME_ROUTE` stays `/chat`.
- ADR-180 Files label. Unchanged (`/context` route, "Files" nav label).

### Amended

- **ADR-167 v2**: list/detail surfaces gain a systemic-agent slot convention. YARNNN + Reviewer are always present, always first in the roster, regardless of whether any domain Agents exist.
- **ADR-189**: Authored-team moat framing preserved — Systemic section is infrastructural (framework gives these two), Domain section is the moat (user authors these).
- **ADR-201**: Route reverses from `/team` back to `/agents`. The rename to "Team" framing was pre-ADR-212; post-flip, "Agents" is more precise and matches operator vocabulary because the surface now contains only Agents.

### Superseded

- **ADR-200** (Review as standalone surface) — `/review` as a top-level cockpit destination is superseded. Reviewer is now an agent detail inside `/agents`. The substrate shape and panes survive; only the navigation slot moves.

### Deleted

- `web/app/(authenticated)/review/page.tsx`
- `web/components/review/` (all four files — absorbed into `web/components/agents/ReviewerDetailView.tsx`)
- `TEAM_ROUTE` constant (replaced by `AGENTS_ROUTE`)
- `REVIEW_ROUTE` constant
- Production-role-as-Agent-group grouping in `AgentRosterSurface.tsx` (`specialist`, `domain-steward`, `synthesizer`, `platform-bot` class-based groups)

### New

- `web/components/agents/ReviewerDetailView.tsx` — absorbs `ReviewSurface` composition.
- `web/lib/routes.ts::AGENTS_ROUTE` = `/agents`.
- Backend synthesis helper in `api/routes/agents.py` that emits Reviewer pseudo-agent envelope in list responses.
- `web/app/(authenticated)/team/page.tsx` — redirect stub (symmetric to the pre-existing `/agents` → `/team` bookmark redirect; 1-file, no duplicated UI).

## Cleanup items absorbed in this ADR

Per the ADR-212/209/213 audit (2026-04-23):

- `AgentContentView.tsx:326` — "Specialist domain outputs" → "Production Role domain outputs"
- `WorkspaceStateView.tsx:408` — `specialist`/`specialists` user-facing label → `Production Role`/`Production Roles`
- `AgentRosterSurface.tsx:96` — stale "Specialists" comment updated (also rewritten as part of roster reshape)

Low-priority educational copy (`how-it-works`, `faq`) deferred to a separate content pass.

## Deferred / follow-on

- **Platforms pane on `/files`.** The user's conceptual alignment (integrations = setup = Files) is correct, but today integration setup lives at `/settings?tab=connectors` and works. Surfacing a read-only Platforms index on `/files` (listing active platform connections with a "Connect new" CTA) is a clean follow-on UX change; it doesn't belong in the ADR-212 cockpit-consolidation commit because it requires weighing duplication vs. settings-stays-as-source-of-truth. Propose: ADR-215 "Files Platforms Pane" when we next touch integrations.
- **Production-role visibility.** Today visible only via `/work` task-detail team sections (implicit). If operators want a capability-roster view of the Orchestration palette, ADR-215 or similar should also address that.

## References

- ADR-167: List/Detail Surfaces with Kind-Aware Detail
- ADR-180: Context → Files nav label
- ADR-194 v2: Reviewer Layer + Operator Impersonation
- ADR-200: Review Surface (superseded by this ADR)
- ADR-201: Team Rename and Cross-Linking (reversed at URL level by this ADR)
- ADR-205 F1: Cockpit nav baseline (chat-first landing)
- ADR-211: Reviewer Substrate Phase 4
- ADR-212: LAYER-MAPPING correction (this ADR's vocabulary basis)
