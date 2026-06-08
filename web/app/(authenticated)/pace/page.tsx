/**
 * /pace → /budget redirect stub (ADR-327).
 *
 * Pace retired — the surface is now /budget (the operation's dollar spend
 * envelope). This stub preserves bookmarks to /pace. Pure server transport
 * per ADR-308 — `redirect()`, never a client-side useEffect redirect (which
 * would paint an orphaned frame inside the OS shell).
 */

import { redirect } from 'next/navigation';

export default function PaceRedirect() {
  redirect('/budget');
}
