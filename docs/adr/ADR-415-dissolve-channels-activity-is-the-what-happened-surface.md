# ADR-415 — Dissolve Channels: Activity is the one "what happened" surface; management goes to the management plane

**Status:** Proposed (doc-first, 2026-07-08)
**Supersedes the Channels-surface shape of:** ADR-385 (Channels — the perception + principal surface), ADR-404 D2 (capture-lane dormancy hiding Channels panes), ADR-370/377 (the Context boundary surface lineage this inherited)
**Preserves:** the underlying substrates (`platform_connections`, `_sources.yaml` watches, `principal_grants`, the emissions ledger `destination_delivery_log` + `notifications`) — **nothing is deleted, everything is re-homed.** ADR-373 grant-consult, ADR-299/304 (sends stay system infra), DP29 (mirror once, compose few).

---

## 1. The problem

The `channels` surface is a fossil of the **Feed → Context → Channels** lineage (ADR-259 → 370 → 377 → 385). Each rename narrowed it; ADR-404 hid two of its five panes behind the dormant capture-lane flag; the 2026-07-02 re-scope retired its Flow pane. In its **current launch state (capture lane dormant, the ratified default)** it renders exactly three panes:

- **AI Connections** — a role-grouped view of `principal_grants` (AI Chats / AI Agents). **This is a filtered duplicate** of the full Workspace-Members roster already mounted at Workspace Settings → Access.
- **In** — the chat narrative filtered to inbound writes (`isInbound` over `session_messages`). **Conceptually overlaps** Notifications → Activity, and reads a *weaker* source than Activity's three attributed ledgers.
- **Out** — the emissions ledger (`EmissionsView` over `GET /api/emissions`). **Genuinely unique** — the Activity timeline does not include emissions.

The surface no longer maps to one coherent operator act. It splits along a **boundary-vs-interior** axis ("what crossed the edge" vs "what happened inside") that operators do not hold in their heads — producing two places (Channels and Notifications → Activity) that both answer *"what happened,"* differing only by an edge distinction. That is the exact user-confusion the operator flagged.

### The scope axis (the operator's framing, and why it doesn't rescue Channels)

The only *principled* reason to keep two "what happened" surfaces would be a **scope** split:
- **user-specific** ("what should *I* be told" — like Slack notifications on a shared workspace), vs
- **shared-workspace-wide** ("the full attributed record, every actor").

That axis is real — but it is **already served, and not by Channels**:
- **Notifications → Activity** (the timeline) = the shared, every-actor, attributed record.
- **The top-bar bell popover** (`AttentionCenter`) = the user-specific, peer-first, since-you-last-looked slice.

Channels is scoped by **boundary**, not by user-vs-shared. It does not earn a place on the scope axis; it earns a weak place on a boundary axis the reframe has hollowed out. **Verdict: Channels is not first-class.** (The first-class test, per DP29 / ADR-340: a surface is first-class iff it maps to one distinct operator *act*. "See what happened at the edge" is not distinct from "see what happened"; "manage who/what connects" is a *management* act that belongs on the management plane, not as a peer of a read-ledger.)

---

## 2. Decision

**Dissolve the `channels` surface.** Split its content along the act each piece actually performs:

| Channels piece | The real act | New home |
|---|---|---|
| **Out** (emissions) | "what happened" — outbound | **→ Notifications → Activity**, as an **Out lens** |
| **In** (inbound crossings) | "what happened" — inbound | **retired** (subsumed by the Activity timeline, which already carries connector/tool writes as revisions) |
| **AI Connections** (principals) | "manage who can write" | **→ Workspace Settings → Access** (already mounts the full roster; the AI-only grouping is absorbed there) |
| **Connections** (`platform_connections`) | "manage what feeds the op" | **→ Workspace Settings** — a **Perception** group (restored as a management pane, NOT hidden behind a flag) |
| **Sources** (`_sources.yaml` watches) | "manage what feeds the op" | **→ Workspace Settings** — the same Perception group |

### D1 — Out becomes an Activity lens (In retired)

`ActivityLedger` gains a **direction lens** alongside its kind chips. The kind chips (All / File changes / Runs / Decisions) operate on the timeline. A new **Out** lens **swaps the body to `EmissionsView`** — because the emissions detail (channel · status · destination · did-it-land) is the whole value of Out and would be gutted if flattened into a revision-row grammar. So the surface reads: the timeline (with its kind chips) is the default/"interior" view; **Out** is a sibling lens showing the emissions ledger. **In is dropped** — inbound crossings already appear in the timeline as attributed revisions; the narrative-filtered In pane was the weakest-justified of the three.

**Rejected:** mapping emissions into unified timeline rows (loses delivery/status/destination detail — the point of Out). **Rejected:** merging AI Connections / Connectors *into Activity* (they are management acts, not "what happened" — that is the category error the dissolve exists to fix).

### D2 — Connectors + Sources restored to Workspace Settings (un-hidden)

ADR-385 D4 removed the Perception group from Workspace Settings and moved Connectors/Sources to Channels; ADR-404 then *hid* them behind `CONNECTOR_CAPTURE_ENABLED`. Both moves are reversed here: **Connections + Sources return to Workspace Settings as a first-class Perception group** — a management pane, always present (management of a peripheral is legible even when its capture lane is dormant; you can see/add/remove a connector without the capture drain running). This ends the "hide-and-defer" posture the operator rejected: the peripheral-management UI is either a real surface or it isn't — it is, so it lives in the management plane unconditionally.

> Note: the *capture lane* (the background drain that ingests connector/watch data) stays governed by `CONNECTOR_CAPTURE_ENABLED` — that flag is about **runtime ingestion**, not about **whether the management UI is visible**. Decoupling these is the point: managing a connector ≠ running its capture.

