# Cross-surface navigation + locator audit (2026-06-25)

**Trigger**: operator observation — "the launcher for agents surface to other
surfaces seem to not have consistent redirect and navigation handling … we may
need a breadcrumb consideration on the URL or another way to show navigation
better."

**Scope**: `web/` — how surfaces launch to other surfaces, and how an operator
knows *where they are* inside the OS-desktop shell.

This is a Hat-A (System Editor) frontend-coherence finding.

> **STATUS — RESOLVED (2026-06-25).** Both workstreams landed in the same
> session. (1) Verb sweep: ~30 cross-surface `<Link>`/`<a>`/`router.push` sites
> migrated to the new `<SurfaceLink to="slug">` (`components/shell/SurfaceLink.tsx`)
> + `navigateToSurface`; bare-param reads (`ReviewerDetail` tabs, Files
> `domain`/`path`, `FeedFilterBar` filters) migrated to `useSurfaceParam`.
> (2) Locator: `BreadcrumbContext` rebuilt as a **per-slug** `WindowCrumbContext`
> (the old global single-crumb was orphaned post-ADR-297-D19); `WindowFrame`
> title bar renders "Surface › Entity" with a back-to-list crumb; detail-mode
> surfaces (agents/recurrence/files) register via `useWindowCrumb(slug, …)`;
> mobile collapses the crumb to its leaf under 420px. Dead `PageHeader.tsx`
> deleted. (3) Ratchet: `api/test_nav_no_cross_surface_router_push.py` —
> zero-baseline guard that turns CI red on any new cross-surface hard-navigation.
> `tsc --noEmit` clean; nav + voice guards green. The inventory below is the
> as-found state.

---

## The canonical model (what code *should* do)

Defined in `web/lib/shell/useSurfacePreferences.tsx` (ADR-297 D19.5/D19.6 +
ADR-358 D5/D6). Two verbs, one rule: **navigation never leaves `/desktop`; the
compositor (window manager) owns it; params are window-namespaced.**

| Intent | Verb | Effect |
|---|---|---|
| **Cross-surface** (open/raise another window) | `navigateToSurface(slug, params?)` | foregrounds the target window, keeps pathname on `/desktop`, writes params as `{slug}.{key}` |
| **Intra-surface** (change what *this* window shows) | `useSurfaceParam(slug).set({...})` | `history.replaceState`, no pathname flip, params namespaced `{slug}.{key}` |

The page entries were migrated correctly — `agents/page.tsx`,
`recurrence/page.tsx`, `files/page.tsx`, `settings/page.tsx` all read their own
state via `useSurfaceParam('<slug>')`. **The drift is entirely in the child
components and a few cross-cutting call sites that still use the pre-OS-shell
patterns.**

---

## Finding 1 — cross-surface links bypass `navigateToSurface` (the user's report)

Raw `<Link href="/route?...">` / `<a href>` for cross-surface moves. Next
intercepts these as a real navigation → **pathname flips off `/desktop`** →
leaves the SPA, resets the docked chat, re-runs the shell's
pathname→foreground effects. This is exactly the "inconsistent redirect"
behaviour the operator felt: some launches foreground a window cleanly, others
hard-navigate.

The agents surface is the headline case:
- `components/agents/ReviewerActivityPanel.tsx:328,344` → `<Link href="/recurrence?…">`
- `components/agents/ReviewerCapabilitiesPanel.tsx:175,195` → `<Link href="/recurrence?task=…">`, `<Link href="/files?path=…">`
- `components/agents/AgentDashboard.tsx:110` → `<Link href="/files?domain=…">`
- `components/agents/AgentContentView.tsx:351,529,574,606` → `<Link href="/files?domain=…">` etc.

Same pattern elsewhere (full inventory — ~20 sites):
- `components/feed-surface/WorkspaceContextOverlay.tsx:350,357,364`
- `components/library/kernel-home/KernelDecisionQueue.tsx:90,100,122` (`/queue`)
- `components/library/kernel-home/KernelRecentArtifacts.tsx:90` (`/files`)
- `components/library/HomeRenderer.tsx:178` (`/setup`)
- `components/library/SetupSequence.tsx:201,398` (`/connectors`, `/program`)
- `components/library/HarvestPicker.tsx:192` (`/connectors`)
- `components/library/programs/alpha-trader/{TraderPortfolio,TraderOrders,TraderSignals,TraderRegime}.tsx`
- `components/work/RecurrenceList.tsx:506` (`/feed`)
- `components/settings/WorkspaceSection.tsx:269` (`/connectors`)
- `components/ui/DestinationSelector.tsx:227` (`/system`)

> Note: a `<Link href>` with an already-namespaced query (e.g.
> `WorkspaceContextOverlay.tsx:364` → `/recurrence?recurrence.pane=activity`)
> still produces the *correct URL* but via the *wrong verb* — it hard-navigates
> instead of foregrounding the window. The verb, not the URL string, is the bug.

**Correct reference sites** (do it right today): `AttentionCenter.tsx:242-244`,
`BudgetCard.tsx:320`, `WorkspaceSection.tsx:139`, `SetupSequence.tsx:184,236`,
`settings/page.tsx:298,318`.

