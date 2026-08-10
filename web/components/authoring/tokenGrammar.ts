/**
 * tokenGrammar.ts — the token-admittance algebra (ADR-542 D2).
 *
 * A served token/measure row declares WHERE it mounts (`scope`: block | page
 * | document) and WHEN a scope admits it (`grains`: predicates, ANY of which
 * suffices; 'any' is unconditional). This is the ONE admitting function —
 * the pane's memos and the surface's span check are consumers, exactly as
 * scopeOf/arityOf are for selection (ADR-541 D2). The fifteen inline
 * `applies.includes(...)` sites this replaces were the leak ADR-525 §1.5
 * named ("a token literally cannot declare 'flow blocks only'") and the
 * defect ADR-536 shipped ("computed and never mounted").
 *
 * Deriving admittance anywhere else re-opens both. Move the derivation here.
 */

export type TokenScope = 'block' | 'page' | 'document';

export type TokenGrain =
  | 'any'
  | 'staged'
  /** ADR-544 D3 — an IMAGES artboard, never a deck slide. The narrower half of
   *  `staged`: free position (x/y/z) lives here since the containment law took
   *  it away from decks, while SIZE still admits `staged` (either frame). */
  | 'artboard'
  | 'flow'
  | 'media'
  | 'callout'
  | 'deck'
  | 'multicol'
  | 'bg';

/** The grain predicates, resolved by the caller from what it already knows
 *  (`.slide` ancestry, the served layout mode, the served media kinds, the
 *  arrangement's slot count, a cited background). Absent = false, so a memo
 *  only states the predicates its scope can even evaluate. */
export type GrainContext = Partial<Record<Exclude<TokenGrain, 'any'>, boolean>>;

export interface TokenGrammarRow {
  scope: string[];
  grains: string[];
}

export function admits(row: TokenGrammarRow, scope: TokenScope, ctx: GrainContext): boolean {
  if (!row.scope.includes(scope)) return false;
  return row.grains.some((g) => g === 'any' || ctx[g as keyof GrainContext] === true);
}
