/**
 * Inference-meta content shape — `<!-- inference-meta: {...} -->` HTML
 * comment trailer on inferred files (IDENTITY.md, BRAND.md).
 *
 * Migrated from `web/lib/inference-meta.ts` by ADR-245 Phase 2.
 *
 * Per ADR-245 D5 the WRITE_CONTRACT is `system_owned` — only
 * `infer_shared_context()` (server-side, ADR-162 Sub-phase D + ADR-209
 * Phase 4) writes the trailer; operators don't edit through L3.
 *
 * Note on PATH_GLOB: this shape doesn't anchor to a single path — the
 * comment trailer can appear on any inferred file. The glob below matches
 * the two known producers (IDENTITY.md + BRAND.md); if more inferred
 * surfaces gain meta trailers later, extend the glob without renaming.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'inference-meta' as const;
export const PATH_GLOB = '**/_shared/{IDENTITY,BRAND}.md';
export const WRITE_CONTRACT = 'system_owned' as const;
export const CANONICAL_L3 = 'InferenceContentView' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface InferenceMetaSources {
  from_chat?: boolean;
  documents?: string[];
  urls?: string[];
}

export interface InferenceGapItem {
  field: string;
  severity: 'high' | 'medium' | 'low';
  suggested_question: string;
  options: string[];
}

export interface InferenceGaps {
  richness?: 'empty' | 'sparse' | 'rich';
  items: InferenceGapItem[];
}

export interface InferenceMeta {
  target: 'identity' | 'brand' | string;
  sources: InferenceMetaSources;
  gaps?: InferenceGaps;
}

export interface ParsedInferenceContent {
  body: string;
  meta: InferenceMeta | null;
}

const META_COMMENT_RE = /\n*<!--\s*inference-meta:\s*(\{[\s\S]*?\})\s*-->\s*$/;

// ---------------------------------------------------------------------------
// Pure parser
// ---------------------------------------------------------------------------

export function parse(content: string | null | undefined): ParsedInferenceContent {
  if (!content) return { body: '', meta: null };

  const match = content.match(META_COMMENT_RE);
  if (!match) {
    return { body: content, meta: null };
  }

  let meta: InferenceMeta | null = null;
  try {
    meta = JSON.parse(match[1]) as InferenceMeta;
  } catch {
    meta = null;
  }

  const body = content.slice(0, match.index ?? 0).trimEnd();
  return { body, meta };
}

/** Legacy alias — back-compat for `parseInferenceMeta` import name. */
export const parseInferenceMeta = parse;

// ---------------------------------------------------------------------------
// Pure formatters
// ---------------------------------------------------------------------------

export function formatSourceCaption(meta: InferenceMeta | null): string | null {
  if (!meta) return null;
  const s = meta.sources || {};
  const parts: string[] = [];

  const docs = s.documents || [];
  const urls = s.urls || [];

  if (docs.length === 1) {
    parts.push(docs[0]);
  } else if (docs.length > 1) {
    parts.push(`${docs.length} documents`);
  }

  if (urls.length === 1) {
    parts.push(urls[0]);
  } else if (urls.length > 1) {
    parts.push(`${urls.length} URLs`);
  }

  if (s.from_chat && parts.length === 0) {
    parts.push('chat');
  }

  if (parts.length === 0) return null;
  return `Last updated from: ${parts.join(', ')}`;
}

export function getPrimaryGap(meta: InferenceMeta | null): InferenceGapItem | null {
  if (!meta?.gaps?.items?.length) return null;
  const severityRank: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const sorted = [...meta.gaps.items].sort(
    (a, b) => (severityRank[a.severity] ?? 3) - (severityRank[b.severity] ?? 3),
  );
  return sorted[0] && sorted[0].severity === 'high' ? sorted[0] : null;
}
