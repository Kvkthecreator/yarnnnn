import { operatorCanOrganize } from '@/lib/workspace/ownership';

/**
 * artifactNaming — the FE mirror of ADR-459 D2's naming rule.
 *
 * The server computes `name` for the artifact LIST (`GET /studio/artifacts`,
 * `services/authoring.py::artifact_name`) — that's the authoritative one, and any
 * surface holding a served row must use it.
 *
 * This exists for the one place that can't: a tree-node picker. The workspace
 * tree is the MIRROR (ADR-459 D4 / ADR-340 DP29 — "complete, neutral,
 * faithful"), so it serves raw filesystem rows and must NOT be enriched with
 * composition names; and fetching every artifact's content just to name a row
 * in a picker would be absurd. So the picker derives, and this module is the
 * ONE place it derives — not a second rule, a second CALLER of the same rule.
 *
 * Keep this in step with `api/services/authoring.py::_titleize` + `artifact_name`.
 * Both are deliberately dumb (sentence case, no acronym heuristic) for the
 * reasons recorded in ADR-459 D2; a cleverer guess here would diverge from the
 * server's and show the member two different names for one file.
 */

/** `ir-deck-v3` → `Ir deck v3`. Sentence case — see ADR-459 D2 on why this is
 *  deliberately dumb rather than acronym-aware. */
export function titleizeSlug(slug: string): string {
  const words = slug.replace(/[-_]/g, ' ').split(/\s+/).filter(Boolean);
  if (words.length === 0) return '';
  return words.map((w, i) => (i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w)).join(' ');
}

/**
 * Where a Studio artifact may be created — the FE mirror of
 * `api/services/authoring.py::STUDIO_ARTIFACT_REGION` (ADR-440 D6).
 *
 * This is a PLACEMENT rule, and it is deliberately NOT `operatorCanOrganize`.
 * That mirror's own header says drift "only risks a stale label, never a wrong
 * write" — true for move/rename/trash, where the backend is the door and a
 * stale FE just greys a verb late. It is FALSE at creation, where the picker
 * IS the door: offering a folder the server refuses produces a 403 AFTER the
 * member has named the thing and pressed Create, citing a path they never
 * typed. Permission answers "may I write here"; this answers "may an artifact
 * LIVE here". Two questions — the create flow must ask this one.
 */
export const STUDIO_ARTIFACT_REGION = '/workspace/operation/';

/** True iff `folder` sits inside the Documents home — the artifact region.
 *
 *  This is now a HOME test, not a permission gate. ADR-551 D2 relaxed
 *  `create_artifact`'s fence to `operator_can_organize`, so an artifact may be
 *  created in any folder the member can organize (a peer folder like
 *  `the-acme-deal/` included) — the region survives as the DEFAULT home
 *  (ADR-549 D3's third rung), not as a wall.
 *
 *  Used by `defaultDestinationFor` to decide whether a source's folder is a
 *  sensible default. It is deliberately NOT the create picker's predicate any
 *  more; gating on it there would under-offer, refusing folders the API now
 *  accepts — the mirror image of the ADR-549 F1 defect. */
export function isArtifactRegion(folder: string): boolean {
  const abs = folder.startsWith('/') ? folder : `/${folder}`;
  return `${abs.replace(/\/+$/, '')}/`.startsWith(STUDIO_ARTIFACT_REGION);
}

/** True iff a new file may be CREATED under `folder` — the FE mirror of the
 *  server's one placement law (ADR-551 D2: `operator_can_organize`, the same
 *  predicate `create_folder` and the upload door ask).
 *
 *  Kept as its own named export rather than inlining `operatorCanOrganize` at
 *  the call sites, so the create-placement gate has ONE home to change if the
 *  law moves again — the fence has now moved twice. */
export function canCreateFileIn(folder: string): boolean {
  return operatorCanOrganize(`${folder.replace(/\/+$/, '')}/x`);
}

/**
 * Where a new artifact should DEFAULT to living, given the file the act is
 * standing on (a source being derived from, or the file currently open).
 * ADR-549 D3/D4 — the default is "where the act is standing", never a
 * hardcoded root chosen by the app.
 *
 * Returns a workspace-relative folder (no leading slash, no trailing slash) —
 * the shape `createArtifact`'s `path` is composed from.
 *
 * Two carves:
 *  - An ARRIVAL (`inbound/`) is not a home. You cannot file authored work into
 *    the immutable intake lane (ADR-422 D2), so a derive from an upload
 *    defaults to Documents.
 *  - Anything outside the artifact region falls back to Documents too, so this
 *    can never propose a destination `create_artifact` would 403 (ADR-440 D6).
 *    When that fence relaxes, this widens with it and needs no edit here.
 */
export function defaultDestinationFor(sourcePath: string | null | undefined): string {
  // `/workspace/operation/` → `operation`. Strip the workspace prefix FIRST:
  // trimming slashes alone yields `workspace/operation`, which composes a path
  // the server then reads as `/workspace/workspace/operation/…`.
  const home = STUDIO_ARTIFACT_REGION.replace(/^\/workspace\//, '').replace(/^\/+|\/+$/g, '');
  const abs = (sourcePath || '').startsWith('/') ? sourcePath! : `/${sourcePath || ''}`;
  if (!sourcePath || !isArtifactRegion(abs)) return home;
  const folder = abs.replace(/\/[^/]*$/, ''); // drop the leaf
  const rel = folder.replace(/^\/workspace\//, '').replace(/\/+$/, '');
  return rel || home;
}

/** The region's path segments — `operation`, `workspace`. Not meaning folders. */
const REGION_SEGMENTS = new Set(
  STUDIO_ARTIFACT_REGION.split('/').filter(Boolean).concat('workspace'),
);

/** The artifact's operator-facing name — its titleized MEANING FOLDER.
 *  `operation/ir-deck-v3/deck.html` → "Ir deck v3". Falls back to the titleized
 *  stem when the artifact sits directly in a root (no meaning folder). */
export function artifactNameFromPath(path: string): string {
  const parts = (path || '').split('/').filter(Boolean);
  if (parts.length === 0) return 'File';
  const parent = parts.length >= 2 ? parts[parts.length - 2] : null;
  // `workspace`/`operation` are the region, not a meaning folder (the server's
  // `artifact_name` makes the same carve against STUDIO_ARTIFACT_REGION).
  const isRegion = !!parent && REGION_SEGMENTS.has(parent);
  const raw =
    parent && !isRegion ? parent : (parts[parts.length - 1] || '').replace(/\.[a-z0-9]+$/i, '');
  return titleizeSlug(raw) || 'File';
}

/** The artifact's kind slug, from its filename stem.
 *
 * The ONE place the FE still guesses a kind. The served kind (ADR-459 D1) is
 * lifted from the artifact's `data-template` and isn't present on a tree node.
 * A wrong guess costs a GLYPH only — never a label, never a wrong file: the
 * row's name and its open target are both path-derived and exact. Anywhere a
 * served row exists (the landing), use `r.kind` instead of this.
 */
export function kindGuessFromPath(path: string): string | null {
  const stem = (path.split('/').pop() || '').replace(/\.[a-z0-9]+$/i, '');
  return stem || null;
}
