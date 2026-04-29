/**
 * Autonomy substrate — shared FE module.
 *
 * Single source of truth for parsing `/workspace/context/_shared/AUTONOMY.md`
 * (per ADR-217 Workspace Autonomy Substrate) on the frontend.
 *
 * Lifted from MandateFace.tsx by ADR-238 (Round 1 of the ADR-236
 * frontend cockpit coherence pass). Future consumers — ADR-237's chat
 * role grammar, ADR-240's onboarding-as-activation prompts, and Round 5
 * mop-up modal-confirmation flows — import from here rather than
 * re-deriving the parser. Singular Implementation discipline: this is
 * the only autonomy parser on the frontend.
 *
 * Pure-TS module — no React imports outside the `useAutonomy()` hook
 * declared at the bottom of the file. The pure functions
 * (`parseAutonomy`, `formatAutonomySummary`, `resolveEffectiveLevel`)
 * are consumable by server components, MCP code, or any non-React
 * surface that needs to format autonomy text.
 *
 * What this module does NOT do (per ADR-238):
 *   - No mutation surface. Operator-authored substrate is mutated
 *     through `WriteFile(scope='workspace', path='context/_shared/AUTONOMY.md', ...)`
 *     per ADR-235 D1.b. The hook is read-only.
 *   - No global React context / provider. Each consumer fetches
 *     independently; if profile shows duplication is a hot path, a
 *     follow-on ADR introduces <AutonomyProvider>.
 *   - No `never_auto` field parsing. The first consumer (chip
 *     display) doesn't need it; ship the field's parser when its
 *     first reader surfaces.
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/**
 * Absolute path of the autonomy substrate file. Mirrors the Python
 * relative constant `SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"`
 * in `api/services/workspace_paths.py`, prefixed with `/workspace/` per
 * the FE addressing convention (the Python helper prepends `/workspace/`
 * before writing).
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
// Pure parser — lifted verbatim from MandateFace.tsx by ADR-238.
// Lightweight YAML walk for the two shapes the substrate carries:
//   default:
//     level: bounded_autonomous
//     ceiling_cents: 200000
//   domains:
//     trading:
//       level: bounded_autonomous
//       ceiling_cents: 50000
// ---------------------------------------------------------------------------

export function parseAutonomy(content: string): AutonomyMeta {
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

// ---------------------------------------------------------------------------
// Summary formatter — lifted verbatim from MandateFace.tsx by ADR-238.
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

// ---------------------------------------------------------------------------
// Effective level resolver — new helper added by ADR-238.
//
// Returns the effective autonomy level for a given domain, falling back
// to default.level. Returns null when neither is set (skeleton substrate
// or empty workspace). Consumers without a domain pass `undefined`.
// ---------------------------------------------------------------------------

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
// React hook — substrate read for FE consumers.
// ---------------------------------------------------------------------------

export interface UseAutonomyResult {
  meta: AutonomyMeta | null;
  loading: boolean;
  effectiveLevel: AutonomyLevel | null;
  /** Operator-facing one-liner. "No autonomy declared" when meta is null. */
  summary: string;
}

/**
 * Reads `/workspace/context/_shared/AUTONOMY.md` and exposes the parsed
 * substrate plus a derived effective-level for the workspace default.
 *
 * Read-only; mutation routes through
 * `WriteFile(scope='workspace', path='context/_shared/AUTONOMY.md', ...)`
 * per ADR-235 D1.b (legacy ADR-217 used UpdateContext; dissolved by ADR-235).
 *
 * Each consumer mount triggers one fetch. Deduplication across multiple
 * components in the same render pass is a deferred concern (ADR-238 R2).
 */
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
          setMeta(parseAutonomy(file.content));
        } else {
          setMeta(null);
        }
      } catch {
        if (cancelled) return;
        // Substrate absent (older workspace, or skeleton state per
        // ADR-226). Hook returns meta=null cleanly; consumers render
        // their own absent-state path.
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
