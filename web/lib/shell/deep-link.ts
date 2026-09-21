/**
 * The way back from the system browser (ADR-661 §8 step 4).
 *
 * §4.3 sends an OAuth consent screen to the member's own browser, which is
 * right — they already have their platform logins there, and a native window
 * with no address bar is a trap. But that handoff is ONE-WAY unless something
 * carries the result home: the member signs in, the browser holds the session,
 * and the app never hears about it. A shell without this can only use a
 * session that was already in its store, which is to say it can never be
 * signed into at all.
 *
 * The return leg is a custom scheme. `yarnnn://auth/callback?...` is
 * registered by the host (`tauri.conf.json` → `plugins.deep-link`), macOS
 * hands the URL to the running app, and `src-tauri/src/main.rs` forwards it to
 * this layer as a `deep-link` event rather than navigating the window — the
 * payload belongs to the Supabase client, not the router.
 *
 * WHY THE SCHEME AND NOT A LOCALHOST SERVER. A loopback listener is the other
 * common pattern, and it would mean the shell opens a port on the member's
 * machine for the lifetime of a sign-in. A scheme needs no port, no listener
 * and no firewall prompt, and it is what the OS is for.
 */

import { isNativeShell } from './external-navigation';

/** The scheme the host registers. One spelling, shared by the URL builder and
 *  the handler, so a rename cannot land in one and miss the other. */
export const SHELL_SCHEME = 'yarnnn';

/**
 * Where an OAuth provider should send the member back to.
 *
 * On the web this is the app's own origin — unchanged, and still what every
 * existing redirect does. In the shell it is the custom scheme, which is the
 * only address that reaches a running desktop app.
 *
 * ⚠️ **Both values must be on the Supabase project's Redirect URLs allowlist**
 * (`yarnnn://auth/callback` alongside the https ones), or the provider refuses
 * the redirect and the member lands on an error page they cannot act on.
 */
export function authCallbackUrl(nextPath: string): string {
  const next = `?next=${encodeURIComponent(nextPath)}`;
  if (isNativeShell()) return `${SHELL_SCHEME}://auth/callback${next}`;
  if (typeof window === 'undefined') return '';
  return `${window.location.origin}/auth/callback${next}`;
}

type Unlisten = () => void;

/**
 * Listen for the host's `deep-link` event.
 *
 * A no-op on the web, where there is no host and nothing to listen to — so the
 * caller mounts it unconditionally and the two builds keep one code path.
 *
 * The Tauri API is imported DYNAMICALLY: `@tauri-apps/api` does not exist in
 * the web bundle's dependency graph and must not be pulled into it. The import
 * is inside the shell branch, so bundlers keep it out of the web chunk and a
 * missing module can never break the web build.
 */
export async function onDeepLink(handler: (url: string) => void): Promise<Unlisten> {
  if (!isNativeShell()) return () => {};
  try {
    const { listen } = await import('@tauri-apps/api/event');
    const unlisten = await listen<string>('deep-link', (event) => {
      if (typeof event.payload === 'string') handler(event.payload);
    });
    return unlisten;
  } catch {
    // A shell build without the API present is a packaging bug, not a runtime
    // condition to recover from — but it must not take the window down with
    // it. The member sees a sign-in that does not complete, which is the
    // symptom that gets reported.
    return () => {};
  }
}
