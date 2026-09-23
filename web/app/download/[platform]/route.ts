import { NextResponse } from "next/server";
import { DESKTOP_DOWNLOADS, isDesktopPlatform } from "@/lib/shell/desktop-app";

/**
 * /download/{mac|windows} — our own address for a desktop build, redirecting
 * to wherever the file lives now (our `desktop-releases` storage bucket;
 * lib/shell/desktop-app.ts says why every link goes through here).
 *
 * 302, not 308: the target is expected to move — to a signed build's store,
 * to a CDN — and a permanent redirect would be cached by browsers and
 * crawlers as the file's real address. `force-dynamic` for the reason
 * app/contact/page.tsx records: a prerendered redirect can reach a plain HTTP
 * client with no `location` header.
 */
export const dynamic = "force-dynamic";

export function GET(_request: Request, { params }: { params: { platform: string } }) {
  const target = isDesktopPlatform(params.platform) ? DESKTOP_DOWNLOADS[params.platform] : null;
  if (!target) {
    return new NextResponse("Not found", { status: 404 });
  }
  return NextResponse.redirect(target, 302);
}