### D3 — AI Connections absorbed into Access

Workspace Settings → Access already mounts `WorkspaceMembersCard variant="full"` (the whole roster: owner, members, and every AI principal). The Channels AI-only role-grouping (AI Chats / AI Agents) is **absorbed** — Access is where "who can write the commons" is governed (narrow / revoke), so the AI principals are visible and governable there. The dedicated role-grouped framing is not a unique data path (one substrate, `principal_grants`); losing the AI-only *view* costs nothing the Access roster doesn't already carry. (If a curated AI-only sub-view proves wanted later, it is a filter chip on the Access roster, not a surface.)

### D4 — delete the surface + re-home the transport

- Delete the `channels` window from `kernel_surfaces.py` + the FE `SurfaceRegistry` + the `KernelSurfaceSlug` union.
- Re-point the redirect hub: `/context` and `/channels` → the appropriate new homes; `/connectors` and `/sources` → `workspace-settings?…pane=connectors|sources`.
- Reset `DEFAULT_KEPT_SURFACES` off `channels` (see §4).
- Normalize any persisted `kept`/`open`/`foregrounded` naming `channels`/`context`/`feed` at the surface-preferences read boundary (the ADR-385 `normalizeSlugList` pattern) so stale docks don't render a dead icon.

---

## 3. What this achieves

The operator's goal — "everything merges into Activity" — realized **correctly**:
- **Activity becomes the single "what happened" surface** (interior timeline + an Out/emissions lens). One answer to "what happened," at two scopes (shared = Activity, personal = the bell).
- The **management** pieces (connectors, sources, AI principals) land on the **management plane** (Workspace Settings), where they are *acts*, not fossils.
- No surface is left holding the incoherent boundary-vs-interior split. Nothing is force-fit into a read-ledger. Nothing is lost.

---

## 4. Blast radius (the re-home checklist)

Every coupling to `channels` that must move (verified against current code, 2026-07-08):

**Delete / rewrite:**
- `web/app/(authenticated)/channels/page.tsx` — DELETE (its bodies re-home: `EmissionsView` → ActivityLedger Out lens; `ConnectedIntegrationsSection` + `SourcesCard` → workspace-settings; `WorkspaceMembersCard` filtered view → dropped, Access keeps the full mount).
- `api/services/kernel_surfaces.py` — delete the `channels` window entry (lines ~280-314); re-home the `connectors` + `sources` pane entries from `pane_of: channels` → `pane_of: workspace-settings` (lines ~719-755); update `STEWARD_SURFACE_SLUGS` (drop `channels`).
- `web/components/notifications/ActivityLedger.tsx` — add the Out lens (mount `EmissionsView`).
- `web/app/(authenticated)/workspace-settings/page.tsx` — restore the Perception group (Connections · Sources), always-present.

**Redirects / defaults / normalization:**
- `web/next.config.js` — `/context` → new home; `/connectors` + `/sources` → `workspace-settings?workspace-settings.pane=connectors|sources` (or keep the stub pages, re-pointed).
- `web/app/(authenticated)/connectors/page.tsx` + `web/app/(authenticated)/sources/page.tsx` — re-point the `redirect()` targets.
- `web/lib/shell/surface-preferences.ts` — `DEFAULT_KEPT_SURFACES` off `channels` (**new default: `['home']`** — Home is the composition front page, the natural default pin; confirm with operator); extend `normalizeSlugList` to fold `channels`/`context`/`feed` → the new default (drop, not remap, since there's no successor surface).
- `web/components/shell/Desktop.tsx` — the `kept[0] === 'channels'` fresh-default check → `'home'`.
- `web/components/shell/chrome/ChatDrawer.tsx` — drop `channels` from the narrow-rail default list (`SUPERVISE_SURFACES`).
- `web/types/desk.ts` — remove `channels` from the `SurfaceSlug` union + default list.

**Stale call sites to fix (they currently `navigateToSurface('channels')` / link to it):**
- `web/app/(authenticated)/settings/page.tsx:302,323` — post-action nav → new home (connectors pane on settings).
- `web/components/settings/WorkspaceSection.tsx:141` — → settings connectors pane.
- `web/components/library/SetupSequence.tsx:187` — → settings connectors pane (setup connects a source).
- `web/components/work/RecurrenceList.tsx:508` — `SurfaceLink to="channels"` (already stale post-Flow-retirement) → Activity or settings, per its intent.
- `web/components/settings/ManageConnectionSubsurface.tsx:246` — the connector back-crumb `/channels?…` → `/workspace-settings?…`.

**Gates / tests:**
- `api/test_adr385_channels_surface.py` — rewrite/retire (asserts the Channels IA this ADR dissolves).
- `api/test_adr404_capture_dormancy.py` — update (Connectors/Sources no longer hide; the capture flag governs the drain only).
- New gate `api/test_adr415_channels_dissolved.py` — assert: no `channels` registry row; connectors/sources are `pane_of: workspace-settings`; Activity carries the Out lens; redirects re-homed.

---

## 5. Open decision for the operator (before code)

**The new default-kept dock surface.** Channels was the default pin (`DEFAULT_KEPT_SURFACES = ['channels']`, inherited from Feed). The natural successor is **Home** (`['home']`) — the composition front page. Confirm, or name another (Notifications? Files?).

---

## 6. Sequencing

Doc-first (this ADR) → operator sign-off → one implementation commit (it's cross-module but singular in intent; the re-home is mechanical once the shape is agreed). Full Render-parity check (kernel_surfaces is backend-driven nav — API + Scheduler read the same registry). `tsc --noEmit` + the new gate + rewritten ADR-385/404 gates green before commit.
