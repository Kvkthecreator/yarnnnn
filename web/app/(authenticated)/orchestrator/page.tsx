/**
 * Legacy /orchestrator route — redirects to HOME_ROUTE.
 *
 * Preserves query params so OAuth callbacks land home with the
 * newly-connected platform reflected in working memory.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(). searchParams
 * arrive as a server-component prop.
 */

import { redirect } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';

export default function OrchestratorRedirect({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const qs = new URLSearchParams(searchParams as Record<string, string>).toString();
  redirect(qs ? `${HOME_ROUTE}?${qs}` : HOME_ROUTE);
}
