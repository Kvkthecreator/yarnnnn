'use client';

/**
 * AuthGate — the client half of the authentication gate (ADR-661 §8 step 1).
 *
 * `middleware.ts` (`updateSession`) is the gate on the web build and stays the
 * gate: it refreshes the session server-side and redirects before a byte of the
 * shell renders. This component is the SECOND half, for the build that has no
 * middleware — the packaged desktop shell (ADR-661 D1/D2) — and it is mounted
 * unconditionally so the two never diverge. On the web it is a fast no-op: the
 * session is already in the cookie the middleware just refreshed, so
 * `getSession()` resolves from local storage without a network round-trip and
 * the children paint on the same frame.
 *
 * WHY THIS EXISTS AS A GATE AND NOT A LISTENER.
 *
 * `AuthenticatedLayout` has carried an `onAuthStateChange` listener since the
 * 2026-08-20 repair, and its own docblock is emphatic that the listener is
 * "Live sign-out invalidation only — NOT an auth gate". That is exactly right:
 * a listener fires AFTER mount and paint. `lib/supabase/middleware.ts:30-43`
 * records what that costs when nothing else is gating — eight surfaces served a
 * full 200 to logged-out visitors, and the member "saw the surface flash and
 * then bounce to login". A shell with no middleware and only a listener would
 * reproduce that defect on every route, so this component resolves the session
 * BEFORE rendering children and renders nothing until it has.
 *
 * WHAT IT DELIBERATELY DOES NOT DO.
 *
 * It does not duplicate the middleware's route classification.
 * `PROTECTED_PREFIXES` there is derived from `KERNEL_SURFACE_SLUGS` precisely so
 * that "a surface is protected because it is a surface, not because someone
 * remembered to list it" — and this component sits INSIDE the authenticated
 * route group, so every route it wraps is protected by construction. Re-deriving
 * the prefix set here would be a second hand-kept list beside a derived truth,
 * which is the drift ADR-592 names. The admin gate likewise stays in the
 * middleware and in `AdminShell`: `/admin` is not in this group.
 *
 * It does not refresh the session itself. `supabase-js` owns that
 * (`autoRefreshToken`), and the listener below sees the result.
 */

import { useEffect, useState } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { getCurrentPathWithSearch } from '@/lib/auth/redirect';

type GateState = 'resolving' | 'allowed';

interface AuthGateProps {
  children: React.ReactNode;
  /** Rendered while the session resolves. Never a spinner-behind-a-spinner —
   *  the caller already owns a shell-shaped fallback. */
  fallback: React.ReactNode;
}

export function AuthGate({ children, fallback }: AuthGateProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [state, setState] = useState<GateState>('resolving');

  useEffect(() => {
    const supabase = createClient();
    let active = true;

    // `?next=` must carry the full address the member asked for, so the bounce
    // returns them where they were going — the same contract `redirectToLogin`
    // honours in the middleware.
    const bounce = () => {
      const search = searchParams.toString();
      const next = getCurrentPathWithSearch(pathname, search ? `?${search}` : '');
      router.replace(`/auth/login?next=${encodeURIComponent(next)}`);
    };

    // getSession(), not getUser(): the question here is "does this client hold
    // a session", which is local and synchronous-ish. getUser() round-trips to
    // the auth server to VALIDATE it, which is the middleware's job on the web
    // and the API's job on every request (every call carries the bearer token
    // and the API verifies it). Asking the network here would block first paint
    // on a check that is made again downstream — the redundant round-trip
    // AuthenticatedLayout's docblock says was removed on purpose.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!active) return;
      if (session) setState('allowed');
      else bounce();
    });

    // Live invalidation. A sign-out in another tab, or an expiry surfaced mid
    // session, bounces immediately rather than leaving a dead shell on screen.
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (!active) return;
      if (event === 'SIGNED_OUT' || !session) {
        setState('resolving');
        bounce();
      } else {
        setState('allowed');
      }
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [router, pathname, searchParams]);

  if (state === 'resolving') return <>{fallback}</>;
  return <>{children}</>;
}
