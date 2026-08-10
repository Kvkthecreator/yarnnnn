/**
 * artifactOps — deterministic structural operations on a Studio artifact
 * (ADR-444: the mechanical layer).
 *
 * These are the PowerPoint-class executions: insert a block at the selection,
 * add a slide from a container layout, apply a container layout to a selected
 * slide. Pure DOM transforms computed in the FE and landed through the
 * Studio's mechanical write door (POST /studio/artifacts/write) as ONE
 * operator-attributed, CAS-guarded revision. No LLM — deterministic member
 * acts; the lane stays the judgment path.
 *
 * Discipline: existing data-block-id values are NEVER renumbered or dropped;
 * new blocks get fresh ids; a container reflow moves blocks intact into the
 * new arrangement's first [data-slot].
 */

import { STRUCTURAL_PAGE_SEL } from './structureLabels';
import { DEEPEST_RUNG, OUT_OF_RUNG_TAGS } from '../workspace/viewers/projection';

function parse(html: string): Document {
  return new DOMParser().parseFromString(html, 'text/html');
}

function serialize(doc: Document): string {
  // ADR-511 D5 — the one write seam normalizes structure on the way out:
  // every op's result carries full identity (bare content promoted, structural
  // containers stamped), so unannotated HTML becomes native on its first write
  // (migration-by-use — no fleet migration, no write-on-open revision).
  normalizeStructure(doc);
  return '<!doctype html>\n' + (doc.documentElement?.outerHTML ?? '');
}

function freshBlockId(doc: Document): string {
  const used = new Set(
    Array.from(doc.querySelectorAll('[data-block-id]')).map(
      (el) => el.getAttribute('data-block-id') ?? '',
    ),
  );
  for (let i = 0; i < 10_000; i++) {
    const id = `b${Math.random().toString(36).slice(2, 6)}`;
    if (!used.has(id)) return id;
  }
  return `b${Date.now().toString(36)}`;
}

/** Parse a fragment string into an element, stamping fresh block ids on
 *  every annotated node inside it (the served fragments carry example ids). */
function materializeFragment(doc: Document, fragment: string): Element | null {
  const tpl = doc.createElement('template');
  tpl.innerHTML = fragment.trim();
  const root = tpl.content.firstElementChild;
  if (!root) return null;
  const annotated = [
    ...(root.hasAttribute('data-block-id') ? [root] : []),
    ...Array.from(root.querySelectorAll('[data-block-id]')),
  ];
  annotated.forEach((el) => el.setAttribute('data-block-id', freshBlockId(doc)));
  return doc.importNode(root, true) as Element;
}

/** ADR-511 Phase 2 — structural containers of a page, document order: divs
 *  outside any block/citation (the same predicate as normalizeStructure pass
 *  B and the projection's label pass — one definition of "container"). */
function containerTargets(page: Element): Element[] {
  return Array.from(page.querySelectorAll('div')).filter(
    (el) =>
      !el.hasAttribute('data-block') &&
      !el.hasAttribute('data-ref') &&
      !el.parentElement?.closest('[data-block], [data-ref]'),
  );
}
/** The first LEAF container — the innermost content region an unanchored
 *  insert lands in (a column, never the columns row that holds it). Replaces
 *  the `[data-slot]` targeting: position decides, not a proprietary name. */
function firstLeafContainer(page: Element): Element | null {
  const all = containerTargets(page);
  return all.find((c) => !all.some((o) => o !== c && c.contains(o))) ?? null;
}

/** The default flow container new blocks append into when nothing is
 *  selected: the last slide's first leaf container (deck), <main> (document),
 *  <article>. */
function defaultFlow(doc: Document): Element {
  const slides = doc.querySelectorAll('section.slide');
  if (slides.length) {
    const last = slides[slides.length - 1];
    return firstLeafContainer(last) ?? last;
  }
  return doc.querySelector('main') ?? doc.querySelector('article') ?? doc.body;
}

export interface OpResult {
  html: string;
  /** The id of the block/container the op landed, for future selection. */
  landedId: string | null;
}

/** Where an operation anchors: the selected block, the selected slide (deck),
 *  and/or the selected page index (ADR-453 — index into the document-order
 *  `section.slide, [data-arrange]` set, so document/article sections anchor
 *  page ops too; the canvas runtime posts the same index). */
export interface OpAnchor {
  blockId?: string | null;
  slideIndex?: number | null;
  pageIndex?: number | null;
}

/** The selector that names a PAGE — ADR-511 Phase 2: STRUCTURAL, imported
 *  from the one vocabulary seam so ops, both canvas runtimes, the navigator
 *  and the surface always agree on indices. Legacy `[data-arrange]` sections
 *  match by position (main/body children); the attribute is an inert name. */
const PAGE_SEL = STRUCTURAL_PAGE_SEL;

/** The page-grain element enclosing the anchor (ADR-447; structural per
 *  ADR-511 Phase 2). `slideIndex` (the pointer's enclosing-slide index) still
 *  resolves a deck slide with no block (a title slide); `pageIndex` resolves
 *  any page. */
function arrangedPageAt(doc: Document, anchor: OpAnchor): Element | null {
  // ADR-519 §5 Q1 — the ID path, first. Since pages are stamped at the
  // normalize seam (2026-08-06) an anchor's `blockId` may BE a page's own id,
  // and `closest` includes the element itself, so this one lookup resolves
  // both "the page holding this block" and "this page". The index fallbacks
  // below serve artifacts not yet written since the stamp landed, and retire
  // by attrition (migration-by-use — no fleet sweep).
  if (anchor.blockId) {
    const viaBlock = doc
      .querySelector(`[data-block-id="${CSS.escape(anchor.blockId)}"]`)
      ?.closest(PAGE_SEL);
    if (viaBlock) return viaBlock;
  }
  const slides = doc.querySelectorAll('section.slide');
  if (anchor.slideIndex != null && slides[anchor.slideIndex]) {
    return slides[anchor.slideIndex];
  }
  const pages = doc.querySelectorAll(PAGE_SEL);
  if (anchor.pageIndex != null && pages[anchor.pageIndex]) {
    return pages[anchor.pageIndex];
  }
  return null;
}

/** Insert a block (from its vocabulary fragment) after the selected block,
 *  into the selected slide's slot, or append to the default flow. */
export function insertBlock(
  html: string,
  fragment: string,
  anchor: OpAnchor,
): OpResult | null {
  const doc = parse(html);
  const el = materializeFragment(doc, fragment);
  if (!el) return null;
  const anchorEl = anchor.blockId
    ? doc.querySelector(`[data-block-id="${CSS.escape(anchor.blockId)}"]`)
    : null;
  // ADR-511 Phase 2 — the anchor decides structurally: a selected BLOCK →
  // insert after it; a selected CONTAINER (identity, no vocabulary) → append
  // INTO it (this is what makes a column an explicit insert target); no
  // anchor → the page's first leaf container, else the page itself.
  if (anchorEl?.parentElement && anchorEl.hasAttribute('data-block')) {
    anchorEl.insertAdjacentElement('afterend', el);
  } else if (anchorEl && !anchorEl.hasAttribute('data-block')) {
    anchorEl.appendChild(el);
  } else {
    const page = arrangedPageAt(doc, anchor);
    const target = page ? (firstLeafContainer(page) ?? page) : defaultFlow(doc);
    target.appendChild(el);
  }
  return { html: serialize(doc), landedId: el.getAttribute('data-block-id') };
}

/** Build a gallery fragment from the registry's base fragment + the picked
 *  image paths (ADR-456 W1): the base's single <figure> is the prototype,
 *  cloned once per path with its data-ref swapped. Registry-driven — the
 *  wrapper (annotation, kind) always comes from the served vocabulary. */
export function galleryFragment(
  base: string,
  paths: string[],
  pins?: Record<string, string | null>,
): string | null {
  if (!paths.length) return null;
  const tpl = document.createElement('template');
  tpl.innerHTML = base.trim();
  const root = tpl.content.firstElementChild;
  const proto = root?.querySelector('figure');
  if (!root || !proto) return null;
  root.innerHTML = '';
  for (const p of paths) {
    const fig = proto.cloneNode(true) as Element;
    const img = fig.querySelector('img');
    if (!img) continue;
    img.setAttribute('data-ref', p);
    // The PIN (ADR-440 D5), stamped at the moment of citation. Empty only when
    // the cited file predates the ADR-209 chain and truly has no head revision.
    img.setAttribute('data-ref-rev', pins?.[p] ?? '');
    img.setAttribute('alt', '');
    root.appendChild(fig);
  }
  return root.outerHTML;
}

/** Insert a block into a CONTAINER by identity (ADR-511 Phase 2 re-cut of
 *  the slot-name-addressed insertBlockInSlot — the empty-region "+ Add here"
 *  and the media picker both land here). The container carries data-block-id
 *  from the load-normalize, so the address is the same one every other op
 *  uses. A placeholder "+ Add here" button inside is ignored (not a block). */
