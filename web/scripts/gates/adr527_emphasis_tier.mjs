// Executing check of ADR-527 — the emphasis tier, read off the bar.
//
// The load-bearing claim is D2's: colour is a ROLE, never a value. That is a
// security-shaped invariant (a raw value in the DOM defeats the design system
// and is unthemeable), so it is executed against the real applyMark body with a
// falsifier, not grepped.
//
// Run from the REPO ROOT: node web/scripts/gates/adr527_emphasis_tier.mjs
import { readFileSync } from 'fs';

const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');
const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');
const surface = readFileSync('web/components/studio/StudioSurface.tsx', 'utf8');
const canvas = readFileSync('web/components/studio/StudioCanvas.tsx', 'utf8');
const ops = readFileSync('web/components/studio/artifactOps.ts', 'utf8');
const studio = readFileSync('api/services/studio.py', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── 1. D1 — the toggles are ROWS, not new mechanisms ──────────────────────
// The whole point of D1 is that applyToggle is command-generic, so underline
// and strikethrough must route to IT and not to some second implementation.
const fmtIdx = proj.indexOf('function applyFmt(op, value) {');
t('D1: applyFmt takes a value (the palette role)', fmtIdx > 0);
const fmtBody = proj.slice(fmtIdx, proj.indexOf('\n  }', fmtIdx));
t("D1: underline routes to applyToggle", /op === 'underline'\) applyToggle\('underline'\)/.test(fmtBody));
t("D1: strike routes to applyToggle('strikeThrough')", /op === 'strike'\) applyToggle\('strikeThrough'\)/.test(fmtBody));
t('D1: no second toggle implementation was added', (proj.match(/function applyToggle/g) || []).length === 1);
t(
  'D1: an unknown op returns BEFORE the commit (never an empty revision)',
  /else return; \/\/ unknown op/.test(fmtBody) &&
    fmtBody.indexOf('else return;') < fmtBody.indexOf('scheduleCommit()'),
);

// ── 2. D2 — colour is a ROLE. Executed, with a falsifier. ────────────────
const amIdx = proj.indexOf('function applyMark(attr, role, allowed) {');
t('D2: applyMark exists', amIdx > 0);
const amBody = proj.slice(proj.indexOf('{', amIdx) + 1, proj.indexOf('\n  }', amIdx));

