# ADR-200: Review Surface — Reviewer Identity + Principles + Decisions Chronicle

> **Status**: Proposed — implementation targeted this cycle
> **Date**: 2026-04-20
> **Authors**: KVK, Claude
> **Extends**: ADR-198 v2 (cockpit destinations), ADR-199 (Overview surface — ships first); FOUNDATIONS v6.0 Derived Principle 12 (Channel legibility gates autonomy)
> **Depends on**: ADR-194 v2 Phases 1 + 2a + 3 (Reviewer substrate shipped: IDENTITY.md, principles.md, decisions.md + reviewer_identity/reviewer_reasoning columns + AI Reviewer agent)
> **Implements**: Review destination — second of four cockpit surface phases (ADR-198 §Implementation)

---

## Context

ADR-199 shipped Overview with a Since-last-look row that links to `/review` for recent reviewer decisions. That link currently 404s — the destination doesn't exist yet. ADR-200 builds it.

### Substrate ready for consumption (backend handoff)

All Review-surface data lives in files already written by ADR-194 v2 Phases 1–3:

- `/workspace/review/IDENTITY.md` — Reviewer's one-line identity + scope + reasoning posture. Scaffolded at signup. Rarely edited.
- `/workspace/review/principles.md` — Operator-editable review framework (auto-approve thresholds, escalation rules, strictness posture). Edited via YARNNN rail, not inline forms.
- `/workspace/review/decisions.md` — Append-only log of every approve/reject/defer, with `reviewer_identity` tagging (`human:<uuid>` / `ai:reviewer-sonnet-v1` / `impersonated:<admin>-as-<persona>` / `reviewer-layer:observed`).

All three readable via the existing `/api/workspace/file?path=…` endpoint. No new backend endpoints needed.

### Why a dedicated Review destination

Per ADR-198 Invariant I3 (one primary cognitive consumer per surface) + Derived Principle 12 (Channel legibility gates autonomy):

- **The Reviewer's cognitive layer is distinct.** ADR-194 v2 establishes Reviewer as the fourth cognitive layer, distinguished by Purpose (independent judgment) + Trigger (reactive to proposals). Its audit trail deserves a dedicated surface where the operator can *supervise the supervisor*.
- **Autonomy requires visibility.** As AI Reviewer decisions accumulate (ADR-194 Phase 3 shipped), operators need a clear place to audit calibration. Burying decisions inside the generic Context file browser is Principle-12-non-compliant — the trust trail must be legible.
- **Impersonation chrome has a home.** When admins operate persona workspaces (ADR-194 Phase 2b), the impersonation banner and identity-tagged decisions need a surface that clearly distinguishes `human:` vs `ai:` vs `impersonated:` entries.

---

## Decision

### 1. `/review` route at destination priority 4 (nav position after ADR-201)

New route composed with `ThreePanelLayout` (no `leftPanel`; ambient YARNNN rail inherited). The center panel renders `ReviewSurface`, composing three archetype patterns per ADR-198 §3:

**Pane 1 — Reviewer card** (Dashboard archetype)
- Renders `/workspace/review/IDENTITY.md` as markdown
- Shows Reviewer's one-line identity + scope
- Static; changes are rare (IDENTITY.md is declarative, edited only through YARNNN rail)

**Pane 2 — Principles** (Dashboard archetype)
- Renders `/workspace/review/principles.md` as markdown
- Read-only surface; edits flow through YARNNN rail ("YARNNN, update my review principles to require a human reviewer for trades over $10k")
- "Edit principles" CTA opens the rail with a seeded prompt

**Pane 3 — Decisions log** (Stream archetype)
- Tail-parses `/workspace/review/decisions.md` for the N most recent entries (newest-at-top)
- Each entry shows: timestamp, reviewer identity tag, decision, brief reasoning, action type, proposal linkage
- Filter chips: **All** / **Human** / **AI** / **Impersonated** (query param `?identity=human|ai|impersonated`)
- Filter chips: **Approved** / **Rejected** / **Deferred** (query param `?decision=approve|reject|defer`)
- Infinite-scroll or "Load older" pagination — older entries stay in the file; surface pages through them on demand

### 2. ToggleBar update — add Review tab

Nav segments after this ADR (pre-ADR-201 rename): **Overview | Work | Files | Agents | Review**

Total: five tabs. ADR-201 will swap `Agents` label for `Team` without changing the tab count.

### 3. Impersonation chrome (ADR-194 v2 Phase 2b dependency)

When `workspaces.impersonation_persona` is set for the current workspace:

- Top banner on every surface (not just `/review`): "Impersonating: {persona} — acting as {admin}-as-{persona}"
- Review surface decisions-log filter adds `impersonated` chip with distinct visual treatment (e.g., amber outline)
- Individual `impersonated:` decision entries rendered with the amber treatment for visual distinction

ADR-194 Phase 2b's backend columns are ready. Phase 2c frontend-admin-impersonation is out of this ADR's scope — the banner renders when impersonation is active, but the admin's ability to *enter* persona workspaces requires the `/api/admin/impersonate/*` endpoints (backend's open phase).

### 4. Empty states

- **No decisions yet (new workspace):** "No reviewer decisions recorded yet. Decisions appear here when you approve/reject proposals."
- **Filter matches zero entries:** "No decisions match the current filter. Try a broader filter or check other identity tags."