export function insertIntoContainer(
  html: string,
  fragment: string,
  containerId: string,
): OpResult | null {
  const doc = parse(html);
  const el = materializeFragment(doc, fragment);
  if (!el) return null;
  const target = doc.querySelector(`[data-block-id="${CSS.escape(containerId)}"]`);
  if (!target || target.hasAttribute('data-block')) return null;
  target.appendChild(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-block-id') };
}

/** Insert a new arrangement (a slide / a section, from its fragment) after the
 *  selected page, or at the end of the artifact (ADR-447 — generalizes
 *  insertSlide to any layout). */
export function insertArrangement(
  html: string,
  fragment: string,
  anchor: OpAnchor,
): OpResult | null {
  const doc = parse(html);
  const el = materializeFragment(doc, fragment);
  if (!el) return null;
  const pages = doc.querySelectorAll(PAGE_SEL);
  const after = arrangedPageAt(doc, anchor) ?? (pages.length ? pages[pages.length - 1] : null);
  if (after?.parentElement) after.insertAdjacentElement('afterend', el);
  else (doc.querySelector('main') ?? doc.querySelector('article') ?? doc.body).appendChild(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-arrange') };
}

/** Strip every executable from a fragment of member-typed inner HTML before
 *  it lands in the source (ADR-446 D2): script/iframe/object/embed elements,
 *  inline on* handlers, javascript: URLs. Typing must not inject a script. */
function sanitizeInner(doc: Document, inner: string): string {
  const holder = doc.createElement('div');
  holder.innerHTML = inner;
  holder.querySelectorAll('script, iframe, object, embed').forEach((el) => el.remove());
  holder.querySelectorAll('*').forEach((el) => {
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      if (name.startsWith('on')) el.removeAttribute(attr.name);
      else if (
        (name === 'href' || name === 'src') &&
        attr.value.trim().toLowerCase().startsWith('javascript:')
      ) {
        el.removeAttribute(attr.name);
      }
    }
  });
  // ADR-456 W2: the format bar rides execCommand, which emits <b>/<i> —
  // normalize to the semantic tags the source speaks (strong/em).
  //
  // ADR-527 D1 extends the same rule to the two new toggles. `underline` emits
  // <u>, which IS the semantic tag and passes through. `strikeThrough` emits
  // <strike> in some engines and <s> in others — one source vocabulary, so the
  // legacy presentational tag normalizes to <s>. Attributes ride across on
  // every branch (a mark span nested inside is untouched either way).
  const NORMALIZE: Record<string, string> = { B: 'strong', I: 'em', STRIKE: 's' };
  holder.querySelectorAll('b, i, strike').forEach((el) => {
    const repl = doc.createElement(NORMALIZE[el.tagName] ?? el.tagName.toLowerCase());
    for (const attr of Array.from(el.attributes)) repl.setAttribute(attr.name, attr.value);
    while (el.firstChild) repl.appendChild(el.firstChild);
    el.replaceWith(repl);
  });
  return holder.innerHTML;
}

/** Direct text edit (ADR-446): replace the inner HTML of the block whose
 *  data-block-id matches, in the SOURCE html. The `newInner` arrives from the
 *  canvas edit runtime already source-mapped (citation islands restored to
 *  their living-reference form); this pass sanitizes it and swaps it in. The
 *  block's id, kind, and every other attribute are untouched — only its
 *  content changes. Returns null (no revision) if the block is gone or the
 *  content is byte-identical (a no-op edit lands nothing). */
export function editBlockText(
  html: string,
  blockId: string,
  newInner: string,
): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block) return null;
  const sanitized = sanitizeInner(doc, newInner);
  if (block.innerHTML === sanitized) return null; // no-op — no revision
  block.innerHTML = sanitized;
  return { html: serialize(doc), landedId: blockId };
}

/** ADR-511 D5 — normalize structure: full identity across the WHOLE document,
 *  every mode, every depth. Generalizes ADR-480 D3's flow-only, one-level
 *  `normalizeBlockIds` (deleted — this is its singular replacement) so that
 *  unannotated HTML — imports, agent output, template placeholders, the bare
 *  elements native Enter mints — becomes addressable, and therefore editable,
 *  on its first write. Runs at the one serialize seam.
 *
 *  Three passes, in order:
 *
 *    A. PROMOTION — a content-bearing element outside any block/citation is
 *       promoted into the block grammar with a tag-derived kind (headings →
 *       heading, blockquote → quote, table → table, figure → figure, the
 *       rest → prose). A `<div>` promotes only when it reads as content (no
 *       block-level element children); a div that HOLDS blocks is structure,
 *       pass B's subject. `<br>`-only / empty elements are left alone (the
 *       annihilation guard already treats them as empty).
 *    B. CONTAINER IDENTITY — a `<div>` that encloses at least one block and
 *       is not itself inside a block/citation is stamped `data-block-id`
 *       (identity WITHOUT vocabulary — never `data-block`). This is what
 *       makes columns/rows/slots selectable and lets the id-addressed ops
 *       (delete/duplicate/move/measure) work on them with no op-side change.
 *    C. ID DISCIPLINE — unchanged from ADR-480 D3: a surviving id keeps its
 *       element; a duplicated id (native split) is kept by the FIRST in
 *       document order, later ones re-minted; an absent id is minted fresh;
 *       a citation island (`data-ref`) is never re-minted or restructured
 *       (the ADR-448 reference edge lifts from data-ref, untouched).
 *
 *  Idempotent; content is never dropped; mutates `doc` in place. Returns the
 *  number of ids minted (0 = fully annotated already, the common case). */
const PROMOTE_KIND: Record<string, string> = {
  // ADR-539 D2/D4 — this map is a pinned projection of the registry's
  // {elements × promote} declaration (the parity gate compares it against
  // studio.py). H4–H6 LEFT the map: pass A0 below clamps them to the deepest
  // declared rung BEFORE promotion runs, so a heading the vocabulary cannot
  // speak never reaches the recognizer.
  H1: 'heading', H2: 'heading', H3: 'heading',
  BLOCKQUOTE: 'quote', TABLE: 'table', FIGURE: 'figure',
  // ADR-536 D1 — UL/OL promote to their OWN kinds. They read `prose` until now
  // because no list kind existed to promote to, which is why a pasted list
  // reported as "prose" in the properties pane and Turn-into offered it the
  // prose roster. A <ul> is not a paragraph; naming it one was the registry
  // gap surfacing at the recognizer.
  //
  // A `checklist` is also a <ul>, and stays unreachable from here on purpose:
  // promotion is a guess from a TAG, and the checkbox list is the marked
  // special case (list-style:none + the ☐ rule). Guessing plain is the honest
  // default — the member reaches checklist through Turn into, deliberately.
  UL: 'list', OL: 'numbered',
  P: 'prose', DIV: 'prose', PRE: 'prose',
};
const BLOCK_LEVEL = new Set(Object.keys(PROMOTE_KIND).concat(['SECTION', 'MAIN', 'ARTICLE', 'HEADER', 'FOOTER']));

export function normalizeStructure(doc: Document): number {
  const root = doc.body;
  if (!root) return 0;
  const insideOwned = (el: Element): boolean =>
    !!el.parentElement?.closest('[data-block], [data-ref]');
  const isPage = (el: Element): boolean => el.matches(PAGE_SEL);

  // Pass A0 — ADR-539 D4: intake clamps to the declared rung set. An
  // out-of-rung heading (h4–h6) is renamed to the deepest spoken rung on the
  // artifact's NEXT write — migration-by-use, never a sweep. This is the one
  // pass that changes an element's TAG: content and attributes carry over
  // whole, so nothing is dropped; only a rung the system never speaks (and
  // whose blocks were therefore invisible to the outline, the crumb, and the
  // lane) stops existing at the door. Runs before every other pass so
  // promotion and the container walk see only in-rung headings.
  for (const el of Array.from(root.querySelectorAll(OUT_OF_RUNG_TAGS.join(',')))) {
    const clamped = doc.createElement(`h${DEEPEST_RUNG}`);
    for (const name of el.getAttributeNames()) {
      clamped.setAttribute(name, el.getAttribute(name) ?? '');
    }
    while (el.firstChild) clamped.appendChild(el.firstChild);
    el.replaceWith(clamped);
  }

  // Pass A — promotion, any depth. Snapshot first: promotion mutates the set.
  for (const el of Array.from(root.querySelectorAll(Object.keys(PROMOTE_KIND).join(',')))) {
    if (el.hasAttribute('data-block') || el.hasAttribute('data-ref')) continue;
    if (insideOwned(el) || isPage(el)) continue;
    if ((el.textContent ?? '').trim() === '') continue; // <br>-only / empty
    if (el.tagName === 'DIV') {
      // A div holding block-level children is structure (pass B), not content.
      const holdsBlocks = Array.from(el.children).some((c) => BLOCK_LEVEL.has(c.tagName));
      if (holdsBlocks) continue;
    }
    el.setAttribute('data-block', PROMOTE_KIND[el.tagName]);
  }

  // Pass B — container identity: divs that enclose blocks, outside any block.
  // A DECLARED region (data-slot) is structure even while empty — the media
  // picker's "+ Add here" selects it before it holds anything.
  const containers = Array.from(root.querySelectorAll('div')).filter(
    (el) =>
      !el.hasAttribute('data-block') &&
      !el.hasAttribute('data-ref') &&
      !insideOwned(el) &&
      !isPage(el) &&
      (!!el.querySelector('[data-block]') || el.hasAttribute('data-slot')),
  );

  // Pass B2 — PAGE identity (ADR-519 §5 Q1, resolved YES at ratification;
  // landed 2026-08-06). Pages were the one grain addressed by INDEX while
  // blocks and containers carry ids, and ADR-516 built a second, anchor-based
  // resolver to cope with it. Stamping the page closes that split: one
  // resolver, and the breadcrumb / ops / set-membership all address every
  // grain the same way.
  //
  // Migration-by-use, exactly like the ADR-511 annotation pattern: a page gets
  // its id on the artifact's NEXT write, never by a fleet sweep and never by a
  // write-on-open revision. The anchor path survives for artifacts not yet
  // written (see `arrangedPageAt`, which tries blockId → id → index in that
  // order), and retires by attrition.
  //
  // Safe because a page is a <section> and every container selector in the
  // system is `div[data-block-id]:not([data-block])` — a stamped page can
  // never read as a container. `climbChain` stops AT the page element, so its
  // un-qualified test is never reached either.
  const pages = Array.from(root.querySelectorAll(PAGE_SEL));

  // Pass C — id discipline over pages + blocks + containers, document order.
  const seen = new Set<string>();
  let minted = 0;
  const subjects = Array.from(root.querySelectorAll('[data-block], [data-block-id]'));
  for (const c of containers) if (!subjects.includes(c)) subjects.push(c);
  for (const p of pages) if (!subjects.includes(p)) subjects.push(p);
  // Document order matters for first-wins dedup; re-sort the merged set.
  subjects.sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
  for (const el of subjects) {
    if (el.hasAttribute('data-ref')) {
      const kept = el.getAttribute('data-block-id');
      if (kept) seen.add(kept);
      continue;
    }
    const id = el.getAttribute('data-block-id');
    if (!id || seen.has(id)) {
      const fresh = freshBlockId(doc);
      el.setAttribute('data-block-id', fresh);
      seen.add(fresh);
      minted++;
    } else {
      seen.add(id);
    }
  }
  return minted;
}

