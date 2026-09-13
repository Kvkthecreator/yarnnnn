/** An IME composition owns Enter first — everywhere, from one rule.
 *
 * ## The defect
 *
 * Twenty `onKeyDown` handlers asked `e.key === 'Enter'` and acted. A repo-wide
 * grep for `isComposing` returned TypeScript's own `lib.dom.d.ts` and two
 * hand-rolled guards — ADR-483 D3's, whose own comment said "kept in lockstep."
 *
 * On an IME keyboard Enter COMMITS a candidate syllable, and the browser fires
 * `keydown` with `key === 'Enter'` while it does. So composing Hangul in the
 * chat composer SENT the message mid-word; the same Enter renamed a lane,
 * created a folder, invited a member, added a source.
 *
 * ADR-483 D3 fixed exactly two name fields and closed with "not a
 * Studio-specific rule". The ruling was already general; only its spelling was
 * local, which is why eighteen other sites never got it.
 *
 * ## What this gate holds
 *
 *   1. the RULE, executed: a composing Enter is never a submit, by either
 *      signal — the standard `isComposing` and the legacy `keyCode === 229`
 *      that some Korean/Android IMEs report INSTEAD of it;
 *   2. both event shapes, because a handler may be given React's synthetic
 *      event or a native one, and the legacy sentinel only ever rides the
 *      native event;
 *   3. Shift+Enter is not a submit by default (every multi-line composer in
 *      this app spells a newline that way) and IS one under `allowShift`;
 *   4. the soft-keyboard rule keys on POINTER PRECISION, never a width or a
 *      user-agent string — an iPad with a keyboard reports `fine` and keeps
 *      Enter-to-send;
 *   5. the CENSUS: no handler acts on a bare `key === 'Enter'` any more. This
 *      is the half that keeps the rule from being forgotten at site
 *      twenty-one, and it is why the fix is a module rather than 20 guards.
 *
 * Run from the REPO ROOT:
 *   node web/scripts/gates/enter_belongs_to_the_ime_first.mjs
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';

const ROOT = process.cwd();
let pass = 0;
let fail = 0;
const t = (label, cond, detail = '') => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label + (cond || !detail ? '' : ` — ${detail}`));
  cond ? pass++ : fail++;
};

const read = (p) => {
  try {
    return readFileSync(`${ROOT}/${p}`, 'utf8');
  } catch {
    t(`the gate reads a path that still exists — ${p}`, false, 'renamed or deleted; re-anchor');
    return '';
  }
};

// ── The rule, EXECUTED ────────────────────────────────────────────────────
// Transpiled rather than grepped: a guard that is present but reads the wrong
// property greps identically to one that works. TS types are stripped by a
// regex here because the module is deliberately plain — no imports, no JSX —
// so there is nothing else to resolve.
const SRC = read('web/lib/shell/submit-key.ts');
const js = SRC
  .replace(/export interface [\s\S]*?\n\}/g, '')
  .replace(/:\s*SubmitKeyEvent/g, '')
  .replace(/\)\s*:\s*boolean/g, ')')
  .replace(/export /g, '');
let isSubmitKey;
let prefersSoftKeyboard;
try {
  ({ isSubmitKey, prefersSoftKeyboard } = new Function(
    `${js}\nreturn { isSubmitKey, prefersSoftKeyboard };`,
  )());
  t('the rule is extractable and evaluates', true);
} catch (e) {
  t('the rule is extractable and evaluates', false, e.message);
}

if (isSubmitKey) {
  // 1 + 2. A composing Enter is never a submit — both signals, both shapes.
  t('a plain Enter submits', isSubmitKey({ key: 'Enter' }) === true);
  t(
    'an Enter during composition does NOT submit (standard flag)',
    isSubmitKey({ key: 'Enter', isComposing: true }) === false,
  );
  t(
    'an Enter during composition does NOT submit (React synthetic shape)',
    isSubmitKey({ key: 'Enter', nativeEvent: { isComposing: true } }) === false,
  );
  t(
    'the LEGACY keyCode 229 sentinel is honoured (older Korean/Android IMEs)',
    isSubmitKey({ key: 'Enter', keyCode: 229 }) === false &&
      isSubmitKey({ key: 'Enter', nativeEvent: { keyCode: 229 } }) === false,
  );
  t('a non-Enter key is never a submit', isSubmitKey({ key: 'a' }) === false);

  // 3. Shift.
  t('Shift+Enter is a newline, not a submit', isSubmitKey({ key: 'Enter', shiftKey: true }) === false);
  t(
    'allowShift lets a single-line control submit on Shift+Enter',
    isSubmitKey({ key: 'Enter', shiftKey: true }, { allowShift: true }) === true,
  );
  t(
    'allowShift still refuses a composing Enter',
    isSubmitKey({ key: 'Enter', isComposing: true }, { allowShift: true }) === false,
  );
}

// 4. The soft-keyboard rule reads pointer precision, and is SSR-safe.
if (prefersSoftKeyboard) {
  t('with no window (SSR) the desktop rule is reported', prefersSoftKeyboard() === false);
}
const softSrc = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
t(
  'the soft-keyboard test keys on POINTER precision, not a width or a UA string',
  /\(pointer:\s*coarse\)/.test(softSrc) &&
    !/innerWidth|userAgent|iPhone|Android/i.test(softSrc),
);

// ── 5. The census ─────────────────────────────────────────────────────────
// Every handler that ACTS on Enter must go through the rule. Comments are
// stripped first so an absence assertion cannot match its own prose (the
// recorded `feedback_gate_assertion_matches_its_own_comment`).
function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === 'node_modules' || name === '.next' || name.startsWith('.')) continue;
    const full = `${dir}/${name}`;
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.tsx?$/.test(name)) out.push(full);
  }
  return out;
}

const offenders = [];
for (const full of walk(`${ROOT}/web/components`).concat(walk(`${ROOT}/web/app`))) {
  const rel = full.slice(ROOT.length + 1);
  const src = readFileSync(full, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
  // `projection.ts` runs inside the artifact IFRAME, which has its own event
  // world and no access to app modules — excluded by path, narrow enough to
  // name.
  if (rel.endsWith('viewers/projection.ts')) continue;
  if (!/\bkey === ['"]Enter['"]/.test(src)) continue;
  // ACTIVATION is not submission. `Enter || ' '` is the ARIA keyboard-
  // activation idiom for an element playing a button: there is no text field,
  // so no composition can be open, and the space bar in the same test is what
  // identifies it. A button that fired on a composing Enter would be a real
  // defect — but a composition cannot be in flight on a focused button.
  const withoutActivation = src.replace(
    /\bkey === ['"]Enter['"]\s*\|\|\s*e?\.?key === ['"] ['"]/g,
    '',
  );
  // The remaining legal spelling: reading WHICH key was pressed after the rule
  // has already decided it was a submit (`step = e.key === 'Enter' ? …`).
  const withoutDiscriminator = withoutActivation.replace(
    /\bkey === ['"]Enter['"]\s*\?/g,
    '',
  );
  if (/\bkey === ['"]Enter['"]/.test(withoutDiscriminator)) offenders.push(rel);
}
t(
  'no handler acts on a bare `key === \'Enter\'` — every one goes through the rule',
  offenders.length === 0,
  offenders.join(', '),
);

// The rule has ONE home. A second copy of the IME guard is the drift that
// ADR-483's "kept in lockstep" comment was already documenting.
const strays = [];
for (const full of walk(`${ROOT}/web/components`)) {
  const rel = full.slice(ROOT.length + 1);
  const src = readFileSync(full, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
  if (/isComposing/.test(src)) strays.push(rel);
}
t(
  'the IME guard has ONE home — no component re-spells isComposing',
  strays.length === 0,
  strays.join(', '),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
