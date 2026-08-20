/**
 * route-sync — the pathname→surface foreground decision (ADR-297 D13),
 * extracted pure so the cold-load contract is executable in a gate.
 *
 * THE RACE THIS SOLVES (recorded in the ADR-518 click-pass run 1, affecting
 * every content surface): AuthenticatedLayout's pathname-match effect used to
 * stamp `lastSyncedPathname` BEFORE looking for a match. On a cold bare-route
 * load (`/docs`, `/studio`, …) the effect runs first against the SEEDED
 * chrome-only composition — every route empty, nothing matches — but the
 * pathname was already stamped as synced, so when the real roster landed on
 * the same pathname the effect no-op'd and the shell kept the REMEMBERED
 * foreground surface instead of the one the URL named.
 *
 * The contract: a pathname is synced ONLY once it has resolved to a surface.
 * An unresolved pathname stays unsynced and re-resolves whenever the roster
 * changes; a pathname that matches nothing in a full roster resolves to null
 * every time (a cheap find — no loop risk, and no foreground call to re-fire).
 */

export interface RouteSurfaceEntry {
  slug: string;
  route: string;
}

/** The served roster is BEST-EFFORT at the program tier: the resolver
 *  guarantees only slug + title on a bundle-contributed row
 *  (composition_resolver._resolve_program_surfaces — bad entries are logged
 *  and skipped, not normalized). The FE type says `route: string`; the wire
 *  does not. A non-string route is a route-less row: it never matches and
 *  must never crash the sort. */
function routeOf(s: RouteSurfaceEntry): string {
  return typeof s.route === 'string' ? s.route : '';
}

/** Resolve which surface (if any) the pathname foregrounds. Longest-prefix
 *  wins; route-less entries (the seeded chrome-only composition, a program
 *  row that omitted its route) never match. */
export function resolveRouteSurface(
  pathname: string,
  surfaces: RouteSurfaceEntry[],
): string | null {
  const sorted = [...surfaces].sort((a, b) => routeOf(b).length - routeOf(a).length);
  const match = sorted.find((s) => {
    const route = routeOf(s);
    return route && (pathname === route || pathname.startsWith(route + '/'));
  });
  return match?.slug ?? null;
}

/**
 * Resolve the pathname the address bar should carry when `foregroundSlug`
 * becomes the foreground (2026-08-20). Extracted pure — same reason
 * `resolveRouteSurface` above is: this is a decision a gate must be able to
 * EXECUTE, not read.
 *
 * THE BUG THIS CLOSES (operator-observed, KVK 2026-08-20): `reconcileUrl`
 * rewrote only the query string and preserved `url.pathname` verbatim, per
 * ADR-297 D19.2 ("the Dock indicator dot is the canonical what's-foregrounded
 * signal, not the URL"). So a bare foreground — dock click, launcher, raising
 * a window by clicking its body — flipped the window while the address bar
 * kept naming the surface you left. That was survivable until the cold-load
 * sync (AuthenticatedLayout, 2026-08-05) made the pathname EXPLICIT INTENT
 * that outranks the remembered posture: refresh then re-foregrounded whatever
 * the stale pathname named. Every refresh landed on Settings — the last
 * surface reached by a param-bearing navigate. D19.2 is withdrawn: the two
 * rules cannot both hold, and a URL the reload trusts must be kept true.
 *
 * Two cases keep the current pathname:
 *   - the target has no usable route (a route-less roster row — the seeded
 *     chrome-only composition, or a program row that omitted its route). We
 *     never write an empty path.
 *   - the pathname is ALREADY under the target route (exact, or a deeper
 *     sub-path like `/files/sub`). The deeper path is more specific than the
 *     bare route; rewriting would discard it.
 */
export function resolveForegroundPathname(
  currentPathname: string,
  foregroundSlug: string,
  surfaces: RouteSurfaceEntry[],
): string {
  const target = routeOf(
    surfaces.find((s) => s.slug === foregroundSlug) ?? { slug: '', route: '' },
  );
  if (!target) return currentPathname;
  if (currentPathname === target) return currentPathname;
  if (currentPathname.startsWith(target + '/')) return currentPathname;
  return target;
}