/** Normalize a raw artifact HTML string (ADR-511 D5's load-side entry): the
 *  surface calls this once when content arrives, so the live canvas and every
 *  subsequent op share one fully-addressed working copy; the identities land
 *  in the substrate with the first real write. */
export function normalizeArtifact(html: string): string {
  const doc = parse(html);
  return serialize(doc); // serialize() runs normalizeStructure
}

/** ADR-480 D1 — a flow-layout edit: the member wrote on ONE continuous
 *  surface (contenteditable on `<main>`/`<article>`), so the runtime reports
 *  the whole region's inner rather than one block's.
 *
 *  The ADR-446 write contract is preserved exactly: the edit maps to the
 *  artifact's SOURCE (the runtime restored citation islands to their
 *  living-reference form before posting), is sanitized here, and lands as ONE
 *  debounced operator-attributed CAS-guarded revision through the one door.
 *  What differs from `editBlockText` is only the size of the region and the
 *  normalize pass that follows it.
 *
 *  Returns null (no revision) when the region is gone, byte-identical, or
 *  would ANNIHILATE a non-empty document (see the guard below). */
export function editFlowRegion(
  html: string,
  regionSelector: string,
  newInner: string,
): OpResult | null {
  const doc = parse(html);
  const region = doc.querySelector(regionSelector);
  if (!region) return null;
  const sanitized = sanitizeInner(doc, newInner);
  if (region.innerHTML === sanitized) return null; // no-op — no revision

  // THE ANNIHILATION GUARD. Unlike `editBlockText`, which replaces ONE block,
  // this replaces the WHOLE document body — so the blast radius of a bad
  // `newInner` is the entire artifact, and it lands as a durable revision.
  //
  // The trigger is never a deliberate act. `flowCommit` fires from three
  // AUTOMATIC sources (projection.ts): idle-2s, a capture-phase `blur` on the
  // root, and `beforeunload`. Each reads the live DOM at whatever instant it
  // happens to run — including mid-teardown, when the root can already be
  // detached or emptied. A member who genuinely wants an empty document
  // deletes the blocks (an explicit op, undoable); nothing about "the region
  // read empty during a blur" carries that intent.
  //
  // So: refuse to be the write that takes a document from HAVING content to
  // having NONE. Emptiness is judged by ANNOTATED BLOCKS, not raw text —
  // contenteditable leaves `<br>` and stray whitespace behind on a select-all
  // delete, and a `<br>`-only body is exactly as destroyed as an empty one
  // (proven: empty / whitespace / `<br>` all reduced a live 4-block document
  // to 0 blocks). A document that was ALREADY block-empty is untouched by this
  // rule — it has nothing to lose, and this must not freeze a blank artifact.
  const hadBlocks = region.querySelectorAll('[data-block]').length > 0;
  if (hadBlocks) {
    const probe = doc.createElement('div');
    probe.innerHTML = sanitized;
    if (probe.querySelectorAll('[data-block]').length === 0) return null;
  }

  region.innerHTML = sanitized;
  // Identity re-establishment (splits/merges/native Enter) happens in
  // serialize()'s normalizeStructure pass — the one seam (ADR-511 D5).
  return { html: serialize(doc), landedId: null };
}

/** Turn a block into another TEXT kind (ADR-456 W2 "turn into"): the target
 *  kind's registry fragment is the shell; the source block's text units
 *  (li/p/heading/summary/cite, document order) are rebuilt into the target's
 *  shape; the block's id and its property tokens survive. Blocks containing
 *  citations refuse to convert (a data-ref must never flatten to text);
 *  same-kind conversions no-op. */
export function convertBlock(
  html: string,
  blockId: string,
  kind: string,
  fragment: string,
): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block) return null;
  // Citations never flatten — check the block's OWN ref (figure/table wear
  // data-ref on their root) as well as any descendant. A root-ref block that
  // slipped past a descendant-only check would keep its live citation pin on
  // the flattened text shell below — a text block dangling a reference.
  if (block.hasAttribute('data-ref') || block.querySelector('[data-ref]')) return null;
  const tpl = doc.createElement('template');
  tpl.innerHTML = fragment.trim();
  const shell = tpl.content.firstElementChild;
  if (!shell) return null;
  // No-op = same kind AND same tag (ADR-487 D1): a heading level change is
  // same-kind/different-tag, so the guard compares both — kind alone would
  // make the rungs unreachable.
  if (block.getAttribute('data-block') === kind && block.tagName === shell.tagName) {
    return null;
  }
  // ADR-539 — the harvest is deliberately WIDER than the rung set (h1–h6):
  // it extracts text units losslessly from whatever markup exists, including
  // a not-yet-normalized artifact still holding pre-clamp h5/h6 headings.
  const units = Array.from(block.querySelectorAll('li, p, h1, h2, h3, h4, h5, h6, summary, cite'))
    .map((el) => (el.textContent ?? '').trim())
    .filter(Boolean);
  if (!units.length) {
    const whole = (block.textContent ?? '').trim();
    if (whole) units.push(whole);
  }
  // Rebuild the content in the target's shape — text harvested, never markup
  // (inline formatting inside a converted block is the one accepted loss).
  const built: Array<[string, string]> = [];
  if (kind === 'heading') {
    // A heading is ONE line on the ramp (ADR-487 D1) — the shell (h1/h2/h3)
    // holds the text directly, no child units. Joining keeps every unit's
    // text (content is never dropped, shape is the accepted loss).
    built.push(['__self__', units.length ? units.join(' ') : 'Heading']);
    // ADR-536 D1 — the list kinds join `checklist` here, not the `<p>` default
    // below: their shell is a <ul>/<ol>, whose only legal child is <li>. The
    // fallback would have built `<ul><p>…</p></ul>` — invalid markup that
    // renders as unmarked text, i.e. a Turn into that visibly does nothing.
    // One line, because a list IS the checklist's shape minus the ☐.
  } else if (kind === 'checklist' || kind === 'list' || kind === 'numbered') {
    (units.length ? units : ['…']).forEach((u) => built.push(['li', u]));
  } else if (kind === 'quote') {
    built.push(['p', units[0] ?? '…']);
    if (units.length > 1) built.push(['cite', units.slice(1).join(' — ')]);
  } else if (kind === 'toggle') {
    built.push(['summary', units[0] ?? 'Summary line']);
    const rest = units.slice(1);
    (rest.length ? rest : ['…']).forEach((u) => built.push(['p', u]));
  } else {
    (units.length ? units : ['…']).forEach((u) => built.push(['p', u]));
  }
  shell.innerHTML = '';
  for (const [tag, text] of built) {
    if (tag === '__self__') {
      shell.textContent = text; // the shell IS the unit (heading)
      continue;
    }
    const child = doc.createElement(tag);
    child.textContent = text;
    shell.appendChild(child);
  }
  // Identity + tokens survive: same id; every data-* except the kind itself.
  shell.setAttribute('data-block', kind);
  shell.setAttribute('data-block-id', blockId);
  for (const attr of Array.from(block.attributes)) {
    if (
      attr.name.startsWith('data-') &&
      attr.name !== 'data-block' &&
      attr.name !== 'data-block-id'
    ) {
      shell.setAttribute(attr.name, attr.value);
    }
  }
  block.replaceWith(doc.importNode(shell, true));
  return { html: serialize(doc), landedId: blockId };
}

// ── ADR-453: the property layer + the mechanical verb completion ──────────
//
// Tokens, not pixels: a property edit sets/clears a data-* attribute whose
// values are a small named set (align/tone/height/fit/ratio/valign), styled
// by the MARKED kernel style element (<style data-kernel="true">). Any token
// op ENSURES that element exists at the served version — the retrofit path
// for artifacts created before the property layer (ADR-453 D2). And the
// editor's missing mechanical basics — delete/duplicate/move at block and
// page grain, apply/remove a design system's skin — land here as the same
// pure transforms through the same door.

/** Upsert the marked kernel style element (ADR-453 D2). Inserted after the
 *  unmarked layout style, BEFORE any data-skin element (cascade: layout <
 *  kernel < skin); replaced in place when an older data-kernel-v is found. */
function ensureKernelStyle(doc: Document, kernelStyleElement: string | undefined): void {
  if (!kernelStyleElement) return;
  const tpl = doc.createElement('template');
  tpl.innerHTML = kernelStyleElement.trim();
  const fresh = tpl.content.firstElementChild;
  if (!fresh || !fresh.hasAttribute('data-kernel')) return;
  const head = doc.querySelector('head');
  if (!head) return;
  const existing = head.querySelector('style[data-kernel]');
  if (existing) {
    const curV = parseInt(existing.getAttribute('data-kernel-v') ?? '0', 10);
    const newV = parseInt(fresh.getAttribute('data-kernel-v') ?? '0', 10);
    if (curV < newV) existing.replaceWith(doc.importNode(fresh, true));
    return;
  }
  const skin = head.querySelector('style[data-skin]');
  if (skin) head.insertBefore(doc.importNode(fresh, true), skin);
  else head.appendChild(doc.importNode(fresh, true));
}

/** Upsert the kernel style element into an artifact's html, standalone.
 *
 *  ADR-453 D2 promises the marked kernel element "retrofits into existing
 *  artifacts on first touch" — that is what lets a new block kind or
 *  arrangement light up in an OLD artifact. But only a handful of ops passed
 *  `kernelStyleElement` through, so the promise held for those paths and
 *  silently failed for every other write (insert a block, type in one, split,
 *  move, delete): an artifact could sit at an old version indefinitely.
 *
 *  This is benign only while kernel CSS is strictly ADDITIVE — a v3 artifact
 *  lacks only rules it never invokes. It becomes a real defect the first time a
 *  version CHANGES or REMOVES a rule an old artifact depends on, and the failure
 *  is silent (a token renders wrong; nothing errors).
 *
 *  So the retrofit is applied ONCE at the member write door rather than
 *  op-by-op — every mechanical write upgrades, none can forget. Returns the html
 *  unchanged (byte-identical) when the artifact is already current, so it never
 *  manufactures a revision on its own. */
