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
