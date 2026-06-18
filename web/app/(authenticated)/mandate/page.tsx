/**
 * /mandate → /workspace-settings?pane=mandate redirect stub.
 *
 * ADR-341 (2026-06-18): Mandate is a Constitution pane inside Workspace
 * Settings (read/manage via MandateCard full variant). Its FIRST-CLASS
 * door stays the Home constitution band (ADR-312 D5 — HomeHeader renders
 * the card directly, independent of this route). Pure server transport
 * per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function MandateRedirect() {
  redirect('/workspace-settings?pane=mandate');
}
