/**
 * Reviewer principles content shape — `/workspace/review/principles.md`.
 *
 * NEW shape entry added by ADR-245 Phase 2 (parser stub). The auto-approval
 * threshold parser lives server-side today (`api/services/review_principles.py`
 * per ADR-194 v2 Phase 3); the FE consumer (PrinciplesTab per ADR-241)
 * renders the raw markdown via `WorkspaceFileView`. ADR-245 Phase 4 will
 * land the FE parser alongside the threshold-editor L3 affordance — at
 * that point this file gains a populated `parse()` body. Phase 2 ships the
 * registry entry only so the shape's WRITE_CONTRACT and canonical L3 are
 * declared on the same axis as the parsers that already exist.
 *
 * Per ADR-245 D5 the WRITE_CONTRACT is `configuration` — operator authors
 * thresholds + framework via the canonical L3 (PrinciplesTab) which will
 * route mutations through `WriteFile(scope='workspace', path='review/principles.md', ...)`
 * per ADR-235 D1.b.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'principles' as const;
export const PATH_GLOB = '**/review/principles.md';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'PrinciplesTab' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Types — provisional; populated alongside Phase 4 threshold-editor work
// ---------------------------------------------------------------------------

export interface PrinciplesData {
  /** Raw markdown body — preserved when no structured parser is present. */
  raw: string;
}

// ---------------------------------------------------------------------------
// Pure parser — Phase 2 stub (returns the raw body wrapped)
// ---------------------------------------------------------------------------

export function parse(content: string): PrinciplesData {
  return { raw: content };
}