export function retrofitKernel(html: string, kernelStyleElement: string | undefined): string {
  if (!kernelStyleElement) return html;
  const doc = parse(html);
  const head = doc.querySelector('head');
  if (!head) return html; // not a full document — leave it alone
  const before = head.querySelector('style[data-kernel]')?.outerHTML ?? '';
  ensureKernelStyle(doc, kernelStyleElement);
  const after = head.querySelector('style[data-kernel]')?.outerHTML ?? '';
  if (before === after) return html; // already current — byte-identical, no churn
  return serialize(doc);
}

/** Set (value) or clear (null) a property token on the selected block, page,
 *  or the artifact ROOT (ADR-453 D1; document grain ADR-455). Absence is the
 *  default — the default value is never written. A byte-identical set is a
 *  no-op (null → no revision). */
export function setToken(
  html: string,
  target: { grain: 'block' | 'page' | 'document'; anchor: OpAnchor },
  key: string,
  value: string | null,
): OpResult | null {
  if (!/^[a-z-]+$/.test(key)) return null; // token keys are kernel-named
  const doc = parse(html);
  const el =
    target.grain === 'document'
      ? doc.documentElement
      : target.grain === 'block' && target.anchor.blockId
        ? doc.querySelector(`[data-block-id="${CSS.escape(target.anchor.blockId)}"]`)
        : arrangedPageAt(doc, target.anchor);
  if (!el) return null;
  const attr = `data-${key}`;
  const current = el.getAttribute(attr);
  if ((current ?? null) === (value ?? null)) return null; // no-op — no revision
  if (value == null) el.removeAttribute(attr);
  else el.setAttribute(attr, value);
  return { html: serialize(doc), landedId: el.getAttribute('data-block-id') };
}

/** Set a MEASURE on a block — the one continuous property (ADR-461 D4).
 *
 *  A measure differs from a token in exactly one way: its VALUE is not
 *  enumerable, so the kernel cannot pre-declare a selector per value. It
 *  pre-declares the MECHANISM instead (`width: var(--yw, auto)`), and the value
 *  rides in the element. This op writes both halves:
 *    - `data-w` — the marker the kernel's selector matches
 *    - `--yw`  — the value the kernel's `var()` reads
 *
 *  Both live in the ONE source file, so R1 is untouched: there is no second
 *  model, no compile step, nothing HTML is generated FROM. The revision chain
 *  sha256s the same string it always did, and `trace` still joins by
 *  data-block-id (a measured block is addressed exactly as before).
 *
 *  CLAMPED to the kernel's declared bound — a measure is free WITHIN its frame,
 *  never unbounded. That bound is the whole reason D4 is deck+media-scoped: a
 *  slide has a frame to be bounded by; a page has only a viewport to guess at.
 *
 *  `value == null` clears BOTH halves — the absence is the natural layout, the
 *  same convention every token uses. Existing style declarations are preserved:
 *  the artifact's own `style` is not ours to stomp.
 */
export function setMeasure(
  html: string,
  blockId: string,
  key: string,
  value: number | null,
  spec: { cssVar: string; unit: string; min: number; max: number },
): OpResult | null {
  if (!/^[a-z]{1,3}$/.test(key)) return null; // measure keys are kernel-named
  const doc = parse(html);
  const el = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!el) return null;
  const attr = `data-${key}`;
  const before = el.outerHTML;

  // Every declaration EXCEPT ours — a measure never stomps what the artifact
  // authored into its own style attribute.
  const others = (el.getAttribute('style') || '')
    .split(';')
    .map((d) => d.trim())
    .filter((d) => d && !d.startsWith(`${spec.cssVar}:`));

  if (value == null) {
    el.removeAttribute(attr);
    if (others.length) el.setAttribute('style', others.join('; '));
    else el.removeAttribute('style');
  } else {
    // Free WITHIN the frame, never unbounded — the kernel declares the bound.
    const clamped = Math.max(spec.min, Math.min(spec.max, Math.round(value)));
    el.setAttribute(attr, '');
    el.setAttribute('style', [...others, `${spec.cssVar}: ${clamped}${spec.unit}`].join('; '));
  }
  // One honest no-op test: did the element actually change? (A byte-identical
  // write must not produce a revision — the setToken convention.)
  if (el.outerHTML === before) return null;
  return { html: serialize(doc), landedId: blockId };
}

/** ADR-466 P8 — ONE geometry revision: any combination of position (x/y) and
 *  width (w), written together. The bounding-box gestures need this because a
 *  west-handle resize moves the origin AND the width in one act — two separate
 *  ops would mean two revisions for one gesture. Values clamp from the SERVED
 *  specs; an axis passed as undefined is left untouched. */
export function setGeometry(
  html: string,
  blockId: string,
  geo: { x?: number; y?: number; w?: number; h?: number; z?: number },
  specs: Record<'x' | 'y' | 'w', { cssVar: string; unit: string; min: number; max: number }> & {
    h?: { cssVar: string; unit: string; min: number; max: number };
    z?: { cssVar: string; unit: string; min: number; max: number };
  },
): OpResult | null {
  const doc = parse(html);
  const el = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!el) return null;
  const before = el.outerHTML;
  const vars = Object.values(specs).filter(Boolean).map((s) => (s as { cssVar: string }).cssVar);
  const decls = (el.getAttribute('style') || '')
    .split(';')
    .map((d) => d.trim())
    .filter((d) => d && !vars.some((v) => d.startsWith(`${v}:`)));
  // Preserve untouched axes' existing declarations.
  const keep = (el.getAttribute('style') || '')
    .split(';')
    .map((d) => d.trim())
    .filter((d) => d && vars.some((v) => d.startsWith(`${v}:`)));
  const next = new Map(keep.map((d) => [d.split(':')[0].trim(), d]));
  (['x', 'y', 'w', 'h', 'z'] as const).forEach((key) => {
    const v = geo[key];
    const s = specs[key];
    if (v == null || !s) return;
    const clamped = Math.max(s.min, Math.min(s.max, Math.round(v)));
    el.setAttribute(`data-${key}`, '');
    next.set(s.cssVar, `${s.cssVar}: ${clamped}${s.unit}`);
  });
  const style = [...decls, ...Array.from(next.values())];
  if (style.length) el.setAttribute('style', style.join('; '));
  else el.removeAttribute('style');
  if (el.outerHTML === before) return null;
  return { html: serialize(doc), landedId: blockId };
}

/** Move/resize SEVERAL blocks as ONE revision — the group gesture (2026-07-24;
 *  reconciled with ADR-519 D2 on 2026-08-06).
 *
 *  THIS op's group is a TRANSIENT SELECTION: what it writes is what a group has
 *  always written in PowerPoint — each member's OWN geometry, one revision, no
 *  wrapper. That is unchanged, and it is why no `ungroup` op sits beside it.
 *
 *  What DID change: this block used to argue that no persisted group may ever
 *  exist. ADR-519 D2 decided the opposite — Group as a verb wraps a selection
 *  in a real `<div data-block-id>`, which is simply a container with no declared
 *  layout. The two coexist: a transient group is a gesture, a persisted group is
 *  structure. Of the two objections recorded here, one was wrong and one was
 *  right, so both are corrected rather than deleted:
 *
 *  WRONG — "`carriedBlocksOf` would hide a wrapper's children." It filters on
 *  `data-block` (a BLOCK); a group wrapper carries `data-block-id` ALONE, so it
 *  never trips that test and its children stay visible to every sweep. Verified
 *  by execution, not by reading: [wrapper[b1,b2]] carries as `b1,b2`.
 *
 *  RIGHT — a persisted group does NOT survive `applyArrangement`, and this is
 *  now the DECIDED, member-visible rule (2026-08-06): **re-arranging a slide
 *  dissolves its groups.** The mechanism is `page.replaceWith(el)` below: the
 *  old page is discarded wholesale and blocks survive only because they were
 *  re-parented into the new arrangement first. A wrapper is therefore never
 *  orphaned — it is destroyed with the page that held it, which is the honest
 *  outcome and needs no cleanup pass. A group is AUTHORED ad hoc; a slot is
 *  DECLARED by the arrangement (AUTHORING.md); when the arrangement is
 *  re-declared, the ad-hoc structure yields to it. The surface owes the member
 *  that sentence before the re-arrange, not a silent disappearance.
 *
 *  ONE revision, not N: the gesture is one act, and N revisions would make the
 *  history unreadable and a single undo insufficient. Blocks are applied in
 *  sequence over one parsed document; a member that no longer resolves is
 *  skipped rather than failing the whole gesture (a concurrent lane may have
 *  removed it). Returns null when nothing changed — the byte-identical no-op
 *  rule every op here obeys.
 */
export function setGeometryMany(
  html: string,
  moves: Array<{ blockId: string; geo: { x?: number; y?: number; w?: number; h?: number; z?: number } }>,
  specs: Record<'x' | 'y' | 'w', { cssVar: string; unit: string; min: number; max: number }> & {
    h?: { cssVar: string; unit: string; min: number; max: number };
    z?: { cssVar: string; unit: string; min: number; max: number };
  },
): OpResult | null {
  let cur = html;
  let landed: string | null = null;
  let changed = false;
  for (const m of moves) {
    const r = setGeometry(cur, m.blockId, m.geo, specs);
    if (!r) continue; // unresolved or byte-identical — skip, never abort
    cur = r.html;
    landed = landed ?? r.landedId;
    changed = true;
  }
  return changed ? { html: cur, landedId: landed } : null;
}

/** ADR-471 D-d — nudge a POSITIONED block's stacking order by ±1. Reads the
 *  current `--yz` off the element's own style (absence = 0, the document-order
 *  default), clamps from the SERVED spec, and writes through setMeasure (one
 *  revision, marker + value). Returns null for a non-positioned block — z
 *  orders positioned blocks; on a static block the kernel rule is inert and a
 *  write would be a lie the menu should not offer (the gate is target.positioned,
 *  this is the op-side backstop). */
