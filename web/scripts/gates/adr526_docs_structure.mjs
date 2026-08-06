// Executing check of ADR-526 — the document shows its shape.
//
// Executes the REAL extracted bodies (outline walk, internal-paste detection,
// the sanitizer's attribute carve) with a falsifier per claim. Source-text
// assertions are used only where the claim IS about wiring.
//
// Run from the REPO ROOT: node web/scripts/gates/adr526_docs_structure.mjs
import { readFileSync } from 'fs';

const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');
const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');
const surface = readFileSync('web/components/studio/StudioSurface.tsx', 'utf8');
const canvas = readFileSync('web/components/studio/StudioCanvas.tsx', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── A tiny DOM good enough for querySelectorAll('h1, h2, h3') ──────────────
function mkHeading(tag, id, text) {
  return {
    tagName: tag.toUpperCase(),
    _a: { 'data-block-id': id },
    textContent: text,
    getAttribute(k) {
      return this._a[k] ?? null;
    },
  };
}
function mkRoot(heads) {
  return { querySelectorAll: () => heads };
}

// ── 1. D2 — the outline derivation, EXECUTED ──────────────────────────────
const oi = proj.length && pane.indexOf('function walkOutline(root');
t('D2: walkOutline exists', oi > 0);
const outlineBody = pane.slice(pane.indexOf('{', oi) + 1, pane.indexOf('\n}', oi));
// Strip the TS annotations so the body runs as plain JS.
const runnable = outlineBody
  .replace(/const out: StructNode\[\] = \[\];/, 'const out = [];')
  .replace(/: Element \| null/g, '')
  .replace(/\bas [A-Za-z<>[\]]+/g, '');
const walkOutline = new Function('root', runnable + '\nreturn out;');

const heads = [
  mkHeading('h1', 'a1', 'Overview'),
  mkHeading('h2', 'b2', 'Pricing'),
  mkHeading('h3', 'c3', 'Enterprise'),
];
const got = walkOutline(mkRoot(heads));
t('D2: every heading becomes a row', got.length === 3);
t('D2: document order is preserved', got.map((n) => n.blockId).join(',') === 'a1,b2,c3');
t('D2: depth is the heading LEVEL (h1=0, h2=1, h3=2)', got.map((n) => n.depth).join(',') === '0,1,2');
t('D2: the label is the heading text', got[1].label === 'Pricing');
t('D2: the id is carried (the row is addressable — clickable)', got[2].blockId === 'c3');

// An un-normalized heading (no id) is not addressable and must not render a
// dead row; an empty heading names nothing.
t(
  'D2: a heading with NO id is skipped (not addressable)',
  walkOutline(mkRoot([mkHeading('h1', null, 'Ghost')])).length === 0,
);
t(
  'D2: an EMPTY heading is skipped (it names nothing)',
  walkOutline(mkRoot([mkHeading('h1', 'x', '   ')])).length === 0,
);
// FALSIFIER: dropping the id guard would emit an unclickable row.
const noGuard = runnable.replace(/if \(!id\) continue;[^\n]*/, '');
t(
  'FALSIFIER: without the id guard the ghost heading DOES emit a row',
  new Function('root', noGuard + '\nreturn out;')(mkRoot([mkHeading('h1', null, 'Ghost')])).length === 1,
);

// ── 2. D2 — the outline is MOUNTED, flow-only, and reuses ContentsRows ─────
t('D2: the outline memo is flow-gated', /mode === 'flow' \? walkOutline/.test(pane));
t('D2: the Outline section renders at document scope', />Outline<\/p>/.test(pane));
t(
  'D2: it reuses ContentsRows (one row component, two mounts)',
  /<ContentsRows nodes=\{outline\}/.test(pane),
);
t('D2: the empty state is honest, not invented', /No headings yet/.test(pane));
t(
  'D2: the enclosing-heading crumb replaces the always-null pathRow on flow',
  /const headingRow =/.test(pane) && /\{headingRow\}/.test(pane),
);
t(
  'D2: the crumb reads selection.headingId (ADR-522 derivation, second consumer)',
  /selection\?\.headingId/.test(pane),
);
t(
  'D2: the document-scope invitation stops naming a grain flow lacks',
  /mode === 'flow'\s*\?\s*'select a block on the canvas/.test(pane),
);

// The parent-side reach must declare the tier (ADR-525 D1) and normalize the
// heading TAG to the vocabulary kind.
t(
  'D2: the reach declares a tier rather than letting the pane guess',
  /tier: !node\.kind/.test(surface),
);
t(
  'D2: the reach reads the SHARED kind list (no second copy of the rule)',
  /TEXT_BLOCK_KINDS as readonly string\[\]/.test(surface),
);
t(
  'D2: the heading TAG is normalized to the vocabulary kind at the seam',
  /\/\^h\[1-6\]\$\/\.test\(node\.kind\) \? 'heading'/.test(surface),
);

// ── 3. D3 — ⌥↑/⌥↓, the structure-tier reorder door ────────────────────────
t('D3: the runtime binds Alt+Arrow', /!e\.altKey \|\| \(e\.key !== 'ArrowUp'/.test(proj));
t(
  'D3: the subject is the STRUCTURE tier, not selectedBlock() (the object gate)',
  /function structureSubject\(\)/.test(proj) && /var subj = structureSubject\(\);/.test(proj),
);
t(
  'D3: a non-collapsed RANGE yields to the platform',
  /if \(s && s\.rangeCount && !s\.getRangeAt\(0\)\.collapsed\) return;/.test(proj),
);
t('D3: it posts the existing key-verb channel', /verb: e\.key === 'ArrowUp' \? 'up' : 'down'/.test(proj));
t(
  'D3: the surface routes up/down to the EXISTING moveBlock op',
  /if \(verb === 'up' \|\| verb === 'down'\) \{[\s\S]{0,200}?moveBlock\(html, blockId, verb\)/.test(surface),
);
// The load-bearing safety property: handleKeyVerb ENDS in an unguarded
// deleteBlock, so a verb without its own branch deletes the member's block.
// Scoped to the function's own body (declaration → its closing `);`), never a
// fixed character window: a comment or a new branch must not be able to push
// the fallthrough out of range and report a false pass OR a false failure.
const kvStart = surface.indexOf('const handleKeyVerb');
const kv = surface.slice(kvStart, surface.indexOf('\n  );', kvStart));
// Match the CALL, not the word: the branch is documented with a comment that
// names `deleteBlock`, and an identifier-only search found the prose first —
// a gate reading its own explanation rather than the code.
t(
  'D3: the move branch precedes the unguarded delete fallthrough',
  kv.indexOf("verb === 'up'") > 0 &&
    kv.indexOf("verb === 'up'") < kv.indexOf('deleteBlock(html, blockId)'),
);
t('D3: the canvas forwards the widened verb union', /'delete' \| 'up' \| 'down'/.test(canvas));

// ── 4. D4 — the internal-paste attribute round-trip ───────────────────────
const ipi = proj.indexOf('function isInternalPaste(html) {');
t('D4: isInternalPaste exists', ipi > 0);
const ipBody = proj.slice(proj.indexOf('{', ipi) + 1, proj.indexOf('\n  }', ipi));
function runIsInternal(html, presentId) {
  const win = { CSS: null };
  const doc = { querySelector: (sel) => (presentId && sel.includes(presentId) ? {} : null) };
  return new Function('html', 'window', 'document', ipBody)(html, win, doc);
}
t(
  'D4: html carrying an id THIS document has is internal',
  runIsInternal('<p data-block-id="abc">x</p>', 'abc') === true,
);
t(
  'D4: html carrying an id this document lacks is FOREIGN',
  runIsInternal('<p data-block-id="zzz">x</p>', 'abc') === false,
);
t('D4: html with no block id at all is FOREIGN', runIsInternal('<p>hello</p>', 'abc') === false);
t(
  'D4: the keep-list is closed and names the grammar only',
  /'data-ref': 1/.test(proj) && /'data-tone': 1/.test(proj) && !/'style': 1/.test(proj) && !/'class': 1/.test(proj),
);
t(
  'D4: data-block-id itself is NEVER kept (ids are re-minted, never duplicated)',
  !/'data-block-id': 1/.test(proj),
);
t(
  'D4: the carve is gated on `internal` — the foreign path is untouched',
  /if \(internal && PASTE_KEEP_INTERNAL\[name\.toLowerCase\(\)\] === 1\) continue;/.test(proj),
);
t(
  'D4: the single caller passes provenance',
  /sanitizePastedHtml\(html, isInternalPaste\(html\)\)/.test(proj),
);
// The security property that must NOT regress: javascript: hrefs still die,
// on both paths.
t(
  'D4: javascript: hrefs are still stripped (the D5 gate is intact)',
  /v\.indexOf\('javascript:'\) === 0\) el\.removeAttribute\('href'\)/.test(proj),
);

console.log(`\nADR-526: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
