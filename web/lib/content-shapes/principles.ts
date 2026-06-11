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
  /** Parsed auto_approve_below_cents value if declared.
   *  @deprecated ADR-261 D5 — folded into _autonomy.yaml::ceiling_cents. Kept
   *  only to read legacy prose that still mentions it; the canonical
   *  execution ceiling lives on /autonomy, not here. */
  autoApproveCents: number | null;
  /** Dollar string for display e.g. "$500". Null if not set. @deprecated — see above. */
  autoApproveDisplay: string | null;
  /** ADR-338 D4.6 / ADR-195 Phase 5 — the actual machine-parsed threshold in
   *  _principles.yaml: realized outcomes ≥ this route to the task feedback.md
   *  (high-impact → feedback loop). null when not declared for the domain. */
  highImpactCents: number | null;
  /** Dollar string for display e.g. "$500". Null if not set. */
  highImpactDisplay: string | null;
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

    domains.push({
      name,
      autoApproveCents,
      autoApproveDisplay,
      highImpactCents: null,  // prose doesn't carry it; merged from _principles.yaml
      highImpactDisplay: null,
      rejectConditions,
    });
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
  /** Map of domain name → auto_approve_below_cents (@deprecated — ADR-261 D5). */
  domains: Record<string, number | null>;
  /** ADR-338 D4.6 — map of domain name → high_impact_threshold_cents (the
   *  actual machine-parsed threshold in _principles.yaml, ADR-195 Phase 5). */
  highImpact: Record<string, number | null>;
}

export function parseYaml(content: string): YamlThresholds {
  const result: YamlThresholds = { domains: {}, highImpact: {} };
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
      result.highImpact[currentDomain] = null;
      continue;
    }
    // Threshold fields under a domain
    if (currentDomain) {
      const autoApprove = line.match(/^\s+auto_approve_below_cents:\s*(\d+)/);
      if (autoApprove) {
        result.domains[currentDomain] = parseInt(autoApprove[1], 10);
      }
      const highImpact = line.match(/^\s+high_impact_threshold_cents:\s*(\d+)/);
      if (highImpact) {
        result.highImpact[currentDomain] = parseInt(highImpact[1], 10);
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
  const cents = (n: number | null) => (n !== null ? `$${(n / 100).toLocaleString()}` : null);
  const merged = prose.domains.map(d => {
    const key = d.name.toLowerCase();
    const yamlCents = yaml.domains[key] ?? null;
    const hiCents = yaml.highImpact[key] ?? null;
    return {
      ...d,
      ...(yamlCents !== null
        ? { autoApproveCents: yamlCents, autoApproveDisplay: cents(yamlCents) }
        : {}),
      highImpactCents: hiCents,
      highImpactDisplay: cents(hiCents),
    };
  });
  // Add yaml-only domains (not present in prose) — union both threshold maps.
  const proseNames = new Set(prose.domains.map(d => d.name.toLowerCase()));
  const yamlNames = Array.from(
    new Set([...Object.keys(yaml.domains), ...Object.keys(yaml.highImpact)]),
  );
  for (const name of yamlNames) {
    if (!proseNames.has(name)) {
      const aac = yaml.domains[name] ?? null;
      const hic = yaml.highImpact[name] ?? null;
      merged.push({
        name,
        autoApproveCents: aac,
        autoApproveDisplay: cents(aac),
        highImpactCents: hic,
        highImpactDisplay: cents(hic),
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