export function nudgeZ(
  html: string,
  blockId: string,
  delta: number,
  spec: { cssVar: string; unit: string; min: number; max: number },
): OpResult | null {
  const doc = parse(html);
  const el = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!el || !el.hasAttribute('data-x') || !el.hasAttribute('data-y')) return null;
  const m = (el.getAttribute('style') || '').match(/--yz:\s*(-?\d+)/);
  const current = m ? parseInt(m[1], 10) : 0;
  return setMeasure(html, blockId, 'z', current + delta, spec);
}

/** ADR-466 D2 — bounded position: place a deck block at a point in its frame.
 *  Writes BOTH x/y measures as one revision (`data-x`/`data-y` + `--yx`/`--yy`
 *  — presence of both is the positioned state); `x == null` clears both (the
 *  block returns to flow). Clamped twice per ADR-461: here from the SERVED
 *  specs, and structurally by the kernel rule's frame. */
export function setPosition(
  html: string,
  blockId: string,
  x: number | null,
  y: number | null,
  specs: {
    x: { cssVar: string; unit: string; min: number; max: number };
    y: { cssVar: string; unit: string; min: number; max: number };
  },
): OpResult | null {
  const doc = parse(html);
  const el = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!el) return null;
  const before = el.outerHTML;
  const others = (el.getAttribute('style') || '')
    .split(';')
    .map((d) => d.trim())
    .filter((d) => d && !d.startsWith(`${specs.x.cssVar}:`) && !d.startsWith(`${specs.y.cssVar}:`));
  if (x == null || y == null) {
    el.removeAttribute('data-x');
    el.removeAttribute('data-y');
    if (others.length) el.setAttribute('style', others.join('; '));
    else el.removeAttribute('style');
  } else {
    const cx = Math.max(specs.x.min, Math.min(specs.x.max, Math.round(x)));
    const cy = Math.max(specs.y.min, Math.min(specs.y.max, Math.round(y)));
    el.setAttribute('data-x', '');
    el.setAttribute('data-y', '');
    el.setAttribute(
      'style',
      [...others, `${specs.x.cssVar}: ${cx}${specs.x.unit}`, `${specs.y.cssVar}: ${cy}${specs.y.unit}`].join('; '),
    );
  }
  if (el.outerHTML === before) return null;
  return { html: serialize(doc), landedId: blockId };
}

/** ADR-511 D4 — container layout: bounded, id-addressed, plain CSS. The
 *  property surface is an ALLOWLIST (never a raw CSS pane — D7); the substrate
 *  is conventional inline style, so exports read as ordinary HTML and the lane
 *  edits the same properties in its native tongue. `null` clears a property.
 *  Works on any id-addressed element; the Design tab offers it on containers. */
const CONTAINER_LAYOUT_PROPS: Record<string, string> = {
  padding: 'padding',
  padY: 'padding-block',
  gap: 'gap',
  align: 'align-items',
  justify: 'justify-content',
  width: 'width',
};
const CONTAINER_LAYOUT_VALUES: Record<string, Set<string>> = {
  // Single-value steps serve containers; the two-value forms are the deck
  // slide's own padding presets (ADR-516 D1 — page presets carry the medium's
  // values, in the same allowlist).
  padding: new Set([
    '0', '0.5rem', '1rem', '1.5rem', '2rem', '3rem',
    '2rem 2.5rem', '3.5rem 4rem', '4.5rem 5.5rem',
  ]),
  // A web band breathes on the block axis only — its inline padding belongs
  // to the band skin's centered content column.
  padY: new Set(['0.25rem', '1rem', '2.5rem']),
  gap: new Set(['0', '0.5rem', '1rem', '1.5rem', '2rem', '3rem']),
  align: new Set(['flex-start', 'center', 'flex-end', 'stretch']),
  justify: new Set(['flex-start', 'center', 'flex-end', 'space-between']),
  // ADR-516 D4 — the container's width as INTENT (Hug | Fill), the ADR-461 D1
  // pair at the container grain. `Fixed` stays refused: continuous.
  width: new Set(['fit-content', '100%']),
};
export function setContainerLayout(
  html: string,
  /** id-addressed for containers; null + anchor for a PAGE (ADR-516 D1 — the
   *  page is a container, addressed by position like every other page op). */
  id: string | null,
  layout: Partial<Record<keyof typeof CONTAINER_LAYOUT_VALUES, string | null>>,
  anchor?: OpAnchor,
): OpResult | null {
  const doc = parse(html);
  const el = id
    ? doc.querySelector(`[data-block-id="${CSS.escape(id)}"]`)
    : anchor
      ? arrangedPageAt(doc, anchor)
      : null;
  if (!el) return null;
  const before = el.outerHTML;
  const cssOf = (k: string) => CONTAINER_LAYOUT_PROPS[k];
  const touched = new Set(Object.keys(layout).map(cssOf).filter(Boolean));
  const decls = (el.getAttribute('style') || '')
    .split(';')
    .map((d) => d.trim())
    .filter((d) => d && !touched.has(d.split(':')[0]?.trim() ?? ''));
  let needsFlex = false;
  for (const [key, value] of Object.entries(layout)) {
    const prop = cssOf(key);
    if (!prop || value == null) continue;
    if (!CONTAINER_LAYOUT_VALUES[key]?.has(value)) continue; // bounded surface
    decls.push(`${prop}: ${value}`);
    if (key === 'gap' || key === 'align' || key === 'justify') needsFlex = true;
  }
  // Flex properties need a flex context — but a flex context must not flip the
  // container's visual axis. A bare `display: flex` defaults to ROW, which
  // horizontally re-flowed every block-flow container (the title slide's
  // kicker/h1/subtitle landed side by side). Row containers are recognized
  // structurally (.col children — the same signal the multicol fallback
  // counts); everything else keeps vertical flow explicitly. A container that
  // already carries `display: flex` without a direction (the pre-fix write)
  // is healed on its next layout write — this surface offers no direction
  // control, so that state can only be the old bug's residue.
  if (needsFlex) {
    const hasDisplay = decls.some((d) => /^display\s*:/.test(d));
    const displayIsFlex = decls.some((d) => /^display\s*:\s*flex\b/.test(d));
    if (!hasDisplay) decls.push('display: flex');
    const isRow = Array.from(el.children).some((c) => c.classList.contains('col'));
    const hasDirection = decls.some((d) => /^flex-direction\s*:/.test(d));
    if (!isRow && !hasDirection && (!hasDisplay || displayIsFlex)) {
      decls.push('flex-direction: column');
    }
  }
  if (decls.length) el.setAttribute('style', decls.join('; '));
  else el.removeAttribute('style');
  // ADR-516 D2 — convergence-by-use: a layout write single-sources THIS
  // element. The legacy layout tokens (inert names per ADR-511 D8 — kernel CSS
  // still honors them on untouched artifacts) leave the element the member is
  // actually re-laying; inline style would win the cascade anyway.
  el.removeAttribute('data-valign');
  el.removeAttribute('data-pad');
  if (el.outerHTML === before) return null;
  return { html: serialize(doc), landedId: id ?? el.getAttribute('data-block-id') };
}

/** Delete the selected block (the missing mechanical basic — a member should
 *  never need a metered judgment turn to remove a block). */
export function deleteBlock(html: string, blockId: string): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block) return null;
  block.remove();
  return { html: serialize(doc), landedId: null };
}

/** Duplicate the selected block in place (fresh ids on the copy). */
export function duplicateBlock(html: string, blockId: string): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block) return null;
  const copy = materializeFragment(doc, block.outerHTML);
  if (!copy) return null;
  block.insertAdjacentElement('afterend', copy);
  return { html: serialize(doc), landedId: copy.getAttribute('data-block-id') };
}

/** ADR-541 D3 — a block-grain token across EVERY covered block, one revision:
 *  the span-aware align/indent. Chained through the single `setToken` so
 *  there is exactly one legality/clamp implementation; a block the single op
 *  refuses is skipped, never a whole-range veto. */
export function setTokenMany(
  html: string,
  blockIds: string[],
  key: string,
  value: string | null,
): OpResult | null {
  let cur = html;
  let landed: string | null = null;
  let hit = 0;
  for (const id of blockIds) {
    const r = setToken(cur, { grain: 'block', anchor: { blockId: id } }, key, value);
    if (r) {
      cur = r.html;
      landed = r.landedId ?? landed;
      hit += 1;
    }
  }
  if (!hit) return null;
  return { html: cur, landedId: landed };
}

/** ADR-541 D4 — delete the SET, one revision. The ⌫-over-five-objects gesture
 *  used to delete one object silently (the runtime keyboard gated on `cur`
 *  alone); a verb over many takes the whole set now, and one ⌘Z restores it.
 *  Missing ids are skipped (a stale set member is not a reason to refuse the
 *  rest); null only when nothing at all was found. */
export function deleteBlocks(html: string, blockIds: string[]): OpResult | null {
  const doc = parse(html);
  let hit = 0;
  for (const id of blockIds) {
    const block = doc.querySelector(`[data-block-id="${CSS.escape(id)}"]`);
    if (block) {
      block.remove();
      hit += 1;
    }
  }
  if (!hit) return null;
  return { html: serialize(doc), landedId: null };
}

/** ADR-541 D4 — duplicate the SET, one revision; each copy lands beside its
 *  original (fresh ids via materializeFragment, as the single op). */
export function duplicateBlocks(html: string, blockIds: string[]): OpResult | null {
  const doc = parse(html);
  let landed: string | null = null;
  for (const id of blockIds) {
    const block = doc.querySelector(`[data-block-id="${CSS.escape(id)}"]`);
    if (!block) continue;
    const copy = materializeFragment(doc, block.outerHTML);
    if (!copy) continue;
    block.insertAdjacentElement('afterend', copy);
    landed = copy.getAttribute('data-block-id');
  }
  if (landed == null) return null;
  return { html: serialize(doc), landedId: landed };
}

