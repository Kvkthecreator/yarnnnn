# Intra-Surface URL Navigation Audit — Recurrence / Agents / Activity

**Date:** 2026-06-12
**Trigger:** Operator-observed (KVK) — clicking a file in the Files surface changed the
URL and disrupted the launcher/topbar. Files fixed in `541285a` (selection → component
state). Follow-up question: do the other URL-driven surfaces (Recurrence, Agents,
Activity) need the same evolved navigation method?
**Verdict:** **Yes — but the fix is NOT the Files fix.** These three surfaces use the URL
param as the *source of truth* for list↔detail mode (not redundant selection state like
Files), and many external cross-surface deep-links depend on the param being URL-readable.
The evolved method is a sanctioned **intra-surface param-update verb** that updates the
window-internal deep-link WITHOUT flipping the window-manager pathname baseline off
`/desktop`.

---

## 1. The canonical frame (ADR-297)

- **D19.2** — the URL is an *informational add-on*; the Dock dot is the canonical
  "what's foregrounded" signal. Bare cross-surface navigation leaves the URL as-is.
- **D19.4** — every surface inside the authenticated workspace is a *window* on the
  Desktop. Window-internal deep-link state (`?agent=X`, `?task=Y`) is "Figma-shaped, like
  `?node-id=X`" — intra-surface, not cross-surface navigation.
- **D19.5** — `navigateToSurface(slug, params?)` is the single sanctioned *cross-surface*
  navigation verb. With params it does `router.push(route?params)` so the target surface
  reads its deep-link state on land.

The boot route is `/desktop` (`HOME_ROUTE = /desktop`). The window manager treats
pathname `/desktop` as the baseline "I'm operating in window mode" signal. When pathname
leaves `/desktop` for a surface route (`/agents`, `/recurrence`, …), the shell's
`pathname → foreground` effect (`AuthenticatedLayout.tsx`) and `SurfaceViewport`'s
`pathnameSlug` resolution both treat it as a genuine navigation.

---

## 2. The two URL-usage shapes

| Surface | Param | Shape | Local fallback state? |
|---|---|---|---|
| **Files** | `?path=` `?domain=` | **Redundant** with `selectedPath` React state | YES (`selectedPath`) |
| **Recurrence** | `?task=` `?agent=` | **Source of truth** — list-vs-detail mode read from `searchParams` | NO |
| **Agents** | `?agent=` | **Source of truth** — list-vs-detail mode read from `searchParams` | NO |
| **Activity** | `?slug=` | **Source of truth** — run-list filter read from `searchParams` | NO |

Files was redundant → the fix was "drop the write, keep component state." The other three
have **no local state** — the URL *is* the state. Adding a parallel local state would
create a dual source of truth (URL vs state) and violate Singular Implementation.

---

## 3. Does the symptom reproduce on the three? (severity)

Yes, with a severity gradient. Tracing a click on `/desktop` with the surface open as a
window:

1. `router.push('/agents?agent=X')` → pathname `/desktop` → `/agents` (genuine change).
2. `AuthenticatedLayout` pathname→foreground effect fires, matches `/agents`,
   calls `foregroundSurface('agents')`.
3. Agents is already foreground (you clicked inside it) → re-foreground bumps z but is
   *visually* near-idempotent **on the surface itself.**

