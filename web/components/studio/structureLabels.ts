/**
 * structureLabels — the operator-word label map (ADR-511 D3).
 *
 * The file speaks HTML (`<section>`, `<div>`, `<h2>`); the chrome speaks
 * operator words (slide, columns, column, heading). This module is the ONE
 * mapping — the navigator, the Design tab, the block menu, and the canvas
 * runtime (projection.ts inlines `labelForJS()` into the injected script) all
 * derive their labels here. The chrome never says "div" (ADR-443 D3 — the
 * macOS rule; Claude Design's `group (div)` breadcrumb is the counterexample
 * we refuse).
 */

/** Label a structural element from its cheap, serializable facts. Mirrors the
 *  logic `labelForJS()` inlines for the iframe runtime — change both together. */
export function labelForElement(el: {
  tagName: string;
  classList?: { contains(name: string): boolean } | null;
  getAttribute(name: string): string | null;
}): string {
  const kind = el.getAttribute('data-block');
  if (kind) return kind; // vocabulary blocks label as their kind (heading, prose…)
  const cl = el.classList ?? null;
  if (cl?.contains('slide')) return 'slide';
  const slot = el.getAttribute('data-slot');
  if (slot) return slot; // a named region keeps its authored name (side, media…)
  if (cl?.contains('cols')) return 'columns';
  if (cl?.contains('col')) return 'column';
  const tag = el.tagName.toUpperCase();
  if (tag === 'SECTION') return 'section';
  if (tag === 'MAIN' || tag === 'ARTICLE') return 'document';
  return 'group';
}

/** The same ladder as a self-contained JS function body, for injection into
 *  the sandboxed canvas runtime (projection.ts template-string world — it
 *  cannot call this module at runtime, so it inlines this source). */
export function labelForJS(fnName: string): string {
  return `function ${fnName}(el) {
    if (!el || !el.getAttribute) return 'group';
    var kind = el.getAttribute('data-block');
    if (kind) return kind;
    var cl = el.classList;
    if (cl && cl.contains('slide')) return 'slide';
    var slot = el.getAttribute('data-slot');
    if (slot) return slot;
    if (cl && cl.contains('cols')) return 'columns';
    if (cl && cl.contains('col')) return 'column';
    var tag = (el.tagName || '').toUpperCase();
    if (tag === 'SECTION') return 'section';
    if (tag === 'MAIN' || tag === 'ARTICLE') return 'document';
    return 'group';
  }`;
}
