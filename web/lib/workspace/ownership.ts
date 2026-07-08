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
 *   3. inbound/ — the raw intake lane (ADR-376 / DP32): immutable attributed
 *      observations of what arrived from outside, retained and reasoned-against,
 *      NEVER rewritten. Moving/renaming/trashing a record of what came in is a
 *      category error. (Added ADR-422 D2 — the FE used to believe intake was
 *      organizable, disagreeing with the gate. uploads/ is the HUMAN raw lane
 *      and stays organizable — the operator owns what they uploaded.)
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

/**
 * True iff the operator may move/rename/trash `path` — mirrors the backend
 * `operator_can_organize`. False only for system/ + inbound/ + _*.yaml/_*.json.
 */
export function operatorCanOrganize(path: string): boolean {
  let rel = path.replace(/^\/+/, '');
  if (rel.startsWith('workspace/')) rel = rel.slice('workspace/'.length);
  if (rel.startsWith('system/')) return false;
  if (rel.startsWith('inbound/')) return false; // ADR-422 D2 — immutable raw intake
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
  if (rel.startsWith('inbound/')) {
    // ADR-422 D2 — raw intake: object-focused, macOS-plain (no DP32 jargon).
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
