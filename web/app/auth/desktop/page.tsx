'use client';

/**
 * `/auth/desktop` — the browser finishes the sign-in and hands the session to
 * the app (ADR-661 §7i).
 *
 * It runs in the member's own BROWSER, and that is the whole point: the
 * desktop app does not authenticate, the website does. The app opens this URL
 * in the system browser and waits for a deep link.
 *
 * WHY THIS SHAPE. It is what Notion, Slack, Linear and Claude's own desktop
 * clients do, and it is the shape the failures argued us into. The previous
 * design had the browser start OAuth and the APP finish it, which split the
 * PKCE verifier across two contexts and a custom-scheme hand-off — three
 * rounds of debugging never got a session out of it. Here the browser both
 * starts and finishes: the verifier never leaves the context that created it,
 * and the app receives a session that is already established.
 *
 * It also collapses two auth implementations into one. `auth-helpers` on the
 * web is now the ONLY code that talks to a provider; the shell's client only
 * ever calls `refreshSession`. Every auth bug has one place to live.
 *
 * WHAT CROSSES THE BOUNDARY (ADR-661 §7r): a ONE-TIME sign-in code minted
 * for this member by the API (`POST /api/desktop/handoff`), which the app
 * redeems with `verifyOtp` for a session of its OWN. Never this browser's
 * refresh token: that made two holders of one session, and Supabase revokes a
 * whole session when a spent refresh token is presented again — so the first
 * time this browser refreshed after the hand-off (this very tab, left open,
 * does it within the hour) it signed the app out too. Measured on production:
 * every hand-off session ended with its newest token revoked and no successor;
 * the one session never handed off rotated hourly and lived.
 *
 * ⚠️ The code rides a URL, bounded three ways: the scheme hands it to a LOCAL
 * app rather than over a network, the OS routes it only to the registered
 * app, and it is single-use and short-lived.
 */

import { useEffect, useState } from 'react';
import { Suspense } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { api } from '@/lib/api/client';
import { Wordmark } from '@/components/shared/Wordmark';
import { Working } from '@/components/shared/Working';

type Phase = 'checking' | 'handing-off' | 'done' | 'signed-out' | 'failed';

function DesktopHandoffBody() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>('checking');

  useEffect(() => {
    const supabase = createClient();
    let active = true;

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!active) return;

      if (!session) {
        // Not signed in yet. Send them through the ordinary web sign-in and
        // come straight back here — the app is still waiting.
        setPhase('signed-out');
        router.replace(`/auth/login?next=${encodeURIComponent('/auth/desktop')}`);
        return;
      }

      setPhase('handing-off');
      api.desktop
        .handoff()
        .then(({ token_hash }) => {
          if (!active) return;
          // The app is listening for this scheme. `location.href` rather than
          // a link click: the member has already consented by opening the
          // app, and a second "do you want to open yarnnn?" step is friction
          // with no decision in it. The browser still asks its own
          // confirmation the first time, which is the OS's to ask, not ours.
          window.location.href = `yarnnn://auth/session?token_hash=${encodeURIComponent(token_hash)}`;
          setPhase('done');
        })
        .catch(() => active && setPhase('failed'));
    });

    return () => {
      active = false;
    };
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-6">
      <div className="text-center max-w-sm">
        <h1 className="mb-6"><Wordmark className="text-2xl" /></h1>
        {phase === 'failed' ? (
          <p className="text-sm text-muted-foreground">
            Couldn&rsquo;t sign the app in just now. Reload this page to try again.
          </p>
        ) : phase === 'done' ? (
          <>
            <p className="text-base">You&rsquo;re signed in.</p>
            <p className="mt-2 text-sm text-muted-foreground">
              yarnnn is open on your desktop — you can close this tab.
            </p>
          </>
        ) : (
          <Working label="Signing you in…" className="text-sm" />
        )}
      </div>
    </div>
  );
}

export default function DesktopHandoff() {
  // ADR-661 §7a — a page whose tree reads the query string needs its Suspense
  // boundary HERE, at the page. `useSearchParams` is not read directly any
  // more, but `useRouter` in a client page still opts this route into the
  // bailout under `output: export`, and the boundary costs nothing.
  return (
    <Suspense fallback={null}>
      <DesktopHandoffBody />
    </Suspense>
  );
}
