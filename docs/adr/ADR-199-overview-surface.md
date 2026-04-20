# ADR-199: Overview Surface — Cockpit Home (`/overview`)

> **Status**: Proposed — implementation targeted this cycle
> **Date**: 2026-04-20
> **Authors**: KVK, Claude
> **Extends**: ADR-198 v2 (Cockpit service model); FOUNDATIONS v6.0 (Axiom 3 Purpose, Axiom 6 Channel, Derived Principle 12 Channel legibility gates autonomy)
> **Implements**: Overview destination from ADR-198 v2 — the first of four surface phases
> **Depended on by**: ADR-200 (Review surface), ADR-201 (Team rename), ADR-202 (External Channel discipline)

---

## Context

ADR-198 v2 ratified the cockpit service model with five destinations (Overview / Team / Work / Context / Review) + ambient YARNNN rail. Overview is the operator's landing surface — "what's going on, what needs me?" — and the replacement for `/chat`-as-HOME.

### Audit finding (not originally in ADR-198's scope estimate)

The ambient YARNNN rail is **already built**. `ThreePanelLayout` (`web/components/shell/ThreePanelLayout.tsx`) renders `ChatPanel` as a resizable right-rail (drag handle, 320–720px, width-persisted to localStorage, default closed) on every surface that uses it. Three of four would-be destinations (`/work`, `/agents`, `/context`) already compose with this layout. The rail is ambient by construction.

This means ADR-199's scope is narrower than originally estimated. The rail is not work to do; it is inherited automatically by any new surface using `ThreePanelLayout`.

### What's actually missing

1. **No `/overview` route.** The cockpit landing surface has no implementation.
2. **`HOME_ROUTE` is `/chat`.** Operators land on full-page chat, not on an operator-state view.
3. **`/chat` is both HOME and a nav tab.** Under cockpit, it's neither — it's the expanded form of the ambient rail, reachable by direct URL or rail-expand, not in primary nav.
4. **Legacy routes (`/orchestrator`, `/workfloor`) still exist.** Pre-ADR-163 residue, cleaned by ADR-163's redirects but worth re-checking under cockpit.

---

## Decision

### 1. Overview surface at `/overview`

New route composed with `ThreePanelLayout` (no `leftPanel` — matches `/work` and `/agents` pattern). The center panel renders `OverviewSurface`, which composes three panes per ADR-198 §3:

**Pane 1 — Since last look** (Briefing archetype)
- Temporal changes since operator's previous session (URL `?since=<iso>` optional; defaults to last-login)
- Agent runs completed: count + most recent (deep-link to `/work/{slug}`)
- Reviewer decisions made: count + recent, with identity-tag breakdown (human vs AI vs impersonated) — deep-link to `/review`
- External deliveries sent (email, Slack) — list with timestamp
- Platform events reconciled (Alpaca fills, LS orders) — count + summary

**Pane 2 — Needs me** (Queue archetype)
- Pending `action_proposals` via existing `/api/proposals?status=pending` endpoint
- Inline `ProposalCard` rendering for top ~3 (reuse shipped component)
- "See all N" link to `/chat?q=proposals` (expanded rail, filtered) — or dedicated queue deeper view deferred to later phase
- Reviewer alerts: AI Reviewer deferred decisions awaiting human (read from proposals with `reviewer_identity=reviewer-layer:observed` or similar per backend handoff)
- Platform alerts: connection failures, rate limits (read from existing `/api/integrations/summary`)

**Pane 3 — Snapshot** (Dashboard-snippets; all linked, not embedded, per I2)
- Book headline: total P&L + revenue from `/workspace/context/_performance_summary.md` frontmatter via `/api/workspace/file?path=…` — link to per-domain `_performance.md`
- Workforce headline: N agents active, M tasks running today (count from existing agents/tasks endpoints) — link to Team
- Context headline: freshest domain + last-accumulated entity — link to Context

### 2. Empty states (Axiom-compliant per ADR-161 heartbeat discipline)

