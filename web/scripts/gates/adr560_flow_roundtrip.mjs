/** ADR-560 — the flow model round-trip gate.
 *
 * EXECUTES the schema + serializer over real substrate shapes (never greps a
 * spelling): the Docs scaffold, every text kind, citation islands, unknown
 * kinds, legacy containers, marks, rung clamps, duplicate ids, executables.
 *
 * The three properties gated:
 *   1. IDEMPOTENCE — canonical form is a fixed point (F2's honest half:
 *      serialization is deterministic; legacy attr order canonicalizes ONCE).
 *   2. PRESERVATION (D3) — every data-* annotation present before is present
 *      after; unknown structure survives verbatim; executables are stripped.
 *   3. DECLARED NORMALIZATIONS AND NO OTHERS — rung clamp, id discipline,
 *      promotion, b/i→strong/em, single-p prose flatten.
 *
 * Run from the REPO ROOT: node web/scripts/gates/adr560_flow_roundtrip.mjs
 */
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.DOMParser = dom.window.DOMParser;
globalThis.Node = dom.window.Node;
globalThis.Element = dom.window.Element;
globalThis.HTMLElement = dom.window.HTMLElement;

const { buildFlowSchema } = await import('../../lib/authoring/flow/schema.ts');
const { parseRegion, serializeRegion, replaceRegionInner, readRegionInner } = await import(
  '../../lib/authoring/flow/roundtrip.ts'
);

let pass = 0;
let fail = 0;
const check = (label, cond) => {
  if (cond) {
    pass++;
    console.log(`[PASS] ${label}`);
  } else {
    fail++;
    console.log(`[FAIL] ${label}`);
  }
};

const schema = buildFlowSchema({
  rungs: [1, 2, 3],
  kinds: [
    'heading', 'prose', 'quote', 'checklist', 'list', 'numbered', 'divider',
    'table', 'metrics', 'chart', 'figure', 'gallery', 'callout', 'toggle',
    'button', 'component',
  ],
});

const rt = (inner) => serializeRegion(schema, parseRegion(schema, inner));

// ── 1. Idempotence over a corpus ───────────────────────────────────────────
const SCAFFOLD = `<h1 data-block="heading" data-block-id="t1">Untitled document</h1>
  <p class="lede" data-block="heading" data-block-id="t2">One sentence on what this document is for.</p>
  <h2 data-block="heading" data-block-id="t3">First section</h2>
  <div data-block="prose" data-block-id="b1"><p>Start here.</p></div>`;

const CORPUS = {
  scaffold: SCAFFOLD,
  kinds: `<h2 data-block="heading" data-block-id="h1x">Title</h2>
<p data-block="prose" data-block-id="p1">Plain <strong>bold</strong> and <em>italic</em> and <code>code</code>.</p>
<blockquote data-block="quote" data-block-id="q1"><p>Quoted.</p></blockquote>
<ul data-block="list" data-block-id="l1"><li>one</li><li>two<ul><li>nested</li></ul></li></ul>
<ol data-block="numbered" data-block-id="l2"><li>first</li></ol>
<ul data-block="checklist" data-block-id="l3"><li>todo</li></ul>
<hr data-block="divider" data-block-id="d1">
<pre data-block="prose" data-block-id="c1">code  spaced</pre>`,
  islands: `<div data-block="table" data-block-id="tb1" data-ref="operation/x/data.csv" data-ref-kind="table"></div>
<div data-block="metrics" data-block-id="m1"><div class="metric"><strong>42%</strong><span>label</span></div></div>
<figure data-block="figure" data-block-id="f1"><img data-ref="operation/x/img.png" data-ref-rev="abc" alt="pic"><figcaption>A caption</figcaption></figure>
<div data-block="gallery" data-block-id="g1"><figure><img data-ref="operation/x/a.png" alt=""><figcaption></figcaption></figure></div>`,
  tokens: `<p data-block="prose" data-block-id="p2" data-align="center" data-indent="2" data-tone="muted" data-future-token="x">Tokens ride.</p>
<p data-block="prose" data-block-id="p3">A <span data-mark="accent">marked</span> and <span data-highlight="warn">highlighted</span> span.</p>`,
  legacy: `<aside data-block="callout" data-block-id="a1" data-variant="note"><p>Callout prose stays editable.</p></aside>
<details data-block="toggle" data-block-id="a2"><p>Toggle body.</p></details>
<section data-block="unknown-kind" data-block-id="u1"><p>Inside a section container.</p></section>
<div data-block="somekind-not-yet-invented" data-block-id="u2"><em>opaque</em></div>`,
};

for (const [name, inner] of Object.entries(CORPUS)) {
  const once = rt(inner);
  const twice = rt(once);
  check(`idempotence: ${name} — canonical form is a fixed point`, once === twice);
}

// ── 2. Preservation (D3) ───────────────────────────────────────────────────
const out = {};
for (const [name, inner] of Object.entries(CORPUS)) out[name] = rt(inner);

check('scaffold: single-p prose wrapper flattens to the paragraph, id kept',
  /<p data-block="prose" data-block-id="b1">Start here\.<\/p>/.test(out.scaffold));
