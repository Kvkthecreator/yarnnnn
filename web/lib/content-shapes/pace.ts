/**
 * Pace content shape — `/workspace/governance/_pace.yaml`.
 *
 * ADR-300 (2026-05-22): pace promoted from cockpit-tab section (ADR-298 D5
 * original) to atomic kernel surface. This module mirrors autonomy.ts's
 * shape — configuration WRITE_CONTRACT, FE-side parse/serialize, write
 * routes through `writeShape('pace', ...)` so ADR-245 D5 contract
 * enforcement runs.
 *
 * V1 edit scope is kind-only (`hourly | daily | weekly | continuous`).
 * `pace.every` (ISO 8601 duration) and `monthly_budget_usd` are read,
 * displayed, and round-tripped on disk; edits to those fields defer to
 * chat → WriteFile (the escape hatch documented in ADR-300 D2).
 *
 * Pace is operator-only substrate per ADR-298 D11: the path is in
 * DEFAULT_REVIEWER_WRITE_LOCKS (api/services/workspace_paths.py). The
 * Reviewer cannot write it; only the operator session can.
 */

'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3 + ADR-300)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'pace' as const;
export const PATH_GLOB = '**/governance/_pace.yaml';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'PaceCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Constants — mirror Python SHARED_PACE_PATH in api/services/workspace_paths.py
// ---------------------------------------------------------------------------

export const PACE_YAML_PATH = '/workspace/governance/_pace.yaml';

export const PACE_KINDS = ['hourly', 'daily', 'weekly', 'continuous'] as const;
export type PaceKind = typeof PACE_KINDS[number];

// ---------------------------------------------------------------------------
// Types — align with api/services/pace.py `Pace` dataclass + `parse_pace_yaml`
// ---------------------------------------------------------------------------

export interface PaceMeta {
  /** One of PACE_KINDS, or undefined when no pace declared. */
  kind?: PaceKind;
  /** Optional ISO 8601 numeric override (e.g., "4h", "12h"). Preserved
   *  on round-trip; not editable in the V1 atomic surface. */
  every?: string;
  /** Optional operator-set monthly cost cap. Preserved on round-trip;
   *  surfaced for context but routed through chat for edits. */
  monthly_budget_usd?: number;
}

// ---------------------------------------------------------------------------
// Tier frontmatter stripper — identical convention to autonomy.ts
// ---------------------------------------------------------------------------

export function stripTierFrontmatter(content: string): string {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (m && /\btier\s*:/.test(m[1])) {
    return content.slice(m[0].length);
  }
  return content;
}

// ---------------------------------------------------------------------------
// Pure parser — reads _pace.yaml (plain YAML after tier strip)
// ---------------------------------------------------------------------------
//
// Lightweight line-based parse — same approach as autonomy.ts. Handles the
// two-line `pace:` block shape that the substrate ships, plus the optional
// top-level `monthly_budget_usd` key. Comments and unknown fields pass
// through unharmed (serialize() reconstructs only the keys it owns and
// preserves the rest of the body verbatim).

