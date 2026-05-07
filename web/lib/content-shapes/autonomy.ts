/**
 * Autonomy content shape — `/workspace/context/_shared/_autonomy.yaml`.
 *
 * ADR-254 (file format discipline): machine-parsed delegation config moved
 * from AUTONOMY.md frontmatter → _autonomy.yaml. AUTONOMY.md is now
 * prose-only (LLM/human reading). All reads and writes target _autonomy.yaml.
 *
 * _autonomy.yaml has a tier frontmatter block (--- tier: authored ... ---)
 * prepended by the bundle fork. stripTierFrontmatter() removes it before
 * YAML parsing so the parser only sees the raw YAML fields.
 *
 * Lifted-from history: MandateFace.tsx → web/lib/autonomy.ts (ADR-238) →
 * content-shapes/autonomy.ts (ADR-245 Phase 2) → _autonomy.yaml target (ADR-254).
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'autonomy' as const;
export const PATH_GLOB = '**/_shared/_autonomy.yaml';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'DelegationCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Machine-parsed delegation config (ADR-254). Mirrors Python constant
 * SHARED_AUTONOMY_YAML_PATH = "context/_shared/_autonomy.yaml".
 * AUTONOMY_PATH kept as alias pointing to prose doc for link-outs only.
 */
export const AUTONOMY_YAML_PATH = '/workspace/context/_shared/_autonomy.yaml';
/** Prose documentation — human/LLM reading only. Not machine-parsed. */
export const AUTONOMY_PATH = '/workspace/context/_shared/AUTONOMY.md';

// ---------------------------------------------------------------------------
// Types — match ADR-217 D1 schema
// ---------------------------------------------------------------------------

export type AutonomyLevel =
  | 'manual'
  | 'assisted'
  | 'bounded_autonomous'
  | 'autonomous';

export interface AutonomyDomain {
  level?: AutonomyLevel | string;
  ceiling_cents?: number;
}

export interface AutonomyMeta {
  default_level?: AutonomyLevel | string;
  default_ceiling_cents?: number;
  domains?: Record<string, AutonomyDomain>;
}

// ---------------------------------------------------------------------------
// Tier frontmatter stripper (ADR-254)
// ---------------------------------------------------------------------------
//
// Bundle-forked yaml files have a `---\ntier: authored\n...\n---` block at
// the top (same convention as Python _strip_tier_frontmatter). Strip it so
// the parser only sees raw YAML field lines.

export function stripTierFrontmatter(content: string): string {
  // Match the leading --- block only if it contains a `tier:` key,
  // distinguishing bundle tier blocks from legitimate YAML `---` separators.
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (m && /\btier\s*:/.test(m[1])) {
    return content.slice(m[0].length);
  }
  return content;
}

// ---------------------------------------------------------------------------
// Pure parser — reads _autonomy.yaml (ADR-254, plain YAML after tier strip)
// ---------------------------------------------------------------------------

export function parse(content: string): AutonomyMeta {
  const yaml = stripTierFrontmatter(content);
  const meta: AutonomyMeta = { domains: {} };
  let currentDomain: string | null = null;
  let inDefault = false;
  let inDomains = false;
  for (const line of yaml.split('\n')) {
    // Skip comment lines and blank lines
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;
    if (/^default:\s*$/.test(line)) {
      inDefault = true;
      inDomains = false;
      currentDomain = null;
      continue;
    }
    if (/^domains:\s*$/.test(line)) {
      inDefault = false;
      inDomains = true;
      currentDomain = null;
      continue;
    }
    // Top-level keys that are not `default` or `domains` (e.g. heartbeat_triggers,
    // never_auto, paused_until) — reset section context so we don't mis-attribute
    if (/^[a-z_]+:\s/.test(line) || /^[a-z_]+:\s*$/.test(line)) {
      const key = line.match(/^([a-z_]+):/)?.[1];
      if (key && key !== 'default' && key !== 'domains') {
        inDefault = false;
        inDomains = false;
        currentDomain = null;
        continue;
      }
    }
    const domainMatch = line.match(/^\s{2}([a-z_]+):\s*$/);
    if (inDomains && domainMatch) {
      currentDomain = domainMatch[1];
      meta.domains![currentDomain] = {};
      continue;
    }
    const fieldMatch = line.match(/^\s+([a-z_]+):\s*(.*)$/);
    if (!fieldMatch) continue;
    const k = fieldMatch[1].trim();
    const v = fieldMatch[2].trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
    if (inDefault) {
      if (k === 'level') meta.default_level = v as AutonomyLevel;
      if (k === 'ceiling_cents') meta.default_ceiling_cents = Number(v);
    } else if (inDomains && currentDomain) {
      const dom = meta.domains![currentDomain];
      if (k === 'level') dom.level = v as AutonomyLevel;
      if (k === 'ceiling_cents') dom.ceiling_cents = Number(v);
    }
  }
  return meta;
}

/** Legacy alias — back-compat for callers still importing `parseAutonomy`. */
export const parseAutonomy = parse;

// ---------------------------------------------------------------------------
// Round-trip parser — splits frontmatter from operator-authored body
// ---------------------------------------------------------------------------
//
// _autonomy.yaml round-trip (ADR-254):
// The file has an optional tier frontmatter block at the top (bundle-forked
// workspaces). parseRoundTrip splits that block from the YAML body so
// serialize() can re-emit it unchanged — operators reading the file keep
// the documentation comments the bundle shipped.

export interface ParsedAutonomy {
  meta: AutonomyMeta;
  /** The tier frontmatter block verbatim (e.g. "---\ntier: authored\n...\n---\n"), or ''. */
  tierBlock: string;
  /** The raw YAML body after the tier block, including comments. */
  body: string;
}

