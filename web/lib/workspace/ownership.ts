/**
 * File ownership — the two-principal topology, made a single FE source of truth
 * (ADR-400).
 *
 * The filesystem has two actor-classes (ADR-373 multi-principal commons): the
 * OPERATOR (the human — owns their uploaded material) and the AGENTS (Freddie +
 * program agents — author, edit, and own everything they write). ADR-320 makes
 * this a pure prefix topology; ADR-400 surfaces it: the operator may move/rename/
 * trash ONLY operator-owned files, and system-owned files show their affordances
 * disabled WITH A REASON (never hidden — legibility over concealment, the GitHub
 * "you don't have write access to this path" model).
 *
 * These prefixes mirror the backend `_OPERATOR_ARCHIVABLE_PREFIXES`
 * (api/routes/documents.py). Keep them in lockstep — the backend is the gate,
 * this is the surface that must not offer a verb the gate will 403.
 */

/** Roots the OPERATOR owns — movable, renamable, trashable, restorable. */
export const OPERATOR_OWNED_PREFIXES = [
  '/workspace/uploads/',          // legacy pre-ADR-395 uploads
  '/workspace/inbound/uploads/',  // ADR-395 upload raw lane
] as const;

/** True iff the human owns this file (may move/rename/trash/restore it). */
export function isOperatorOwned(path: string): boolean {
  return OPERATOR_OWNED_PREFIXES.some((prefix) => path.startsWith(prefix));
}

/** The reason an operator verb is unavailable on a system-owned file — shown as
 * a disabled tooltip / caption (the two-principal division made legible). */
export const SYSTEM_OWNED_REASON = 'Managed by Freddie — edit through chat';

/**
 * The file's owning principal class, for the ownership badge (ADR-400 D6).
 * 'you' = operator-owned material; 'agent' = system/agent-authored substrate.
 * (The finer WHO-authored-it attribution — Freddie / ChatGPT-via-MCP / … — comes
 * from the ADR-388 attribution module keyed on authored_by; this is the coarser
 * WHO-OWNS-THE-VERBS class the topology defines.)
 */
export function ownerClass(path: string): 'you' | 'agent' {
  return isOperatorOwned(path) ? 'you' : 'agent';
}
