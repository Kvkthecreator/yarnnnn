'use client';

/**
 * DeepLinkBridge — the desktop app's return leg from the system browser
 * (ADR-661 §8 step 4, §7i, §7k, §7p).
 *
 * The host registers `yarnnn://` and forwards an incoming URL as a `deep-link`
 * event (`src-tauri/src/main.rs`). Two shapes:
 *
 * - `yarnnn://auth/session?token_hash=…` — the website finished signing the
 *   member in and minted a ONE-TIME code for the app (§7r). Redeemed with
 *   `verifyOtp` for a session of the app's own — never the browser's refresh
 *   token, which made two holders of one session and signed both out. A
 *   failure lands on `/auth/login` with the reason in words (§7h).
 * - anything else — in-app navigation (`yarnnn://files?path=…` → `/files?…`).
 *
 * Mounted unconditionally at the ROOT (a member finishing sign-in is on
 * `/auth/login`, outside the authenticated group); `onDeepLink` is a no-op off
 * the desktop app, so both builds keep one code path.
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

      // `yarnnn://auth/session?token_hash=…` — the browser finished the
      // sign-in and minted a one-time code for this app (ADR-661 §7r). This is
      // the ONLY auth deep link: the app never talks to a provider.
      if (url.host === 'auth' && url.pathname.replace(/\/+$/, '') === '/session') {
        const tokenHash = url.searchParams.get('token_hash');
        if (!tokenHash) {
          router.replace('/auth/login?error=handoff&message=No+sign-in+was+handed+over');
          return;
        }
        // `verifyOtp` redeems the code for a NEW session — its own
        // refresh-token chain, so the browser refreshing its session can never
        // revoke this one. The session lands in the website's cookie like any
        // other sign-in.
        void createClient()
          .auth.verifyOtp({ token_hash: tokenHash, type: 'magiclink' })
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
