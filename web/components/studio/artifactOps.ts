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

/** Where an operation anchors: the selected block, the selected slide (deck),
 *  and/or the selected page index (ADR-453 — index into the document-order
 *  `section.slide, [data-arrange]` set, so document/article sections anchor
 *  page ops too; the canvas runtime posts the same index). */
export interface OpAnchor {
  blockId?: string | null;
  slideIndex?: number | null;
  pageIndex?: number | null;
}

/** The selector that names a PAGE (a deck slide or an arranged section) —
 *  must match the canvas runtime's pageSel so indices agree. */
const PAGE_SEL = 'section.slide, [data-arrange]';

/** The page-grain arrangement element enclosing the anchor (ADR-447). A
 *  deck slide (`section.slide[data-arrange]`) and a document/article section
 *  (`section[data-arrange]`) are both `[data-arrange]` — so this finds either.
 *  `slideIndex` (the pointer's enclosing-slide index) still resolves a deck
 *  slide with no block (a title slide); `pageIndex` resolves any page. */
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
  pageIndex?: number | null,
): OpResult | null {
  const doc = parse(html);
  const el = materializeFragment(doc, fragment);
  if (!el) return null;
  const scope =
    slideIndex != null
      ? (doc.querySelectorAll('section.slide')[slideIndex] ?? doc)
      : pageIndex != null
        ? (doc.querySelectorAll(PAGE_SEL)[pageIndex] ?? doc)
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
  // ADR-456 W2: the format bar rides execCommand, which emits <b>/<i> —
  // normalize to the semantic tags the source speaks (strong/em).
  holder.querySelectorAll('b, i').forEach((el) => {
    const repl = doc.createElement(el.tagName === 'B' ? 'strong' : 'em');
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
  if (block.getAttribute('data-block') === kind) return null; // no-op
  if (block.querySelector('[data-ref]')) return null; // citations never flatten
  const tpl = doc.createElement('template');
  tpl.innerHTML = fragment.trim();
  const shell = tpl.content.firstElementChild;
  if (!shell) return null;
  const units = Array.from(block.querySelectorAll('li, p, h1, h2, h3, h4, summary, cite'))
    .map((el) => (el.textContent ?? '').trim())
    .filter(Boolean);
  if (!units.length) {
    const whole = (block.textContent ?? '').trim();
    if (whole) units.push(whole);
  }
  // Rebuild the content in the target's shape — text harvested, never markup
  // (inline formatting inside a converted block is the one accepted loss).
  const built: Array<[string, string]> = [];
  if (kind === 'checklist') {
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
 *  `beforeBlockId` is null — to the END of its own parent. The general reorder
 *  the ⋮⋮ drag posts on drop (F1). v1 keeps a move within the block's own
 *  parent (same slot/flow); the runtime only offers same-parent siblings as
 *  drop targets, so `beforeBlockId` (when set) is always a sibling. A no-op
 *  (dropping a block onto itself or just before its current next sibling)
 *  returns null so no empty revision lands. */
export function moveBlockTo(
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

/** Move the selected block up/down among its sibling blocks — the Design tab's
 *  accessible verb, now expressed on top of moveBlockTo (Singular Implementation
 *  with the drag). Up = before the previous block; down = before the block
 *  AFTER the next (so it lands past the next), or to the end. */
export function moveBlock(html: string, blockId: string, dir: 'up' | 'down'): OpResult | null {
  const doc = parse(html);
  const block = doc.querySelector(`[data-block-id="${CSS.escape(blockId)}"]`);
  if (!block?.parentElement) return null;
  const prevBlock = (el: Element): Element | null => {
    let s = el.previousElementSibling;
    while (s && !s.hasAttribute('data-block')) s = s.previousElementSibling;
    return s;
  };
  const nextBlock = (el: Element): Element | null => {
    let s = el.nextElementSibling;
    while (s && !s.hasAttribute('data-block')) s = s.nextElementSibling;
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
  const carried = Array.from(page.querySelectorAll('[data-block]')).filter(
    (b) => b.getAttribute('data-block') !== 'heading',
  );
  const targetSlots = Array.from(el.querySelectorAll('[data-slot]'));

  if (carried.length && !targetSlots.length) return null; // refuse, never delete

  if (targetSlots.length) {
    // Placeholders yield to real content — but only in a slot that receives.
    const byName = new Map(targetSlots.map((s) => [s.getAttribute('data-slot'), s]));
    const fallback = targetSlots[0];
    const receiving = new Set<Element>();
    carried.forEach((b) => {
      const from = b.closest('[data-slot]')?.getAttribute('data-slot') ?? null;
      const target = (from && byName.get(from)) || fallback;
      if (!receiving.has(target)) {
        target.querySelectorAll('[data-block]').forEach((p) => p.remove());
        receiving.add(target);
      }
      target.appendChild(b);
    });
  }
  page.replaceWith(el);
  return { html: serialize(doc), landedId: el.getAttribute('data-arrange') };
}
