'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

/**
 * Legacy /context route — redirects to /files, preserving query params.
 *
 * 2026-06-01: the Files surface slug is `files`; route, slug, and label are
 * now coherent at /files. The old /context URL (and its ?path= / ?domain= /
 * ?section= deep-links) survive as a bookmark-safety stub.
 *
 * Note: the substrate namespace `/workspace/context/…` is unrelated — it's
 * the filesystem path, not a route URL, and was never touched by the rename.
 *
 * See web/lib/routes.ts for the redirect-stub policy.
 */
export default function ContextRedirect() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const qs = searchParams.toString();
    router.replace(qs ? `/files?${qs}` : '/files');
  }, [router, searchParams]);

  return null;
}
