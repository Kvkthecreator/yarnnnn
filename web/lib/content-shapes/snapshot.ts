/**
 * Snapshot-marker content shape — `<!-- snapshot: {...} -->` HTML comment
 * trailer on assistant chat messages.
 *
 * Migrated from `web/lib/snapshot-meta.ts` by ADR-245 Phase 2.
 *
 * Per ADR-245 D5 the WRITE_CONTRACT is `system_owned` — only YARNNN
 * (server-side, `api/agents/yarnnn.py` + prompt directives in
 * `api/agents/prompts/`) emits the marker; operators don't author it.
 *
 * Note on PATH_GLOB: this marker is a chat-message trailer, not a file.
 * The shape registry glob is set to a sentinel that no real file path
 * matches (the literal string is checked at lookup time and skipped) so
 * `shapeForPath` won't return it for filesystem reads. Consumers call
 * `parse()` directly with message content. This pattern is the
 * registry's accommodation for content shapes whose substrate is
 * ephemeral (chat messages) rather than a file.
 */

import type { ContentShapeMeta } from './index';

// ---------------------------------------------------------------------------
// Shape registry metadata (ADR-245 D3)
// ---------------------------------------------------------------------------

export const SHAPE_KEY = 'snapshot' as const;
export const PATH_GLOB = '__chat_message__/snapshot';
export const WRITE_CONTRACT = 'system_owned' as const;
export const CANONICAL_L3 = 'SnapshotPane' as const;

export const META: ContentShapeMeta = {
  SHAPE_KEY,
  PATH_GLOB,
  WRITE_CONTRACT,
  CANONICAL_L3,
};

// ---------------------------------------------------------------------------
// Snapshot marker
// ---------------------------------------------------------------------------

export type SnapshotLead =
  | 'mandate'
  | 'review'
  | 'recent';

export interface SnapshotDirective {
  lead: SnapshotLead;
  reason?: string;
}

export interface ParsedSnapshotContent {
  body: string;
  directive: SnapshotDirective | null;
}

const SNAPSHOT_RE = /\n*<!--\s*snapshot:\s*(\{[\s\S]*?\})\s*-->\s*$/;

const VALID_LEADS: ReadonlySet<SnapshotLead> = new Set<SnapshotLead>([
  'mandate',
  'review',
  'recent',
]);

export function parse(
  content: string | null | undefined,
): ParsedSnapshotContent {
  if (!content) return { body: '', directive: null };

  const match = content.match(SNAPSHOT_RE);
  if (!match) {
    return { body: content, directive: null };
  }

  let directive: SnapshotDirective | null = null;
  try {
    const parsed = JSON.parse(match[1]) as SnapshotDirective;
    if (parsed && VALID_LEADS.has(parsed.lead)) {
      directive = parsed;
    }
  } catch {
    directive = null;
  }

  const body = content.slice(0, match.index ?? 0).trimEnd();
  return { body, directive };
}

/** Legacy alias — back-compat for `parseSnapshotMeta` import name. */
export const parseSnapshotMeta = parse;

export function stripSnapshotMeta(content: string | null | undefined): string {
  return parse(content).body;
}

// ---------------------------------------------------------------------------
// Onboarding marker — retired emission (ADR-190 + ADR-215 Phase 5)
// ---------------------------------------------------------------------------
//
// YARNNN no longer emits `<!-- onboarding -->`. `stripOnboardingMeta`
// remains for display hygiene on historical messages.

const ONBOARDING_RE = /\n*<!--\s*onboarding\s*-->\s*$/;

export function stripOnboardingMeta(content: string | null | undefined): string {
  if (!content) return '';
  const match = content.match(ONBOARDING_RE);
  if (!match) return content;
  return content.slice(0, match.index ?? 0).trimEnd();
}
