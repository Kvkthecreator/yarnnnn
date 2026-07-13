/**
 * File organize-reach — the operator's move/rename/trash authority, mirrored
 * from the backend (ADR-400 Amendment 1).
 *
 * It's the operator's filesystem. The human may move/rename/trash their WHOLE
 * workspace EXCEPT three carves — the SAME three the backend `operator_can_organize`
 * (api/services/workspace_paths.py) enforces:
 *
 *   1. system/ — runtime orchestration state, not hand-organized (the declared
 *      operator write-lock).
 *   2. _*.yaml / _*.json machine-config — code reads these at an EXACT path
 *      (the scheduler reads _budget.yaml, the gate reads _principles.yaml);
 *      renaming or moving one breaks the reader. A FILESYSTEM-INTEGRITY rule,
 *      NOT a permission hierarchy — the operator "owns" it, the machine depends
 *      on its location.
 *   3. inbound/ (EXCEPT inbound/uploads/) — the raw intake lane (ADR-376 / DP32):
 *      immutable attributed observations of what arrived from outside, retained
 *      and reasoned-against, NEVER rewritten. Moving/renaming/trashing a record
 *      of what came in is a category error. (Added ADR-422 D2 — the FE used to
 *      believe intake was organizable, disagreeing with the gate.) inbound/uploads/
 *      is the HUMAN raw lane (ADR-395 relocated uploads here) and STAYS
 *      organizable — the operator owns what they uploaded.
 *
 * Everything else — constitution/, persona/, operation/, uploads/, all prose —
 * is the operator's to reorganize (delete is reversible, so it's safe).
 *
 * The backend is authoritative (it 403s what it forbids). This mirror exists so
 * the FE can be OPTIMISTIC without being wrong: it does not defensively grey the
 * verbs — it lets the operator try, and surfaces the backend's honest error if
 * a rare carve is hit (the Windows-Explorer model). Keep this in lockstep with
 * `operator_can_organize`; drift only risks a stale label, never a wrong write.
 */

const MACHINE_CONFIG_EXTS = ['.yaml', '.yml', '.json'];

// The human upload sublane of inbound/ (ADR-395: uploads land at
// inbound/uploads/{principal}/{slug}.{ext}). Carved BACK OUT of the inbound/
// immutability rule — the operator owns what they uploaded (ADR-422 D2 invariant).
const INBOUND_UPLOADS_PREFIX = 'inbound/uploads/';

/**
 * True iff the operator may move/rename/trash `path` — mirrors the backend
 * `operator_can_organize`. False only for system/ + inbound/ (except
 * inbound/uploads/) + _*.yaml/_*.json.
 */
export function operatorCanOrganize(path: string): boolean {
  let rel = path.replace(/^\/+/, '');
  if (rel.startsWith('workspace/')) rel = rel.slice('workspace/'.length);
  if (rel.startsWith('system/')) return false;
  // ADR-422 D2 — immutable raw intake, EXCEPT the human upload lane (ADR-395).
  if (rel.startsWith('inbound/') && !rel.startsWith(INBOUND_UPLOADS_PREFIX)) return false;
  const leaf = rel.split('/').pop() || '';
  if (leaf.startsWith('_') && MACHINE_CONFIG_EXTS.some((e) => leaf.toLowerCase().endsWith(e))) {
    return false;
  }
  return true;
}

/** The reason a file can't be organized — surfaced when the operator hits a
 * carve (system/ or machine-config). macOS-plain: object-focused, no mechanism
 * jargon ("used by the system", not "read by name / would break the reader").
 * Returns a { title, body } pair for the styled confirm/alert dialog. */
export function organizeBlockedReason(path: string): { title: string; body: string } {
  let rel = path.replace(/^\/+/, '');
  if (rel.startsWith('workspace/')) rel = rel.slice('workspace/'.length);
  const leaf = rel.split('/').pop() || 'This item';
  if (rel.startsWith('system/')) {
    return {
      title: `“${leaf}” can’t be changed`,
      body: 'It’s used by the system to keep your workspace running. Moving, renaming, or deleting it isn’t allowed.',
    };
  }
  if (rel.startsWith('inbound/') && !rel.startsWith(INBOUND_UPLOADS_PREFIX)) {
    // ADR-422 D2 — raw intake: object-focused, macOS-plain (no DP32 jargon).
    // inbound/uploads/ is excluded — the human upload lane is organizable, so it
    // never reaches this blocked reason.
    return {
      title: `“${leaf}” is a record`,
      body: 'It’s a record of something that came into your workspace, kept exactly as it arrived. Records like this don’t change.',
    };
  }
  return {
    title: `“${leaf}” can’t be changed`,
    body: 'It’s a settings file the system needs in this exact place. Moving, renaming, or deleting it isn’t allowed.',
  };
}
