/**
 * Legacy /chat route — redirects to the workspace narrative (the operator↔Freddie
 * conversation + every invocation). ADR-259 pointed it at /feed; ADR-385 folded
 * the Feed into Channels as the Flow pane. The 2026-07-02 ACTIVITY re-scope
 * RETIRED the Channels Flow pane — a Channels surface tracks only boundary
 * crossings (In/Out), not the global narrative. The narrative's real home is
 * Notifications → Activity (the `understand` pane), so /chat now lands there.
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
  if (!params.has('notifications.pane')) params.set('notifications.pane', 'understand');
  redirect(`/notifications?${params.toString()}`);
}