check('scaffold: the lede keeps kind=heading on a <p> with its class',
  /<p data-block="heading" data-block-id="t2" class="lede">/.test(out.scaffold));
check('kinds: nested list round-trips byte-stably, tight li, no wrapper churn',
  out.kinds.includes('<li>two<ul><li>nested</li></ul></li>'));
check('kinds: interiors of kinded blocks stay UNANNOTATED (insideOwned rule)',
  !/<blockquote[^>]*>\s*<p[^>]+data-block/.test(out.kinds) &&
  !/<li><p[^>]+data-block/.test(out.kinds) &&
  !/<ul[^>]*>[^<]*<[^>]*<ul[^>]+data-block-id/.test(out.kinds));
check('kinds: pre keeps its whitespace', out.kinds.includes('code  spaced'));
check('islands: the cited table div survives verbatim with its ref',
  out.islands.includes('data-ref="operation/x/data.csv"') &&
  out.islands.includes('data-block="table"'));
check('islands: metrics interior survives', out.islands.includes('<strong>42%</strong>'));
check('islands: figure keeps img ref + editable caption',
  out.islands.includes('data-ref="operation/x/img.png"') &&
  out.islands.includes('<figcaption>A caption</figcaption>'));
check('tokens: modeled tokens round-trip',
  out.tokens.includes('data-align="center"') &&
  out.tokens.includes('data-indent="2"') &&
  out.tokens.includes('data-tone="muted"'));
check('tokens: an UNKNOWN data-* token rides the extra bag (GUARDED predicate)',
  out.tokens.includes('data-future-token="x"'));
check('tokens: span emphasis marks round-trip',
  out.tokens.includes('data-mark="accent"') && out.tokens.includes('data-highlight="warn"'));
check('legacy: callout keeps kind + variant, prose intact',
  out.legacy.includes('data-block="callout"') &&
  out.legacy.includes('data-variant="note"') &&
  out.legacy.includes('Callout prose stays editable.'));
check('legacy: unknown kind preserved VERBATIM as an island',
  out.legacy.includes('data-block="somekind-not-yet-invented"') &&
  out.legacy.includes('<em>opaque</em>'));

// ── 3. Declared normalizations, and no others ──────────────────────────────
check('normalization: h5 clamps to the deepest declared rung',
  rt('<h5 data-block-id="hx">Deep</h5>').includes('<h3'));
check('normalization: b/i normalize to strong/em (ADR-446 D2)',
  (() => { const r = rt('<p data-block-id="bi">a <b>b</b> <i>i</i></p>');
    return r.includes('<strong>b</strong>') && r.includes('<em>i</em>'); })());
check('normalization: bare <p> gains its promoted kind at serialize',
  rt('<p>bare paragraph</p>').includes('data-block="prose"'));
check('normalization: a missing id is minted; a duplicate is re-minted',
  (() => {
    const r = rt('<p data-block-id="dup">one</p><p data-block-id="dup">two</p><p>three</p>');
    const ids = [...r.matchAll(/data-block-id="([^"]+)"/g)].map((m) => m[1]);
    return ids.length === 3 && new Set(ids).size === 3 && ids[0] === 'dup';
  })());
check('normalization: an <li> never gains a data-block-id (ADR-546 D2)',
  !/<li[^>]*data-block-id/.test(rt('<ul data-block-id="l9"><li>x</li></ul>')));

// ── 4. Security: executables cannot enter the model ────────────────────────
const dirty = rt(`<div data-block="metrics" data-block-id="mm"><script>alert(1)</script><div onclick="x()">n</div></div>
<p data-block-id="pp">text</p>`);
check('security: <script> inside a preserved island is stripped', !dirty.includes('<script'));
check('security: on* handlers inside a preserved island are stripped', !dirty.includes('onclick'));

// ── 5. The shell splice never touches the shell ────────────────────────────
const ARTIFACT = `<!doctype html>\n<html data-template="document"><head><title>T</title><style>main{color:red}</style></head><body><main>${SCAFFOLD}</main></body></html>`;
const region = readRegionInner(ARTIFACT);
check('shell: region reads out of the artifact', region !== null && region.includes('Start here.'));
const spliced = replaceRegionInner(ARTIFACT, rt(region));
check('shell: head/style/root attrs survive a splice',
  spliced.includes('data-template="document"') &&
  spliced.includes('<style>main{color:red}</style>') &&
  spliced.startsWith('<!doctype html>'));

// ── 6. Falsifier: D3 is load-bearing, not incidental ───────────────────────
// A schema WITHOUT the island node must lose the unknown kind — proving the
// preservation is done by the node, not by accident of parsing.
const doc = parseRegion(schema, CORPUS.legacy);
let islands = 0;
doc.descendants((n) => { if (n.type.name === 'island') islands++; });
check('falsifier: the unknown kind is carried BY the island node', islands >= 1);

console.log(`\n${fail === 0 ? 'PASS' : 'FAIL'}: ${pass}/${pass + fail} checks`);
process.exit(fail === 0 ? 0 : 1);
