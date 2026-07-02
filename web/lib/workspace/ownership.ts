/**
 * File organize-reach — the operator's move/rename/trash authority, mirrored
 * from the backend (ADR-400 Amendment 1).
 *
 * It's the operator's filesystem. The human may move/rename/trash their WHOLE
 * workspace EXCEPT two carves — the SAME two the backend `operator_can_organize`
 * (api/services/workspace_paths.py) enforces:
 *
 *   1. system/ — runtime orchestration state, not hand-organized (the declared
 *      operator write-lock).
 *   2. _*.yaml / _*.json machine-config — code reads these at an EXACT path
 *      (the scheduler reads _budget.yaml, the gate reads _principles.yaml);
 *      renaming or moving one breaks the reader. A FILESYSTEM-INTEGRITY rule,
 *      NOT a permission hierarchy — the operator "owns" it, the machine depends
 *      on its location.
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
 * `operator_can_organize`. False only for system/ + _*.yaml/_*.json.
 */
export function operatorCanOrganize(path: string): boolean {
  let rel = path.replace(/^\/+/, '');
  if (rel.startsWith('workspace/')) rel = rel.slice('workspace/'.length);
  if (rel.startsWith('system/')) return false;
  const leaf = rel.split('/').pop() || '';
  if (leaf.startsWith('_') && MACHINE_CONFIG_EXTS.some((e) => leaf.toLowerCase().endsWith(e))) {
    return false;
  }
  return true;
}

/** The reason a file can't be organized — surfaced when the operator hits a
 * carve (system/ or machine-config). Honest, specific, Explorer-style. */
export function organizeBlockedReason(path: string): string {
  let rel = path.replace(/^\/+/, '');
  if (rel.startsWith('workspace/')) rel = rel.slice('workspace/'.length);
  if (rel.startsWith('system/')) {
    return 'This is system runtime state and can’t be moved, renamed, or trashed.';
  }
  return 'This is a machine-config file the system reads by name — renaming or moving it would break the reader.';
}
