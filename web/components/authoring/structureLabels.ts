/**
 * structureLabels — the operator-word label map (ADR-511 D3, re-cut by ADR-544 D4).
 *
 * The file speaks HTML (`<section>`, `<div>`, `<h2>`); the chrome speaks
 * operator words. This module is the ONE mapping — the navigator, the Design
 * tab, the block menu, and the canvas runtime (projection.ts inlines
 * `labelForJS()` into the injected script) all derive their labels here. The
 * chrome never says "div" (ADR-443 D3 — the macOS rule; Claude Design's
 * `group (div)` breadcrumb is the counterexample we refuse).
 *
 * ADR-544 D4 — WHAT CHANGED, AND WHY IT WAS A DEFECT. This module's own
 * docstring promised operator words while three of its rungs returned raw
 * substrate strings:
 *
 *   - `if (kind) return kind`     → a `<div data-block="prose">` labelled PROSE,
 *                                   while the registry already declared
 *                                   `{"prose": {"label": "Text"}}`. The same
 *                                   object read "Text" in the menu you inserted
 *                                   it from and "PROSE" in the pane that
 *                                   described it — two vocabularies disagreeing
 *                                   by construction (ADR-544 §1.2).
 *   - `if (slot) return slot`     → MAIN / SIDE / A / B / C: free-form strings
 *                                   an LLM wrote into `data-slot`, shown
 *                                   verbatim to the operator. It didn't say
 *                                   "div"; it said "main".
 *   - `.cols` → "columns"         → a SKIN class surfaced as a structural rung,
 *                                   so one paragraph read `slide 2 › columns ›
 *                                   main` — two rungs, neither a chosen word.
 *
 * The law now: the four grains are **Slide · Layout · Area · Block**, and a
 * label is DERIVED (a block from the served registry, an Area from its role +
 * place) — never echoed from the substrate. `.cols` is a layout property of the
 * parent Area (D2), not a rung, so it produces no label at all.
 */

/** ADR-511 Phase 2 — the ONE page selector, structural. A page is a deck
 *  slide or a top-level section of the document body — identified by where
 *  it SITS, never by a proprietary attribute. Legacy `section[data-arrange]`
 *  pages match by position (they are main/body children); new pages need no
 *  attribute at all. Every consumer (ops, both canvas runtimes, the
 *  navigator, the surface's reconciliation) imports or inlines THIS constant
 *  so indices always agree. */
export const STRUCTURAL_PAGE_SEL = 'section.slide, :is(body, main, article) > section';

/** ADR-544 D2 — the Area roles, as the operator reads them. A raw
 *  `data-area` name is never a display word; the ROLE is the Area's identity
 *  and this is where it becomes English. `place` disambiguates same-role
 *  siblings ("Body (left)"), which is what `main`/`side` were doing badly. */
export const AREA_ROLE_LABELS: Record<string, string> = {
  heading: 'Heading',
  body: 'Body',
  media: 'Media',
  aside: 'Aside',
};

/** The label for an Area, from its role and optional place. Unknown roles
 *  degrade to "Area" rather than leaking the authored name — the whole point
 *  of D4 is that a free-form string never reaches the operator. */
export function areaLabel(role: string | null, place?: string | null): string {
  const base = (role && AREA_ROLE_LABELS[role]) || 'Area';
  return place ? `${base} (${place})` : base;
}

/** Label a structural element from its cheap, serializable facts. Mirrors the
 *  logic `labelForJS()` inlines for the iframe runtime — change both together.
 *
 *  `blockLabels` is the served registry's kind→label map (ADR-544 D4). It is
 *  optional ONLY because the vocabulary loads async; a missing map degrades to
 *  the kind, which is the pre-544 behavior and visibly wrong on purpose rather
 *  than silently plausible. */
export function labelForElement(
  el: {
    tagName: string;
    classList?: { contains(name: string): boolean } | null;
    getAttribute(name: string): string | null;
  },
  blockLabels?: Record<string, string> | null,
): string {
  const kind = el.getAttribute('data-block');
  if (kind) return blockLabels?.[kind] ?? kind; // the REGISTRY's word, not the attribute's
  const cl = el.classList ?? null;
  if (cl?.contains('slide')) return 'Slide';
  const role = el.getAttribute('data-area-role');
  if (role) return areaLabel(role, el.getAttribute('data-area-place'));
  // ADR-544 D2 — `.cols`/`.col` are the parent Area's declared LAYOUT, not a
  // grain. A `.col` that holds blocks carries the Area markers and was caught
  // above; a bare grid wrapper is structure the operator never addresses.
  const tag = el.tagName.toUpperCase();
  if (tag === 'SECTION') return 'Slide';
  if (tag === 'MAIN' || tag === 'ARTICLE') return 'Document';
  return 'Group';
}

/** The same ladder as a self-contained JS function body, for injection into
 *  the sandboxed canvas runtime (projection.ts template-string world — it
 *  cannot call this module at runtime, so it inlines this source).
 *
 *  The kind→label map arrives as `window.__yarnnnBlockLabels`, injected ahead
 *  of the runtime by `resolveArtifactHtml` — the same mechanism ADR-485 D3
 *  established for `__yarnnnMeasureBounds`. The runtime constants are
 *  module-level template strings and cannot close over per-projection data, so
 *  served values reach them as globals, never as baked literals. */
export function labelForJS(fnName: string): string {
  const roles = JSON.stringify(AREA_ROLE_LABELS);
  return `function ${fnName}(el) {
    if (!el || !el.getAttribute) return 'Group';
    var LABELS = window.__yarnnnBlockLabels || {};
    var ROLES = ${roles};
    var kind = el.getAttribute('data-block');
    if (kind) return LABELS[kind] || kind;
    var cl = el.classList;
    if (cl && cl.contains('slide')) return 'Slide';
    var role = el.getAttribute('data-area-role');
    if (role) {
      var base = ROLES[role] || 'Area';
      var place = el.getAttribute('data-area-place');
      return place ? base + ' (' + place + ')' : base;
    }
    var tag = (el.tagName || '').toUpperCase();
    if (tag === 'SECTION') return 'Slide';
    if (tag === 'MAIN' || tag === 'ARTICLE') return 'Document';
    return 'Group';
  }`;
}