/** ADR-541 D3 — convert EVERY covered block, one revision: the span-aware
 *  turn-into/ramp. Per-block legality is per-block — `convertBlock` refuses a
 *  citation island or a same-shape no-op by returning null, and that block is
 *  simply SKIPPED (a whole-range veto would deliver neither benchmark:
 *  Google Docs styles every paragraph a range covers; Notion converts every
 *  block in a set). Chained through the single op so there is exactly one
 *  legality implementation; the final html is one write, one ⌘Z. */
export function convertBlocks(
  html: string,
  blockIds: string[],
  kind: string,
  fragment: string,
): OpResult | null {
  let cur = html;
  let landed: string | null = null;
  let hit = 0;
  for (const id of blockIds) {
    const r = convertBlock(cur, id, kind, fragment);
    if (r) {
      cur = r.html;
      landed = r.landedId ?? landed;
      hit += 1;
    }
  }
  if (!hit) return null;
  return { html: cur, landedId: landed };
}

/** Paste a copied block's SOURCE after `afterBlockId` (or into the default
 *  flow when nothing was under the cursor). ADR-462 D1: a second entrance to
 *  the insert that already exists, never a new op — `materializeFragment`
 *  stamps fresh ids, so a paste is a NEW block rather than a second element
 *  wearing an address the trace already knows.
 *
 *  The clipboard unit is a block's outerHTML, not its text: a pasted block
 *  arrives whole (kind + tokens + citation islands intact) instead of smearing
 *  its characters into whatever block received it. */
export function pasteBlock(
  html: string,
  fragment: string,
  afterBlockId: string | null,
): OpResult | null {
  const doc = parse(html);
  const copy = materializeFragment(doc, fragment);
  if (!copy) return null;
  const anchor = afterBlockId
    ? doc.querySelector(`[data-block-id="${CSS.escape(afterBlockId)}"]`)
    : null;
  if (anchor) anchor.insertAdjacentElement('afterend', copy);
  else defaultFlow(doc).appendChild(copy);
  return { html: serialize(doc), landedId: copy.getAttribute('data-block-id') };
}

/** Move a block so it sits immediately BEFORE `beforeBlockId`, or — when
 *  `beforeBlockId` is null — to the END of its own parent. A move stays within
 *  the block's own parent (same slot/flow). A no-op (moving a block onto itself
 *  or just before its current next sibling) returns null so no empty revision
 *  lands.
 *
 *  MODULE-INTERNAL since ADR-505 D4: this was the drop handler for the `⋮⋮`
 *  drag, which is deleted. Its one remaining caller is `moveBlock` (the menu's
 *  Move up/down), which expresses the accessible verb on top of it. Kept
 *  un-exported so the general form cannot grow a second caller without a
 *  decision — a new positional move belongs to a gesture that has an ADR. */
function moveBlockTo(
  html: string,
  blockId: string,
  beforeBlockId: string | null,
): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block?.parentElement) return null;
  const parent = block.parentElement;
  if (beforeBlockId) {
    if (beforeBlockId === blockId) return null; // dropped on itself
    const target = doc.querySelector(`[data-block-id="${CSS.escape(beforeBlockId)}"]`);
    if (!target || target.parentElement !== parent) return null; // v1: same parent only
    if (block.nextElementSibling === target) return null; // already immediately before it — no-op
    parent.insertBefore(block, target);
  } else {
    if (parent.lastElementChild === block) return null; // already last — no-op
    parent.appendChild(block);
  }
  return { html: serialize(doc), landedId: blockId };
}

/** Move the selected element up/down among its siblings — the Design tab's
 *  accessible verb, now expressed on top of moveBlockTo (Singular Implementation
 *  with the drag). Up = before the previous sibling; down = before the sibling
 *  AFTER the next (so it lands past the next), or to the end.
 *
 *  The walk steps by `data-block-id`, NOT by `data-block`: after ADR-519 D1 the
 *  hierarchy has four grains and TWO of them are movable siblings — a block
 *  (`data-block`) and a structural container (`data-block-id` alone). Filtering
 *  on `data-block` made a container invisible to its own reorder, so the
 *  container verb row ADR-519 Phase A mounted answered Up/Down with silence
 *  (moveBlockTo returned null; the button never disabled). `data-block-id` is
 *  the right test because it is exactly what moveBlockTo addresses by — the
 *  walk and the move now agree on what a sibling is. */
export function moveBlock(html: string, blockId: string, dir: 'up' | 'down'): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block?.parentElement) return null;
  const prevBlock = (el: Element): Element | null => {
    let s = el.previousElementSibling;
    while (s && !s.hasAttribute('data-block-id')) s = s.previousElementSibling;
    return s;
  };
  const nextBlock = (el: Element): Element | null => {
    let s = el.nextElementSibling;
    while (s && !s.hasAttribute('data-block-id')) s = s.nextElementSibling;
    return s;
  };
  if (dir === 'up') {
    const prev = prevBlock(block);
    if (!prev) return null;
    return moveBlockTo(html, blockId, prev.getAttribute('data-block-id'));
  }
  // down: land before the block after next, or at the end if next is last.
  const next = nextBlock(block);
  if (!next) return null;
  const after = nextBlock(next);
  return moveBlockTo(html, blockId, after ? after.getAttribute('data-block-id') : null);
}

/** Split a text block at the caret (F6): the block keeps `beforeInner`, and a
 *  fresh block (same kind, id = `newId`) carrying `afterInner` is inserted right
 *  after it. The runtime computes both halves' SOURCE inner (citation islands
 *  restored) and the caller passes them + the pre-generated id so the source op
 *  matches the optimistic in-frame DOM exactly. Heading blocks split into a
 *  heading + a prose block (the tail of a title is body, not another title). */
export function splitBlock(
  html: string,
  blockId: string,
  newId: string,
  beforeInner: string,
  afterInner: string,
): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block?.parentElement) return null;
  const kind = block.getAttribute('data-block') || 'prose';
  // The block keeps the before-half.
  block.innerHTML = beforeInner;
  // The tail block: same kind, EXCEPT a heading's tail is prose (a split title
  // continues as body). Clone the element shell so tag + skin attrs carry over
  // for same-kind splits; for a heading tail, build a <p> prose block.
  let tail: Element;
  if (kind === 'heading' || /^h[1-6]$/i.test(block.tagName)) {
    tail = doc.createElement('p');
    tail.setAttribute('data-block', 'prose');
  } else {
    tail = block.cloneNode(false) as Element; // shell only (no children)
    tail.removeAttribute('data-ref'); // never carry a citation ref to the tail
  }
  tail.setAttribute('data-block-id', newId);
  tail.innerHTML = afterInner;
  block.insertAdjacentElement('afterend', tail);
  return { html: serialize(doc), landedId: newId };
}

/** Split a block at the caret and drop a NEW block between the halves — the
 *  mid-sentence '/' gesture. The block keeps the before-half, the new block
 *  lands after it, and the after-half follows as a tail block of the same kind
 *  (a heading's tail continues as prose, matching splitBlock).
 *
 *  This is splitBlock + insertBlock as ONE op because it is one gesture: two
 *  ops would race on the same head (the parent applies both against the same
 *  expected revision) and the second would lose. Returns the NEW block as the
 *  landed id — the caret belongs in what the member just asked for.
 */
export function splitBlockAndInsert(
  html: string,
  blockId: string,
  beforeInner: string,
  afterInner: string,
  fragment: string,
): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block?.parentElement) return null;
  const inserted = materializeFragment(doc, fragment);
  if (!inserted) return null;
  const kind = block.getAttribute('data-block') || 'prose';

  // The block keeps the before-half; the new block goes directly after it.
  block.innerHTML = beforeInner;
  block.insertAdjacentElement('afterend', inserted);

  // The after-half continues below the inserted block, same kind (a heading's
  // tail becomes prose — a split title continues as body).
  let tail: Element;
  if (kind === 'heading' || /^h[1-6]$/i.test(block.tagName)) {
    tail = doc.createElement('p');
    tail.setAttribute('data-block', 'prose');
  } else {
    tail = block.cloneNode(false) as Element; // shell only (no children)
    tail.removeAttribute('data-ref'); // never carry a citation ref to the tail
  }
  tail.setAttribute('data-block-id', freshBlockId(doc));
  tail.innerHTML = afterInner;
  inserted.insertAdjacentElement('afterend', tail);

  // A block emptied by the split carries nothing — drop it rather than leave a
  // blank line where the member's sentence used to start.
  if ((beforeInner ?? '').trim() === '') block.remove();

  return { html: serialize(doc), landedId: inserted.getAttribute('data-block-id') };
}

/** Merge a block into the previous TEXT block (F6 — Backspace at block start):
 *  the previous block's inner gains this block's inner (concatenated), and this
 *  block is removed. The caller passes the previous block's id (the runtime
 *  found it) + the merged source inner (islands restored). Returns the previous
 *  block id as landedId (the caret lands there, at the join). */
export function mergeBlock(
  html: string,
  blockId: string,
  prevBlockId: string,
  mergedInner: string,
): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  const prev = doc.querySelector(`[data-block-id="${CSS.escape(prevBlockId)}"]`);
  if (!block || !prev || block.parentElement !== prev.parentElement) return null;
  prev.innerHTML = mergedInner;
  block.remove();
  return { html: serialize(doc), landedId: prevBlockId };
}

/** Set a cited BACKGROUND image on the selected page/section (ADR-456 W3):
 *  data-ref + data-ref-kind="background" on the page element itself — the
 *  projection materializes the pixels; the source stays citation + tokens. */
export function setPageBackground(
  html: string,
  anchor: OpAnchor,
  path: string,
): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  page.setAttribute('data-ref', path);
  page.setAttribute('data-ref-kind', 'background');
  page.setAttribute('data-ref-rev', '');
  return { html: serialize(doc), landedId: page.getAttribute('data-arrange') };
}

/** Remove the page's cited background (and its bg-only tokens). */
export function removePageBackground(html: string, anchor: OpAnchor): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page || page.getAttribute('data-ref-kind') !== 'background') return null;
  ['data-ref', 'data-ref-kind', 'data-ref-rev', 'data-scrim', 'data-bg-pos'].forEach((a) =>
    page.removeAttribute(a),
  );
  return { html: serialize(doc), landedId: page.getAttribute('data-arrange') };
}

