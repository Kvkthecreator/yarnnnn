/**
 * Legacy /feed route — redirects to the Context boundary surface's Flow lens
 * (ADR-370, 2026-06-25), preserving query params.
 *
 * The Feed dissolved into Context as its Flow lens (the complete narrative,
 * FeedSurface intact). `/feed` (and its deep-links — `?prompt=`, the
 * `/chat → /feed` / `/orchestrator → /feed` / `/workfloor → /feed` chain)
 * survives as a bookmark-safety stub → /context?context.pane=flow. Existing
 * query params (e.g. `?prompt=…` from InferenceContentView) are merged onto
 * the Flow target so chat-summon deep-links keep working.
 *
 * NOTE: the in-shell `feed` slug is NOT served by this route page — the
 * SurfaceRegistry maps `feed → ContextPage` (Flow default) so legacy deck
 * state that foregrounds `feed` mounts the live Context surface, never this
 * redirect (which would paint an orphaned frame — the ADR-308 anti-pattern).
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell. searchParams arrive as a server-component prop.
 */

import { redirect } from 'next/navigation';

export default function FeedRedirect({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const params = new URLSearchParams(searchParams as Record<string, string>);
  // Land on the Flow lens (the full narrative) unless a pane is already named.
  if (!params.has('context.pane')) params.set('context.pane', 'flow');
  redirect(`/context?${params.toString()}`);
}
