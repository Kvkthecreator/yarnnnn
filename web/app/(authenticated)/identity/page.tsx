/**
 * /identity → /workspace-settings?pane=identity redirect stub.
 *
 * ADR-341 (2026-06-18): Identity (+ Brand, co-rendered) is a Constitution
 * pane inside Workspace Settings (read/manage via IdentityBrandCard full
 * variant). Its FIRST-CLASS door stays the Home constitution band
 * (ADR-312 D5). /brand also redirects here (sibling). Pure server
 * transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function IdentityRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=identity');
}
