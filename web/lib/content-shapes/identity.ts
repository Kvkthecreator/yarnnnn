/**
 * Identity content shape — `/workspace/context/_shared/IDENTITY.md`.
 *
 * Extracts the first substantive paragraph for display. Full prose
 * is operator-authored; no structured schema exists. The parser
 * extracts only what the L3 component needs to show state.
 *
 * WRITE_CONTRACT is `authored_prose` — Chat edits via InferContext.
 */

import type { ContentShapeMeta } from './index';

export const SHAPE_KEY = 'identity' as const;
export const PATH_GLOB = '**/_shared/IDENTITY.md';
export const WRITE_CONTRACT = 'authored_prose' as const;
export const CANONICAL_L3 = 'IdentityBrandCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

export interface IdentityData {
  /** First substantive prose line (not a heading or placeholder). */
  excerpt: string | null;
  isEmpty: boolean;
}

const PLACEHOLDER_RE = /operator:|author this|not yet|placeholder|_</i;

export function parse(content: string): IdentityData {
  const excerpt = content
    .split('\n')
    .map(l => l.trim())
    .find(l => l.length > 20 && !l.startsWith('#') && !l.startsWith('>') && !PLACEHOLDER_RE.test(l))
    ?? null;

  return { excerpt, isEmpty: !excerpt };
}
