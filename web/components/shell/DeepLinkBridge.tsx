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

      // `yarnnn://auth/callback?x=1#y=2` parses with host="auth" and
      // pathname="/callback", so the in-app path is host + pathname rather
      // than pathname alone — a custom scheme has no authority component the
      // way https does, and reading only `pathname` would drop "auth".
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
