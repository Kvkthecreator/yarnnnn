import { HOME_ROUTE } from "@/lib/routes";

const AUTH_PATH_PREFIX = "/auth/";

// The one `/auth/` page that is a destination rather than a step of the
// sign-in itself: the desktop app opens it, and it bounces a signed-out member
// through login with `?next=/auth/desktop` to come back and hand the session
// over (ADR-661 §7l). Refusing it sent every desktop sign-in to HOME_ROUTE in
// the browser, and the app never heard back. Exact match only — every other
// `/auth/` path stays refused, which is what prevents a login loop.
const AUTH_RETURN_TARGETS: ReadonlySet<string> = new Set(["/auth/desktop"]);

export function getSafeNextPath(next: string | null | undefined, fallback = HOME_ROUTE): string {
  if (!next) return fallback;

  if (!next.startsWith("/") || next.startsWith("//")) {
    return fallback;
  }

  if (next.startsWith(AUTH_PATH_PREFIX) && !AUTH_RETURN_TARGETS.has(next)) {
    return fallback;
  }

  return next;
}

export function getCurrentPathWithSearch(pathname: string, search: string): string {
  return `${pathname}${search || ""}`;
}
