/**
 * Mandate content shape — `/workspace/context/_shared/MANDATE.md`.
 *
 * Extracts operator-meaningful fields from the markdown structure:
 *   - primaryAction: the ## Primary Action section body (one-sentence goal)
 *   - successCriteria: bullet items from ## Success Criteria
 *   - boundaryCount: number of items under ## Boundary Conditions
 *
 * The file uses markdown heading conventions established by the alpha-trader
 * bundle reference workspace. Parse is tolerant — missing sections return
 * null/empty rather than errors, so every workspace empty state degrades
 * gracefully.
 *
 * WRITE_CONTRACT is `authored_prose` — operators author via Chat
 * (WriteFile(scope='workspace') or InferContext per ADR-235 D1).
 * No serialize() needed — the file is prose, not structured config.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'mandate' as const;
export const PATH_GLOB = '**/_shared/MANDATE.md';
export const WRITE_CONTRACT = 'authored_prose' as const;
export const CANONICAL_L3 = 'MandateCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface MandateData {
  /** The prose under ## Primary Action. Null if section absent or placeholder. */
  primaryAction: string | null;
  /** Bullet items under ## Success Criteria. Empty array if section absent. */
  successCriteria: string[];
  /** Number of items under ## Boundary Conditions (0 if absent). */
  boundaryCount: number;
  /** True when the file has not been authored (still a skeleton). */
  isEmpty: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PLACEHOLDER_RE = /<not yet declared|_<not yet|placeholder/i;

function extractSection(content: string, heading: string): string {
  const re = new RegExp(`##\\s+${heading}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`, 'i');
  const m = content.match(re);
  return m ? m[1].trim() : '';
}

function extractBullets(sectionBody: string): string[] {
  return sectionBody
    .split('\n')
    .map(l => l.replace(/^[-*]\s+/, '').trim())
    .filter(l => l.length > 0 && !PLACEHOLDER_RE.test(l));
}

function countItems(sectionBody: string): number {
  return sectionBody
    .split('\n')
    .filter(l => /^[-*]\s+/.test(l))
    .length;
}

// ---------------------------------------------------------------------------
// Pure parser
// ---------------------------------------------------------------------------

export function parse(content: string): MandateData {
  const primarySection = extractSection(content, 'Primary Action');
  const criteriaSection = extractSection(content, 'Success Criteria');
  const boundarySection = extractSection(content, 'Boundary Conditions');

  const primaryRaw = primarySection
    .split('\n')
    .find(l => l.trim().length > 0 && !PLACEHOLDER_RE.test(l) && !l.startsWith('#'))
    ?.trim() ?? null;

  const successCriteria = extractBullets(criteriaSection);
  const boundaryCount = countItems(boundarySection);

  const isEmpty = !primaryRaw && successCriteria.length === 0 && boundaryCount === 0;

  return { primaryAction: primaryRaw ?? null, successCriteria, boundaryCount, isEmpty };
}
