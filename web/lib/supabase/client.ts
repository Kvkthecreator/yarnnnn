import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";

/**
 * The browser Supabase client.
 *
 * `createClientComponentClient` persists the session as a cookie, which
 * `middleware.ts` reads and ROTATES server-side on every request. The desktop
 * app is the website in a native window (ADR-663 D1), so it holds the same
 * cookie session, refreshed by the same middleware — one client, one refresh
 * discipline. A hand-off from the browser (`DeepLinkBridge` →
 * `refreshSession`) lands in that cookie like any other sign-in.
 */
export function createClient() {
  return createClientComponentClient();
}
