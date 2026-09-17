/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-034: Context (emergent domains)
 *
 * Type definitions for the surface system (the steward-era transcript
 * types left with ADR-632)
 */

// =============================================================================
// Desk Surface Types
// =============================================================================

// ADR-297 axiom (2026-05-21): surface = viewport panel, not URL
// destination. KernelSurfaceSlug enumerates the 15 atomic surfaces
// declared by api/services/kernel_surfaces.py.
// ADR-309 (2026-06-01): `brand` slug DELETED — Brand is not a standalone
// surface; the Identity surface (IdentityBrandCard) owns Brand. /brand is
// a server redirect → /identity per ADR-308. Surfaces also carry a
// `register` (intent | os-config | application per ADR-309 + ADR-312 D5).
// D19.4 (2026-05-22): settings + connectors promoted from legacy
// pages to atomic kernel surfaces — reverses D19.7. Inside the
// authenticated workspace, every surface is a window.
// ADR-312 D1 (2026-06-02): `cockpit` slug renamed → `home`.
// 2026-06-03: `cadence` slug renamed → `recurrence` (substrate already
// spoke "recurrence"; only the surface label lagged). /cadence is a
// redirect stub.
export type KernelSurfaceSlug =
  // ADR-415 (2026-07-08): the `channels` slug is DELETED from the union (the
  // Channels surface dissolved — its content re-homed to Activity + Workspace
  // Settings). The legacy feed + context alias slugs were already deleted
  // (ADR-385 follow-on, 2026-06-30). Persisted dock state naming any of these
  // is normalized to the default by the surface-preferences read boundary, and
  // the old /channels + /context URLs are next.config.js server redirects.
  // (Keep this comment free of quoted-slug literals AND semicolons — the
  // ADR-297 parity gate parses the union up to the first semicolon and reads
  // quoted names.)
  | 'chat'  // ADR-412 D3 — the lanes surface; ADR-435 — the dock anchor (Home deleted)
  // ADR-599 — `docs` is DELETED with its app (the writing app's future is a
  // separate blogger-app arc); its slug left this union entirely.
  | 'slides'  // ADR-440 Studio → ADR-599 the full evolve: the dedicated deck app
  | 'blogger' // ADR-627 — the publish medium's desk (the outward type returns)
  | 'images'  // ADR-472 — the second authoring app (stages, rendered rasters)
  // ADR-639 (2026-09-04): the strings slug LEFT this union with its app — standing
  // work is a kernel lane, its roster a Notifications pane; the route is a
  // redirect stub hand-listed in middleware (the ADR-592 obligation).
  | 'text'    // ADR-571 — the prose app (md · txt), Editor beside the canvas
  // ADR-603 D5 (2026-08-24): `recurrence` + `activity` LEFT the union — the
  // window and its Runs lens are deleted (retire-clean, 0 live declarations);
  // both routes are redirect stubs into /notifications, hand-listed in
  // middleware (the ADR-592 obligation).
  // ADR-491 D3 (2026-07-28): `budget` LEFT the union — the Budget pane
  // dissolved (its numbers live on Workspace Settings → Usage; /budget is a
  // redirect stub; the kernel registry row is deleted). ADR-491 D1 launcher
  // catch-up: `billing` + `usage` join as pane-grade rows on the workspace
  // door (search-only — Spotlight finds the money surfaces again).
  | 'billing'
  | 'usage'
  // 2026-08-26: `autonomy` LEFT the union with the allowlist — it names a
  // redirect stub, not a surface (no KERNEL_SURFACES row).
  // ADR-348 added the Expected-Output pane. ADR-418 (2026-07-08) made it DORMANT
  // (routeless, off this allowlist) — the output contract is a HIRED agent's
  // concern with no constitution-band door, so its slug leaves the navigable set
  // until the per-agent contract FE (ADR-382 / ADR-414 §9b). The registry row
  // survives backend-side (services/kernel_surfaces.py) so the concept persists.
  // (Slug intentionally NOT written as a quoted literal here — the parity gate
  // reads quoted names from this union up to the first semicolon.)
  //
  // ADR-421 (2026-07-08): the mandate / principles / identity slugs are REMOVED
  // from the union too — a workspace has no constitution of its own (ADR-414 D6);
  // those are per-agent concepts surfaced on the agent detail. The registry rows
  // survive backend-side (dormant) so flat search knows them; they leave the FE
  // navigable set. (Slugs not quoted in this comment for the same parity reason.)
  // ADR-437 (2026-07-10): the `setup` slug is REMOVED from the union — the
  // guided first-boot wizard is deleted (genesis is empty, ADR-414; activation
  // reframes to cold-landing + the shared-artifact wedge). The registry row
  // survives backend-side (dormant) for flat search; /setup → /chat stub.
  // (Slug intentionally not written as a quoted literal here — the parity gate
  // reads quoted names from this union up to the first semicolon.)
  | 'files'
  | 'agents'
  // ADR-642 (2026-09-07): the queue slug LEFT this union — the surface is
  // ABSORBED by Reach (its body mounts on the Leaving pane, filtered to the
  // boundary families, and on Notifications → To do unfiltered). Its route
  // is a redirect stub into that pane, hand-listed in middleware (the
  // ADR-592 obligation). Slug not quoted here — the parity gate reads
  // quoted names from this union up to the first semicolon.
  | 'reach'  // ADR-642 — the boundary's door: connected · leaving · crossed
  | 'notifications'  // ADR-346/349 — the operating-work composition (was 'operation')
  | 'settings'
  | 'workspace-settings'  // ADR-341 — the second Settings door (the operation)
  | 'notification-settings';  // ADR-593 D5 — the account door's Notifications pane (pane_of: settings)
  // ADR-645 D3 (2026-09-08): `connectors` LEFT this union — the pane retired to
  // Reach → Connected and its registry row went `stage: internal`, so it no
  // longer reaches the served roster. It stayed here until 2026-09-17, which
  // made it a PHANTOM: `isKernelSurfaceSlug('connectors')` was true, so
  // `Launcher.navigate` foregrounded it (Launcher.tsx) and `SurfaceViewport`
  // resolved no component and rendered null — an empty window. Same treatment
  // as `sources` (ADR-425 D2) and `system-agent` (ADR-454 D4) before it: a
  // retired slug leaves the union WITH the roster. /connectors remains a
  // redirect stub, hand-listed in middleware.ts.
  // ADR-454 D4 (2026-07-13): the ADR-426 system-agent slug LEFT the navigable
  // allowlist — the door is reversed (the ambient steward); the registry row is
  // `hidden` (hide-not-delete), the dials re-home pane_of → workspace-settings
  // ("System" group), and /system-agent is an ADR-308 redirect stub. (Slug
  // intentionally not written as a quoted literal here — the parity gate reads
  // the union up to the first semicolon.)
  // ADR-425 D2 (2026-07-09): the `sources` slug LEFT the navigable allowlist — it
  // is `hidden` (no operator door; a bookmark-safe /sources → /home redirect stub
  // only). The backend row is retained (hide-not-delete) for a future first-class
  // home (ADR-425 OQ3); it is simply not a navigable FE surface. (Slug intentionally
  // not written as a quoted literal here — the parity gate reads the union up to
  // the first semicolon.)