## Finding 2 — `router.push/replace` to surface routes (intra-surface, wrong transport)

- `components/agents/AgentContentView.tsx:759` — Reviewer tab switch does
  `router.replace('/agents?tab=' + key)`. **Two bugs in one line**: (a) uses
  `router.replace` (real nav, pathname flip) instead of `useSurfaceParam`, and
  (b) writes the **bare** `tab=` key, not `agents.tab=` — so even the namespace
  is wrong. This is why the Reviewer Identity/Capabilities/Activity tabs feel
  different from switching agents in the same window (which *is* migrated).
- `components/feed-surface/FeedFilterBar.tsx:112,116,122` — filter state via
  `router.replace('/feed?…')` (bare keys).
- `app/(authenticated)/settings/page.tsx:116` — legacy `?tab=memory` →
  `router.replace('/files?path=…')` (acceptable as a one-shot legacy redirect,
  but should be `navigateToSurface('files', {path})`).

## Finding 3 — bare (un-namespaced) param reads/writes (ADR-358 D6 collision risk)

Reading flat `?key=` instead of `{slug}.key` means two open windows fight over
the same query key on the shared `/desktop` URL.

- `components/agents/AgentContentView.tsx:751` — `searchParams.get('tab')` (bare)
- `components/feed-surface/FeedFilterBar.tsx:55,56,57,82,86,89` — `weight`,
  `identity`, `task` (all bare)
- `app/(authenticated)/files/page.tsx:334,335` — `domain`, `path` (bare; the
  page reads these directly rather than via `useSurfaceParam('files')`)

Intentional non-surface params (leave alone): `?first_run=`, `?subscription=`
(OAuth/Stripe callbacks) — these are external-callback transport, not
intra-window state.

---

## Finding 4 — the locator gap ("show navigation better")

The operator's instinct is right and it's a *separate* problem from the verb
drift. When the surfaces became windows (ADR-297 D19), each page **deleted its
`setBreadcrumb()` call** (see the docblocks in `agents/page.tsx:8`,
`recurrence/page.tsx:142`, `files/page.tsx:510`). The intent was "the
WindowFrame title bar is the chrome now."

But the WindowFrame title is a **flat surface name** — `titleFor(slug)` reads
`composition.surfaces[].title` (`SurfaceViewport.tsx:129-132`). It says
"Agents", never "Agents › Reviewer › Activity". So:

- **`BreadcrumbContext` + `PageHeader` are now orphaned.** `BreadcrumbProvider`
  still wraps the tree (`AuthenticatedLayout.tsx:81`) but **no surface writes to
  it** — every `setBreadcrumb` call was deleted. `PageHeader` has zero live
  mounts. Dead infrastructure (Singular-Implementation violation — ADR §2).
- **The URL no longer encodes a human-legible position** by design (it stays
  `/desktop`, deep-link state lives in namespaced query params). So the URL bar
  can't serve as the locator either.

Net: inside a window, in detail mode (a specific agent / recurrence / file
open), there is **no breadcrumb and no in-title path** telling the operator
where they are or offering a one-click "back to the roster." That's the felt
gap.

### Options for the locator (pick one — see recommendation)

- **(L1) WindowFrame sub-title / breadcrumb slot.** Give `WindowFrame` an
  optional `subtitle`/`crumbs` prop; the foregrounded surface reports its
  in-window position via a small context (revive `BreadcrumbContext`, properly
  wired this time). Title bar reads "Agents › Reviewer". Most OS-idiomatic;
  fixes the orphan at the same time.
- **(L2) In-body `SurfaceIdentityHeader` with a back affordance.** `files`
  already renders `SurfaceIdentityHeader` in-body; extend the pattern to
  `agents`/`recurrence` detail modes with a "‹ All agents" crumb that calls
  `useSurfaceParam(slug).set({agent: null})`. Lighter; no chrome changes.
- **(L3) Namespaced deep-link in URL is the locator (status quo + polish).**
  Keep the URL as the source of truth but surface a readable crumb derived from
  it. Weakest — the operator explicitly said the current handling is unclear.

---

## Recommendation (sequence)

1. **Verb sweep (Findings 1–3)** — mechanical, high-confidence. Replace
   cross-surface `<Link>`/`router.push` with `navigateToSurface(slug, params)`;
   replace intra-surface `router.replace`/bare-`searchParams` with
   `useSurfaceParam(slug)`. ~42 sites; the agents surface is the priority since
   that's what the operator hit. A lint rule (ban `<Link href="/{surface}">` and
   `router.push('/{surface}')` in `components/`) prevents regression.
2. **Locator (Finding 4)** — adopt **L1**: add a breadcrumb/subtitle slot to
   `WindowFrame`, revive + properly wire `BreadcrumbContext` (or delete it and
   use a fresh per-surface context), and have detail-mode surfaces report
   "Surface › Entity". This both fixes the orphan and answers "show navigation
   better." A back-to-list crumb (L2) composes on top for free.

Findings 1–3 and 4 are independent — the verb sweep can land first without the
locator, and vice-versa.
