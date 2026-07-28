// Executing check of ADR-482 D11 — normalizeBlockIds promotes the bare
// block-level elements native Enter creates on a flow root.
//
// The regression it guards: pressing Enter on a flow root's contenteditable
// inserts a native <div>/<p> with NO data-block. normalizeBlockIds only ever
// touched elements that ALREADY carried data-block, so those bare divs saved
// as un-addressable, un-selectable content (verified in prod: a document of
// raw <div>text</div> siblings). Promotion names them prose so the id pass —
// and every downstream affordance (select, address, '/') — reaches them.
//
// Runs the REAL function body extracted from artifactOps.ts against a hand-mock
// DOM whose API is exactly what the body calls. A FALSIFIER restores the
// pre-D11 body (no promotion) and asserts the bare div is left un-annotated.
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
// Strip the one TS generic the body carries (`new Set<string>(`) so `new
// Function` parses it as plain JS. The promotion loop D11 adds is untyped.
const body = extractFn('normalizeBlockIds').replace('new Set<string>(', 'new Set(');

// ── The hand-mock DOM ──────────────────────────────────────────────────────
// Only the surface normalizeBlockIds touches: children, hasAttribute,
// getAttribute, setAttribute, tagName, textContent, contains, querySelectorAll,
// doc.querySelectorAll, doc.createElement (freshBlockId reads doc-wide ids).
function El(tag, attrs) {
  return {
    tagName: tag.toUpperCase(),
    _attrs: { ...(attrs || {}) },
    _children: [],
    _text: '',
    get children() { return this._children; },
    get textContent() { return this._text || this._children.map((c) => c.textContent).join(''); },
    set textContent(v) { this._text = v; },
    hasAttribute(k) { return k in this._attrs; },
    getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; },
    setAttribute(k, v) { this._attrs[k] = v; },
    append(...kids) { kids.forEach((k) => this._children.push(k)); return this; },
    contains(node) {
      if (node === this) return true;
      return this._children.some((c) => c === node || (c.contains && c.contains(node)));
    },
    _walk(pred, out) {
      this._children.forEach((c) => { if (pred(c)) out.push(c); c._walk && c._walk(pred, out); });
      return out;
    },
    querySelectorAll(sel) {
      const pred = matcher(sel);
      return this._walk(pred, []);
    },
  };
}
function matcher(sel) {
  if (sel === '[data-block-id]') return (el) => el.hasAttribute('data-block-id');
  if (sel === '[data-block]') return (el) => el.hasAttribute('data-block');
  throw new Error(`gate mock: unhandled selector ${sel}`);
}
function makeDoc(region, strays) {
  const all = [region, ...collect(region), ...(strays || [])];
  return {
    createElement: (t) => El(t),
    querySelectorAll(sel) { const pred = matcher(sel); return all.filter(pred); },
  };
}
function collect(el, out = []) { el.children.forEach((c) => { out.push(c); collect(c, out); }); return out; }

function run(bodySrc, region, strays) {
  const doc = makeDoc(region, strays);
  const fn = new Function('doc', 'region', 'freshBlockId',
    'const CSS = { escape: (s) => s };\n' + bodySrc);
  let n = 0;
  const freshBlockId = () => `gen${++n}`;
  return fn(doc, region, freshBlockId);
}

let pass = 0, fail = 0;
const t = (label, cond) => { console.log((cond ? '[PASS] ' : '[FAIL] ') + label); cond ? pass++ : fail++; };

// A flow root: one real prose block + two bare divs Enter created + a <br>-only line.
function scene() {
  const main = El('main');
  const prose = El('div', { 'data-block': 'prose', 'data-block-id': 'b1' });
  prose.textContent = 'kept';
  const bare1 = El('div'); bare1.textContent = 'ddd';
  const bare2 = El('p'); bare2.textContent = 'more';
  const brOnly = El('div'); // empty — a <br>-only line
  const island = El('span', { 'data-ref': 'x', 'data-block-id': 'r1' }); island.textContent = 'ref';
  main.append(prose, bare1, bare2, brOnly, island);
  return { main, prose, bare1, bare2, brOnly, island };
}

// ── D11: the bare divs get promoted + minted; the rest is untouched ────────
{
  const s = scene();
  const minted = run(body, s.main);
  t('D11 bare <div> promoted to prose', s.bare1.getAttribute('data-block') === 'prose');
  t('D11 bare <p> promoted to prose', s.bare2.getAttribute('data-block') === 'prose');
  t('D11 promoted blocks get fresh ids', !!s.bare1.getAttribute('data-block-id') && !!s.bare2.getAttribute('data-block-id'));
  t('D11 the <br>-only line is NOT promoted', !s.brOnly.hasAttribute('data-block'));
  t('D11 the existing prose block keeps its id', s.prose.getAttribute('data-block-id') === 'b1');
  t('D11 the citation island is never promoted', !s.island.hasAttribute('data-block'));
  t('D11 two ids minted (the two bare blocks)', minted === 2);
}

// FALSIFIER: the pre-D11 body had no promotion loop — strip it and re-run.
{
  const stripped = body.slice(body.indexOf('const seen = new Set'));
  const s = scene();
  run(stripped, s.main);
  t('FALSIFIER: without the promotion pass the bare div stays un-annotated', !s.bare1.hasAttribute('data-block'));
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
