/**
 * Sources content shape — the standing-watch `_sources.yaml` (ADR-336 / ADR-338 D4.1).
 *
 * The operator's declared web/RSS watch sources — the "drivers" view of the
 * standing watch (ADR-338 D2). Mirrors autonomy.ts / budget.ts: a
 * `configuration` WRITE_CONTRACT shape with FE-side parse/serialize; writes
 * route through `writeShape('sources', <declaration_path>, ...)` so ADR-245
 * D5 contract enforcement runs.
 *
 * Kernel-agnostic path (ADR-224 boundary): the declaration path is NOT a
 * kernel constant. It is discovered per-workspace from the active bundle's
 * `substrate_abi.watches[].declaration` and served by GET /api/sources. The
 * PATH_GLOB below is the conventional location (bundles place it under
 * operation/authored/) used only for L1→shape resolution in Files; the
 * authoritative write path comes from the API response.
 *
 * The declaration is operator-owned (operator edits the source list). The
 * observed health (`_watch_signal.yaml`) is system-written by TrackWebSources
 * and read-only — surfaced by the hook from the same API response, never
 * edited here.
 *
 * V1 edit scope: the `sources[]` list (id + url + attestation + max_entries),
 * capped at 12 (a portfolio of attention, not a crawler — ADR-335 D5).
 */

'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'sources' as const;
export const PATH_GLOB = '**/operation/authored/_sources.yaml';
export const WRITE_CONTRACT = 'configuration' as const;
export const CANONICAL_L3 = 'SourcesCard' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Source-count cap — mirrors track_web_sources._MAX_SOURCES. A portfolio of
 *  attention, not a crawler (ADR-335 D5). */
export const SOURCE_CAP = 12;

export const ATTESTATIONS = ['platform', 'operator', 'agent'] as const;
export type Attestation = typeof ATTESTATIONS[number];

export const DEFAULT_MAX_ENTRIES = 8;
export const MAX_ENTRIES_CAP = 20;

// ---------------------------------------------------------------------------
// Types — align with track_web_sources `sources[]` schema + GET /api/sources
// ---------------------------------------------------------------------------

export interface WatchSource {
  id: string;
  url: string;
  attestation?: Attestation;
  max_entries?: number;
}

export interface SourcesMeta {
  sources: WatchSource[];
}

/** Observed per-source health from _watch_signal.yaml (read-only). */
export interface ObservedSourceHealth {
  id: string;
  status: string; // 'ok' | 'error'
  observed_at: string | null;
  entry_count: number;
  error: string | null;
}

/** One standing watch: declared sources + observed health, paired. */
export interface WatchView {
  watch_id: string;
  program_slug: string | null;
  shape: string | null;
  recurrence: string | null;
  declaration_path: string;
  signal_path: string | null;
  declared: Required<WatchSource>[];
  observed: ObservedSourceHealth[];
  observed_at: string | null;
  source_cap: number;
}

// ---------------------------------------------------------------------------
// Tier frontmatter stripper — identical convention to autonomy.ts/budget.ts
// ---------------------------------------------------------------------------

export function stripTierFrontmatter(content: string): string {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (m && /\btier\s*:/.test(m[1])) {
    return content.slice(m[0].length);
  }
  return content;
}

// ---------------------------------------------------------------------------
// Pure parser — reads the `sources:` block from _sources.yaml
// ---------------------------------------------------------------------------
//
// Line-based parse (same approach as autonomy.ts). The list shape is:
//   sources:
//     - id: stereogum
//       url: https://...
//       attestation: platform
//       max_entries: 8
// `sources: []` (inline empty) → empty list. Comments + unknown top-level
// keys pass through; serialize() reconstructs only the `sources:` block.