export const KERNEL_SURFACE_SLUGS: readonly KernelSurfaceSlug[] = [
  // ADR-418 removed the Expected-Output slug (dormant). ADR-421 (2026-07-08)
  // removes mandate / principles / identity too — a workspace has no
  // constitution of its own (ADR-414 D6). ADR-432 D2d (2026-07-09) removes
  // `program` — the operator-facing hire pane is retired; the slug goes dormant
  // (routeless, backend-only, like the constitution surfaces). ADR-437
  // (2026-07-10) removes `setup` — the guided first-boot wizard is deleted
  // (genesis is empty, ADR-414; activation reframes to cold-landing + the
  // shared-artifact wedge). All are dormant registry rows; the three-way parity
  // (navigable == allowlist == registry∪panes) holds with them out of all three.
  // ADR-491 D3: `budget` LEFT (pane dissolved into Usage; slug retired).
  // ADR-491 D1: `billing` + `usage` join (pane-grade on the workspace door).
  // ADR-518: `docs` joins — the writing app, carved from Studio.
  // ADR-603 D5: `recurrence` + `activity` LEFT (window + Runs lens deleted).
  // 2026-08-26: `autonomy` LEFT this list. It is a redirect stub (→
  // /workspace-settings) with NO row in KERNEL_SURFACES, so it was a phantom
  // slug driving SURFACE_PREFIXES — protecting its route by accident rather
  // than by declaration. It is hand-listed in middleware's stub block, where
  // every other row-less stub lives.
  // ADR-642: `queue` LEFT (absorbed by Reach; /queue is a stub into its
  // Leaving pane, hand-listed in middleware); `reach` joins.
  'chat', 'text', 'slides', 'blogger', 'images', 'billing', 'usage',
  'files', 'agents', 'reach', 'notifications',
  // ADR-425 D2: `sources` LEFT the allowlist (hidden, redirect-stub only).
  // ADR-454 D4: the system-agent slug LEFT too (door reversed; hidden row).
  // ADR-593 D5: `notification-settings` joins — the account door's
  // Notifications pane (pane-grade, search-only; /notification-settings stub).
  // ADR-645 D3: `connectors` LEFT (retired to Reach; redirect-stub only).
  'settings', 'workspace-settings', 'notification-settings',
] as const;

