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

// ── 1. THE CUE SCOPE — execute the real CHOKEPOINT ─────────────────────────
// ADR-525 D2 re-pointed this section. It used to execute the left-click flow
// branch, which is where ADR-484 put its guard — and that is exactly why the
// defect came back: the guard lived at the CALL SITES, so `__yarnnnSelect`
// (reached by the parent re-command, the backspace-merge, the Esc-from-edit and
// the Esc-walk) boxed prose while this gate stayed green at 14/14. A gate over
// two of six routes is a gate over the wrong extent.
//
// Now: execute the one function that may draw a box, and separately ASSERT that
// it is the only one (§1b). Enumerate + completeness-assert + falsify.
const sel = src.indexOf('window.__yarnnnSelect = function (el) {');
const selBody = src.slice(src.indexOf('{', sel + 30) + 1, src.indexOf('\n  };', sel));

const tierIdx = src.indexOf('function tierOf(el) {');
const tierBody = src.slice(src.indexOf('{', tierIdx) + 1, src.indexOf('\n  }', tierIdx));

const TEXT_KINDS = ['prose', 'callout', 'quote', 'checklist', 'toggle', 'heading'];

/** Execute the real __yarnnnSelect + the real tierOf, in the given medium. */
function selectIn(flow, blockKind) {
  const el = mkEl('div', blockKind);
  const win = { __yarnnnFlowMode: () => flow };
  // ADR-519 D4.1 (2026-08-06) — __yarnnnSelect now also clears the multi-select
  // SET and posts the empty set to the parent, so the harness supplies those
  // two closures too. Shimmed rather than modelled on purpose: this gate is
  // about the CUE (is prose boxed), and the set is adr519_d41's subject. An
  // empty `group` means the clear branch is skipped, which is the state every
  // case here runs in.
  const fn = new Function(
    'window',
    'TEXT_KINDS',
    'el',
    'cur',
    'clearGroup',
    'group',
    'parent',
    `function tierOf(el) {${tierBody}}
     var __sel = function (el) {${selBody}};
     __sel(el); return el;`,
  );
  fn(win, TEXT_KINDS, el, null, () => {}, [], { postMessage: () => {} });
  return el.classList.contains('yarnnn-pointed');
}

// The regression: prose must NOT be boxed. This is the operator's report.
t('cue: clicking PROSE draws no outline (the regression)', selectIn(true, 'prose') === false);
t('cue: clicking a HEADING draws no outline', selectIn(true, 'heading') === false);
t('cue: clicking a QUOTE draws no outline', selectIn(true, 'quote') === false);
t('cue: clicking a CHECKLIST draws no outline', selectIn(true, 'checklist') === false);

// Objects keep it — there is no caret to stand in for the cue.
t('cue: a FIGURE is still selected visibly', selectIn(true, 'figure') === true);
t('cue: a TABLE is still selected visibly', selectIn(true, 'table') === true);
t('cue: a CHART is still selected visibly', selectIn(true, 'chart') === true);
t('cue: a DIVIDER is still selected visibly', selectIn(true, 'divider') === true);

// ADR-525 D1 — on PAGED every block is an enclosure (ADR-480 D1), prose too.
t('cue: PROSE on a PAGED medium still boxes (the enclosure grain)', selectIn(false, 'prose') === true);
t('cue: a HEADING on PAGED still boxes', selectIn(false, 'heading') === true);

// FALSIFIER: restore the unconditional apply; prose boxes again on flow.
const preFix = selBody.replace(
  /if \(tierOf\(el\) !== 'text'\) el\.classList\.add\('yarnnn-pointed'\);/,
  "el.classList.add('yarnnn-pointed');",
);
const falsified = (() => {
  const el = mkEl('div', 'prose');
  const win = { __yarnnnFlowMode: () => true };
  new Function(
    'window',
    'TEXT_KINDS',
    'el',
    'cur',
    'clearGroup',
    'group',
    'parent',
    `function tierOf(el) {${tierBody}}
     var __sel = function (el) {${preFix}};
     __sel(el);`,
  )(win, TEXT_KINDS, el, null, () => {}, [], { postMessage: () => {} });
  return el.classList.contains('yarnnn-pointed');
})();
t('FALSIFIER: the pre-fix unconditional apply DOES box prose', falsified === true);

// ── 1b. COMPLETENESS (ADR-525 D2) — the chokepoint is the ONLY box site ────
// The invariant this gate exists to defend is per-site, and a per-site
// invariant cannot be defended by executing one site. Enumerate every place
// that paints the class and assert exactly one survives, inside the function.
const addSites = [...src.matchAll(/classList\.add\('yarnnn-pointed'\)/g)].map((m) => m.index);
const selStart = src.indexOf('window.__yarnnnSelect = function (el) {');
const selEnd = src.indexOf('\n  };', selStart);
const outside = addSites.filter((idx) => idx < selStart || idx > selEnd);
t(
  `completeness: exactly ONE site paints the cue (found ${addSites.length})`,
  addSites.length === 1,
);
t(
  `completeness: no box site outside __yarnnnSelect (found ${outside.length})`,
  outside.length === 0,
);
// FALSIFIER for the completeness assertion itself — a gate that cannot fail is
// not a gate. Injecting a second site must trip it.
const withLeak = src.slice(0, selStart) + "el.classList.add('yarnnn-pointed');\n  " + src.slice(selStart);
const leakSites = [...withLeak.matchAll(/classList\.add\('yarnnn-pointed'\)/g)];
t('FALSIFIER: an injected second box site IS detected', leakSites.length === 2);

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
