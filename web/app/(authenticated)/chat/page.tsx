/**
 * Legacy /chat route — redirects to /feed per ADR-259 (Feed Surface).
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
  const qs = new URLSearchParams(searchParams as Record<string, string>).toString();
  redirect(qs ? `/feed?${qs}` : '/feed');
}
