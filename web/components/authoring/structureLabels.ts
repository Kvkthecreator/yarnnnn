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
 * The law now: the four grains are **Frame · Layout · Area · Block**, and a
 * label is DERIVED (a block from the served registry, an Area from its role +
 * place) — never echoed from the substrate. `.cols` is a layout property of the
 * parent Area (D2), not a rung, so it produces no label at all.
 *
 * ADR-633 D3 — the FRAME grain's word is the APP's, not the class's. The frame
 * is a `section.slide` on Slides and on IMAGES alike (the class is the kernel's
 * staged grain, D1), and reading that class literally made the chrome call an
 * artboard a "Slide" in the crumb while the rail called it a "Section" — two
 * wrong nouns for one object, neither of which is what it is. `frameNoun()` is
 * the one source; `objectModel` threads from the app row to every consumer.
 */

/** ADR-511 Phase 2 — the ONE page selector, structural. A page is a deck
 *  slide or a top-level section of the document body — identified by where
 *  it SITS, never by a proprietary attribute. Legacy `section[data-arrange]`
 *  pages match by position (they are main/body children); new pages need no
 *  attribute at all. Every consumer (ops, both canvas runtimes, the
 *  navigator, the surface's reconciliation) imports or inlines THIS constant
 *  so indices always agree. */
export const STRUCTURAL_PAGE_SEL = 'section.slide, :is(body, main, article) > section';

/** The REGION grain — an Area (`data-area`) or an un-healed legacy region
 *  (`data-slot`, retired by ADR-544 D2 and still present in older documents).
 *
 *  ADR-544 D7 states the rule this constant makes enforceable: every consumer
 *  of the region grain reads BOTH. It was true of the projection's payload and
 *  climb, of `applyArrangement`'s mapping, and of the label ladder — and false
 *  in exactly one place, `normalizeStructure`'s container predicate, which
 *  tested `data-slot` alone. That pass MINTS IDS, so the one divergent reader
 *  was the one that decided whether a region could be addressed at all: every
 *  empty Area on every new slide went unstamped, and the "+ Add" the runtime
 *  drew inside it posted a message the surface dropped for want of an id.
 *
 *  Spelled once, here, so the pair cannot drift again (the 2026-08-28 audit;
 *  the predicate predated the `data-area` migration and was never swept). */
export const REGION_SEL = '[data-area], [data-slot]';

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

/** ADR-633 D2/D3 — the app's property model, as the label ladder reads it.
 *  Structurally identical to `AuthoringApp['objectModel']`, redeclared here so
 *  the vocabulary seam does not import the surface (the dependency runs the
 *  other way: StudioSurface imports this module). */
export type ObjectModel = 'flow' | 'pages' | 'layers';

/** ADR-633 D3 — THE ONE SOURCE for the frame's noun.
 *
 *  The frame is a `section.slide` on both apps: the class IS the staged grain
 *  and D1 keeps it shared (ADR-472 D2). What changed is that the chrome stops
 *  reading a CLASS NAME as a DISPLAY WORD. The noun comes from the app's
 *  declared model, so an artboard reads "Artboard" in the crumb, the Esc-walk,
 *  the pane's path and the injected canvas runtime — one word, every site.
 *
 *  D6 is explicit that there is no `'Artboard'` alias sitting beside `'Slide'`
 *  in a lookup table: a second entry is a second thing to keep in step, and
 *  §1.1's whole defect was two chrome sites disagreeing about one object. This
 *  function is the only place either word is spelled, and `labelForJS()`
 *  RESOLVES it at composition rather than restating the ladder — so the pane's
 *  crumb and the in-canvas runtime cannot drift by construction.
 *
 *  Undefined model → "Slide": the pre-633 word, for the callers that reach the
 *  ladder without an app in scope (the projection's own hover-label pass). It
 *  is NOT a default for an app row — D2 forbids that, and `objectModel` is
 *  required precisely so no app can arrive here undeclared. */
export function frameNoun(objectModel?: ObjectModel | null): string {
  return objectModel === 'layers' ? 'Artboard' : 'Slide';
}

/** Label a structural element from its cheap, serializable facts. Mirrors the
 *  logic `labelForJS()` inlines for the iframe runtime — change both together.
 *
 *  `blockLabels` is the served registry's kind→label map (ADR-544 D4). It is
 *  optional ONLY because the vocabulary loads async; a missing map degrades to
 *  the kind, which is the pre-544 behavior and visibly wrong on purpose rather
 *  than silently plausible.
 *
 *  `objectModel` is the app's declared property model (ADR-633 D2) and decides
 *  the FRAME's noun only — every other rung is medium-independent. It threads
 *  from the app row through the surface; see `frameNoun` for why it is not a
 *  table entry. */
