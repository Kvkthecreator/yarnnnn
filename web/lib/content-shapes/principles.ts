/**
 * Reviewer principles content shape.
 *
 * ADR-254 (file format discipline): machine-parsed thresholds live in
 * `_principles.yaml`; reject conditions and narrative remain in `principles.md`.
 * Two-file merge: parseYaml() reads _principles.yaml thresholds, parse() reads
 * principles.md reject conditions, mergeThresholds() combines them.
 *
 * WRITE_CONTRACT is `configuration` — complex judgment framework,
 * Chat is the edit surface per ADR-235 D1.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'principles' as const;
export const PATH_GLOB = '**/persona/principles.md';
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

// ---------------------------------------------------------------------------
// _principles.yaml parser (ADR-254)
// ---------------------------------------------------------------------------
//
// Structure: per-domain YAML keys with auto_approve_below_cents.
// Example:
//   trading:
//     auto_approve_below_cents: 20000
//
// Strips tier frontmatter block (--- tier: authored ... ---) before parsing.

export interface YamlThresholds {
  /** Map of domain name → auto_approve_below_cents */
  domains: Record<string, number | null>;
}

export function parseYaml(content: string): YamlThresholds {
  const result: YamlThresholds = { domains: {} };
  // Strip tier frontmatter block
  const stripped = content.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '');
  let currentDomain: string | null = null;
  for (const line of stripped.split('\n')) {
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;
    // Top-level domain key (no leading spaces, ends with colon)
    const domainMatch = line.match(/^([a-z_]+):\s*$/);
    if (domainMatch) {
      currentDomain = domainMatch[1];
      result.domains[currentDomain] = null;
      continue;
    }
    // Threshold field under a domain
    if (currentDomain) {
      const thresholdMatch = line.match(/^\s+auto_approve_below_cents:\s*(\d+)/);
      if (thresholdMatch) {
        result.domains[currentDomain] = parseInt(thresholdMatch[1], 10);
      }
    }
  }
  return result;
}

/**
 * Merge yaml thresholds into prose-parsed domains.
 * Yaml threshold wins over anything extracted from the prose
 * (thresholds are now canonical in _principles.yaml per ADR-254).
 * Domains only in yaml get added with empty reject conditions.
 */
export function mergeThresholds(
  prose: PrinciplesData,
  yaml: YamlThresholds,
): PrinciplesData {
  const merged = prose.domains.map(d => {
    const yamlCents = yaml.domains[d.name.toLowerCase()] ?? null;
    if (yamlCents === null) return d;
    return {
      ...d,
      autoApproveCents: yamlCents,
      autoApproveDisplay: `$${(yamlCents / 100).toLocaleString()}`,
    };
  });
  // Add yaml-only domains (not present in prose)
  const proseNames = new Set(prose.domains.map(d => d.name.toLowerCase()));
  for (const [name, cents] of Object.entries(yaml.domains)) {
    if (!proseNames.has(name)) {
      merged.push({
        name,
        autoApproveCents: cents,
        autoApproveDisplay: cents !== null ? `$${(cents / 100).toLocaleString()}` : null,
        rejectConditions: [],
      });
    }
  }
  return {
    domains: merged,
    hasPrinciples: merged.length > 0,
    raw: prose.raw,
  };
}
