/**
 * Brand content shape — `/workspace/context/_shared/BRAND.md`.
 *
 * Extracts the first voice/tone rule for display.
 * WRITE_CONTRACT is `authored_prose` — Chat edits via InferContext.
 */

import type { ContentShapeMeta } from './index';

export const SHAPE_KEY = 'brand' as const;
export const PATH_GLOB = '**/_shared/BRAND.md';
export const WRITE_CONTRACT = 'authored_prose' as const;
export const CANONICAL_L3 = 'IdentityBrandCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

export interface BrandData {
  /** First substantive prose line (voice/tone descriptor). */
  excerpt: string | null;
  isEmpty: boolean;
}

const PLACEHOLDER_RE = /author this|not yet|placeholder|_</i;

export function parse(content: string): BrandData {
  const excerpt = content
    .split('\n')
    .map(l => l.trim())
    .find(l => l.length > 10 && !l.startsWith('#') && !l.startsWith('>') && !PLACEHOLDER_RE.test(l))
    ?? null;

  return { excerpt, isEmpty: !excerpt };
}
