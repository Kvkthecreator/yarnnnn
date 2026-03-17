import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function middleware(request: NextRequest) {
  const host = request.headers.get("host") || request.nextUrl.host;
  const pathname = request.nextUrl.pathname;

  // Redirect www → apex. HTTPS is enforced by the hosting platform (Vercel),
  // so we only need to handle the subdomain redirect here.
  if (host === "www.yarnnn.com") {
    const url = request.nextUrl.clone();
    url.protocol = "https:";
    url.host = "yarnnn.com";
    return NextResponse.redirect(url, 308);
  }

  // Legacy public auth entry point kept for backlinks/bookmarks.
  if (pathname === "/login") {
    const url = request.nextUrl.clone();
    url.pathname = "/auth/login";
    return NextResponse.redirect(url, 308);
  }

  // Removed pre-v5 routes should return a real gone response, not bounce through auth.
  const gonePrefixes = ["/baskets", "/blocks", "/projects", "/docs/integrations"];
  if (gonePrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    return new NextResponse("Gone", {
      status: 410,
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "x-robots-tag": "noindex, nofollow",
      },
    });
  }

  return await updateSession(request);
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
