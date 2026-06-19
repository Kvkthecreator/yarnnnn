/**
 * /operation → /notifications redirect stub (ADR-349 D2).
 *
 * The operating-work composition renamed operation → notifications (the
 * window and the topbar bell are one object at two zooms; they now share one
 * name). Pure server transport per ADR-308 — `redirect()`, never a
 * client-side useEffect redirect. Preserves any bookmarked /operation links.
 */

import { redirect } from 'next/navigation';

export default function OperationRedirect() {
  redirect('/notifications');
}
