# ADR-201: Team Destination — `/agents` → `/team` Rename + Work Cross-Linking

> **Status**: Proposed — implementation targeted this cycle
> **Date**: 2026-04-20
> **Authors**: KVK, Claude
> **Extends**: ADR-198 v2 (cockpit nav: Overview / Team / Work / Context / Review); ADR-199 (Overview shipped); ADR-200 (Review shipped); FOUNDATIONS v6.0 GLOSSARY (team vs agents vocabulary)
> **Implements**: Team destination — third of four cockpit surface phases (ADR-198 §Implementation)

---

## Context

ADR-198 v2 ratified "Team" as the operator-native nav label for the agents-as-identity surface. The actual route + directory still live at `/agents`. This ADR closes that gap — full rename, no dual nav vocabulary.

### Why rename the route, not just the label

Singular implementation discipline. A nav tab labeled "Team" pointing at `/agents` creates three forms of drift:

1. **Vocabulary drift** — operators see "Team" in nav, "Agents" in URL, "Agents" in breadcrumbs. NARRATIVE v4.2 retired "Agents" as a nav destination word; keeping `/agents` as the URL leaks the retired vocabulary into every bookmark, share, and dev-tools inspection.
2. **Component drift** — `AgentRosterSurface`, `AgentContentView` already have the right substrate-level names (they render `agents` table rows). Relabeling only the URL path lets the component names stay aligned with the table name while the destination uses the user-facing name. Nav says "Team"; URL says `/team`; component says `AgentRosterSurface` — three layers, each named for its consumer. This is not drift; it's layered-naming-by-audience.
3. **Future ADR load** — every follow-on doc writing "`/team` route" vs "`/agents` route" is extra cognitive load. Pick one. Ship it.

### Why cross-linking matters

ADR-198 v2 committed Team and Work as peer destinations. For them to function as peers, the cross-link flow must be seamless: agent detail shows the agent's tasks (deep-link to `/work/{slug}`); task detail shows the assigned agent (deep-link to `/team/{slug}` — currently `/agents?agent={slug}`). Audit shows `WorkDetail.tsx` already links to `AGENTS_ROUTE` via the constant — updating the constant plus a small pattern change (query param `?agent=` → route segment `/{slug}`) is the scope.

---

## Decision

### 1. Route rename: `/agents` → `/team`

Move `web/app/(authenticated)/agents/*` to `web/app/(authenticated)/team/*`. Directory rename; file contents preserved.

Routes after this ADR:
- `/team` — roster surface (was `/agents`)
- `/team/[id]` — legacy by-id redirect (was `/agents/[id]` — already redirected to `/agents` pre-cockpit; now redirects to `/team`)
- `/team?agent=<slug>` — deep-link shortcut preserved (query param name unchanged; consistent with `/work?task=<slug>`)

### 2. Legacy `/agents` redirect

New thin redirect at `web/app/(authenticated)/agents/page.tsx` that `router.replace()`s to `/team` preserving any query params. Matches the existing `/workfloor` + `/orchestrator` redirect pattern — no hand-wringing over bookmark breakage, just a clean migration path.

**Singular implementation note:** this redirect is a *migration bridge*, not a dual nav. It exists to preserve bookmark safety during the cockpit rollout and should be deleted in a future cleanup commit once we're confident external links have caught up. For now, it's the lightest-weight migration strategy.

### 3. `AGENTS_ROUTE` constant → `TEAM_ROUTE`

In `web/lib/routes.ts`:

- Remove `AGENTS_ROUTE = "/agents"`
- Add `TEAM_ROUTE = "/team"`
- Update all internal references (WorkDetail, SnapshotPane, BreadcrumbContext, AuthenticatedLayout, WorkspaceStateView) to import `TEAM_ROUTE`

Singular implementation: no dual constant, no backwards-compat alias. The rename is atomic.

### 4. ToggleBar: `Agents` → `Team`

Label + segment id both change. Route reflects the new path. Final ToggleBar state:

```
Overview | Work | Files | Agents(→Team) | Review
```

becomes

```
Overview | Work | Files | Team | Review
```

Five destinations, all operator-native.

### 5. Cross-linking pattern

**Task → Team linking (already partial):** `WorkDetail.tsx` lines 153, 192, 248 currently link to `${AGENTS_ROUTE}?agent=${slug}`. Updated to `${TEAM_ROUTE}?agent=${slug}`. Query-param shortcut preserved.

**Team → Work linking (new verification):** `AgentContentView.tsx` should show the agent's assigned tasks with clickable links to `/work/{slug}`. Audit during implementation; add links if missing. This is what makes Team and Work feel like peer destinations, not rivals.

### 6. Component + type naming stays `Agent*`

Not renamed: `AgentRosterSurface.tsx`, `AgentContentView.tsx`, `AgentDetail`, `Agent` type, etc. These are *substrate-level* names aligned with the `agents` DB table + Axiom 2 cognitive layer terminology. The URL is operator-vocabulary; the code is substrate-vocabulary; both are correct for their audience.

**This is the layered-naming principle:**
- **URL / nav label** — operator vocabulary ("Team")
- **Components / types** — substrate vocabulary ("Agent", matches `agents` table + ADR-189 cognitive layer)
- **DB + cognitive layer** — Axiom-1 substrate (unchanged forever)

Each layer is named for its consumer. No drift; deliberate separation.

### 7. GLOSSARY + NARRATIVE re-check

Both already use "Team" and "Agent" correctly:
- **GLOSSARY.md:** "Team" = per-task specialist composition; "Agent" = user-created, domain-scoped worker. Distinct concepts.
- **NARRATIVE.md v4.2:** "Team" is the destination vocabulary; agents are what the team is *made of*.

