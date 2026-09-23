/**
 * The way back from the system browser (ADR-661 §8 step 4, §7i, §7p).
 *
 * The desktop app signs in by opening the website's `/auth/desktop` in the
 * member's own browser; the website authenticates and hands the session back
 * as `yarnnn://auth/session?refresh_token=…`. The host registers the scheme
 * (`tauri.conf.json` → `plugins.deep-link`), the OS hands the URL to the
 * running app, and `src-tauri/src/main.rs` forwards it here as a `deep-link`
 * event rather than navigating the window — the payload belongs to the
 * Supabase client (`DeepLinkBridge`), not the router.
 *
 * WHY THE SCHEME AND NOT A LOCALHOST SERVER. A loopback listener is the other
 * common pattern, and it would mean the app opens a port on the member's
 * machine for the lifetime of a sign-in. A scheme needs no port, no listener
 * and no firewall prompt, and it is what the OS is for.
 *
 * There is no `yarnnn://auth/callback`. It belonged to the superseded design in
 * which the app started OAuth itself (§7i, deleted in §7p): an email link or an
 * OAuth return can only complete in the context that began it.
 */

import { isNativeShell } from './external-navigation';

/** The scheme the host registers. One spelling, shared with the handler, so a
 *  rename cannot land in one place and miss the other. */
export const SHELL_SCHEME = 'yarnnn';

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