export function parseRoundTrip(content: string): ParsedAutonomy {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  const hasTierBlock = m && /\btier\s*:/.test(m[1]);
  const tierBlock = hasTierBlock ? m![0] : '';
  const body = hasTierBlock ? content.slice(tierBlock.length) : content;
  return { meta: parse(content), tierBlock, body };
}

// ---------------------------------------------------------------------------
// serialize() — writes back only the `default:` and `domains:` keys,
// preserving the tier block and the rest of the YAML body verbatim.
// ---------------------------------------------------------------------------

export function serialize(meta: AutonomyMeta, body: string = '', tierBlock: string = ''): string {
  // Rebuild only the structured keys we own; preserve comment lines in body.
  const lines: string[] = [];
  if (meta.default_level !== undefined || meta.default_ceiling_cents !== undefined) {
    lines.push('default:');
    if (meta.default_level !== undefined) {
      lines.push(`  level: ${meta.default_level}`);
    }
    if (meta.default_ceiling_cents !== undefined) {
      lines.push(`  ceiling_cents: ${meta.default_ceiling_cents}`);
    }
  }
  if (meta.domains && Object.keys(meta.domains).length > 0) {
    lines.push('domains:');
    for (const [name, dom] of Object.entries(meta.domains)) {
      lines.push(`  ${name}:`);
      if (dom.level !== undefined) lines.push(`    level: ${dom.level}`);
      if (dom.ceiling_cents !== undefined) lines.push(`    ceiling_cents: ${dom.ceiling_cents}`);
    }
  }
  const yamlSection = lines.join('\n') + (lines.length > 0 ? '\n' : '');
  // Patch the `default:` block inside the existing body to replace only
  // the structured keys, keeping comment lines (never_auto, heartbeat_triggers…).
  // Strategy: strip existing `default:` + `domains:` blocks from body, prepend new ones.
  const bodyWithoutStructured = body
    .replace(/^default:\s*\n(\s+\S[^\n]*\n)*/m, '')
    .replace(/^domains:\s*\n(\s+\S[^\n]*\n)*/m, '');
  let out = tierBlock + yamlSection + bodyWithoutStructured;
  if (!out.endsWith('\n')) out += '\n';
  return out;
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

export function formatAutonomySummary(autonomy: AutonomyMeta): string {
  const level =
    autonomy.default_level ??
    Object.values(autonomy.domains ?? {})[0]?.level ??
    null;
  if (!level) return 'No autonomy declared';
  const ceiling =
    autonomy.default_ceiling_cents ??
    Object.values(autonomy.domains ?? {})[0]?.ceiling_cents ??
    null;
  const levelLabel = level.replace(/_/g, ' ');
  if (ceiling && ceiling > 0) {
    return `${levelLabel} · ceiling $${(ceiling / 100).toLocaleString()}`;
  }
  return levelLabel;
}

export function resolveEffectiveLevel(
  meta: AutonomyMeta | null,
  domain?: string,
): AutonomyLevel | null {
  if (!meta) return null;
  if (domain) {
    const domEntry = meta.domains?.[domain];
    if (domEntry?.level) return domEntry.level as AutonomyLevel;
  }
  if (meta.default_level) return meta.default_level as AutonomyLevel;
  return null;
}

// ---------------------------------------------------------------------------
// React hook — substrate read for FE consumers
// ---------------------------------------------------------------------------

export interface UseAutonomyResult {
  meta: AutonomyMeta | null;
  loading: boolean;
  effectiveLevel: AutonomyLevel | null;
  summary: string;
  /** Direct DB write via PATCH /api/workspace/file — zero LLM. */
  setLevel: (level: AutonomyLevel, ceilingCents?: number) => Promise<void>;
}

export function useAutonomy(): UseAutonomyResult {
  const [meta, setMeta] = useState<AutonomyMeta | null>(null);
  const [loading, setLoading] = useState(true);
  // Preserved for round-trip: tier block + body lines (comments, other keys)
  const [tierBlock, setTierBlock] = useState('');
  const [rawBody, setRawBody] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // ADR-254: machine-parsed config lives in _autonomy.yaml, not AUTONOMY.md
        const file = await api.workspace.getFile(AUTONOMY_YAML_PATH);
        if (cancelled) return;
        if (file?.content) {
          const parsed = parseRoundTrip(file.content);
          setMeta(parsed.meta);
          setTierBlock(parsed.tierBlock);
          setRawBody(parsed.body);
        } else {
          setMeta(null);
        }
      } catch {
        if (cancelled) return;
        setMeta(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const setLevel = async (level: AutonomyLevel, ceilingCents?: number) => {
    const next: AutonomyMeta = {
      ...(meta ?? {}),
      default_level: level,
      default_ceiling_cents:
        level === 'bounded_autonomous'
          ? (ceilingCents ?? meta?.default_ceiling_cents ?? 200000)
          : undefined,
    };
    const content = serialize(next, rawBody, tierBlock);
    // Optimistic update — UI reflects immediately, API confirms in background
    setMeta(next);
    // ADR-254: write to _autonomy.yaml, not AUTONOMY.md
    await api.workspace.editFile(
      'context/_shared/_autonomy.yaml',
      content,
      `autonomy level → ${level}`,
      `set autonomy level to ${level}`,
    );
  };

  const effectiveLevel = resolveEffectiveLevel(meta);
  const summary = formatAutonomySummary(meta ?? {});

  return { meta, loading, effectiveLevel, summary, setLevel };
}
