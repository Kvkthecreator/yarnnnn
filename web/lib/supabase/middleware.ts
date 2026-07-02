import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";
import { NextResponse, type NextRequest } from "next/server";
import { isAdminEmail } from "@/lib/internal-access";
import { getCurrentPathWithSearch, getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";

// ADR-205 F1 + ADR-214 + ADR-259 cockpit nav + ADR-297 D17 boot model:
//   HOME_ROUTE = /desktop (ADR-297 D17, 2026-05-22). Pre-D17 was /feed.
//   Login boots to /desktop — the authenticated Desktop layer that restores
//   last-session windows (open-surfaces registry from D13) or shows the
//   empty-state welcome copy. Per-slug routes (/feed, /cadence, etc.) survive
//   as deep-link transports for direct surface mounting.
//
// Atomic surface slugs are also top-level URLs: /feed /home /recurrence
// /pace /autonomy /mandate /principles /identity /files
// /agents /program /queue /activity. Each is a protected route + a deep-link
// transport — cold-load opens that surface in a window. (/home renamed from
// /cockpit per ADR-312 D1; /recurrence renamed from /cadence 2026-06-03.)
// /delegation is a redirect stub → /autonomy (2026-05-24 surface rename).
// /chat is a redirect stub → /notifications?notifications.pane=understand
// (the narrative's home; 2026-07-02 ACTIVITY re-scope — preserves bookmarks).
// /overview was absorbed into the Home composition; ADR-225 Phase 3 +
// ADR-312 made the Home's slots compositor-resolved.
// /team redirects to /agents per ADR-214 (reverses ADR-201). /review is
// deleted; Reviewer lives at /agents?agent=freddie.
// /schedule is now a redirect stub → /work (ADR-243 folded into Work tabs).
// /connectors is a user-menu shortcut (same pattern as /workspace).
const PROTECTED_PREFIXES = [
  "/desktop", // ADR-297 §D17 — authenticated boot route
  "/setup", // ADR-331 — guided first-boot sequence surface (first-run redirect target)
  "/feed", // redirect stub → /notifications?notifications.pane=understand (the narrative's home; 2026-07-02 ACTIVITY re-scope)
  "/recurrence", // ADR-297 — absorbed /work (recurrence list + task detail); renamed from /cadence 2026-06-03
  "/cadence", // redirect stub → /recurrence (2026-06-03 — surface rename)
  "/agents",
  "/files",
  "/context", // redirect stub → /channels (ADR-385). Was a /files redirect stub (2026-06-01); reclaimed by ADR-370, renamed by ADR-385.
  "/activity",
  "/connectors",
  "/sources", // ADR-338 D4.1 — standing-watch drivers surface
  "/operation", // redirect stub → /mandate
  "/memory",
  "/system",
  "/settings",
  "/workspace-settings", // ADR-341 — the second Settings door (the operation)
  "/integrations",
  "/docs",
  // Legacy routes still protected for redirect stubs
  "/chat",       // ADR-259 — redirect stub → /feed
  "/backend",    // ADR-265 — redirect stub → /activity
  "/schedule",
  "/overview",
  "/team",
  "/workfloor",
  "/orchestrator",
];

function redirectToLogin(request: NextRequest) {
  const url = request.nextUrl.clone();
  const next = getCurrentPathWithSearch(request.nextUrl.pathname, request.nextUrl.search);
  url.pathname = "/auth/login";
  url.search = "";
  url.searchParams.set("next", next);
  return NextResponse.redirect(url);
}

export async function updateSession(request: NextRequest) {
  const response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const supabase = createMiddlewareClient({ req: request, res: response });

  // Refresh session if expired
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;

  // Protected routes - redirect to login if not authenticated
  const isProtectedRoute = PROTECTED_PREFIXES.some((prefix) => path.startsWith(prefix));
  const isAdminRoute = path.startsWith("/admin");
  const isAuthRoute = path.startsWith("/auth/login") || path.startsWith("/auth/signup");

  if (isProtectedRoute && !user) {
    return redirectToLogin(request);
  }

  // Admin routes - require auth + admin email
  if (isAdminRoute) {
    if (!user) {
      return redirectToLogin(request);
    }
    if (!isAdminEmail(user.email)) {
      // Redirect non-admins to home
      const url = request.nextUrl.clone();
      url.pathname = HOME_ROUTE;
      return NextResponse.redirect(url);
    }
  }

  // Redirect authenticated users away from auth pages
  if (isAuthRoute && user) {
    const nextParam = request.nextUrl.searchParams.get("next");
    const nextPath = getSafeNextPath(nextParam, HOME_ROUTE);
    return NextResponse.redirect(new URL(nextPath, request.url));
  }

  return response;
}
