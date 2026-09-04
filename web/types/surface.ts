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
  | 'program'
  | 'queue'
  | 'notifications'  // ADR-346/349 — the operating-work composition (was 'operation')
  | 'settings'
  | 'workspace-settings'  // ADR-341 — the second Settings door (the operation)
  | 'connectors'  // ADR-425 — the account door's Connections pane (pane_of: settings)
  | 'notification-settings';  // ADR-593 D5 — the account door's Notifications pane (pane_of: settings)
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
  'chat', 'text', 'slides', 'blogger', 'images', 'billing', 'usage',
  'files', 'agents', 'queue', 'notifications',
  // ADR-425 D2: `sources` LEFT the allowlist (hidden, redirect-stub only).
  // ADR-454 D4: the system-agent slug LEFT too (door reversed; hidden row).
  // ADR-593 D5: `notification-settings` joins — the account door's
  // Notifications pane (pane-grade, search-only; /notification-settings stub).
  'settings', 'workspace-settings', 'connectors', 'notification-settings',
] as const;

export function isKernelSurfaceSlug(s: string): s is KernelSurfaceSlug {
  return (KERNEL_SURFACE_SLUGS as readonly string[]).includes(s);
}
