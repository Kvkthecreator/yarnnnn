/**
 * Reading a CAS conflict off the wire (ADR-572 D7).
 *
 * Pure and dependency-light on purpose: the gate transpiles and CALLS this
 * against the REAL 409 body captured from production, because the defect it
 * fixes was invisible to types, to `next build`, and to every source-level
 * check — a field read that yields `undefined` is not an error, and the
 * fallback string reads like intended copy.
 */

import { formatAuthorLabel } from '@/lib/workspace/attribution';

/** What a 409 tells the surface: who moved the head, and to what. */
export interface ConflictState {
  actor: string;
  currentHeadId: string | null;
}

/**
 * Read the current head out of a 409 body — from EITHER envelope.
 *
 * ADR-572 D7. The API serves the stale-write detail under
 * `error.hint.current_head`; FastAPI's older shape put it at
 * `detail.current_head`. This client read only the second, so on a real
 * conflict both fields came back undefined and the surface degraded twice
 * over: the banner said the generic "Someone else" instead of naming who
 * moved the head, and — worse — the **"Save mine over theirs" button
 * disappeared entirely**, because it is conditional on `currentHeadId`. The
 * member was left with one exit ("Discard mine") where the design promises
 * two.
 *
 * Found by driving a real 409 in production; every gate and `next build` were
 * green over it, because a field read that yields `undefined` is not a type
 * error and the fallback string reads like intended copy.
 *
 * Both shapes are accepted rather than the new one alone: the envelope is not
 * this component's to pin, and a reader that survives either cannot break
 * again on the next migration.
 */
export function readConflict(data: unknown): ConflictState {
  type Head = { id?: string; authored_by?: string };
  const d = data as {
    error?: { hint?: { current_head?: Head } };
    detail?: { current_head?: Head };
  } | null;
  const head = d?.error?.hint?.current_head ?? d?.detail?.current_head;
  return {
    actor: formatAuthorLabel(head?.authored_by ?? '') || 'Someone else',
    currentHeadId: head?.id ?? null,
  };
}
