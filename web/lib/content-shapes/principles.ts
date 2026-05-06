/**
 * Reviewer principles content shape — `/workspace/review/principles.md`.
 *
 * Extracts operator-meaningful fields:
 *   - domains: per-domain thresholds and reject conditions
 *   - hasPrinciples: whether any domain is declared
 *
 * The file uses heading conventions from the alpha-trader bundle.
 * Domain sections are `## Domain: {name}` with sub-sections
 * `### Auto-approve threshold` and `### Reject conditions`.
 *
 * WRITE_CONTRACT is `configuration` — complex judgment framework,
 * Chat is the edit surface per ADR-235 D1.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'principles' as const;
export const PATH_GLOB = '**/review/principles.md';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'PrinciplesCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DomainPrinciples {
  name: string;
  /** Parsed auto_approve_below_cents value if declared. */
  autoApproveCents: number | null;
  /** Dollar string for display e.g. "$500". Null if not set. */
  autoApproveDisplay: string | null;
  /** Bullet items under ### Reject conditions. */
  rejectConditions: string[];
}

export interface PrinciplesData {
  domains: DomainPrinciples[];
  hasPrinciples: boolean;
  /** Raw body — preserved for full-text display when structured parse is insufficient. */
  raw: string;
}

// ---------------------------------------------------------------------------
// Pure parser
// ---------------------------------------------------------------------------

export function parse(content: string): PrinciplesData {
  const domains: DomainPrinciples[] = [];

  // Split into domain blocks: ## Domain: {name}
  const domainBlocks = content.split(/(?=^## Domain:\s)/im).filter(b => /^## Domain:\s/i.test(b.trim()));

  for (const block of domainBlocks) {
    const nameMatch = block.match(/^## Domain:\s+(.+)/im);
    if (!nameMatch) continue;
    const name = nameMatch[1].trim();

    // Auto-approve threshold — look for the backtick form first, then bare
    let autoApproveCents: number | null = null;
    const thresholdMatch = block.match(/auto_approve_below_cents:\s*(\d+)/i);
    if (thresholdMatch) {
      autoApproveCents = parseInt(thresholdMatch[1], 10);
    }

    const autoApproveDisplay = autoApproveCents !== null
      ? `$${(autoApproveCents / 100).toLocaleString()}`
      : null;

    // Reject conditions section
    const rejectSection = block.match(/###\s+Reject conditions?\s*\n([\s\S]*?)(?=###|\n##|$)/i);
    const rejectConditions = rejectSection
      ? rejectSection[1]
          .split('\n')
          .map(l => l.replace(/^[-*]\s+/, '').trim())
          .filter(l => l.length > 0 && !l.startsWith('#'))
      : [];

    domains.push({ name, autoApproveCents, autoApproveDisplay, rejectConditions });
  }

  return {
    domains,
    hasPrinciples: domains.length > 0,
    raw: content,
  };
}