/** Delete the selected page (slide/section). */
export function deletePage(html: string, anchor: OpAnchor): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  page.remove();
  return { html: serialize(doc), landedId: null };
}

/** Duplicate the selected page in place (fresh block ids throughout). */
export function duplicatePage(html: string, anchor: OpAnchor): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  const copy = materializeFragment(doc, page.outerHTML);
  if (!copy) return null;
  page.insertAdjacentElement('afterend', copy);
  return { html: serialize(doc), landedId: copy.getAttribute('data-arrange') };
}

/** Move the selected page up/down among its sibling pages. */
export function movePage(html: string, anchor: OpAnchor, dir: 'up' | 'down'): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page?.parentElement) return null;
  let sib: Element | null = dir === 'up' ? page.previousElementSibling : page.nextElementSibling;
  while (sib && !sib.matches(PAGE_SEL)) {
    sib = dir === 'up' ? sib.previousElementSibling : sib.nextElementSibling;
  }
  if (!sib) return null;
  if (dir === 'up') sib.insertAdjacentElement('beforebegin', page);
  else sib.insertAdjacentElement('afterend', page);
  return { html: serialize(doc), landedId: page.getAttribute('data-arrange') };
}

/** Move the slide at `from` to sit at position `to` in document order — the
 *  navigator's drag-to-reorder (PowerPoint). Indices are into the deck's
 *  `section.slide` set (the same index space the navigator + selection use).
 *  Moves the whole slide node INTACT (content preserved); a no-op when the
 *  target equals the source. The reflow is by NODE, so ids/blocks are untouched. */
export function movePageTo(html: string, from: number, to: number): OpResult | null {
  const doc = parse(html);
  const slides = Array.from(doc.querySelectorAll('section.slide'));
  if (from < 0 || from >= slides.length || to < 0 || to >= slides.length || from === to) {
    return null;
  }
  const moving = slides[from];
  const ref = slides[to];
  if (!moving.parentElement || !ref.parentElement) return null;
  // Moving DOWN (to > from): land after the target. Moving UP: land before it.
  // Because `to` names the slide currently at the destination index, "after"
  // when descending and "before" when ascending places `moving` exactly at `to`.
  if (to > from) ref.insertAdjacentElement('afterend', moving);
  else ref.insertAdjacentElement('beforebegin', moving);
  return { html: serialize(doc), landedId: moving.getAttribute('data-arrange') };
}

/** Delete several pages at once — the navigator's multi-select delete (one
 *  compound revision, not N). Indices are into the `PAGE_SEL` set (deck slides
 *  AND arranged page sections — the same index space the navigator uses), so
 *  this is paged-mode-general, not deck-only. Removes high-index-first so an
 *  earlier removal never shifts a not-yet-removed index. A no-op (empty set /
 *  all out of range) returns null — no revision lands. */
export function deletePages(html: string, indices: number[]): OpResult | null {
  const doc = parse(html);
  const pages = Array.from(doc.querySelectorAll(PAGE_SEL));
  const targets = Array.from(new Set(indices))
    .filter((i) => i >= 0 && i < pages.length)
    .sort((a, b) => b - a); // high-first: removals don't invalidate lower indices
  if (!targets.length) return null;
  targets.forEach((i) => pages[i].remove());
  return { html: serialize(doc), landedId: null };
}

/** Move a contiguous-or-scattered SELECTION of pages to sit at position `to`
 *  in document order, preserving their internal order (the navigator's
 *  group drag-reorder). Indices + `to` are into the `PAGE_SEL` set. The moved
 *  group lands as a contiguous run starting where `to` names in the ORIGINAL
 *  order (the pages before `to` that are NOT moving anchor the landing). One
 *  revision; nodes move INTACT (ids/blocks untouched). A no-op (the selection
 *  already sits at `to`, or nothing valid) returns null. */
export function movePages(html: string, indices: number[], to: number): OpResult | null {
  const doc = parse(html);
  const pages = Array.from(doc.querySelectorAll(PAGE_SEL));
  const moving = Array.from(new Set(indices))
    .filter((i) => i >= 0 && i < pages.length)
    .sort((a, b) => a - b); // document order preserved within the group
  if (!moving.length) return null;
  if (to < 0 || to > pages.length) return null;

  // The landing reference is the first page at/after `to` that is NOT itself
  // moving; the group is inserted before it. If none (dropping at the end),
  // append after the last stationary page. This keeps the group contiguous and
  // lands it exactly at the gap the navigator computed.
  const movingSet = new Set(moving);
  let ref: Element | null = null;
  for (let i = to; i < pages.length; i++) {
    if (!movingSet.has(i)) {
      ref = pages[i];
      break;
    }
  }
  // No-op guard: the selection is already the contiguous run ending at the gap.
  const nodes = moving.map((i) => pages[i]);
  const container = nodes[0].parentElement;
  if (!container) return null;
  if (ref && ref.parentElement !== container) return null;

  if (ref) {
    nodes.forEach((n) => ref!.insertAdjacentElement('beforebegin', n));
  } else {
    // Drop at the end: after the last stationary sibling matching PAGE_SEL.
    const stationary = pages.filter((_, i) => !movingSet.has(i));
    const last = stationary.length ? stationary[stationary.length - 1] : null;
    if (last && last.parentElement === container) {
      let anchor: Element = last;
      nodes.forEach((n) => {
        anchor.insertAdjacentElement('afterend', n);
        anchor = n;
      });
    } else {
      nodes.forEach((n) => container.appendChild(n));
    }
  }
  return { html: serialize(doc), landedId: null };
}

/** Apply a design system's composed, MARKED skin element (ADR-449 via the
 *  Design tab — the FE mirror of apply_skin_to_html): replace the existing
 *  data-skin element, else append LAST in head (cascade order makes the
 *  workspace's identity win). The unmarked layout style is never touched. */
export function applySkin(html: string, skinElement: string): OpResult | null {
  const doc = parse(html);
  const head = doc.querySelector('head');
  if (!head) return null;
  const tpl = doc.createElement('template');
  tpl.innerHTML = skinElement.trim();
  const fresh = tpl.content.firstElementChild;
  if (!fresh || !fresh.hasAttribute('data-skin')) return null;
  const existing = head.querySelector('style[data-skin]');
  if (existing) existing.replaceWith(doc.importNode(fresh, true));
  else head.appendChild(doc.importNode(fresh, true));
  return { html: serialize(doc), landedId: null };
}

/** Remove the marked skin element (D3's inverse — an ordinary edit). */
export function removeSkin(html: string): OpResult | null {
  const doc = parse(html);
  const existing = doc.querySelector('head style[data-skin]');
  if (!existing) return null;
  existing.remove();
  return { html: serialize(doc), landedId: null };
}

/** Apply an arrangement to the selected page (a slide / a section): every
 *  existing [data-block] in the page moves INTACT (ids preserved) into the new
 *  arrangement's first [data-slot]; other slots keep their placeholders; the
 *  old page is replaced. The reflow (ADR-447 — generalizes applySlideLayout to
 *  any layout; the deck slide-master reflow is the deck case). */
export function applyArrangement(
  html: string,
  fragment: string,
  anchor: OpAnchor,
  /** ADR-466 D5, re-cut by ADR-544 D6: the target arrangement's AREA roles,
   *  keyed by area name (from the served registry). Distribution is ROLE-FIRST:
   *  heading→heading, body→body, media→media, with the authored name only
   *  breaking ties among same-role Areas. Optional — without it the
   *  name/first-Area ladder still applies (a pre-544 document's fallback). */
  slotRoles?: Record<string, string>,
): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  const el = materializeFragment(doc, fragment);
  if (!el) return null;

  // THE INVARIANT: a layout change never destroys content (ADR-462 D9).
  //
  // This used to read `const slot = el.querySelector('[data-slot]')` and then
  // `if (slot && blocks.length) {…}` — followed unconditionally by
  // `page.replaceWith(el)`. Two silent losses fell out of that:
  //   · 5 arrangements carry NO data-slot (title, section-header, closing,
  //     hero, cta). `slot` was null, the carry was skipped, and replaceWith
  //     DESTROYED every content block on the page.
  //   · 6 carry MORE than one. querySelector took the first, so a two-column
  //     slide's `side` content collapsed into `main`.
  // Both read as "re-arrange wiped my slide", because that is what happened.
  //
  // Now: sweep every non-heading block, distribute by SOURCE SLOT where the
  // target has a same-named slot (side → side), and land the remainder in the
  // first flow slot. If the target has no slot at all, REFUSE (return null) —
  // a layout with nowhere to put content cannot receive content, and saying so
  // is the honest act. The caller surfaces the refusal.
  const carried = carriedBlocksOf(page);
  // ADR-544 D2 — an Area is the region element. `[data-slot]` is kept as a
  // READ-side fallback so a pre-544 document (or one an older lane authored)
  // still re-lays instead of refusing.
  const targetSlots = Array.from(el.querySelectorAll('[data-area], [data-slot]'));

  if (carried.length && !targetSlots.length) return null; // refuse, never delete

  if (targetSlots.length) {
    // ADR-544 D6 — THE MAPPING IS ROLE-FIRST. Pre-544 this keyed on the
    // authored NAME with roles as a fallback, which was fragile for exactly the
    // reason §1.1 gives: names were free-form LLM output, so `main`→`main` held
    // only by luck and any re-naming silently collapsed a column into the
    // first slot. The role is the Area's identity, so it is what maps.
    const nameOf = (s: Element) => s.getAttribute('data-area') ?? s.getAttribute('data-slot');
    // The target Area's role: read from the markup first (post-544 fragments
    // carry it inline), then the served registry (which keys by name).
    const roleOfEl = (s: Element) =>
      s.getAttribute('data-area-role') ?? (slotRoles ? (slotRoles[nameOf(s) ?? ''] ?? null) : null);
    // The SOURCE block's Area role, by the same ladder — a pre-544 page has no
    // inline role, so the served map answers for it.
    const sourceRole = (b: Element) => {
      const from = b.closest('[data-area], [data-slot]');
      if (!from) return null;
      return roleOfEl(from);
    };
    const byRole = new Map<string, Element[]>();
    targetSlots.forEach((s) => {
      const r = roleOfEl(s);
      if (!r) return;
      byRole.set(r, [...(byRole.get(r) ?? []), s]);
    });
    // The primary body Area — where content lands when its role has no home.
    // Never a media or heading Area: flow content must not fill either.
    const bodyFallback =
      (byRole.get('body') ?? [])[0] ??
      targetSlots.find((s) => {
        const r = roleOfEl(s);
        return r !== 'media' && r !== 'heading';
      }) ??
      targetSlots[0];
    const receiving = new Set<Element>();
    carried.forEach((b) => {
      const kind = b.getAttribute('data-block');
      const from = b.closest('[data-area], [data-slot]');
      const fromName = from ? nameOf(from) : null;
      // A picture seeks a media Area regardless of where it sat (ADR-466 D5).
      const isMedia = kind === 'figure' || kind === 'gallery';
      const wanted = isMedia ? 'media' : sourceRole(b);
      const sameRole = wanted ? (byRole.get(wanted) ?? []) : [];
      let target: Element;
      if (sameRole.length > 1 && fromName) {
        // Same-role siblings: the authored NAME breaks the tie (side → side),
        // which is the one job a name still has (D2).
        target = sameRole.find((s) => nameOf(s) === fromName) ?? sameRole[0];
      } else if (sameRole.length === 1) {
        target = sameRole[0];
      } else {
        target = bodyFallback;
      }
      // Flow content never lands in a media Area, even via the fallback.
      if (!isMedia && roleOfEl(target) === 'media') target = bodyFallback;
      if (!receiving.has(target)) {
        target.querySelectorAll('[data-block]').forEach((p) => p.remove());
        receiving.add(target);
      }
      returnToFlow(b);
      target.appendChild(b);
    });
  }
  page.replaceWith(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-arrange') };
}

