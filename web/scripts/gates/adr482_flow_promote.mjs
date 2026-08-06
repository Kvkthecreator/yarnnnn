// Executing check of ADR-482 D11 (as re-cut by ADR-511 D5) — normalizeStructure
// promotes the bare block-level elements native Enter creates, at ANY depth,
// and stamps structural containers with identity.
//
// The regression it guards is unchanged since D11: pressing Enter on a flow
// root's contenteditable inserts a native <div>/<p> with NO data-block, which
// saved as un-addressable, un-selectable content. ADR-511 widened the fix from
// "flow root, one level" to the whole document (imports, deck templates, any
// depth) and added container identity (pass B) — so this harness exercises
// promotion, container stamping, and the id discipline together.
//
// Runs the REAL function body extracted from artifactOps.ts against a hand-mock
// DOM whose API is exactly what the body calls. A FALSIFIER strips pass A
// (promotion) and asserts the bare div is left un-annotated.
import { readFileSync } from 'fs';

const src = readFileSync('web/components/studio/artifactOps.ts', 'utf8');
function extractFn(name) {
  const i = src.indexOf(`export function ${name}(`);
  let d = 0, start = src.indexOf('{', i);
  for (let j = start; j < src.length; j++) {
    if (src[j] === '{') d++;
    else if (src[j] === '}') { d--; if (d === 0) return src.slice(start + 1, j); }
  }
  throw new Error(`gate: could not brace-match ${name}`);
}
// The body reads three module-level constants — extract them too, stripping
// the one TS annotation each carries, so the harness runs the REAL values.
function extractConst(decl) {
  const i = src.indexOf(decl);
  if (i < 0) throw new Error(`gate: missing ${decl}`);
  const end = src.indexOf(';\n', i);
  return src.slice(i, end + 1);
}
// ADR-511 Phase 2: PAGE_SEL is the structural constant, sourced from the ONE
// vocabulary seam (structureLabels.ts) exactly as the real module imports it.
const labelsSrc = readFileSync('web/components/studio/structureLabels.ts', 'utf8');
const pageSelLit = labelsSrc.match(/export const STRUCTURAL_PAGE_SEL = ('[^']+');/)?.[1];
if (!pageSelLit) throw new Error('gate: STRUCTURAL_PAGE_SEL literal not found');
const prelude = [
  `const PAGE_SEL = ${pageSelLit};`,
  extractConst('const PROMOTE_KIND: Record<string, string> = {').replace(
    ': Record<string, string>',
    '',
  ),
  extractConst('const BLOCK_LEVEL = new Set('),
].join('\n');
const body = prelude + extractFn('normalizeStructure')
  .replace(/: Element\b/g, '')
  .replace(/: boolean\b/g, '')
  .replace('new Set<string>()', 'new Set()');

// ── The hand-mock DOM ──────────────────────────────────────────────────────
let ORD = 0;
function El(tag, attrs) {
  return {
    tagName: tag.toUpperCase(),
    _attrs: { ...(attrs || {}) },
    _children: [],
    _text: '',
    _parent: null,
    _ord: ++ORD,
    get children() { return this._children; },
    get parentElement() { return this._parent; },
    get textContent() { return this._text || this._children.map((c) => c.textContent).join(''); },
    set textContent(v) { this._text = v; },
    hasAttribute(k) { return k in this._attrs; },
    getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    setAttribute(k, v) { this._attrs[k] = v; },
    append(...kids) { kids.forEach((k) => { k._parent = this; this._children.push(k); }); return this; },
    matches(sel) { return matcher(sel)(this); },
    closest(sel) {
      const pred = matcher(sel);
      let n = this;
      while (n) { if (pred(n)) return n; n = n._parent; }
      return null;
    },
    compareDocumentPosition(other) { return other._ord > this._ord ? 4 : 2; },
    _walk(pred, out) {
      this._children.forEach((c) => { if (pred(c)) out.push(c); c._walk && c._walk(pred, out); });
      return out;
    },
    querySelectorAll(sel) { return this._walk(matcher(sel), []); },
    querySelector(sel) { return this._walk(matcher(sel), [])[0] ?? null; },
  };
}
function matcher(sel) {
  const alts = sel.split(',').map((s) => s.trim());
  return (el) =>
    alts.some((a) => {
      if (a === 'section.slide') return el.tagName === 'SECTION' && el._attrs.class === 'slide';
      const attr = a.match(/^\[([a-z-]+)\]$/);
      if (attr) return el.hasAttribute(attr[1]);
      return el.tagName === a.toUpperCase();
    });
}

function run(bodySrc, root) {
  const doc = {
    body: root,
    createElement: (t) => El(t),
    querySelectorAll: (sel) => root._walk(matcher(sel), root.matches(sel) ? [root] : []),
  };
  const fn = new Function('doc', 'freshBlockId', 'Node',
    'const CSS = { escape: (s) => s };\n' + bodySrc);
  let n = 0;
  const freshBlockId = () => `gen${++n}`;
  return fn(doc, freshBlockId, { DOCUMENT_POSITION_FOLLOWING: 4 });
}

let pass = 0, fail = 0;
const t = (label, cond) => { console.log((cond ? '[PASS] ' : '[FAIL] ') + label); cond ? pass++ : fail++; };

// A page with a column container holding a BARE <p> (the shipped two-column
// template's dead placeholder), plus the classic flow scene: a real prose
// block, bare Enter divs, a <br>-only line, a citation island.
function scene() {
  const body = El('body');
  const prose = El('div', { 'data-block': 'prose', 'data-block-id': 'b1' });
  prose.textContent = 'kept';
  const bare1 = El('div'); bare1.textContent = 'ddd';
  const bare2 = El('p'); bare2.textContent = 'more';
  const brOnly = El('div'); // empty — a <br>-only line
  const island = El('span', { 'data-ref': 'x', 'data-block-id': 'r1' }); island.textContent = 'ref';
  const col = El('div', { class: 'col', 'data-slot': 'side' });
  const nestedBare = El('p'); nestedBare.textContent = 'Second column.';
  col.append(nestedBare);
  body.append(prose, bare1, bare2, brOnly, island, col);
  return { body, prose, bare1, bare2, brOnly, island, col, nestedBare };
}

// ── D11 + ADR-511: promotion at any depth; containers get identity ────────
{
  const s = scene();
  run(body, s.body);
  t('D11 bare <div> promoted to prose', s.bare1.getAttribute('data-block') === 'prose');
  t('D11 bare <p> promoted to prose', s.bare2.getAttribute('data-block') === 'prose');
  t('D11 promoted blocks get fresh ids', !!s.bare1.getAttribute('data-block-id') && !!s.bare2.getAttribute('data-block-id'));
  t('D11 the <br>-only line is NOT promoted', !s.brOnly.hasAttribute('data-block'));
  t('D11 the existing prose block keeps its id', s.prose.getAttribute('data-block-id') === 'b1');
  t('D11 the citation island is never promoted', !s.island.hasAttribute('data-block'));
  t('ADR-511 the NESTED bare <p> (a template placeholder) is promoted too', s.nestedBare.getAttribute('data-block') === 'prose');
  t('ADR-511 the container gets IDENTITY, never vocabulary', !!s.col.getAttribute('data-block-id') && !s.col.hasAttribute('data-block'));
}

// FALSIFIER: strip pass A (promotion) — the bare div must stay un-annotated.
{
  const fnBody = extractFn('normalizeStructure')
    .replace(/: Element\b/g, '')
    .replace(/: boolean\b/g, '')
    .replace('new Set<string>()', 'new Set()');
  const stripped = fnBody.slice(fnBody.indexOf('// Pass B'));
  const shim =
    'const root = doc.body;\n' +
    'const insideOwned = (el) => !!(el.parentElement && el.parentElement.closest("[data-block], [data-ref]"));\n' +
    'const isPage = (el) => el.matches(PAGE_SEL);\n';
  const s = scene();
  run(prelude + shim + stripped, s.body);
  t('FALSIFIER: without the promotion pass the bare div stays un-annotated', !s.bare1.hasAttribute('data-block'));
}

// ── ADR-519 §5 Q1 — PAGE identity, stamped at the normalize seam ───────────
// Pages were the one grain addressed by INDEX while blocks and containers
// carried ids, and ADR-516 built a second anchor-based resolver to cope.
// Stamping them closes the split. Migration-by-use: on the NEXT write, never
// a fleet sweep.
//
// Safe because a page is a <section> and every container selector in the
// system is `div[data-block-id]:not([data-block])` — a stamped page can never
// read as a container. Asserted below against the real source, not assumed.
function pageScene() {
  const body = El('body');
  const s1 = El('section', { class: 'slide' });
  const s2 = El('section', { class: 'slide' });
  const col = El('div', { 'data-slot': 'main' });
  const blk = El('div', { 'data-block': 'prose', 'data-block-id': 'b1' });
  blk.textContent = 'kept';
  col.append(blk);
  s1.append(col);
  body.append(s1, s2);
  return { body, s1, s2, col, blk };
}
{
  const s = pageScene();
  run(body, s.body);
  t('§5 Q1: a page is STAMPED with an id at the seam', !!s.s1.getAttribute('data-block-id'));
  t('§5 Q1: an EMPTY page is stamped too (identity is not content-gated)',
    !!s.s2.getAttribute('data-block-id'));
  t('§5 Q1: page ids are UNIQUE across pages',
    s.s1.getAttribute('data-block-id') !== s.s2.getAttribute('data-block-id'));
  t('§5 Q1: a page never gains data-block (it is not a block)', !s.s1.hasAttribute('data-block'));
  // The load-bearing safety property: a stamped page must not read as a
  // CONTAINER. It cannot, because it is a <section> and every container
  // selector is div-qualified — pinned here so a future un-qualified selector
  // is caught by this gate rather than by a member selecting a slide as a box.
  t('§5 Q1: the page stays a SECTION (container selectors are div-qualified)',
    s.s1.tagName === 'SECTION');
  t('§5 Q1: the block keeps its OWN id (stamping pages renumbers nothing)',
    s.blk.getAttribute('data-block-id') === 'b1');
  t('§5 Q1: containers are still stamped alongside', !!s.col.getAttribute('data-block-id'));
}
{
  // Idempotence — an already-stamped page keeps its id on the next write, or
  // "migration by use" would churn a fresh id into every revision.
  const s = pageScene();
  run(body, s.body);
  const first = s.s1.getAttribute('data-block-id');
  run(body, s.body);
  t('§5 Q1: re-normalizing KEEPS the page id (no churn per revision)',
    s.s1.getAttribute('data-block-id') === first);
}
{
  // Every container selector in the app must stay div-qualified, or the
  // safety argument above collapses. Enumerate, never count.
  const files = [
    'web/components/workspace/viewers/projection.ts',
    'web/components/studio/artifactOps.ts',
    'web/components/studio/StudioDesignTab.tsx',
  ];
  const bad = [];
  for (const f of files) {
    const text = readFileSync(f, 'utf8');
    for (const m of text.matchAll(/(.{4})\[data-block-id\]:not\(\[data-block\]\)/g)) {
      if (!m[1].endsWith('div')) bad.push(`${f}: …${m[0]}`);
    }
  }
  t(`§5 Q1: every container selector is div-qualified${bad.length ? ` — ${bad[0]}` : ''}`,
    bad.length === 0);
}
{
  // FALSIFIER: drop the page pass — pages go back to being index-only.
  const mutated = src.replace('for (const p of pages) if (!subjects.includes(p)) subjects.push(p);', '');
  if (mutated === src) {
    t('FALSIFIER: the page-pass removal actually mutated the source', false);
  } else {
    console.log('mutated: removed the page pass from normalizeStructure (in memory)');
    const mBody =
      prelude +
      (function () {
        let d = 0;
        const i = mutated.indexOf('export function normalizeStructure');
        const start = mutated.indexOf('{', i);
        for (let j = start; j < mutated.length; j++) {
          if (mutated[j] === '{') d++;
          else if (mutated[j] === '}') { d--; if (d === 0) return mutated.slice(start + 1, j); }
        }
        throw new Error('gate: brace match failed');
      })()
        .replace(/: Element\b/g, '')
        .replace(/: boolean\b/g, '')
        .replace('new Set<string>()', 'new Set()');
    const s = pageScene();
    run(mBody, s.body);
    t('FALSIFIER: without the page pass, a page is left UNSTAMPED (index-only)',
      !s.s1.getAttribute('data-block-id'));
  }
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