**But the Team nav destination surfaces agents**, which GLOSSARY currently defines as a per-task concept. Is there a vocabulary conflict?

**No** — Team-the-nav-destination is the **roster of your workspace's Agents**. When the operator says "check my team," they mean "see the agents I've authored + their tasks." GLOSSARY's "Team" (per-task specialist draft) is still correct as an internal YARNNN concept — it's orthogonal to the nav label. The operator's mental model is "I supervise my team" where "team" = workspace roster; YARNNN's internal composition layer uses "team" = per-task draft. Same word, two consumers, clear-by-context.

Adding a GLOSSARY note to make this explicit.

---

## Implementation plan

Single commit. Frontend only. No backend changes.

### Files renamed (git mv)

- `web/app/(authenticated)/agents/page.tsx` → `web/app/(authenticated)/team/page.tsx`
- `web/app/(authenticated)/agents/[id]/page.tsx` → `web/app/(authenticated)/team/[id]/page.tsx`

### Files created

- `web/app/(authenticated)/agents/page.tsx` (new, thin redirect) — `router.replace('/team' + queryString)`

### Files modified

- `web/lib/routes.ts` — `AGENTS_ROUTE` → `TEAM_ROUTE`
- `web/components/shell/ToggleBar.tsx` — segment id + label + href → Team
- `web/components/work/WorkDetail.tsx` — 3 `AGENTS_ROUTE` references → `TEAM_ROUTE`
- `web/components/overview/SnapshotPane.tsx` — `/agents` literals → `/team` (2 occurrences)
- `web/components/chat-surface/WorkspaceStateView.tsx` — `href="/agents"` → `href="/team"` (2 occurrences)
- `web/components/shell/AuthenticatedLayout.tsx` — `router.push('/agents')` → `router.push('/team')`
- `web/contexts/BreadcrumbContext.tsx` — doc comment update (JSDoc), breadcrumb labels where hardcoded
- `web/app/(authenticated)/work/page.tsx` — breadcrumb label `'Agents'` → `'Team'` (line 131)
- `web/lib/supabase/middleware.ts` — `"/agents"` → `"/team"` in protected routes list

### Team detail — cross-linking verification pass

Audit `AgentContentView.tsx` + any agent-detail sub-components: ensure every agent's task list deep-links to `/work?task={slug}` or `/work/{slug}` as appropriate. Add missing links.

### Docs updated in the same commit (per ADR discipline)

- **[docs/architecture/SERVICE-MODEL.md](../architecture/SERVICE-MODEL.md)** — nav table route column `/agents` → `/team`
- **[docs/design/SURFACE-ARCHITECTURE.md](../design/archive/SURFACE-ARCHITECTURE.md)** — route map section
- **[docs/architecture/GLOSSARY.md](../architecture/GLOSSARY.md)** — add the "team" dual-meaning note

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | **Helps** | Final cockpit vocabulary — "my team produces campaigns, tracks customers, handles refunds" reads correctly. Work and Team cross-link cleanly. |
| **Day trader** | **Helps** | "My team watches the market" is the mental model. Team destination surfaces trading-bot + analyst; Work surfaces their tasks. |
| **AI influencer** (scheduled) | Forward-helps | Creator-native vocabulary — "team" matches how creators describe their collaborators. |
| **International trader** (scheduled) | Forward-helps | Operations-team vocabulary. Team = logistics agents + compliance bots. |

No domain hurt. Gate passes. Pure rename + operator-vocabulary alignment.

---

## Implementation sequence (this ADR ships in one phase)

| Step | Description |
|------|-------------|
| 1 | `git mv` route dirs `/agents` → `/team` |
| 2 | Create thin `/agents` redirect |
| 3 | Update `routes.ts` constant + all imports |
| 4 | Update ToggleBar |
| 5 | Update all route literals in components (grep pass) |
| 6 | Update docs (SERVICE-MODEL, SURFACE-ARCHITECTURE, GLOSSARY) |
| 7 | Verify cross-links: Work → Team + Team → Work |
| 8 | Commit + push |

Single atomic commit.

---

## Open questions (resolvable during implementation)

1. **Redirect lifetime.** `/agents → /team` redirect intended as migration bridge. When to delete? Leaning: next major cleanup commit; not urgent.
2. **Route segment pattern.** Team detail: `/team/[id]` (current `/agents/[id]` pattern) or `/team?agent={slug}` (current `/agents?agent=` pattern)? Both exist in the current codebase; the `/agents/[id]` file already does a `router.replace('/agents')` — so it's effectively unused. Simplify: keep only `/team?agent={slug}` as the canonical deep-link; `/team/[id]` directory gets deleted during the rename.
3. **Cross-link audit thoroughness.** Should I also audit `/agents/${slug}` hardcodings in backend-generated URLs (email templates, etc.)? Backend session confirmed they're not touching web/. If backend emits `/agents` in email links, the `/agents` redirect catches it. Verify at implementation if time permits.

---

## What this completes

- **Cockpit nav fully operator-native.** Five destinations, five operator-vocabulary labels, five URLs that match.
- **Team and Work as peer destinations.** Cross-links work in both directions; vocabulary respects their distinct Purposes (identity vs activity).
- **ADR-198 v2 §2 commitment delivered.** The full rename is now in production; no lingering "Agents" references except in component names (correctly retained per §6 layered-naming principle).

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial proposal. Full route rename `/agents` → `/team`; legacy redirect as migration bridge; constant rename; component + type names preserved per layered-naming principle. Cross-link audit between Team and Work. Single-commit frontend phase. |