### 5. What this ADR does NOT change

- `/workspace/review/*` files — read-only from this surface. Writes flow through existing primitives.
- `decisions.md` format — preserved as-is per ADR-194 v2 Phase 2a append convention.
- AI Reviewer agent (ADR-194 Phase 3) — orthogonal; this ADR surfaces its outputs but does not change its logic.
- Backend APIs — zero new endpoints. Reuses `/api/workspace/file?path=`.

---

## Implementation plan

Single commit. Frontend only. No backend changes.

### Files created

- `web/app/(authenticated)/review/page.tsx` — route entry with `ThreePanelLayout`
- `web/components/review/ReviewSurface.tsx` — composes three panes + impersonation banner
- `web/components/review/ReviewerCardPane.tsx` — Dashboard archetype: IDENTITY.md render
- `web/components/review/PrinciplesPane.tsx` — Dashboard archetype: principles.md render + edit CTA
- `web/components/review/DecisionsStreamPane.tsx` — Stream archetype: decisions.md tail-parse, filterable
- `web/components/review/ImpersonationBanner.tsx` — chrome banner when impersonating (used across surfaces via AuthenticatedLayout, but component lives here for scope locality)

### Files modified

- `web/components/shell/ToggleBar.tsx` — add Review segment at position 5
- `web/components/shell/AuthenticatedLayout.tsx` — render `ImpersonationBanner` above the main content when `workspaces.impersonation_persona` is set (needs workspace state read)

### API usage (existing endpoints only)

- `GET /api/workspace/file?path=/workspace/review/IDENTITY.md`
- `GET /api/workspace/file?path=/workspace/review/principles.md`
- `GET /api/workspace/file?path=/workspace/review/decisions.md`
- Possibly `GET /api/workspace/nav` to detect impersonation state (if `workspaces.impersonation_persona` surfaces through nav; otherwise add minimal endpoint in backend handoff)

### Impersonation state discovery

The backend session's handoff notes Migration 153 adds `workspaces.impersonation_persona`. Frontend needs a way to read that column. Options:

1. **Reuse workspace nav** if it already exposes workspace metadata (preferred — no new endpoint)
2. **Add tiny `/api/workspace/metadata` endpoint** (new, coordinate with backend)
3. **Parse from session JWT claims** (if workspace identity is in JWT)

Implementation will check (1) first; if absent, coordinate with backend for (2). Low complexity; not blocking.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | **Helps** | Audit past AI-Reviewer campaign approvals + discount approvals; understand whether the AI's EV reasoning matches operator's actual outcomes. |
| **Day trader** | **Helps** | Calibration is existential — audit AI Reviewer's trade-approval track record vs realized P&L. Filter by `ai:` tag to see only autonomous decisions. |
| **AI influencer** (scheduled) | Forward-helps | Brand-deal approval audit + publishing decision trail. Same surface, same pattern. |
| **International trader** (scheduled) | Forward-helps | Compliance decision audit — who approved which shipment / counterparty / tariff response. Regulatory-friendly. |

No domain hurt. Gate passes.

---

## Implementation sequence (this ADR ships in one phase)

| Step | Description |
|------|-------------|
| 1 | Create route + `ReviewSurface` component skeleton using `ThreePanelLayout` |
| 2 | Implement three panes reading from `/api/workspace/file` |
| 3 | Decisions stream parser + filter chips |
| 4 | Impersonation banner + workspace-metadata plumbing |
| 5 | ToggleBar add Review segment |
| 6 | Verify Overview's "See reviewer decisions" link now lands on populated surface |
| 7 | Commit + push |

Single atomic commit.

---

## Open questions (resolvable during implementation)

1. **Decisions pagination.** Load first 50 entries; "Load older" for the rest? Or infinite scroll? Leaning 50 + explicit "Load older" for legibility.
2. **Workspace metadata endpoint.** Prefer reuse of `/api/workspace/nav`; may need minor backend coordination if impersonation state isn't exposed.
3. **Decisions-log rich rendering.** Each entry has structured fields (timestamp, identity, decision, action_type, reasoning). Render as a table or as timeline cards? Cards feel right for the archetype (Stream = chronological) but table gives scannability. Leaning cards with optional "compact" toggle.
4. **Linking to referenced proposals.** Each decision references a `proposal_id`. Deep-link into the proposal detail? Proposal detail UI doesn't exist yet (ProposalCard is the current render surface). For now, show proposal summary inline; defer proposal-detail route to later if demand emerges.

---

## What this unblocks

- **Overview → Review linking is now live.** ADR-199's "See reviewer decisions" link lands on a real surface.
- **Principle 12 compliance for Reviewer layer.** Autonomous AI Reviewer decisions are now legible — calibration is auditable.
- **ADR-201 (Team rename + cross-linking).** ADR-200 ships before 201 because Review's nav slot is independent; 201 needs Review to exist for its final nav state.
- **ADR-194 Phase 4 (calibration tuning).** Needs an audit surface operators actually use. ADR-200 delivers it; calibration work becomes measurable.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial proposal. Reuses `/api/workspace/file?path=` for all reads; no new backend endpoints needed. Three panes (ReviewerCard Dashboard / Principles Dashboard / Decisions Stream). Impersonation banner component included in scope. Single-commit frontend phase. |
