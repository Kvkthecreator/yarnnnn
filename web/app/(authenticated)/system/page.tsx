/**
 * Legacy /system route — redirects to /settings.
 *
 * System tab removed (2026-05-02): the only content was Scheduler Heartbeat,
 * already visible on the admin page.
 *
 * ADR-308 (2026-06-01): pure transport — server redirect().
 */

import { redirect } from 'next/navigation';

export default function SystemRedirect() {
  redirect('/settings');
}
