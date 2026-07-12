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

function parse(html: string): Document {
  return new DOMParser().parseFromString(html, 'text/html');
}

function serialize(doc: Document): string {
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

/** The default flow container new blocks append into when nothing is
 *  selected: the last slide's slot (deck), <main> (document), <article>. */
function defaultFlow(doc: Document): Element {
  const slides = doc.querySelectorAll('section.slide');
  if (slides.length) {
    const last = slides[slides.length - 1];
    return last.querySelector('[data-slot]') ?? last;
  }
  return doc.querySelector('main') ?? doc.querySelector('article') ?? doc.body;
}

export interface OpResult {
  html: string;
  /** The id of the block/container the op landed, for future selection. */
  landedId: string | null;
}

/** Where an operation anchors: the selected block and/or the selected slide
 *  (title slides carry no blocks, so slide ops need the index too). */
export interface OpAnchor {
  blockId?: string | null;
  slideIndex?: number | null;
}

/** The page-grain arrangement element enclosing the anchor (ADR-447). A
 *  deck slide (`section.slide[data-arrange]`) and a document/article section
 *  (`section[data-arrange]`) are both `[data-arrange]` — so this finds either.
 *  `slideIndex` (the pointer's enclosing-slide index) still resolves a deck
 *  slide with no block (a title slide). */
function arrangedPageAt(doc: Document, anchor: OpAnchor): Element | null {
  if (anchor.blockId) {
    const viaBlock = doc
      .querySelector(`[data-block-id="${CSS.escape(anchor.blockId)}"]`)
      ?.closest('[data-arrange]');
    if (viaBlock) return viaBlock;
  }
  const slides = doc.querySelectorAll('section.slide');
  if (anchor.slideIndex != null && slides[anchor.slideIndex]) {
    return slides[anchor.slideIndex];
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
  const afterBlock = anchor.blockId
    ? doc.querySelector(`[data-block-id="${CSS.escape(anchor.blockId)}"]`)
    : null;
  if (afterBlock?.parentElement) {
    afterBlock.insertAdjacentElement('afterend', el);
  } else {
    const page = arrangedPageAt(doc, anchor);
    const target = page ? (page.querySelector('[data-slot]') ?? page) : defaultFlow(doc);
    target.appendChild(el);
  }
  return { html: serialize(doc), landedId: el.getAttribute('data-block-id') };
}

/** Insert a block into a NAMED slot (ADR-447 Phase 4 — the empty-slot
 *  "+ Add here"). Targets `[data-slot="<slot>"]` within the given slide (deck)
 *  or the first matching slot in the artifact. Appends the block there; a
 *  placeholder "+ Add here" button in the slot is ignored (it is not a
 *  [data-block]). */
export function insertBlockInSlot(
  html: string,
  fragment: string,
  slot: string,
  slideIndex: number | null,
): OpResult | null {
  const doc = parse(html);
  const el = materializeFragment(doc, fragment);
  if (!el) return null;
  const scope =
    slideIndex != null
      ? (doc.querySelectorAll('section.slide')[slideIndex] ?? doc)
      : doc;
  const target =
    (scope as ParentNode).querySelector?.(`[data-slot="${CSS.escape(slot)}"]`) ?? null;
  if (!target) return null;
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
  const pages = doc.querySelectorAll('[data-arrange]');
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

/** Apply an arrangement to the selected page (a slide / a section): every
 *  existing [data-block] in the page moves INTACT (ids preserved) into the new
 *  arrangement's first [data-slot]; other slots keep their placeholders; the
 *  old page is replaced. The reflow (ADR-447 — generalizes applySlideLayout to
 *  any layout; the deck slide-master reflow is the deck case). */
export function applyArrangement(
  html: string,
  fragment: string,
  anchor: OpAnchor,
): OpResult | null {
  const doc = parse(html);
  const page = arrangedPageAt(doc, anchor);
  if (!page) return null;
  const el = materializeFragment(doc, fragment);
  if (!el) return null;
  // Reflow moves CONTENT blocks into the new arrangement; heading blocks
  // (title/kicker/subtitle) belong to the page's own structure and the new
  // arrangement brings its own — so they are NOT swept (ADR-446: headings are
  // editable blocks, but they anchor the page, they don't flow into a slot).
  const blocks = Array.from(page.querySelectorAll('[data-block]')).filter(
    (b) => b.getAttribute('data-block') !== 'heading',
  );
  const slot = el.querySelector('[data-slot]');
  if (slot && blocks.length) {
    // Placeholder fragment blocks in the target slot yield to the real ones.
    slot.querySelectorAll('[data-block]').forEach((p) => p.remove());
    blocks.forEach((b) => slot.appendChild(b));
  }
  page.replaceWith(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-arrange') };
}
