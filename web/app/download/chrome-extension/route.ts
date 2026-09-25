import { NextResponse } from "next/server";
import { EXTENSION_DOWNLOAD } from "@/lib/shell/desktop-app";

/**
 * /download/chrome-extension — the yarnnn extension's manual-install zip, until
 * the Chrome Web Store listing is approved (ADR-664 Amendment 2). Linked only
 * from Settings → Your browser, beside the three steps that install it.
 * A 302 and `force-dynamic`, as in `[platform]/route.ts`.
 */
export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.redirect(EXTENSION_DOWNLOAD, 302);
}
