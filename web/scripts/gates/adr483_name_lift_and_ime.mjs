// Executing check of the ADR-483 paths — the name lift and the IME guard.
//
// Both are EXECUTED, not grepped, and each carries a FALSIFIER that restores
// the pre-fix behaviour and asserts the defect comes back. That distinction is
// the lesson this repo keeps relearning: a source-shape assertion stays green
// while the surface is unusable (ADR-482's own gate did exactly that).
//
// Run: node web/scripts/gates/adr483_name_lift_and_ime.mjs
import { readFileSync } from 'fs';

const src = readFileSync('web/components/studio/StudioSurface.tsx', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── Extract the REAL functions from the component source ────────────────────
// Sliced by name so the gate breaks loudly if they are renamed away, rather
// than silently testing a stale copy.
function extract(name) {
  const i = src.indexOf(`function ${name}(`);
  if (i < 0) throw new Error(`ADR-483 gate: ${name}() not found in StudioSurface.tsx`);
  // Walk braces from the signature's opening `{` to its match.
  const start = src.indexOf('{', i);
  let depth = 0;
  for (let j = start; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') {
      depth--;
      if (depth === 0) return src.slice(i, j + 1);
    }
  }
  throw new Error(`ADR-483 gate: could not close ${name}()`);
}

// The three name functions, loaded as real code. `document` is stubbed to the
// textarea-unescape shim the browser provides.
const nameSrc = [extract('artifactNameFromPath'), extract('extractTitle'), extract('artifactNameOf')]
  .join('\n')
  .replace(/: string\[\]/g, '')
  .replace(/: string \| undefined/g, '')
  .replace(/: string \| null/g, '')
  .replace(/: string/g, '');

const mkDoc = () => ({
  createElement: () => ({
    set innerHTML(v) {
      this._v = String(v).replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>');
    },
    get value() {
      return this._v ?? '';
    },
  }),
});

const load = () =>
  new Function(
    'document',
    `${nameSrc}; return { artifactNameFromPath, extractTitle, artifactNameOf };`,
  )(mkDoc());

const { artifactNameOf, artifactNameFromPath } = load();
const PLACEHOLDERS = [
  'The headline promise.',
  'The one-line thesis goes here.',
  'Untitled article',
  'Untitled document',
];
const html = (title) => `<html><head><title>${title}</title></head><body></body></html>`;

// ── 1. THE REGRESSION: the operator's actual artifact ───────────────────────
// `operation/sd/document.html` carrying <title>sdㄴ</title>. Pre-fix the crumb
// read "Sd" — the folder slug, because the non-Latin character drops on the
// way into the path key. The lift must read what the member typed.
t(
  'lift: a non-Latin name reads from <title>, not the lossy slug (the regression)',
  artifactNameOf('/workspace/operation/sd/document.html', html('sdㄴ'), PLACEHOLDERS) === 'sdㄴ',
);
t(
  'lift: a fully non-Latin name survives (path slugs to `untitled`)',
  artifactNameOf('/workspace/operation/untitled/document.html', html('한글 문서'), PLACEHOLDERS) ===
    '한글 문서',
);
t(
  'lift: exact casing survives (ADR-469 — `IR deck v3`, never `Ir deck v3`)',
  artifactNameOf('/workspace/operation/ir-deck-v3/deck.html', html('IR deck v3'), PLACEHOLDERS) ===
    'IR deck v3',
);