export function labelForElement(
  el: {
    tagName: string;
    classList?: { contains(name: string): boolean } | null;
    getAttribute(name: string): string | null;
  },
  blockLabels?: Record<string, string> | null,
  mode?: 'flow' | 'paged' | null,
  objectModel?: ObjectModel | null,
): string {
  const kind = el.getAttribute('data-block');
  if (kind) return blockLabels?.[kind] ?? kind; // the REGISTRY's word, not the attribute's
  // ── ADR-546 D5: the four words are PER MEDIUM ───────────────────────────
  //
  // A document's grains are Document · Rung · Block · Range — there is no Slide,
  // no Layout and no Area on flow, by derivation (ADR-546 D0: a capture surface
  // that asks "where on the page" has stopped being one).
  //
  // Pre-546 this ladder was deck-scoped in its DOCSTRING and global in its
  // REACH: the flow click handler, the Esc-walk and the edit runtime all call it
  // ungated, so a <section> in a document labelled "Slide" and a bare structural
  // div labelled "Group" — the very word ADR-544 D7 spent a commit removing from
  // the deck crumb. ADR-544 F2 forbade the substrate's words "for deck
  // structure" and so was ONE-DIRECTIONAL; nothing forbade a deck word on flow.
  // The falsifier is symmetric now (ADR-546 F1/F5).
  //
  // On flow the honest answer for a structural element is the DOCUMENT itself:
  // the member never addresses a container there, so naming one is the chrome
  // promising a grain the medium does not have (rule 6).
  if (mode === 'flow') return 'Document';
  const cl = el.classList ?? null;
  // ADR-633 D3 — the frame's noun is the APP's word, not the class's. `.slide`
  // stays the class (D1: it is the kernel's grain boundary and forking it to
  // fix a display string is the over-reach this ADR refuses).
  if (cl?.contains('slide')) return frameNoun(objectModel);
  const role = el.getAttribute('data-area-role');
  if (role) return areaLabel(role, el.getAttribute('data-area-place'));
  // ADR-544 D7 — the LEGACY rung. An un-healed document still carries
  // `data-slot`, and every OTHER consumer of the region grain reads
  // `[data-area], [data-slot]` (projection's payload + climb, applyArrangement's
  // mapping). This ladder alone had no fallback, so a pre-heal deck's regions
  // fell through to "Group" and the crumb read `Slide 2 › Group › Group › Text`
  // — the vocabulary applied to blocks but not to the regions around them,
  // which is worse than either state because it hides WHICH layer is stale.
  //
  // A legacy region is an Area whose role was never stamped: label it "Area",
  // never its authored name (D4 — a free-form string is data, not a word).
  if (el.getAttribute('data-slot') !== null) return areaLabel(null);
  // ADR-544 D2 — `.cols`/`.col` are the parent Area's declared LAYOUT, not a
  // grain. A `.col` that holds blocks carries the Area markers and was caught
  // above; a bare grid wrapper is structure the operator never addresses.
  const tag = el.tagName.toUpperCase();
  // ADR-633 D3 — the same frame, reached by tag rather than class (an artboard
  // or slide whose class was stripped). Both rungs name ONE object, so both
  // take the app's noun; splitting them is how §1.1's two-nouns defect starts.
  if (tag === 'SECTION') return frameNoun(objectModel);
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
 *  served values reach them as globals, never as baked literals.
 *
 *  ADR-633 D3 — the frame's noun rides the SAME global channel, as
 *  `window.__yarnnnFrameNoun`, and for the same reason: the two runtime
 *  constants that inline this ladder (`POINTER_SCRIPT`, `OBJECT_SCRIPT`) are
 *  module-level template strings evaluated once at import, so a per-projection
 *  value cannot reach them as a baked literal.
 *
 *  What matters for D6 is that the WORD is still resolved by `frameNoun()` —
 *  once, at the injection site — and never re-derived here. This ladder does
 *  not test the model; it reads the answer. Restating `layers ? … : …` as a
 *  second JS ternary would be exactly the drift this ADR is fixing: the pane's
 *  crumb and the in-canvas runtime disagreeing about one object (§1.1).
 *
 *  The fallback is `frameNoun(null)` = "Slide" — the pre-633 word, for a
 *  projection composed without the global (a viewer with no app in scope). It
 *  is a READ fallback, not an app default: D2 forbids the latter. */
export function labelForJS(fnName: string): string {
  const roles = JSON.stringify(AREA_ROLE_LABELS);
  const frame = JSON.stringify(frameNoun(null));
  return `function ${fnName}(el) {
    if (!el || !el.getAttribute) return 'Group';
    var LABELS = window.__yarnnnBlockLabels || {};
    var ROLES = ${roles};
    // ADR-633 D3 — the frame's noun, RESOLVED by frameNoun() at the injection
    // site and read here. The runtime does not know what a 'layers' app is; it
    // knows the word the chrome chose (see the docstring).
    var FRAME = window.__yarnnnFrameNoun || ${frame};
    var kind = el.getAttribute('data-block');
    if (kind) return LABELS[kind] || kind;
    // ADR-546 D5 — the flow rung of the ladder (see labelForElement). The mode
    // reaches the runtime the same way every other served fact does: as a global
    // read off the document, never a baked literal.
    if (document.documentElement.getAttribute('data-yarnnn-mode') === 'flow') return 'Document';
    var cl = el.classList;
    // ADR-633 D3 — the app's word, resolved at composition (see the docstring).
    if (cl && cl.contains('slide')) return FRAME;
    var role = el.getAttribute('data-area-role');
    if (role) {
      var base = ROLES[role] || 'Area';
      var place = el.getAttribute('data-area-place');
      return place ? base + ' (' + place + ')' : base;
    }
    // ADR-544 D7 — the legacy rung (see labelForElement; change both together).
    if (el.getAttribute('data-slot') !== null) return 'Area';
    var tag = (el.tagName || '').toUpperCase();
    if (tag === 'SECTION') return FRAME;
    if (tag === 'MAIN' || tag === 'ARTICLE') return 'Document';
    return 'Group';
  }`;
}
