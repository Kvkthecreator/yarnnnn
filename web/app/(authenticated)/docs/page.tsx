/**
 * /docs → /text redirect stub (ADR-592).
 *
 * The Docs app is HIDDEN IN FULL (`stage: internal`, ADR-592). ADR-574 D2
 * declared it paused on 2026-08-17 and it stayed reachable — this is that
 * decision taking effect. The app's implementation is INTACT (it is Studio
 * parameterized, `StudioSurface app={DOCS_APP}`); only its exposure is gone,
 * so reopening is a stage flip plus restoring this route + its registry mount.
 *
 * Text is the destination per ADR-574 D1's prose premise: prose leads, and a
 * .md/.txt already opens there.
 *
 * This stub also keeps /docs AUTHENTICATED. Middleware derives its protected
 * set from the served roster, and `internal` removes the slug from it — a
 * route left rendering would serve 200 to logged-out visitors.
 *
 * Pure server transport per ADR-308 — `redirect()`, never a client-side
 * useEffect redirect (which would paint an orphaned frame inside the shell).
 */

import { redirect } from 'next/navigation';

export default function DocsRedirect() {
  redirect('/text');
}
