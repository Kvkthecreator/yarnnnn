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

/** Resolve which surface (if any) the pathname foregrounds. Longest-prefix
 *  wins; route-less entries (the seeded chrome-only composition) never match. */
export function resolveRouteSurface(
  pathname: string,
  surfaces: RouteSurfaceEntry[],
): string | null {
  const sorted = [...surfaces].sort((a, b) => b.route.length - a.route.length);
  const match = sorted.find(
    (s) => s.route && (pathname === s.route || pathname.startsWith(s.route + '/')),
  );
  return match?.slug ?? null;
}
