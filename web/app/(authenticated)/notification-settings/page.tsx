/**
 * /notification-settings → User Settings → Notifications redirect stub
 * (ADR-593 D5, 2026-08-21). The Notifications settings pane is pane-grade on
 * the account door; this stub gives it a bookmarkable route, matching the
 * /billing pattern. Pure server transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function NotificationSettingsRedirect() {
  redirect('/settings?settings.pane=notification-settings');
}
