/**
 * artifactNaming — the FE mirror of ADR-459 D2's naming rule.
 *
 * The server computes `name` for the artifact LIST (`GET /studio/artifacts`,
 * `services/studio.py::artifact_name`) — that's the authoritative one, and any
 * surface holding a served row must use it.
 *
 * This exists for the one place that can't: a tree-node picker. The workspace
 * tree is the MIRROR (ADR-459 D4 / ADR-340 DP29 — "complete, neutral,
 * faithful"), so it serves raw filesystem rows and must NOT be enriched with
 * composition names; and fetching every artifact's content just to name a row
 * in a picker would be absurd. So the picker derives, and this module is the
 * ONE place it derives — not a second rule, a second CALLER of the same rule.
 *
 * Keep this in step with `api/services/studio.py::_titleize` + `artifact_name`.
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

/** The artifact's operator-facing name — its titleized MEANING FOLDER.
 *  `operation/ir-deck-v3/deck.html` → "Ir deck v3". Falls back to the titleized
 *  stem when the artifact sits directly in a root (no meaning folder). */
export function artifactNameFromPath(path: string): string {
  const parts = (path || '').split('/').filter(Boolean);
  if (parts.length === 0) return 'File';
  const parent = parts.length >= 2 ? parts[parts.length - 2] : null;
  // `workspace`/`operation` are the region, not a meaning folder (the server's
  // `artifact_name` makes the same carve against STUDIO_ARTIFACT_REGION).
  const isRegion = parent === 'operation' || parent === 'workspace';
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
