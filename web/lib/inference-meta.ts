/**
 * Inference meta parsing — ADR-162 Sub-phase D + ADR-163.
 *
 * The backend's `infer_shared_context()` appends an HTML comment at the end
 * of every inference output:
 *
 *   <!-- inference-meta: {"target":"identity","inferred_at":"...","sources":{...},"gaps":{...}} -->
 *
 * This module parses that comment (if present) into a structured object and
 * returns the markdown body with the comment stripped for clean rendering.
 *
 * The meta comment is written atomically with the content it describes, so
 * the parsed gap report and source provenance are always in sync with the
 * markdown the user sees.
 */

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
  inferred_at: string;
  sources: InferenceMetaSources;
  gaps?: InferenceGaps;
}

export interface ParsedInferenceContent {
  /** The markdown body with the inference-meta comment stripped. */
  body: string;
  /** Parsed meta object, or null if no comment was present. */
  meta: InferenceMeta | null;
}

const META_COMMENT_RE = /\n*<!--\s*inference-meta:\s*(\{[\s\S]*?\})\s*-->\s*$/;

/**
 * Parse and strip the inference-meta HTML comment from inference output.
 *
 * Returns the markdown body (comment removed) and the parsed meta object.
 * If the content has no meta comment, `meta` is null and `body` is the
 * content unchanged.
 */
export function parseInferenceMeta(content: string | null | undefined): ParsedInferenceContent {
  if (!content) return { body: '', meta: null };

  const match = content.match(META_COMMENT_RE);
  if (!match) {
    return { body: content, meta: null };
  }

  let meta: InferenceMeta | null = null;
  try {
    meta = JSON.parse(match[1]) as InferenceMeta;
  } catch {
    // Malformed comment — fall through with meta=null but still strip it
    meta = null;
  }

  const body = content.slice(0, match.index ?? 0).trimEnd();
  return { body, meta };
}

/**
 * Build a human-readable source caption from parsed meta.
 *
 * Examples:
 *   "Last updated from: 2 documents, 1 URL"
 *   "Last updated from: pitch-deck.pdf"
 *   "Last updated from: chat"
 *   null when sources are empty
 */
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

/**
 * Return the highest-severity gap item, or null if there are no gaps or
 * no high-severity items. Used by UI to decide whether to show a banner.
 */
export function getPrimaryGap(meta: InferenceMeta | null): InferenceGapItem | null {
  if (!meta?.gaps?.items?.length) return null;
  const severityRank: Record<string, number> = { high: 0, medium: 1, low: 2 };
  const sorted = [...meta.gaps.items].sort(
    (a, b) => (severityRank[a.severity] ?? 3) - (severityRank[b.severity] ?? 3)
  );
  return sorted[0] && sorted[0].severity === 'high' ? sorted[0] : null;
}
