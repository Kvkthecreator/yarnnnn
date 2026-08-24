/**
 * /studio → /slides redirect stub (ADR-599 D4 — Studio's full evolve).
 *
 * Pure server transport (ADR-308): never 'use client' + useEffect. Query
 * params (e.g. ?file=…) are NOT carried — the shell's surface params are
 * window-internal state, and a stale deep link lands on the Slides surface
 * itself, which restores its own posture.
 */

import { redirect } from 'next/navigation';

export default function StudioRedirect() {
  redirect('/slides');
}