/** ADR-479 D1 — the page's blocks, as the planner needs to see them: an id, a
 *  kind, and a short text excerpt. The judgment reads MEANING, so it gets the
 *  text; it never gets markup, and it never returns any. */
export function blocksForPlan(
  html: string,
  anchor: OpAnchor,
): Array<{ id: string; kind: string; text: string }> | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  return carriedBlocksOf(page)
    .map((b) => ({
      id: b.getAttribute('data-block-id') || '',
      kind: b.getAttribute('data-block') || 'content',
      text: (b.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 200),
    }))
    .filter((b) => b.id);
}

/** ADR-479 D1 — apply a PLANNED re-arrangement: the judgment named an Area per
 *  block, and this puts each block there. Deterministic by construction — the
 *  same plan always yields the same HTML, because this function makes no
 *  placement decisions at all. It is the mechanism half of the split.
 *
 *  `placements` is assumed VALIDATED (ADR-479 D2: real Areas, real blocks, total
 *  coverage) — the server rejects anything else before it reaches here. This
 *  still guards defensively: a block whose Area is missing from the target lands
 *  in the first Area rather than being dropped, because the never-destroy-content
 *  invariant (ADR-462 D9) outranks the plan.
 *
 *  Returns null when the anchor resolves to no page or the fragment won't
 *  materialize — the caller falls back to the mechanical `applyArrangement`. */
export function applyArrangementPlan(
  html: string,
  fragment: string,
  anchor: OpAnchor,
  placements: Array<{ block_id: string; area: string }>,
): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  const el = materializeFragment(doc, fragment);
  if (!el) return null;

  const carried = carriedBlocksOf(page);
  // ADR-544 D2/D6 — an Area is the region element. This queried `[data-slot]`
  // ALONE while its sibling `applyArrangement` was re-cut to read both, so on a
  // post-544 fragment it found ZERO targets and refused every plan: the AI
  // re-arrange degraded silently to the mechanical ladder, which looks exactly
  // like "the router is off". `[data-slot]` stays as the legacy read for a
  // document authored before the heal.
  const targetSlots = Array.from(el.querySelectorAll('[data-area], [data-slot]'));
  if (carried.length && !targetSlots.length) return null; // nowhere to put it

  const nameOf = (s: Element) => s.getAttribute('data-area') ?? s.getAttribute('data-slot');
  const byName = new Map(targetSlots.map((s) => [nameOf(s), s]));
  const byAreaPlan = new Map(placements.map((p) => [p.block_id, p.area]));
  const receiving = new Set<Element>();

  carried.forEach((b) => {
    const id = b.getAttribute('data-block-id') || '';
    const planned = byAreaPlan.get(id);
    const target = (planned ? byName.get(planned) : undefined) ?? targetSlots[0];
    if (!target) return;
    // A slot receiving real content sheds its scaffold placeholders — once,
    // on first receipt, so the second block into a slot doesn't wipe the first.
    if (!receiving.has(target)) {
      target.querySelectorAll('[data-block]').forEach((p) => p.remove());
      receiving.add(target);
    }
    returnToFlow(b);
    target.appendChild(b);
  });

  page.replaceWith(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-arrange') };
}

/** ADR-466 D2 (the ADR-461 honest remainder, closed): re-laying a page is the
 *  act that returns a POSITIONED block to flow — the arrangement's slots are
 *  about to lay it out, so its measures are cleared as it is carried.
 *
 *  ADR-485 D2 — the CLEAR-grain now matches the WRITE-grain. `setGeometry`
 *  writes x/y/w/h/z as ONE geometry unit from one gesture; this cleared two of
 *  the five, so `--yw: 60%` survived a re-arrange and was silently re-based
 *  against a narrower rectangle: measured in Chrome, a block laid out by the
 *  slide at 595.2px became 247.2px (−58.5%) on being carried into a `flex: 1`
 *  column, with height collapsing 223.2px → 18.0px because a flex-start column
 *  has no definite height for a percentage to resolve against. No gesture
 *  involved — one click. A width that was a percent of the slide is not a width
 *  that means anything in a column, so the arrangement lays the block out
 *  fresh. `data-z` goes too: it orders POSITIONED siblings, and on a static
 *  block it is inert state that `nudgeZ` then refuses to touch. */
const GEOMETRY_VARS = ['--yx:', '--yy:', '--yw:', '--yh:', '--yz:'];
function returnToFlow(b: Element): void {
  const keys = ['x', 'y', 'w', 'h', 'z'];
  if (!keys.some((k) => b.hasAttribute(`data-${k}`))) return;
  keys.forEach((k) => b.removeAttribute(`data-${k}`));
  const kept = (b.getAttribute('style') || '')
    .split(';')
    .map((d) => d.trim())
    .filter((d) => d && !GEOMETRY_VARS.some((v) => d.startsWith(v)));
  if (kept.length) b.setAttribute('style', kept.join('; '));
  else b.removeAttribute('style');
}

/** The blocks an arrangement change must carry: every top-level non-heading
 *  [data-block] on the page (headings anchor; nested blocks ride with their
 *  parent). Shared by applyArrangement / countCarriedBlocks / the resolution. */
function carriedBlocksOf(page: Element): Element[] {
  return Array.from(page.querySelectorAll('[data-block]')).filter(
    (b) =>
      b.getAttribute('data-block') !== 'heading' &&
      !b.parentElement?.closest('[data-block]'),
  );
}

/** ADR-466 D5 — the galleries pre-filter instead of post-failing: how many
 *  blocks would an arrangement change on this page have to carry? null when
 *  the anchor resolves to no page. */
export function countCarriedBlocks(html: string, anchor: OpAnchor): number | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  return carriedBlocksOf(page).length;
}

/** ADR-519 D2.1 — how many authored GROUPS would a re-arrange of this page
 *  dissolve? The galleries forewarn with it, exactly as ADR-466 D5 forewarns
 *  carried content: `applyArrangement` ends in `page.replaceWith(el)`, so a
 *  group wrapper dies with the page that held it. Never orphaned, no cleanup
 *  pass — but a group vanishing SILENTLY is the defect the rule must not
 *  produce, so the count exists to be said out loud before the gesture.
 *
 *  A group IS a container with no declared layout (D2 — Figma's Group ≡ a
 *  `<div data-block-id>` without layout; there is no group node type). So:
 *  identity, no vocabulary, no inline layout style, and it must actually hold
 *  blocks — a declared-but-empty region (`data-slot`) is the arrangement's own
 *  structure, not something the member authored, and it is not dissolved in
 *  any sense worth warning about.
 *
 *  Nested groups each count: each is one wrapper the member made. */
export function countGroupsOnPage(html: string, anchor: OpAnchor): number | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  return Array.from(page.querySelectorAll('div[data-block-id]:not([data-block])')).filter(
    (el) =>
      !el.hasAttribute('data-slot') && // a DECLARED region, not an authored group
      !(el.getAttribute('style') || '').trim() && // layout declared → a frame, not a group
      !!el.querySelector('[data-block]'),
  ).length;
}

/** ADR-466 D5 — the refusal's RESOLUTION: apply a slotless arrangement (title /
 *  section-header / closing / hero / cta) by moving the page's content to a NEW
 *  content page inserted right after it. One compound act, one revision, never
 *  a dead-end. `contentFragment` is the layout's content arrangement (the
 *  caller picks it from the served registry). */
export function applyArrangementMovingContent(
  html: string,
  fragment: string,
  anchor: OpAnchor,
  contentFragment: string,
): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  const el = materializeFragment(doc, fragment);
  const overflow = materializeFragment(doc, contentFragment);
  if (!el || !overflow) return null;
  const slot = overflow.querySelector('[data-slot]');
  if (!slot) return null; // the resolution needs a receiving slot
  const carried = carriedBlocksOf(page);
  if (!carried.length) return applyArrangement(html, fragment, anchor);
  slot.querySelectorAll('[data-block]').forEach((p) => p.remove());
  carried.forEach((b) => {
    returnToFlow(b);
    slot.appendChild(b);
  });
  page.replaceWith(el);
  el.insertAdjacentElement('afterend', overflow);
  return { html: serialize(doc), landedId: el.getAttribute('data-arrange') };
}
