/**
 * Content-Shape Registry — ADR-245 Frontend Kernel L2 home.
 *
 * Phase 1 shipped the empty stub. Phase 2 (this commit) populates entries
 * by migrating four existing parsers and adding two new shape declarations.
 *
 * Each entry under `web/lib/content-shapes/` owns one content shape and
 * exports a `META: ContentShapeMeta` const + a `parse()` function (and,
 * for shapes whose WRITE_CONTRACT permits, a `serialize()`). Phase 4 lands
 * the typed `writeShape()` helper that routes to the correct write
 * primitive based on WRITE_CONTRACT.
 *
 * Phase 2 implementation-time finding: `web/lib/recurrence-shapes.ts` was
 * listed as a Phase 2 migration target in ADR-245 §Implementation, but
 * inspection found it isn't a content-shape parser — it's a domain-key
 * utility (no `parse()` of file content, no `PATH_GLOB`). It stays at its
 * current location. The recurrence-spec content shape (DECLARATION class
 * per D5) exists conceptually but its FE parser lives nowhere yet —
 * server-side `api/services/recurrence.py` parses YAML; FE reads come
 * through API endpoints, not direct YAML parsing. When Phase 4 lands the
 * recurrence-spec L3 editor, the parser gets created at that point.
 */

export type WriteContract =
  | 'narrative'
  | 'authored_prose'
  | 'configuration'
  | 'live_aggregate'
  | 'declaration'
  | 'composed_artifact'
  | 'system_owned';

export type ContentShape = {
  SHAPE_KEY: string;
  PATH_GLOB: string;
  WRITE_CONTRACT: WriteContract;
  CANONICAL_L3: string;
};

/** Alias for module-side imports — same shape; provided for readability. */
export type ContentShapeMeta = ContentShape;

import { META as autonomyMeta } from './autonomy';
import { META as decisionsMeta } from './decisions';
import { META as inferenceMetaMeta } from './inference-meta';
import { META as snapshotMeta } from './snapshot';
import { META as performanceMeta } from './performance';
import { META as principlesMeta } from './principles';

export const CONTENT_SHAPES: Readonly<Record<string, ContentShape>> = Object.freeze({
  autonomy: autonomyMeta,
  decisions: decisionsMeta,
  'inference-meta': inferenceMetaMeta,
  snapshot: snapshotMeta,
  performance: performanceMeta,
  principles: principlesMeta,
});

// ---------------------------------------------------------------------------
// Path resolution
// ---------------------------------------------------------------------------
//
// Lightweight glob matcher — supports `**`, `*`, and `{a,b,c}` alternation.
// No external dependency. Anchored to the full path string. Returns the
// first matching shape (registry insertion order) or null. This intentionally
// does NOT match the `__chat_message__/*` sentinel globs used by ephemeral
// content shapes (snapshot) — those shapes are reached by direct module
// import, never by path resolution.

function globToRegExp(glob: string): RegExp {
  // Expand alternation `{a,b}` → `(?:a|b)` first, escaping each alt's literals.
  let pattern = '';
  let i = 0;
  while (i < glob.length) {
    const ch = glob[i];
    if (ch === '{') {
      const end = glob.indexOf('}', i);
      if (end === -1) {
        pattern += escapeRegExp(glob.slice(i));
        break;
      }
      const alts = glob
        .slice(i + 1, end)
        .split(',')
        .map((alt) => alt.trim())
        .filter(Boolean)
        .map((alt) => globToRegExpInner(alt));
      pattern += `(?:${alts.join('|')})`;
      i = end + 1;
    } else {
      pattern += globToRegExpInner(ch);
      i += 1;
    }
  }
  return new RegExp(`^${pattern}$`);
}

function globToRegExpInner(seg: string): string {
  let out = '';
  let i = 0;
  while (i < seg.length) {
    const ch = seg[i];
    if (ch === '*' && seg[i + 1] === '*') {
      out += '.*';
      i += 2;
    } else if (ch === '*') {
      out += '[^/]*';
      i += 1;
    } else {
      out += escapeRegExp(ch);
      i += 1;
    }
  }
  return out;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function shapeForPath(path: string): ContentShape | null {
  if (!path) return null;
  for (const shape of Object.values(CONTENT_SHAPES)) {
    if (shape.PATH_GLOB.startsWith('__chat_message__/')) continue;
    if (globToRegExp(shape.PATH_GLOB).test(path)) {
      return shape;
    }
  }
  return null;
}
