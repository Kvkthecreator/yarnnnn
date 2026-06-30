/**
 * Legacy /chat route — redirects to the Channels surface's Flow pane (the
 * narrative). ADR-259 originally pointed it at /feed; ADR-385 folded the Feed
 * into Channels as the Flow pane, and the ADR-385 follow-on (2026-06-30) DELETED
 * the `/feed` page stub (full alias deletion). So `/chat` now redirects DIRECTLY
 * to /channels?channels.pane=flow — no double-hop through the retired /feed.
 *
 * Preserves query params so deep-linked operator bookmarks survive the
 * vocabulary migration.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(), never renders
 * inside the OS shell. searchParams arrive as a server-component prop.
 */

import { redirect } from 'next/navigation';

export default function ChatRedirect({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const params = new URLSearchParams(searchParams as Record<string, string>);
  if (!params.has('channels.pane')) params.set('channels.pane', 'flow');
  redirect(`/channels?${params.toString()}`);
}
