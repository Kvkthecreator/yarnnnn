'use client';

/**
 * DeepLinkBridge — the shell's return leg from the system browser
 * (ADR-661 §8 step 4).
 *
 * The host registers `yarnnn://` and forwards an incoming URL as a `deep-link`
 * event (`src-tauri/src/main.rs`). This component turns that event into
 * ordinary in-app navigation.
 *
 * WHAT IT DELIBERATELY DOES NOT DO: parse a token, call `verifyOtp`, or touch
 * the Supabase client. `app/auth/callback` already handles every shape the
 * provider sends — PKCE `?code=`, a `token_hash` OTP in the query OR the hash
 * fragment, the recovery branch that stops to collect a new password, the
 * error branch, and the retry when a session is slow to materialise. That
 * logic was earned against production and must have exactly one home.
 *
 * So this bridge does the one thing the callback page cannot do for itself:
 * it converts `yarnnn://auth/callback?…` into `/auth/callback?…` and routes
 * there. Everything after that is the flow the web build already runs.
 *
 * Mounted unconditionally; `onDeepLink` is a no-op off the shell, so both
 * builds keep one code path (the same discipline as `AuthGate`).
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { onDeepLink, SHELL_SCHEME } from '@/lib/shell/deep-link';
import { createClient } from '@/lib/supabase/client';
import { HOME_ROUTE } from '@/lib/routes';

export function DeepLinkBridge() {
  const router = useRouter();

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    let active = true;

    void onDeepLink((raw) => {
      let url: URL;
      try {
        url = new URL(raw);
      } catch {
        return;
      }
      if (url.protocol.replace(':', '') !== SHELL_SCHEME) return;

      // `yarnnn://auth/session?refresh_token=…` — the browser finished the
      // sign-in and is handing the session over (ADR-661 §7i). This is the
      // ONLY auth deep link: the app never talks to a provider.
      if (url.host === 'auth' && url.pathname.replace(/\/+$/, '') === '/session') {
        const refreshToken = url.searchParams.get('refresh_token');
        if (!refreshToken) {
          router.replace('/auth/login?error=handoff&message=No+session+was+handed+over');
          return;
        }
        // `refreshSession`, NOT `setSession`. `setSession` requires BOTH
        // tokens — it throws `AuthSessionMissingError` on a falsy
        // `access_token` before it ever looks at the refresh token, so passing
        // an empty string failed with "Auth session missing!" (observed in a
        // real hand-off). `refreshSession({ refresh_token })` takes the
        // refresh token alone and mints a fresh session from it, which is
        // exactly what a hand-off carries: the browser holds the live session,
        // and the app is being given the means to establish its own.
        void createClient()
          .auth.refreshSession({ refresh_token: refreshToken })
          .then(({ error }) => {
            if (error) {
              router.replace(
                `/auth/login?error=handoff&message=${encodeURIComponent(error.message)}`,
              );
              return;
            }
            router.replace(HOME_ROUTE);
          });
        return;
      }

      // Any other deep link is ordinary navigation. `yarnnn://x/y?a=1` parses
      // with host="x" and pathname="/y", so the in-app path is host + pathname
      // — a custom scheme has no authority component the way https does, and
      // reading only `pathname` would drop the first segment.
      const path = `/${url.host}${url.pathname}`.replace(/\/+$/, '') || '/';
      router.replace(`${path}${url.search}${url.hash}`);
    }).then((fn) => {
      if (!active) {
        fn();
        return;
      }
      unlisten = fn;
    });

    return () => {
      active = false;
      unlisten?.();
    };
  }, [router]);

  return null;
}
