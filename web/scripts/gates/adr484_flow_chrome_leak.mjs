// Executing check of the ADR-484 paths — the flow selection cue's scope, and
// the chrome-class leak into saved substrate.
//
// Both EXECUTE the real bodies extracted from projection.ts, and each carries a
// FALSIFIER that restores the pre-fix behaviour and asserts the defect returns.
//
// Run from the REPO ROOT: node web/scripts/gates/adr484_flow_chrome_leak.mjs
import { readFileSync } from 'fs';

const src = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── A minimal DOM good enough for classList + querySelectorAll('.cls') ──────
function mkEl(tag, blockKind, classes = []) {
  const el = {
    tagName: tag.toUpperCase(),
    _cls: new Set(classes),
    _attrs: { 'data-block': blockKind },
    children: [],
    getAttribute(k) {
      if (k === 'class') return this._cls.size ? [...this._cls].join(' ') : null;
      return this._attrs[k] ?? null;
    },
    setAttribute(k, v) {
      this._attrs[k] = v;
    },
    removeAttribute(k) {
      delete this._attrs[k];
      if (k === 'class') this._cls.clear();
    },
    classList: {
      add: (c) => el._cls.add(c),
      remove: (c) => el._cls.delete(c),
      contains: (c) => el._cls.has(c),
    },
  };
  return el;
}

// ── 1. THE CUE SCOPE — execute the real flow branch ────────────────────────
// Extracted verbatim so a future edit to the guard is caught here.
const i = src.indexOf('if (flowMode) {');
const flowBranch = src.slice(src.indexOf('{', i) + 1, src.indexOf('parent.postMessage(payload', i));

const TEXT_KINDS = ['prose', 'callout', 'quote', 'checklist', 'toggle', 'heading'];

function clickFlow(blockKind) {
  const blk = mkEl('div', blockKind);
  const fn = new Function('cur', 'blk', 'TEXT_KINDS', flowBranch + '; return blk;');
  fn(null, blk, TEXT_KINDS);
  return blk.classList.contains('yarnnn-pointed');
}

// The regression: prose must NOT be boxed. This is the operator's report.
t('cue: clicking PROSE draws no outline (the regression)', clickFlow('prose') === false);
t('cue: clicking a HEADING draws no outline', clickFlow('heading') === false);
t('cue: clicking a QUOTE draws no outline', clickFlow('quote') === false);
t('cue: clicking a CHECKLIST draws no outline', clickFlow('checklist') === false);

// Objects keep it — there is no caret to stand in for the cue.
t('cue: a FIGURE is still selected visibly', clickFlow('figure') === true);
t('cue: a TABLE is still selected visibly', clickFlow('table') === true);
t('cue: a CHART is still selected visibly', clickFlow('chart') === true);
t('cue: a DIVIDER is still selected visibly', clickFlow('divider') === true);

// FALSIFIER: restore ADR-482 D2's unconditional apply; prose boxes again.
const preFix = flowBranch.replace(
  /if \(cur && TEXT_KINDS\.indexOf\(cur\.getAttribute\('data-block'\)\) === -1\) \{\s*cur\.classList\.add\('yarnnn-pointed'\);\s*\}/,
  "if (cur) cur.classList.add('yarnnn-pointed');",
);
const falsified = (() => {
  const blk = mkEl('div', 'prose');
  new Function('cur', 'blk', 'TEXT_KINDS', preFix)(null, blk, TEXT_KINDS);
  return blk.classList.contains('yarnnn-pointed');
})();
t('FALSIFIER: the pre-fix unconditional apply DOES box prose', falsified === true);

// ── 2. THE LEAK — execute the real readSourceInner sanitizer ───────────────
const rsi = src.indexOf('function readSourceInner(el)');
const rsiBody = src.slice(src.indexOf('{', rsi) + 1, src.indexOf('\n  }', rsi));

// A clone whose querySelectorAll answers for the painted class.
function mkClone(els) {
  return {
    cloneNode: () => mkClone(els),
    // Answers for ANY class selector — the strip enumerates a list of chrome
    // classes now (yarnnn-pointed + yarnnn-grouped, 2026-07-24), so a stub
    // hard-coded to one selector would silently return [] for the others and
    // report a leak-free serialize that never actually looked.
    querySelectorAll: (sel) =>
      sel.startsWith('.') ? els.filter((e) => e.classList.contains(sel.slice(1))) : [],
    get innerHTML() {
      return els
        .map((e) => {
          const c = e.getAttribute('class');
          return `<${e.tagName.toLowerCase()}${c ? ` class="${c}"` : ''}>`;
        })
        .join('');
    },
  };
}

function serialize(els) {
  const root = { cloneNode: () => mkClone(els) };
  const fn = new Function('el', 'document', rsiBody);
  return fn(root, { createElement: () => ({ innerHTML: '', firstElementChild: null }) });
}

// The exact prod shape: an h2 that carried the class into the saved file.
const painted = mkEl('h2', 'heading', ['yarnnn-pointed']);
t(
  'leak: the chrome class is stripped from the serialized output (the regression)',
  !serialize([painted]).includes('yarnnn-pointed'),
);
t(
  'leak: a class-less element gains no empty class attribute',
  !serialize([mkEl('div', 'prose')]).includes('class='),
);
// An element with BOTH keeps the member's own class.
const mixed = mkEl('p', 'prose', ['lede', 'yarnnn-pointed']);
const out = serialize([mixed]);
t('leak: an authored class SURVIVES the strip', out.includes('lede'));
t('leak: only the chrome class is removed', !out.includes('yarnnn-pointed'));

// FALSIFIER: remove the strip; the class ships again.
// Removes the whole ENUMERATED strip (the CHROME_CLASSES loop, 2026-07-24 —
// previously a single `querySelectorAll('.yarnnn-pointed')` block). A
// falsifier that no longer matches the code it is meant to delete silently
// stops falsifying: it would leave the strip in place and then assert the leak
// that cannot happen. Anchored on the declaration through the loop's close.
const rsiPre = rsiBody.replace(
  /var CHROME_CLASSES = \[[\s\S]*?\n      \}\n    \}/,
  '',
);
if (rsiPre === rsiBody) {
  console.log('[FAIL] FALSIFIER could not remove the strip — the anchor drifted');
  process.exitCode = 1;
}
const leaked = (() => {
  const root = { cloneNode: () => mkClone([mkEl('h2', 'heading', ['yarnnn-pointed'])]) };
  return new Function('el', 'document', rsiPre)(root, {
    createElement: () => ({ innerHTML: '', firstElementChild: null }),
  });
})();
t('FALSIFIER: without the strip, the chrome class IS serialized', leaked.includes('yarnnn-pointed'));

console.log(`\nADR-484: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