export function parse(content: string): SourcesMeta {
  const yaml = stripTierFrontmatter(content);
  const meta: SourcesMeta = { sources: [] };
  let inSources = false;
  let current: WatchSource | null = null;

  const flush = () => {
    if (current && current.url) meta.sources.push(current);
    current = null;
  };

  for (const line of yaml.split('\n')) {
    if (/^\s*#/.test(line) || /^\s*$/.test(line)) continue;

    // Top-level `sources:` opens the block. `sources: []` is inline-empty.
    const topMatch = line.match(/^([a-z_]+):\s*(.*)$/);
    if (topMatch && !line.startsWith(' ')) {
      flush();
      if (topMatch[1] === 'sources') {
        inSources = true;
        // inline empty form stays empty; block items follow otherwise
        continue;
      }
      inSources = false;
      continue;
    }

    if (!inSources) continue;

    // New list item: `  - id: x` or `  - url: x`
    const itemStart = line.match(/^\s{2}-\s*([a-z_]+):\s*(.*)$/);
    if (itemStart) {
      flush();
      current = {} as WatchSource;
      _assignField(current, itemStart[1], itemStart[2]);
      continue;
    }

    // Continued field of the current item: `    url: x`
    const field = line.match(/^\s{4,}([a-z_]+):\s*(.*)$/);
    if (field && current) {
      _assignField(current, field[1], field[2]);
    }
  }
  flush();
  return meta;
}

function _assignField(src: WatchSource, key: string, rawValue: string): void {
  const v = rawValue.trim().replace(/^['"]|['"]$/g, '').replace(/\s*#.*$/, '').trim();
  if (key === 'id') src.id = v;
  else if (key === 'url') src.url = v;
  else if (key === 'attestation') {
    src.attestation = (ATTESTATIONS as readonly string[]).includes(v) ? (v as Attestation) : 'platform';
  } else if (key === 'max_entries') {
    const n = Number(v);
    if (!Number.isNaN(n)) src.max_entries = Math.max(1, Math.min(n, MAX_ENTRIES_CAP));
  }
}

// ---------------------------------------------------------------------------
// Round-trip parser — splits tier frontmatter so serialize() preserves it
// ---------------------------------------------------------------------------

export interface ParsedSources {
  meta: SourcesMeta;
  tierBlock: string;
  body: string;
}

export function parseRoundTrip(content: string): ParsedSources {
  const m = content.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  const hasTierBlock = m && /\btier\s*:/.test(m[1]);
  const tierBlock = hasTierBlock ? m![0] : '';
  const body = hasTierBlock ? content.slice(tierBlock.length) : content;
  return { meta: parse(content), tierBlock, body };
}

// ---------------------------------------------------------------------------
// serialize() — rewrites the `sources:` block; preserves tier + rest of body
// ---------------------------------------------------------------------------

export function serialize(meta: SourcesMeta, body: string = '', tierBlock: string = ''): string {
  const lines: string[] = [];
  const list = (meta.sources || []).filter((s) => s.url && s.url.trim());
  if (list.length === 0) {
    lines.push('sources: []');
  } else {
    lines.push('sources:');
    for (const s of list) {
      const id = (s.id || s.url).trim();
      lines.push(`  - id: ${id}`);
      lines.push(`    url: ${s.url.trim()}`);
      lines.push(`    attestation: ${s.attestation || 'platform'}`);
      lines.push(`    max_entries: ${s.max_entries ?? DEFAULT_MAX_ENTRIES}`);
    }
  }
  const sourcesSection = lines.join('\n') + '\n';

  // Strip the existing `sources:` block (whole block incl. indented children).
  const bodyWithoutSources = body.replace(/^sources:\s*(?:\[\s*\]\s*)?\n(\s+\S[^\n]*\n)*/m, '');

  let out = tierBlock + sourcesSection + bodyWithoutSources;
  if (!out.endsWith('\n')) out += '\n';
  return out;
}

// ---------------------------------------------------------------------------
// React hook — reads watches (declared + observed) from GET /api/sources;
// writes the declaration file via writeShape().
// ---------------------------------------------------------------------------

export interface UseSourcesResult {
  watches: WatchView[];
  loading: boolean;
  /** True when no active bundle declares a standing watch — honest empty
   *  state (perception is a flow, never a gate). */
  noWatch: boolean;
  /** Replace the source list for a given watch (by declaration path). Routes
   *  through writeShape('sources', ...) → WriteFile per ADR-235 D1.b. */
  setSources: (declarationPath: string, sources: WatchSource[]) => Promise<void>;
  /** Re-fetch from the route (after a write or on demand). */
  refresh: () => Promise<void>;
}

export function useSources(): UseSourcesResult {
  const [watches, setWatches] = useState<WatchView[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const res = await api.sources();
      setWatches((res?.watches as WatchView[]) ?? []);
    } catch {
      setWatches([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await load();
      if (cancelled) setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [load]);

  const setSources = useCallback(
    async (declarationPath: string, sources: WatchSource[]) => {
      // Read the existing declaration to preserve its tier block + comments,
      // then re-serialize only the sources list. The declaration path is
      // workspace-relative (from the API response); editFile expects the
      // path WITHOUT the /workspace/ prefix (writeShape's contract).
      const wsRelative = declarationPath.replace(/^\/workspace\//, '').replace(/^\//, '');
      let tierBlock = '';
      let body = '';
      try {
        const file = await api.workspace.getFile(`/workspace/${wsRelative}`);
        if (file?.content) {
          const parsed = parseRoundTrip(file.content);
          tierBlock = parsed.tierBlock;
          body = parsed.body;
        }
      } catch {
        /* new file — no existing tier/body */
      }
      // Optimistic local update for the matching watch.
      setWatches((prev) =>
        prev.map((w) =>
          w.declaration_path === declarationPath
            ? {
                ...w,
                declared: sources.map((s) => ({
                  id: (s.id || s.url).trim(),
                  url: s.url.trim(),
                  attestation: s.attestation || 'platform',
                  max_entries: s.max_entries ?? DEFAULT_MAX_ENTRIES,
                })) as Required<WatchSource>[],
              }
            : w,
        ),
      );
      const content = serialize({ sources }, body, tierBlock);
      const { writeShape } = await import('./write');
      await writeShape('sources', wsRelative, content, {
        message: `standing-watch sources → ${sources.length} ${sources.length === 1 ? 'source' : 'sources'}`,
      });
    },
    [],
  );

  const noWatch = !loading && watches.length === 0;

  return { watches, loading, noWatch, setSources, refresh: load };
}