- **Day zero:** "Your workforce is here. Connect a platform or describe your work to activate it." + chips (identity setup, platform connect, task creation). Triggers YARNNN rail expansion with seeded prompts.
- **No changes since last look:** "Quiet day. Last run was {agent} at {time} — {outcome}." + pointers. Never silent, never blank.

### 3. Route & navigation changes

- `HOME_ROUTE = "/overview"` in `web/lib/routes.ts`
- `ToggleBar` updates: replace Chat tab with Overview tab in position 1. Final nav: **Overview / Work / Agents / Context** (Team rename follows in ADR-201; no double-migration).
- `/chat` route preserved — now serves as the expanded form of the ambient rail. Renders `ChatSurface` as today; no change to that page. Reachable via direct URL or rail-expand affordance. Not listed in primary nav.
- Legacy routes `/orchestrator`, `/workfloor` continue their existing redirect-to-HOME behavior, now landing on `/overview`.

### 4. Relationship to YARNNN meta-awareness

Overview renders substrate for the **operator**; YARNNN's compact index (`format_compact_index()` in `api/services/working_memory.py`) renders substrate for **YARNNN**. Same substrate, two consumers — per FOUNDATIONS v6.0 Axiom 2 (Identity) + ADR-198 Invariant I3 (every surface has exactly one primary cognitive consumer). Not a conflict; the intended pattern.

**Substrate overlap (explicit):**

| Substrate | Compact index reads it as | Overview reads it as |
|---|---|---|
| `action_proposals` (pending) | Count + summary for YARNNN situational prompt | Queue pane with inline Approve/Reject affordances |
| Active tasks | Workforce health signal | Snapshot tile + Since-last-look row |
| `_performance_summary.md` | Future money-truth signal (not yet wired into compact index) | Snapshot book-headline tile |
| `decisions.md` | Not read | Since-last-look row (tail-parse) |

**Drift risk:** compact-index logic and Overview logic read overlapping substrate. Changes to one should audit the other. This is a known coupling — not hidden, not structural; just worth surfacing for future maintainers. Code comments in both files should cross-reference.

**Behavioral coordination (deferred, not blocking):** when the operator is on Overview with the ambient YARNNN rail open, YARNNN's situational prompt guidance should emphasize *helping the operator act on what they see* rather than *announcing what they already see*. This is a surface-aware prompt-profile tuning concern per ADR-186 (prompt profiles), not a structural ADR-199 concern. The pattern works today — YARNNN does not currently proactively re-announce state the operator is viewing — but as autonomy grows, explicit guidance in the `workspace` profile (or a new `overview` profile) may be warranted. Tracked for a follow-up ADR-186 revision if operator signal shows drift.

### 5. What this ADR does NOT change

- **Ambient rail implementation.** Already exists via `ThreePanelLayout`. Zero new work.
- **`/agents` → `/team` rename.** Deferred to ADR-201 (singular change, not coupled to Overview).
- **ProposalCard component.** Reused as-is.
- **Workspace file API.** Reused as-is (`/api/workspace/file?path=`).
- **Backend APIs.** No new endpoints. All Overview data is read from existing endpoints.

---

## Implementation plan

Single commit. No backend changes. Frontend only.

### Files created

- `web/app/(authenticated)/overview/page.tsx` — route entry, mirrors `/work`'s `ThreePanelLayout` pattern
- `web/components/overview/OverviewSurface.tsx` — composes three panes
- `web/components/overview/SinceLastLookPane.tsx` — Briefing archetype pane
- `web/components/overview/NeedsMePane.tsx` — Queue archetype pane (reuses ProposalCard)
- `web/components/overview/SnapshotPane.tsx` — Dashboard-snippet tiles with links
- `web/components/overview/OverviewEmptyState.tsx` — day-zero + quiet-day variants

### Files modified