// ── 2. THE PLACEHOLDER GUARD — parity with services/studio.py::artifact_name.
// A scaffold title is NOT a name: a pre-ADR-469 artifact kept the placeholder
// while its folder held the real name, so content-wins would mislabel it.
t(
  'guard: a scaffold <title> falls through to the meaning folder',
  artifactNameOf(
    '/workspace/operation/prd-for-yarnnn/document.html',
    html('Untitled document'),
    PLACEHOLDERS,
  ) === 'Prd for yarnnn',
);
t(
  'guard: a paged scaffold thesis is a placeholder too, not a name',
  artifactNameOf(
    '/workspace/operation/q3-review/deck.html',
    html('The headline promise.'),
    PLACEHOLDERS,
  ) === 'Q3 review',
);
t(
  'guard: no <title> at all → the folder (degrades honestly)',
  artifactNameOf('/workspace/operation/prd-for-yarnnn/document.html', '<html></html>', PLACEHOLDERS) ===
    'Prd for yarnnn',
);
t(
  'guard: an escaped title round-trips exact (`&amp;` → `&`)',
  artifactNameOf('/workspace/operation/r-and-d/document.html', html('R &amp; D'), PLACEHOLDERS) ===
    'R & D',
);

// ── 3. FALSIFIER for the lift ───────────────────────────────────────────────
// Restore the pre-ADR-483 crumb (path-only) and assert the defect returns. If
// this ever PASSES the lift, the test above is not proving what it claims.
t(
  'FALSIFIER: the pre-fix path-only derivation does mangle the name',
  artifactNameFromPath('/workspace/operation/sd/document.html') === 'Sd',
);

// ── 4. THE IME GUARD — executed against the real onKeyDown body ─────────────
// Extracted from the crumb input so the gate runs the shipped handler.
function extractKeyDown(marker) {
  const i = src.indexOf(marker);
  if (i < 0) throw new Error(`ADR-483 gate: marker not found: ${marker}`);
  // The marker is the input's aria-label, which sits AFTER onKeyDown in the
  // JSX — so search backward from it for the handler belonging to this input.
  const kd = src.lastIndexOf('onKeyDown={(e) => {', i);
  if (kd < 0) throw new Error('ADR-483 gate: no onKeyDown before the marker');
  const start = src.indexOf('{', src.indexOf('=>', kd));
  let depth = 0;
  for (let j = start; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}') {
      depth--;
      if (depth === 0) return src.slice(start + 1, j);
    }
  }
  throw new Error('ADR-483 gate: could not close onKeyDown');
}

const kdBody = extractKeyDown('aria-label="Rename this artifact"');

function pressEnter({ isComposing, value = 'sd' }) {
  const calls = { commit: [], closed: false, prevented: false };
  const e = {
    key: 'Enter',
    nativeEvent: { isComposing },
    currentTarget: { value },
    preventDefault: () => {
      calls.prevented = true;
    },
  };
  new Function('e', 'commitRename', 'setRenaming', kdBody)(
    e,
    (v) => calls.commit.push(v),
    (v) => {
      calls.closed = !v;
    },
  );
  return calls;
}

// THE BUG: mid-composition Enter must NOT commit. This is what wrote `sdㄴ`.
const composing = pressEnter({ isComposing: true, value: 'sdㄴ' });
t('ime: Enter DURING composition commits nothing (the regression)', composing.commit.length === 0);
t('ime: Enter during composition does not preventDefault (the IME needs it)', !composing.prevented);

// The assembled syllable still commits on the next Enter — the guard must not
// break the ordinary path for anyone.
const done = pressEnter({ isComposing: false, value: '스터디' });
t('ime: Enter AFTER composition still commits', done.commit.length === 1);
t('ime: it commits the assembled value', done.commit[0] === '스터디');
t('ime: Latin typing is entirely unaffected', pressEnter({ isComposing: false }).commit[0] === 'sd');

// FALSIFIER: strip the guard, assert the fragment commits again.
const preFix = kdBody.replace(/if \(e\.nativeEvent\.isComposing\) return;/, '');
const broke = (() => {
  const calls = [];
  new Function('e', 'commitRename', 'setRenaming', preFix)(
    {
      key: 'Enter',
      nativeEvent: { isComposing: true },
      currentTarget: { value: 'sdㄴ' },
      preventDefault: () => {},
    },
    (v) => calls.push(v),
    () => {},
  );
  return calls;
})();
t("FALSIFIER: without the guard, the half-formed 'sdㄴ' commits again", broke[0] === 'sdㄴ');

console.log(`\nADR-483: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
