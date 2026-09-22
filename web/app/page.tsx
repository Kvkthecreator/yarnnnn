'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';

/**
 * The shell's root (ADR-661 §8 step 4).
 *
 * On the web `/` is the marketing landing page (`page.web.tsx`), which the
 * shell does not ship: a member who opened the app has already arrived, and a
 * pitch is what they came through, not what they came for.
 *
 * ⚠️ **This is a CLIENT redirect, and that is not a violation of ADR-308 — it
 * is the only thing that works here.** ADR-308 requires a stub to be pure
 * server transport, because a `'use client'` redirect paints one orphaned
 * frame inside the OS shell. That ruling is about the WEB build, which has a
 * server to do the redirecting.
 *
 * A static export has none. `redirect()` from `next/navigation` is a server
 * call, and Next exported this route as an ERROR PAGE (`id="__next_error__"`)
 * — which is exactly what the member saw: sign in successfully, land on a page
 * that looks like a logged-out start, and wonder why the app forgot them.
 * Found by reading the exported HTML after the operator reported it.
 *
 * The orphaned-frame cost ADR-308 names does not apply the same way: the shell
 * reaches this route only at cold boot, before any Desktop exists to be
 * orphaned, and `replace` keeps it out of history so no Back button returns to
 * it. The web build still uses the server redirect — `page.web.tsx` is
 * untouched.
 */
export default function ShellRoot() {
  const router = useRouter();

  useEffect(() => {
    router.replace(HOME_ROUTE);
  }, [router]);

  return null;
}