export function isKernelSurfaceSlug(s: string): s is KernelSurfaceSlug {
  return (KERNEL_SURFACE_SLUGS as readonly string[]).includes(s);
}

// ===========================================================================
// ADR-653 D3.c — member apps, the second kind of openable surface
// ===========================================================================

/**
 * A MEMBER APP's slug (ADR-653 D1). Nominally a string, and that is the whole
 * point: an app is AUTHORED, so its slug cannot live in a compile-time union.
 *
 * ⭐ WHY `KernelSurfaceSlug` IS NOT WIDENED, and must never be. That union is
 * one leg of the ADR-338 three-way lockstep (backend navigable == FE allowlist
 * == component registry), and the gate's whole job is to fail when a kernel
 * surface exists in two of the three. Admitting an open-ended string would
 * make the parity vacuously true and retire the gate without a ruling — the
 * `LIBRARY_COMPONENTS` death (ADR-653 §1.3), repeated.
 *
 * So member apps are a SECOND kind, resolved at runtime against the served
 * roster, and the kernel's three-way parity is untouched.
 */
export type AppSurfaceSlug = string;

/** The one route namespace member apps live under (ADR-653 D3.c). */
export const APP_ROUTE_PREFIX = '/apps';

/**
 * Is this surface a member app's? The ONE predicate — every gate reads it.
 *
 * ⚠️ `register === 'composition'` is the test, NOT the tier and NOT the route.
 * The register is the field ADR-653 D3.a promoted precisely so a surface could
 * say *"my shape is DECLARED, not mirrored"*, and `is_composition()` on the
 * server is its counterpart. Matching on the route would make a string a
 * capability; matching on the register makes the server's own classification
 * the authority.
 */
export function isAppSurface(s: { register?: string } | undefined | null): boolean {
  return !!s && s.register === 'composition';
}

/**
 * Every member-app slug the server is CURRENTLY serving.
 *
 * ⭐⭐⭐ THE ROSTER IS THE AUTHORITY, and this is the whole safety property of
 * the FE half. The backend withholds any declaration with a `problem`
 * (`_resolve_member_app_surfaces`), so a slug that reaches here is one the
 * server has already decided can be drawn. A client that instead trusted the
 * URL, or a persisted window state, could foreground an app that does not
 * exist and render an empty window — which is exactly the `connectors`
 * phantom (ADR-653 §10.1), arriving from the other direction.
 *
 * Degrades CLOSED: no roster, no openable apps.
 */
export function appSurfaceSlugs(
  surfaces: ReadonlyArray<{ slug: string; register?: string }> | undefined | null,
): Set<string> {
  const out = new Set<string>();
  for (const s of surfaces ?? []) {
    if (isAppSurface(s) && s.slug) out.add(s.slug);
  }
  return out;
}

/**
 * May this slug be foregrounded — is it a kernel surface OR a served app?
 *
 * The predicate the five `isKernelSurfaceSlug` gates widen to. It takes the
 * roster explicitly rather than reading a module-level cache, so a caller
 * cannot accidentally ask the question without the evidence to answer it.
 */
export function isOpenableSurfaceSlug(
  slug: string,
  appSlugs: ReadonlySet<string>,
): boolean {
  return isKernelSurfaceSlug(slug) || appSlugs.has(slug);
}

/** An app's route, from its slug. The single spelling (ADR-653 D3.c). */
export function appRoute(slug: string): string {
  return `${APP_ROUTE_PREFIX}/${slug}`;
}

/**
 * The app slug in a pathname, or null. `/apps/photos` → `photos`.
 *
 * ⚠️ Shape only — it does NOT assert the app exists. The caller checks it
 * against the served roster, for the reason `appSurfaceSlugs` records.
 */
export function appSlugFromPath(pathname: string): string | null {
  const parts = (pathname || '').split('/').filter(Boolean);
  if (parts.length < 2 || `/${parts[0]}` !== APP_ROUTE_PREFIX) return null;
  return parts[1] || null;
}
