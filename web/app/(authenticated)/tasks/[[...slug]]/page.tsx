'use client';

/**
 * Tasks → Work redirect.
 *
 * ADR-163: The top-level /tasks catchall is superseded by /work. Bookmarks
 * pointing at /tasks or /tasks/{slug} get preserved here. If a slug was
 * provided, it's forwarded to /work?task={slug} so deep-links land on the
 * right detail panel.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { WORK_ROUTE } from '@/lib/routes';

export default function TasksRedirect() {
  const router = useRouter();
  const params = useParams();
  const slug = params?.slug ? (params.slug as string[])[0] : null;

  useEffect(() => {
    const target = slug ? `${WORK_ROUTE}?task=${encodeURIComponent(slug)}` : WORK_ROUTE;
    router.replace(target);
  }, [router, slug]);

  return null;
}
