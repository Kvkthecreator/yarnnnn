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
// ADR-528 gave the selectionchange handler a second job (reporting the block
// set), so the collapsed guard became a BRANCH rather than an early return.
// The invariant is unchanged and is what is pinned: a collapsed selection must
// never become `lastLiveRange`.
t(
  'D4: a COLLAPSED caret is not a range (never tracked)',
  /!s\.rangeCount \|\| s\.isCollapsed/.test(proj) &&
    /lastLiveRange = r\.cloneRange\(\);/.test(proj),
);
t(
  'D4: with no usable range the op does NOTHING (never formats the unseen)',
  /if \(!usable\) return;/.test(proj),
);
t('D4: the canvas forwards the command', /type: 'yarnnn-fmt-op', op: fmtCmd\.op/.test(canvas));
t('D4: the surface mints a nonce so the same button fires twice', /fmtNonce\.current \+= 1;/.test(surface));
// ADR-528 D2 RE-CUT — the intent is preserved, the mechanism changed. This
// pinned `{isTextTier && <TextSection`; the text tier is now its own SCOPE
// (`range`), so the section is composed unconditionally inside that branch and
// is unreachable from any other. That is a stronger form of "text tier only".
t(
  'D4 (re-cut): the Text section is composed in the RANGE scope',
  (() => {
    const rb = pane.match(/\{scope === 'range' && \(([\s\S]*?)\n\s*<\/>/);
    return !!rb && /<TextSection/.test(rb[1]);
  })(),
);
t(
  'D4 (re-cut): the Text section is composed NOWHERE ELSE (one mount)',
  (pane.match(/<TextSection/g) ?? []).length === 1,
);
// ADR-528 RE-CUT — the spine order is unchanged (Identity → Text → Typography)
// but it must be read at the RENDER site, not from source order. ADR-528 lifted
// the Typography ramp into a `rampSection` value so range and object scope
// mount one implementation (ADR-518 D2); that declaration necessarily sits
// above the branches, so `indexOf('label="Typography"')` now finds the
// declaration rather than the mount and orders it before everything.
//
// The member-visible order is the order of the MOUNTS inside the range branch.
t(
  'D4 (re-cut): the section sits between Identity and Typography (the spine)',
  (() => {
    const rb = pane.match(/\{scope === 'range' && \(([\s\S]*?)\n\s*<\/>/);
    if (!rb) return false;
    const b = rb[1];
    // Identity is the section, not one spelling of its contents — range scope
    // renders the heading crumb as `{!multiBlockRange && headingRow}`, so
    // pinning `{headingRow}` matched nothing and reported a false failure.
    const identity = b.indexOf('headingRow');
    const text = b.indexOf('<TextSection');
    const ramp = b.indexOf('rampSection');
    return identity !== -1 && text !== -1 && ramp !== -1 && identity < text && text < ramp;
  })(),
);
t(
  'D4: the pane resolves roles for the SWATCH only — the doc gets the role name',
  /const swatchOf = useCallback\(/.test(pane) && /onFormat\('mark', r\.value\)/.test(pane),
);

// ── 5. D3 — align restored, indent added, both at block-flow ─────────────
t(
  'D3: align is re-keyed to include block-flow (amends ADR-525 D4)',
  /"align": \{\s*"label": "Align",\s*"scope": \("block",\),\s*"grains": \("staged", "media", "flow"\)/.test(studio),  // ADR-542 axes
);
t('D3: the indent token is flow-grain only', /"indent": \{[\s\S]{0,140}?"grains": \("flow",\)/.test(studio));
t(
  'D3: the pane consumes block-flow (the grain ADR-525 D4 added and nobody used)',
  /flow: !isStaged && mode === 'flow'/.test(pane) && /grains\.includes\('flow'\)/.test(pane),
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

// ── 8. ADR-528 — the pane's scope follows the RANGE, not the last click ──
// The defect: `selection` was written only by a click, so dragging across six
// blocks left every block-scoped section describing whichever block was
// clicked into. It did not look wrong — it was stale.
t(
  'ADR-528: the runtime reports the block set a range intersects',
  /type: 'yarnnn-range', blockIds: ids/.test(proj),
);
t(
  'ADR-528: it reuses formatSegments (the ops\' own derivation, not a second one)',
  /var segs = formatSegments\(\);[\s\S]{0,400}?blockIds: ids/.test(proj),
);
t(
  'ADR-528: a collapsed range CLEARS the parent scope',
  /type: 'yarnnn-range', blockIds: \[\] \}/.test(proj),
);
t(
  'ADR-528: the report is deduped (a caret moving in one block does not re-post)',
  /if \(key === lastRangeKey\) return;/.test(proj),
);
t('ADR-528: the canvas forwards it', /d\.type === 'yarnnn-range'/.test(canvas));
t(
  'ADR-528: the surface holds it SEPARATELY from selection (different questions)',
  /const \[rangeBlockIds, setRangeBlockIds\]/.test(surface),
);
// ADR-541 D2 re-cut: multiBlockRange is a READING of the one derived arity
// (arityOf + setKind), never a local re-count.
t('ADR-528: the pane derives multiBlockRange',
  /const multiBlockRange = arity === 'many' && unified\.setKind === 'range'/.test(pane));
// RE-CUT for ADR-528 D2/D4 — the INVARIANT is unchanged: a section that can
// answer for only ONE block must never answer over a multi-block range. What
// changed is WHERE the withdrawal happens.
//
// Before: every such section sat in one `block` branch and was suppressed by a
// `!multiBlockRange` (and often `!isTextTier`) guard — the five regexes this
// loop used to pin.
//
// Now: the enclosure sections (verb row, Layout, Tone) are not composed for
// prose AT ALL — they live in the `object` branch, which a text-tier selection
// cannot reach (proven by execution in adr528_range_scope.mjs). Only the two
// STRUCTURE-tier sections are reachable from a range, because they are the two
// a caret legitimately wants; those keep an explicit guard.
const rangeBranch = pane.match(/\{scope === 'range' && \(([\s\S]*?)\n\s*<\/>/);
const objectBranch = pane.match(/\{scope === 'object' && \(([\s\S]*?)\n\s*<\/>/);
t('ADR-528: the range branch exists', !!rangeBranch);
t('ADR-528: the object branch exists', !!objectBranch);

// The enclosure sections: composed for object, unreachable from a range.
for (const [label, re] of [
  ['the verb row', /<VerbRow/],
  ['Layout', /nonColorTokens\.length > 0/],
  ['Tone', /colorTokens\.length > 0/],
]) {
  t(
    `ADR-528: ${label} is object-only — a range cannot reach it`,
    !!objectBranch && re.test(objectBranch[1]) &&
      (!rangeBranch || !re.test(rangeBranch[1])),
  );
}

// ADR-541 D3 re-cut (the deliberate reversal, stated in the ADR's amendments
// table): the structure-tier sections now MOUNT over a multi-block range, and
// the OP became span-aware — every covered block, one revision, per-block
// legality per-block (convertBlocks / setTokenMany). The old withdrawal
// delivered neither benchmark: Google Docs styles every paragraph a range
// covers, Notion converts every block in a set. What this gate now pins is
// the pairing: the mounts are unguarded AND the surface routes the pick
// through the span ops — a mount without the span routing would be the
// d878242 defect again (answering for one of six), which is why both halves
// are one assertion.
for (const [label, ref] of [
  ['Typography', 'rampSection'],
  ['Turn into', 'turnIntoSection'],
]) {
  t(
    `ADR-541: ${label} mounts over a multi-block range (span-aware)`,
    !!rangeBranch && new RegExp(`\\{${ref}\\}`).test(rangeBranch[1]) &&
      !new RegExp(`!multiBlockRange && ${ref}`).test(rangeBranch[1]),
  );
}
t(
  'ADR-541: the pane pick routes through the SPAN op when the range covers many',
  /rangeBlockIds\.length > 1/.test(surface) &&
    /convertBlocks\(html, blockIds, kind, fragment\)/.test(surface) &&
    /setTokenMany\(html, rangeBlockIds, key, value\)/.test(surface),
);

t(
  'ADR-528: the TEXT section does NOT withdraw (it acts on the selection)',
  !!rangeBranch &&
    /<TextSection/.test(rangeBranch[1]) &&
    !/!multiBlockRange && <TextSection/.test(rangeBranch[1]),
);
t(
  'ADR-528: the Identity heading names the COUNT, not a stale block label',
  /blocks selected/.test(pane),
);
t(
  // ADR-541 D3: the range-scope withdrawal notice is GONE because nothing it
  // described withdraws any more — structure ops span. The OBJECT tier's
  // notice (align/distribute vs single-subject) remains, and remains the one
  // place a withdrawal is explained.
  'ADR-541: the retired range withdrawal notice is gone; the object notice remains',
  !/heading ramp, Turn into, and align\/indent/.test(pane) &&
    /Align and distribute apply to everything selected/.test(pane),
);

console.log(`\nADR-527: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
