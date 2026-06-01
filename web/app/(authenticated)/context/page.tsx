/**
 * Legacy /context route — redirects to /files, preserving query params.
 *
 * 2026-06-01: the Files surface slug/route/label are now coherent at /files.
 * The old /context URL (and its ?path= / ?domain= / ?section= deep-links)
 * survive as a bookmark-safety stub. The substrate namespace
 * /workspace/context/… is unrelated (filesystem path, not a route URL).
 *
 * ADR-308 (2026-06-01): pure transport — server redirect(). searchParams
 * arrive as a server-component prop.
 */

import { redirect } from 'next/navigation';

export default function ContextRedirect({
  searchParams,
}: {
  searchParams: Record<string, string | string[] | undefined>;
}) {
  const qs = new URLSearchParams(searchParams as Record<string, string>).toString();
  redirect(qs ? `/files?${qs}` : '/files');
}
