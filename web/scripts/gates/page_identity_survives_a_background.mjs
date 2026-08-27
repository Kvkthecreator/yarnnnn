/** A page is stamped even when it cites a background.
 *
 * `data-ref` says two different things. On a BLOCK it means "this element IS
 * the citation" — a figure, a table, a chart — and such an island keeps its
 * identity in the citation, never re-minted (ADR-511 D5 pass C; the ADR-448
 * reference edge lifts from `data-ref` untouched). On a PAGE, since ADR-456
 * W3, it means "this page cites an image for its backdrop". That page is not
 * an island; it is an ordinary page that happens to cite.
 *
 * Pages joined pass C at ADR-519 ("page identity at the seam") and silently
 * inherited the block rule. The consequence, measured in production: every
 * slide carrying a background had NO `data-block-id` while every other slide
 * had one. An id-less page falls through `arrangedPageAt` to INDEX
 * addressing, so a page op addressed a POSITION rather than a slide — and
 * `materializeFragment`, which re-stamped only what already had an id,
 * propagated the condition into every duplicate.
 *
 * This gate DRIVES the real normalize seam rather than grepping it: the
 * defect was a predicate reading the wrong attribute, and a text assertion
 * would pass against either predicate.
 *
 * Run from the REPO ROOT:
 *   node --import ./web/scripts/gates/_ts_register.mjs \
 *        --import ./web/scripts/gates/_stub_projection_register.mjs \
 *        web/scripts/gates/page_identity_survives_a_background.mjs
 */
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.DOMParser = dom.window.DOMParser;
globalThis.Node = dom.window.Node;
globalThis.Element = dom.window.Element;
globalThis.HTMLElement = dom.window.HTMLElement;

const { normalizeArtifact, duplicatePage, setPageBackground } = await import(
  '../../components/authoring/artifactOps.ts'
);

let pass = 0;
let fail = 0;
const t = (label, cond) => {
  if (cond) {
    pass++;
    console.log(`[PASS] ${label}`);
  } else {
    fail++;
    console.log(`[FAIL] ${label}`);
  }
};

const slides = (html) =>
  Array.from(
    new dom.window.DOMParser()
      .parseFromString(html, 'text/html')
      .querySelectorAll('section.slide'),
  );

// The production shape: a plain slide, and a slide carrying a cited backdrop.
const DECK = `<!doctype html><html><head></head><body><main>
<section class="slide" data-arrange="content" data-block-id="keepme">
  <section data-block="prose" data-block-id="p1"><p>plain</p></section>
</section>
<section class="slide" data-arrange="content" data-ref="inbound/uploads/operator/bg.png" data-ref-kind="background" data-ref-rev="">
  <section data-block="prose" data-block-id="p2"><p>backdrop</p></section>
</section>
<figure data-block="figure" data-ref="inbound/uploads/operator/fig.png" data-ref-kind="figure"><img src=""></figure>
</main></body></html>`;

// ── 1. The defect itself ───────────────────────────────────────────────────
const normalized = normalizeArtifact(DECK);
const [plain, backdrop] = slides(normalized);

t('a plain page keeps the id it already had', plain?.getAttribute('data-block-id') === 'keepme');
t(
  'FALSIFIER: a page citing a BACKGROUND is stamped like any other page',
  !!backdrop?.getAttribute('data-block-id'),
);
t(
  'the two pages are addressable APART (identity, not position)',
  !!backdrop?.getAttribute('data-block-id') &&
    backdrop.getAttribute('data-block-id') !== plain?.getAttribute('data-block-id'),
);

// ── 2. The island rule it must NOT break ───────────────────────────────────
// A citation island keeps its identity in the citation. Narrowing the skip to
// exclude backgrounds must not start minting ids onto figures.
const fig = new dom.window.DOMParser()
  .parseFromString(normalized, 'text/html')
  .querySelector('figure[data-ref]');
t(
  'FALSIFIER: a citation ISLAND is still never stamped (the rule is narrowed, not deleted)',
  !!fig && !fig.hasAttribute('data-block-id'),
);

// ── 3. Idempotence — the seam runs on every write ──────────────────────────
const twice = normalizeArtifact(normalized);
t(
  'normalizing twice mints nothing new (ids are stable across writes)',
  slides(twice).map((s) => s.getAttribute('data-block-id')).join() ===
    slides(normalized).map((s) => s.getAttribute('data-block-id')).join(),
);

// ── 4. The propagation path ────────────────────────────────────────────────
// A duplicate of a backgrounded page must be its OWN object. Driven from the
// pre-fix substrate shape (a page that reaches the copier with no id at all),
// because that is the population already written to the workspace.
const LEGACY = `<!doctype html><html><head></head><body><main>
<section class="slide" data-arrange="content" data-ref="x.png" data-ref-kind="background">
  <section data-block="prose" data-block-id="q1"><p>legacy</p></section>
</section>
</main></body></html>`;
const dup = duplicatePage(LEGACY, { blockId: null, slideIndex: 0, pageIndex: null });
const dupSlides = dup ? slides(dup.html) : [];
t('duplicating a legacy backgrounded page yields two pages', dupSlides.length === 2);
t(
  'FALSIFIER: the copy carries its OWN id — an id-less page never propagates',
  dupSlides.length === 2 &&
    !!dupSlides[0]?.getAttribute('data-block-id') &&
    !!dupSlides[1]?.getAttribute('data-block-id') &&
    dupSlides[0].getAttribute('data-block-id') !== dupSlides[1].getAttribute('data-block-id'),
);

// ── 5. The ORDER that produced the production shape ────────────────────────
// The measured defect is a page that gains a background BEFORE it has ever
// been stamped — a deck authored, then given a backdrop, on a substrate where
// pages were index-addressed. The old skip preserved an id it FOUND, so a
// pre-stamped page cannot tell the two predicates apart; this drives the
// sequence that actually loses the identity.
const UNSTAMPED = `<!doctype html><html><head></head><body><main>
<section class="slide" data-arrange="content">
  <section data-block="prose" data-block-id="r1"><p>fresh</p></section>
</section>
</main></body></html>`;
const bgFirst = setPageBackground(UNSTAMPED, { blockId: null, slideIndex: 0, pageIndex: null }, 'bg.png');
const healed = bgFirst ? slides(normalizeArtifact(bgFirst.html))[0] : null;
t(
  'FALSIFIER: a page backgrounded BEFORE it was ever stamped still gets an id',
  !!healed?.getAttribute('data-block-id'),
);
t(
  '…and it keeps the background it was given (the heal is additive)',
  healed?.getAttribute('data-ref-kind') === 'background',
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
