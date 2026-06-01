/**
 * Legacy /workfloor route — redirects to HOME_ROUTE. Preserved for stale
 * bookmarks.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect().
 */

import { redirect } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';

export default function WorkfloorRedirect() {
  redirect(HOME_ROUTE);
}