**The real disruption is downstream**: pathname is now stuck at `/agents`, not `/desktop`.
Subsequent Launcher / Dock / close actions branch on whether pathname matches a surface
route (`closeSurface`'s URL-sync; the deep-link resolution in `SurfaceViewport`). With the
pathname off-baseline, those behave as "navigated to /agents as a page" rather than
"Agents is one window among several on the Desktop." This is the same class as the Files
disruption — less immediately visible (foreground didn't visibly jump) but the same root
cause: **an intra-surface param update changed the window-manager pathname baseline.**

The existing code already carries scar tissue from this exact class — see the
`AuthenticatedLayout.tsx` 2026-06-01 "re-fire-loop fix" and the D18.2 close-race fix, both
operator-observed pathname/foreground collisions.

---

## 4. Why `navigateToSurface` is NOT the answer for the intra-surface case

`navigateToSurface(slug, params)` *also* does `router.push(route?params)` when params are
present. It was built for **cross-surface** navigation (open Files from Home with a path)
where the pathname flip is *correct* — you are genuinely changing which surface is
foreground. For an **intra-surface** param update (already in Agents, switch which agent),
the pathname flip away from `/desktop` is the same disruption.

**The architecture has a genuine gap:** there is no sanctioned verb for "update my own
surface's deep-link param without disrupting the window-manager pathname baseline."

---

## 5. External deep-links that MUST keep working

Removing the URL param entirely is not viable — many cross-surface entries link in by
param and read it on cold-load:

- `/recurrence?task=` — Home `KernelRecentArtifacts`, alpha-trader `TraderRegime`,
  `ReviewerCapabilitiesPanel`, Activity declaration-lens link, `/cadence` redirect.
- `/agents?agent=` — `IsometricRoom`, `ReviewerActivityPanel`, `HomeHeader`,
  `WorkspaceContextOverlay`, `/agents/[id]` + `/integrations/[provider]` redirect stubs.
- `/activity?slug=` — `ReviewerActivityPanel`, `RecurrenceList` "View runs".

So the param must remain **URL-readable on cold-load** (and on cross-surface
`navigateToSurface` entry). Only the **intra-surface self-update** should avoid the
pathname flip.

---

## 6. The evolved method (recommendation)

Add one sanctioned intra-surface verb to the window manager (`useSurfacePreferences`),
sibling to `navigateToSurface`:

```ts
/** Update the foregrounded surface's deep-link params WITHOUT a pathname
 *  flip. Writes the params under the CURRENT pathname via history.replaceState
 *  (or router.replace to the same surface route only when already on it).
 *  Never calls foregroundSurface; never changes the pathname baseline. The
 *  param is window-internal state, surfaced in the URL for shareability —
 *  not a navigation. (ADR-297 D19.2 corollary.) */
setSurfaceParams(params: Record<string, string | null>): void
```

Semantics:
- Writes/merges params onto the **current** URL via `window.history.replaceState` so
  pathname stays `/desktop` (or wherever) — **no pathname flip, no foreground effect,
  no Next router navigation event.**
- Surfaces keep reading `useSearchParams()` as their source of truth (no local state added
  → Singular Implementation preserved). The component re-renders on the searchParams
  change exactly as today.
- Cold-load + cross-surface `navigateToSurface(slug, params)` entries are **unchanged** —
  those legitimately land on the surface route and the param reads on mount.

Surfaces migrate their intra-surface `router.push/replace('/{slug}?param=X')` calls to
`setSurfaceParams({ param: X })`:
- Agents: 2 call sites (reviewer card, agent card).
- Recurrence: 3 call sites (select, clear-agent-filter, back-to-list).
- Activity: 1 call site (filter change).
- Files: already off the URL entirely (no migration; selection is component state).

### Why `history.replaceState` over `router.replace`
`router.replace('/agents?agent=X')` from `/desktop` still changes pathname → `/agents`
(the disruption). `window.history.replaceState(null, '', '/desktop?agent=X')` updates the
URL query under the *current* pathname with **no Next navigation event** — `useSearchParams`
still reflects it (Next reads `window.location.search`), but the pathname→foreground effect
and `SurfaceViewport` pathnameSlug logic never fire. This is the precise tool for
"window-internal state surfaced in the URL, not a navigation."

> **Propagation risk — RESOLVED by version (2026-06-12).** The repo runs **Next 14.2.0**,
> which natively patches `window.history.pushState`/`replaceState` (see
> `node_modules/next/dist/client/components/app-router.js` lines 405–436: "Patch
> replaceState to ensure external changes to the history are reflected in the Next.js
> Router"). A raw `window.history.replaceState(null, '', '/desktop?agent=X')` therefore (a)
> updates the URL with pathname unchanged, (b) syncs the Next router so `useSearchParams()`
> re-renders with the new param, and (c) fires NO navigation event — the pathname→foreground
> effect and `SurfaceViewport` pathnameSlug logic stay quiet. This is the official Next 14.1+
> mechanism for "update search params without a navigation." No fallback needed; no
> dual-source state.

---

## 7. Scope boundary

- **In scope:** the `setSurfaceParams` verb + migrating the 6 intra-surface call sites
  across Agents/Recurrence/Activity. Files needs no change.
- **Out of scope (separate, lower priority):** the ~15 external `href`/`navigateToSurface`
  cross-surface deep-links — they are *correct* as cross-surface navigation (pathname flip
  is intended when you genuinely move to that surface). The `settings/page.tsx?tab=memory`
  → `/files?path=` legacy redirect is also cross-surface; leave it.

---

## 8. Decision + outcome

**Operator chose (1): ship the `setSurfaceParams` verb + migrate.** Ratified as ADR-297
**D19.6** (2026-06-12, Implemented). The §6 propagation risk was resolved by version — Next
14.2 natively patches `history.replaceState` to sync the router. Enacted:

- `web/lib/shell/useSurfacePreferences.tsx`: `setSurfaceParams` verb (the third nav verb,
  sibling to `navigateToSurface`).
- Agents (2 sites), Recurrence (3 sites), Activity (1 site) migrated off `router.push/replace`.
- Files (`541285a`) already off the URL — no `setSurfaceParams` needed.
- Regression gate: `api/test_adr297_d196_intra_surface_nav.py`.

The three-verb model is now: `foregroundSurface` (bare cross-surface) · `navigateToSurface`
(cross-surface + deep-link, pathname flips) · `setSurfaceParams` (intra-surface deep-link,
pathname preserved).
