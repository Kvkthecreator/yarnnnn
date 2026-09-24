import { NextResponse } from "next/server";
import { DESKTOP_UPDATE_MANIFEST } from "@/lib/shell/desktop-app";

/**
 * /download/latest.json — the address every desktop host asks for its update
 * (ADR-663 D6; `plugins.updater.endpoints` in src-tauri/tauri.conf.json).
 *
 * A redirect to the manifest the publish script writes, for the reason
 * `/download/{platform}` is one: the address is compiled into every installed
 * host, so it must be ours and outlive wherever the file lives. The updater
 * follows redirects, and verifies what it downloads against the public key
 * compiled into the host — the manifest's location is not what makes it
 * trusted. 302 and `force-dynamic`, as in `[platform]/route.ts`.
 */
export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.redirect(DESKTOP_UPDATE_MANIFEST, 302);
}
