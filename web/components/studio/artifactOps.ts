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

function slideAt(doc: Document, anchor: OpAnchor): Element | null {
  if (anchor.blockId) {
    const viaBlock = doc
      .querySelector(`[data-block-id="${CSS.escape(anchor.blockId)}"]`)
      ?.closest('section.slide');
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
    const slide = slideAt(doc, anchor);
    const target = slide ? (slide.querySelector('[data-slot]') ?? slide) : defaultFlow(doc);
    target.appendChild(el);
  }
  return { html: serialize(doc), landedId: el.getAttribute('data-block-id') };
}

/** Insert a new slide (from a container fragment) after the selected slide,
 *  or at the end of the deck. */
export function insertSlide(
  html: string,
  containerFragment: string,
  anchor: OpAnchor,
): OpResult | null {
  const doc = parse(html);
  const el = materializeFragment(doc, containerFragment);
  if (!el) return null;
  const slides = doc.querySelectorAll('section.slide');
  const after = slideAt(doc, anchor) ?? (slides.length ? slides[slides.length - 1] : null);
  if (after) after.insertAdjacentElement('afterend', el);
  else (doc.querySelector('main') ?? doc.body).appendChild(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-container') };
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

/** Apply a container layout to the selected slide: every existing
 *  [data-block] in the slide moves INTACT (ids preserved) into the new
 *  arrangement's first [data-slot]; other slots keep their placeholders;
 *  the old slide is replaced. The slide-master reflow. */
export function applySlideLayout(
  html: string,
  containerFragment: string,
  anchor: OpAnchor,
): OpResult | null {
  const doc = parse(html);
  const slide = slideAt(doc, anchor);
  if (!slide) return null;
  const el = materializeFragment(doc, containerFragment);
  if (!el) return null;
  // Reflow moves CONTENT blocks into the new arrangement; heading blocks
  // (title/kicker/subtitle) belong to the slide's own structure and the new
  // container brings its own — so they are NOT swept (ADR-446: headings are
  // editable blocks, but they anchor the slide, they don't flow into a slot).
  const blocks = Array.from(slide.querySelectorAll('[data-block]')).filter(
    (b) => b.getAttribute('data-block') !== 'heading',
  );
  const slot = el.querySelector('[data-slot]');
  if (slot && blocks.length) {
    // Placeholder fragment blocks in the target slot yield to the real ones.
    slot.querySelectorAll('[data-block]').forEach((p) => p.remove());
    blocks.forEach((b) => slot.appendChild(b));
  }
  slide.replaceWith(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-container') };
}
