import { createMiddlewareClient } from "@supabase/auth-helpers-nextjs";
import { NextResponse, type NextRequest } from "next/server";
import { isAdminEmail } from "@/lib/internal-access";
import { getCurrentPathWithSearch, getSafeNextPath } from "@/lib/auth/redirect";
import { HOME_ROUTE } from "@/lib/routes";

// ADR-205 F1+F2 cockpit nav: Chat | Work | Files | Team | Review.
// HOME_ROUTE is /chat. /overview was absorbed into /work as a BriefingStrip
// (F2); the /overview path itself is a redirect stub for old bookmarks.
// /agents continues to be protected (redirect to /team per ADR-201).
const PROTECTED_PREFIXES = [
  "/chat",
  "/work",
  "/team",
  "/context",
  "/review",
  "/memory",
  "/system",
  "/settings",
  "/integrations",
  "/docs",
  // Legacy routes still protected for redirect stubs
  "/overview",
  "/agents",
  "/workfloor",
  "/orchestrator",
  "/tasks",
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
