/**
 * Legacy /context route — redirects to the Channels surface (ADR-385,
 * 2026-06-29), preserving query params.
 *
 * The `context` surface was renamed `channels` (the word "context" is
 * ambiguous with the filesystem [Files surface] and the operation/context/
 * substrate namespace). `/context` (and its deep-links — `?context.pane=…`,
 * `?prompt=…`) survives as a bookmark-safety stub → /channels. Existing
 * `context.pane` params are remapped to `channels.pane`; everything else is
 * merged through.
 *
 * NOTE: the in-shell `context` slug is NOT served by this route page — the
 * SurfaceRegistry maps `context → ChannelsPage` (Flow default) so legacy deck
 * state that foregrounds `context` mounts the live Channels surface, never this
 * redirect (which would paint an orphaned frame — the ADR-308 anti-pattern).
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell. searchParams arrive as a server-component prop.
 */

import { redirect } from 'next/navigation';

export default function ContextRedirect({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const params = new URLSearchParams(searchParams as Record<string, string>);
  // Remap the legacy window-namespaced param: context.pane → channels.pane.
  const pane = params.get('context.pane');
  if (pane !== null) {
    params.delete('context.pane');
    params.set('channels.pane', pane);
  }
  const qs = params.toString();
  redirect(qs ? `/channels?${qs}` : '/channels');
}
