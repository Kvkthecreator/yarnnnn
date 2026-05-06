import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";
import { NextResponse, type NextRequest } from "next/server";
import { isAdminEmail } from "@/lib/internal-access";
import { getCurrentPathWithSearch, getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";

// ADR-205 F1 + ADR-214 cockpit nav: Chat | Work | Agents | Files + /workspace (user menu).
// HOME_ROUTE is /chat. /overview was absorbed into /work's cockpit zone
// (F2); ADR-225 Phase 3 made cockpit panes compositor-resolved. The
// /overview path itself is a redirect stub for old bookmarks.
// /team redirects to /agents per ADR-214 (reverses ADR-201). /review is
// deleted; Reviewer lives at /agents?agent=reviewer.
// /schedule is now a redirect stub → /work (ADR-243 folded into Work tabs).
// /connectors is a user-menu shortcut (same pattern as /workspace).
const PROTECTED_PREFIXES = [
  "/chat",
  "/work",
  "/agents",
  "/context",
  "/workspace",
  "/connectors",
  "/operation", // redirect stub → /workspace
  "/memory",
  "/system",
  "/settings",
  "/integrations",
  "/docs",
  // Legacy routes still protected for redirect stubs
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