export function parse(content: string): PaceMeta {
  const yaml = stripTierFrontmatter(content);
  const meta: PaceMeta = {};
  let inPaceBlock = false;
  for (const line of yaml.split('\n')) {
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;

    // Top-level key (no leading whitespace).
    const topLevelMatch = line.match(/^([a-z_]+):\s*(.*)$/);
    if (topLevelMatch && !line.startsWith(' ')) {
      const key = topLevelMatch[1];
      const rawValue = topLevelMatch[2]
        .trim()
        .replace(/^['"]|['"]$/g, '')
        .replace(/\s*#.*$/, '')
        .trim();
      if (key === 'pace') {
        inPaceBlock = true;
        continue;
      }
      inPaceBlock = false;
      if (key === 'monthly_budget_usd' && rawValue) {
        const n = Number(rawValue);
        if (!Number.isNaN(n)) meta.monthly_budget_usd = n;
      }
      continue;
    }

    // Indented field — only consumed when we're inside `pace:`.
    if (!inPaceBlock) continue;
    const fieldMatch = line.match(/^\s+([a-z_]+):\s*(.*)$/);
    if (!fieldMatch) continue;
    const k = fieldMatch[1].trim();
    const v = fieldMatch[2]
      .trim()
      .replace(/^['"]|['"]$/g, '')
      .replace(/\s*#.*$/, '')
      .trim();
    if (k === 'kind' && PACE_KINDS.includes(v as PaceKind)) {
      meta.kind = v as PaceKind;
    }
    if (k === 'every' && v) {
      meta.every = v;
    }
  }
  return meta;
}

// ---------------------------------------------------------------------------
// Round-trip parser — splits tier frontmatter so serialize() preserves it
// ---------------------------------------------------------------------------

export interface ParsedPace {
  meta: PaceMeta;
  /** Tier frontmatter block verbatim (e.g. "---\ntier: authored\n...\n---\n"), or ''. */
  tierBlock: string;
  /** Raw YAML body after tier block, including comments. */
  body: string;
}

export function parseRoundTrip(content: string): ParsedPace {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  const hasTierBlock = m && /\btier\s*:/.test(m[1]);
  const tierBlock = hasTierBlock ? m![0] : '';
  const body = hasTierBlock ? content.slice(tierBlock.length) : content;
  return { meta: parse(content), tierBlock, body };
}

// ---------------------------------------------------------------------------
// serialize() — rewrites the `pace:` block; preserves tier + the rest of
// the body (including monthly_budget_usd if present as a top-level key).
// ---------------------------------------------------------------------------
//
// V1 edit scope only mutates kind. `every` is round-tripped from the parsed
// meta — if the operator hand-edited `pace.every` in chat, the FE preserves
// it across kind edits (serialize emits both kind and every when present).
// monthly_budget_usd is preserved by NOT being inside the rewritten `pace:`
// block — it lives as a top-level key in the body, and we leave that
// portion of the body untouched.

export function serialize(meta: PaceMeta, body: string = '', tierBlock: string = ''): string {
  const lines: string[] = ['pace:'];
  if (meta.kind) {
    lines.push(`  kind: ${meta.kind}`);
  }
  if (meta.every) {
    lines.push(`  every: ${meta.every}`);
  }
  const paceSection = lines.join('\n') + '\n';

  // Strip the existing `pace:` block from body (the whole block including
  // its indented children). Leave everything else (comments, top-level
  // monthly_budget_usd, anything else) intact.
  const bodyWithoutPace = body.replace(/^pace:\s*\n(\s+\S[^\n]*\n)*/m, '');

  let out = tierBlock + paceSection + bodyWithoutPace;
  if (!out.endsWith('\n')) out += '\n';
  return out;
}

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

const KIND_LABELS: Record<PaceKind, string> = {
  hourly: 'Hourly',
  daily: 'Daily',
  weekly: 'Weekly',
  continuous: 'Continuous',
};

export function paceKindLabel(kind: PaceKind | undefined | null): string {
  if (!kind) return 'No pace declared';
  return KIND_LABELS[kind];
}

export function formatPaceSummary(meta: PaceMeta | null): string {
  if (!meta || !meta.kind) return 'No pace declared';
  const base = paceKindLabel(meta.kind);
  if (meta.every) return `${base} · every ${meta.every}`;
  return base;
}

// ---------------------------------------------------------------------------
// React hook — substrate read + write for FE consumers
// ---------------------------------------------------------------------------

export interface UsePaceResult {
  meta: PaceMeta | null;
  loading: boolean;
  /** Effective kind: parsed `pace.kind` or null when undeclared. */
  kind: PaceKind | null;
  summary: string;
  /** Mutate `pace.kind`. Routes through writeShape('pace', ...) so
   *  ADR-245 D5 WRITE_CONTRACT enforcement runs. Round-trips `every`
   *  and `monthly_budget_usd` verbatim per ADR-300 D2. */
  setKind: (kind: PaceKind) => Promise<void>;
}

export function useCockpitPace(opts?: { initialContent?: string | null }): UsePaceResult {
  const initial = opts?.initialContent;
  const initialParsed =
    initial != null && initial !== ''
      ? parseRoundTrip(initial)
      : null;
  const [meta, setMeta] = useState<PaceMeta | null>(initialParsed?.meta ?? null);
  const [loading, setLoading] = useState(initialParsed === null);
  const [tierBlock, setTierBlock] = useState(initialParsed?.tierBlock ?? '');
  const [rawBody, setRawBody] = useState(initialParsed?.body ?? '');

  useEffect(() => {
    if (initial !== undefined) {
      if (initial != null && initial !== '') {
        const parsed = parseRoundTrip(initial);
        setMeta(parsed.meta);
        setTierBlock(parsed.tierBlock);
        setRawBody(parsed.body);
      } else {
        setMeta(null);
        setTierBlock('');
        setRawBody('');
      }
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(PACE_YAML_PATH);
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
    return () => {
      cancelled = true;
    };
  }, [initial]);

  const setKind = async (next: PaceKind) => {
    if (!PACE_KINDS.includes(next)) {
      throw new Error(`useCockpitPace.setKind: invalid kind ${next}`);
    }
    const nextMeta: PaceMeta = {
      ...(meta ?? {}),
      kind: next,
    };
    const content = serialize(nextMeta, rawBody, tierBlock);
    // Optimistic update.
    setMeta(nextMeta);
    // ADR-245 D5: configuration shapes route through writeShape so the
    // WRITE_CONTRACT guard runs. Same backend primitive as autonomy.
    const { writeShape } = await import('./write');
    await writeShape('pace', 'governance/_pace.yaml', content, {
      message: `pace: kind=${next}`,
    });
  };

  const kind = meta?.kind ?? null;
  const summary = formatPaceSummary(meta);

  return {
    meta,
    loading,
    kind,
    summary,
    setKind,
  };
}
