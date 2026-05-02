/**
 * Autonomy content shape — `/workspace/context/_shared/AUTONOMY.md`.
 *
 * Migrated from `web/lib/autonomy.ts` by ADR-244 Phase 2 (commit
 * <see git log>). The pure parser + helpers + React hook are unchanged in
 * shape; only the import path moved into the content-shape registry home.
 *
 * Per ADR-244 D5 the WRITE_CONTRACT is `configuration` — operator mutates
 * via the canonical L3 (MandateFace) which serializes parsed data and
 * writes through `WriteFile(scope='workspace', path='context/_shared/AUTONOMY.md', ...)`
 * per ADR-235 D1.b. The Phase 4 toggle implementation will land
 * `serialize()` + canonical L3 mutation; Phase 2 ships the parser + read
 * surfaces only.
 *
 * Lifted-from history: MandateFace.tsx → web/lib/autonomy.ts (ADR-238) →
 * here (ADR-244 Phase 2).
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-244 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'autonomy' as const;
export const PATH_GLOB = '**/_shared/AUTONOMY.md';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'MandateFace' as const;

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
 * Absolute path of the autonomy substrate file. Mirrors the Python
 * relative constant `SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"`
 * in `api/services/workspace_paths.py`.
 */
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
// Pure parser (lifted verbatim from prior `web/lib/autonomy.ts`)
// ---------------------------------------------------------------------------

export function parse(content: string): AutonomyMeta {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return {};
  const meta: AutonomyMeta = { domains: {} };
  let currentDomain: string | null = null;
  let inDefault = false;
  let inDomains = false;
  for (const line of fm[1].split('\n')) {
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
    const domainMatch = line.match(/^\s{2}([a-z_]+):\s*$/);
    if (inDomains && domainMatch) {
      currentDomain = domainMatch[1];
      meta.domains![currentDomain] = {};
      continue;
    }
    const fieldMatch = line.match(/^\s+([a-z_]+):\s*(.*)$/);
    if (!fieldMatch) continue;
    const k = fieldMatch[1].trim();
    const v = fieldMatch[2].trim().replace(/^['"]|['"]$/g, '');
    if (inDefault) {
      if (k === 'level') meta.default_level = v;
      if (k === 'ceiling_cents') meta.default_ceiling_cents = Number(v);
    } else if (inDomains && currentDomain) {
      const dom = meta.domains![currentDomain];
      if (k === 'level') dom.level = v;
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
// Phase 4 introduces serialize() for the autonomy `configuration` shape.
// Bundle-shipped AUTONOMY.md templates (e.g. alpha-trader's reference
// workspace) have prose body after the closing `---` explaining phase
// progression + design intent. The toggle round-trip MUST preserve that
// body verbatim — operators reading the file later must see what was
// written. parseRoundTrip returns both halves so serialize can re-emit
// the body unchanged.

export interface ParsedAutonomy {
  meta: AutonomyMeta;
  body: string;
}

export function parseRoundTrip(content: string): ParsedAutonomy {
  const fm = content.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!fm) return { meta: {}, body: content };
  return {
    meta: parse(content),
    body: content.slice(fm[0].length).replace(/^\s*\n/, ''),
  };
}

// ---------------------------------------------------------------------------
// serialize() — Phase 4 (ADR-244 D5 configuration class write contract)
// ---------------------------------------------------------------------------
//
// Round-trips AutonomyMeta + optional body back to file content. Emits
// the same YAML frontmatter shape that parse() reads. Body is preserved
// verbatim. The output is structurally idempotent: parse(serialize(m)) ≡ m
// for every meta the parser can produce.

export function serialize(meta: AutonomyMeta, body: string = ''): string {
  const lines: string[] = ['---'];
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
      if (dom.level !== undefined) {
        lines.push(`    level: ${dom.level}`);
      }
      if (dom.ceiling_cents !== undefined) {
        lines.push(`    ceiling_cents: ${dom.ceiling_cents}`);
      }
    }
  }
  lines.push('---');
  let out = lines.join('\n') + '\n';
  if (body) {
    out += '\n' + body;
    if (!out.endsWith('\n')) out += '\n';
  }
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
}

export function useAutonomy(): UseAutonomyResult {
  const [meta, setMeta] = useState<AutonomyMeta | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(AUTONOMY_PATH);
        if (cancelled) return;
        if (file?.content) {
          setMeta(parse(file.content));
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
    return () => {
      cancelled = true;
    };
  }, []);

  const effectiveLevel = resolveEffectiveLevel(meta);
  const summary = formatAutonomySummary(meta ?? {});

  return { meta, loading, effectiveLevel, summary };
}
