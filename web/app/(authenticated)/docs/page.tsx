/**
 * Legacy /docs index route — redirects to the Files surface.
 *
 * (The /docs/[id] public document viewer is a separate, operator-external
 * page and is unaffected — it stays outside the OS shell per ADR-297 D19.4.)
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(). Replaces the
 * prior client stub that rendered a "Redirecting to Context…" spinner frame
 * inside the OS shell (stale copy + orphaned-frame seam, both gone).
 */

import { redirect } from 'next/navigation';

export default function DocsIndexRedirect() {
  redirect('/files');
}