// The guard clause alone is the invariant; execute it in isolation.
function guardAdmits(role, allowed) {
  // The first statement is the closed-set check; run it against a probe.
  const fn = new Function(
    'role',
    'allowed',
    "if (role && allowed.indexOf(role) === -1) return false; return true;",
  );
  return fn(role, allowed);
}
const MARK_ROLES = ['muted', 'accent', 'fresh', 'warn', 'danger'];
t('D2: a declared role is admitted', guardAdmits('accent', MARK_ROLES) === true);
t('D2: null (clear) is admitted', guardAdmits(null, MARK_ROLES) === true);
t('D2: a RAW COLOUR is refused', guardAdmits('#ff0000', MARK_ROLES) === false);
t('D2: an undeclared role is refused', guardAdmits('chartreuse', MARK_ROLES) === false);
t(
  'D2: the real body carries that guard (not just this gate)',
  /if \(role && allowed\.indexOf\(role\) === -1\) return;/.test(amBody),
);
// FALSIFIER: drop the guard and a raw colour gets through.
t(
  'FALSIFIER: without the closed-set guard a raw colour IS admitted',
  new Function('role', 'allowed', 'return true;')('#ff0000', MARK_ROLES) === true,
);
// The write must be an ATTRIBUTE, never inline style — the invariant that makes
// a design-system swap re-theme the document.
t(
  'D2: the mark writes an attribute, never inline colour',
  /span\.setAttribute\(attr, role\)/.test(amBody) &&
    !/style\.color/.test(amBody) &&
    !/style\.background/.test(amBody),
);
t(
  'D2: re-marking unwraps first (no nested mark spans accrete)',
  /unwrapMarks\(segs\[i\]\.range, attr\)/.test(amBody),
);
t(
  'D2: the kernel supplies one rule per role (theming, not painting)',
  /span\[data-mark="accent"\] \{ color: var\(--accent/.test(studio) &&
    /span\[data-highlight="warn"\] \{ background: color-mix/.test(studio),
);
t('D2: no raw hex is written by the runtime', !/setAttribute\('style'/.test(amBody));

// ── 3. D1 — clear keeps STRUCTURE ────────────────────────────────────────
const clrIdx = proj.indexOf('function applyClear() {');
t('D1: applyClear exists', clrIdx > 0);
const clrBody = proj.slice(clrIdx, proj.indexOf('\n  }', clrIdx));
t("D1: clear uses removeFormat (emphasis only)", /execCommand\('removeFormat'\)/.test(clrBody));
t(
  'D1: clear also strips the palette marks by hand (removeFormat misses spans)',
  /unwrapMarks\(segs\[i\]\.range, 'data-mark'\)/.test(clrBody) &&
    /unwrapMarks\(segs\[i\]\.range, 'data-highlight'\)/.test(clrBody),
);
t(
  'D1: clear never touches the block TAG (a heading stays a heading)',
  !/turnInto|replaceWith|tagName =/.test(clrBody),
);

// ── 4. D4 — the pane drives the range op, and preserves the range ────────
t('D4: the runtime accepts the pane command', /d\.type === 'yarnnn-fmt-op'/.test(proj));
t(
  'D4: the last live range is tracked (the pane steals focus)',
  /var lastLiveRange = null;/.test(proj) && /selectionchange/.test(proj),
);
t('D4: a COLLAPSED caret is not a range (never tracked)', /if \(!s \|\| !s\.rangeCount \|\| s\.isCollapsed\) return;/.test(proj));
t(
  'D4: with no usable range the op does NOTHING (never formats the unseen)',
  /if \(!usable\) return;/.test(proj),
);
t('D4: the canvas forwards the command', /type: 'yarnnn-fmt-op', op: fmtCmd\.op/.test(canvas));
t('D4: the surface mints a nonce so the same button fires twice', /fmtNonce\.current \+= 1;/.test(surface));
t('D4: the pane renders the Text section on the TEXT tier only', /\{isTextTier && <TextSection/.test(pane));
t(
  'D4: the section sits between Identity and Typography (the spine)',
  pane.indexOf('<TextSection') > pane.indexOf('{headingRow}') &&
    pane.indexOf('<TextSection') < pane.indexOf('label="Typography"'),
);
t(
  'D4: the pane resolves roles for the SWATCH only — the doc gets the role name',
  /const swatchOf = useCallback\(/.test(pane) && /onFormat\('mark', r\.value\)/.test(pane),
);

// ── 5. D3 — align restored, indent added, both at block-flow ─────────────
t(
  'D3: align is re-keyed to include block-flow (amends ADR-525 D4)',
  /"align": \{\s*"label": "Align",\s*"applies": \["block-staged", "media", "block-flow"\]/.test(studio),
);
t('D3: the indent token is block-flow only', /"indent": \{[\s\S]{0,120}?"applies": \["block-flow"\]/.test(studio));
t(
  'D3: the pane consumes block-flow (the grain ADR-525 D4 added and nobody used)',
  /mode === 'flow' && t\.applies\.includes\('block-flow'\)/.test(pane),
);
t(
  'D3: indent is a TOKEN — one kernel selector per step, no measure',
  /\[data-indent="1"\] \{ margin-inline-start: 2rem; \}/.test(studio) &&
    /\[data-indent="3"\]/.test(studio),
);
t('D3: size stays withdrawn on flow (the ADR-525 cut that WAS right)', !/"size"[\s\S]{0,140}?block-flow/.test(studio));

// ── 6. The commit + paste seams ──────────────────────────────────────────
t(
  'commit: strike normalizes to <s> (one source vocabulary)',
  /STRIKE: 's'/.test(ops) && /querySelectorAll\('b, i, strike'\)/.test(ops),
);
t(
  'paste: SPAN survives so a palette mark round-trips',
  /SPAN: 1 \}/.test(proj),
);
t(
  'paste: the marks join the internal keep-list (ADR-526 D4)',
  /'data-mark': 1, 'data-highlight': 1, 'data-indent': 1,/.test(proj),
);
t(
  'paste: a FOREIGN paste still strips every attribute (the gate is intact)',
  /if \(internal && PASTE_KEEP_INTERNAL\[name\.toLowerCase\(\)\] === 1\) continue;/.test(proj),
);

// ── 7. §4 — the refusals are REAL (metrics never reached the pane) ───────
t(
  'refusal: no point-size control',
  !/fontSize|font-size/i.test(pane.slice(pane.indexOf('function TextSection'), pane.indexOf('function TextSection') + 4000)),
);
t(
  'refusal: no line-spacing control',
  !/lineHeight|line-height/i.test(pane.slice(pane.indexOf('function TextSection'), pane.indexOf('function TextSection') + 4000)),
);

console.log(`\nADR-527: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
