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

/**
 * Where an OAuth provider or an auth email sends the member back to: this
 * site's `/auth/callback`, carrying the resume target. The ONE builder — the
 * sign-in page and the MCP connect page used to spell it separately. There is
 * no desktop variant: the desktop app never receives a callback, it opens
 * `/auth/desktop` in the browser and is handed a session (ADR-661 §7i/§7p).
 */
export function authCallbackUrl(nextPath: string): string {
  if (typeof window === "undefined") return "";
  return `${window.location.origin}/auth/callback?next=${encodeURIComponent(nextPath)}`;
}

export function getCurrentPathWithSearch(pathname: string, search: string): string {
  return `${pathname}${search || ""}`;
}