- `web/lib/routes.ts` — `HOME_ROUTE = "/overview"`, `HOME_LABEL = "Overview"`, add `OVERVIEW_ROUTE`
- `web/components/shell/ToggleBar.tsx` — replace `{ id: 'chat', ..., href: '/chat' }` with `{ id: 'overview', label: 'Overview', icon: LayoutDashboard, href: '/overview' }` in position 1
- `web/components/shell/AuthenticatedLayout.tsx` (if redirect logic lives there) — ensure `/` redirects to `/overview`

### Files preserved unchanged

- `web/components/tp/ChatPanel.tsx` — the rail itself
- `web/components/chat-surface/ChatSurface.tsx` — the `/chat` expanded form
- `web/components/shell/ThreePanelLayout.tsx` — rail container
- All `/work`, `/agents`, `/context` page-level code

### API usage (existing endpoints only)

- `GET /api/proposals?status=pending&limit=<N>` — Needs me pane
- `GET /api/tasks` + `/api/agents` — Since last look + Snapshot workforce-headline
- `GET /api/workspace/file?path=/workspace/context/_performance_summary.md` — Snapshot book-headline
- `GET /api/workspace/file?path=/workspace/review/decisions.md` — Since last look reviewer decisions section (tail-parse for recent entries)
- `GET /api/integrations/summary` — Snapshot platform-connection state (if present; skip if absent)

### No new primitives, no new DB, no new services

Per FOUNDATIONS v6.0 Axiom 1 (filesystem is substrate), all Overview reads are file reads + existing ephemeral-queue reads. No DB schema change, no new API contract.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | **Helps** | Landing on Overview shows overnight orders + refund proposals + revenue snapshot inline. Replaces "open email, see summary, click into YARNNN, click into each proposal." |
| **Day trader** | **Helps** | Pre-market Overview shows P&L + pending bracket orders + risk alerts in one glance. Primary use case for cockpit. |
| **AI influencer** (scheduled) | Forward-helps | Overview surfaces content performance + pending campaign proposals. Same archetype mix. |
| **International trader** (scheduled) | Forward-helps | Overview surfaces overnight logistics + compliance alerts + counterparty state. |

No domain hurt. Gate passes.

---

## Implementation sequence (this ADR ships in one phase)

| Step | Description |
|------|-------------|
| 1 | Create route + surface component skeleton; verify `ThreePanelLayout` composition |
| 2 | Implement three panes reading from existing endpoints |
| 3 | Empty states |
| 4 | Update `routes.ts` + `ToggleBar` |
| 5 | Test flow: sign-in → lands on `/overview`; click ProposalCard inline; rail opens from any surface |
| 6 | Commit + push |

Single atomic commit. No dual nav state, no phased rollout — per singular-implementation discipline.

---

## Open questions (resolvable during implementation)

1. **Since-last-look boundary.** Default "since last login" vs "since 24h ago" vs user-preferred lookback? Leaning last-login with a simple override via URL param.
2. **Proposal count threshold for "See all N."** 3 inline + link for 4+? Or always link regardless of count? Leaning 3 inline, link for 4+.
3. **Platform connection alerts.** If `/api/integrations/summary` doesn't exist or returns no alert shape, Snapshot pane's third tile degrades gracefully. Verify at implementation.
4. **Mobile.** `ThreePanelLayout` already handles mobile (rail closes); Overview should work with no special handling. Verify at implementation.

---

## What this unblocks

- **ADR-200 (Review surface)** — Overview's Since-last-look pane links to `/review`; Review route needs to exist before those links are live. Ships next.
- **ADR-195 v2 Phase 4** — "daily-update briefing integration" was rejected as content-embedding per ADR-198; the correct form is Overview's Since-last-look pane reading from daily-update output + linking onward. This ADR delivers it.
- **Alpha onboarding** — day-zero empty state is the first thing a new operator sees. ADR-161's heartbeat artifact now has a cockpit twin.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial proposal. Narrower scope than ADR-198 originally estimated because ambient rail is already built via `ThreePanelLayout`. Single-commit frontend-only implementation reusing existing backend endpoints. |
