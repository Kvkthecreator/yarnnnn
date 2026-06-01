/**
 * Legacy /team route — redirects to /agents (ADR-214). Reverses ADR-201 at
 * the URL level. Query params preserved.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(). searchParams
 * arrive as a server-component prop.
 */

import { redirect } from 'next/navigation';
import { AGENTS_ROUTE } from '@/lib/routes';

export default function TeamRedirect({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const qs = new URLSearchParams(searchParams as Record<string, string>).toString();
  redirect(qs ? `${AGENTS_ROUTE}?${qs}` : AGENTS_ROUTE);
}
