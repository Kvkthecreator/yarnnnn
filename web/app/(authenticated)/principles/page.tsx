/**
 * /principles → /workspace-settings?pane=principles redirect stub.
 *
 * ADR-341 (2026-06-18): Principles is a Constitution pane inside Workspace
 * Settings (read/manage via PrinciplesCard full variant). Its FIRST-CLASS
 * door stays the Home constitution band (ADR-312 D5). Pure server
 * transport per ADR-308.
 */

import { redirect } from 'next/navigation';

export default function PrinciplesRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=principles');
}
