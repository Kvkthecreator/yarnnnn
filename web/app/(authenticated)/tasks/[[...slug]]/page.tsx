'use client';

/**
 * Tasks redirect → Agents page.
 *
 * SURFACE-ARCHITECTURE.md v3: Tasks are now accessed through the agents
 * page as responsibilities under each agent. This redirect preserves
 * bookmarks and links while the tasks page is superseded.
 */

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';

export default function TasksRedirect() {
  const router = useRouter();
  const params = useParams();
  const slug = params?.slug ? (params.slug as string[])[0] : null;

  useEffect(() => {
    // Redirect to agents page. Task slug context is lost since tasks
    // are now children of agents — the user will need to find the task
    // through its agent.
    router.replace(HOME_ROUTE);
  }, [router]);

  return null;
}
