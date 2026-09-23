/**
 * /contact — permanent redirect to /support.
 *
 * 2026-09-17: this route 404'd alongside /support. One canonical support
 * surface answers the required field; this is an alias people and listing
 * forms actually type. See app/support/page.tsx for the full why.
 *
 * ADR-308: pure server redirect, never 'use client' + useEffect.
 *
 * TWO details, both found by driving the route rather than reading it:
 *
 * 1. `permanentRedirect` (308), not `redirect` (307). These aliases are
 *    permanent, and 308 is what tells a crawler /support is the canonical
 *    URL so the alias does not compete with it in the index.
 *
 * 2. `force-dynamic` is LOAD-BEARING. Without it Next prerenders this stub
 *    as a static page and serves the redirect as a cached RSC payload —
 *    `x-nextjs-cache: HIT`, 307, and NO `location` header at all. A browser
 *    following a client-side navigation still lands on /support, so it looks
 *    fine in a click-pass, but a plain HTTP client (curl -L, a listing
 *    validator, a crawler) gets a redirect it cannot follow and sees the
 *    alias as broken. That is exactly the audience this page exists for.
 */

import { permanentRedirect } from 'next/navigation';

export const dynamic = 'force-dynamic';

export default function ContactRedirect() {
  permanentRedirect('/support');
}
