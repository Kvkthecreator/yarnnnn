#!/usr/bin/env node
/**
 * GATE — the authoring workbench's width ladder (2026-08-12).
 *
 * Run from the REPO ROOT: `node web/scripts/gates/authoring_width_ladder.mjs`
 *
 * ## What this defends
 *
 * Docs and Studio share one component (`StudioSurface`). It was the only major
 * surface doing responsive purely in raw Tailwind class strings, and two
 * defects followed, both measured live on prod:
 *
 *  1. The shell collapses to single-window at `MOBILE_BREAKPOINT_PX` (640); the
 *     workbench switched panes at `md` (768). Between them — and from 768 up to
 *     the layout's real ~1008px minimum — three columns were attempted with no
 *     room. At 820px the toolbar row's content needed 274px inside a 16px box
 *     and, being necessarily `overflow: visible` (its galleries are
 *     `absolute top-full`), painted 260px over the Properties column.
 *  2. The canvas absorbed the whole deficit (177px at 768) because it was the
 *     sole `flex-1` among `shrink-0` siblings.
 *
 * ## How it defends it
 *
 * By EXECUTING the derivation (`rungForWidth` / `widthFromRung`) at each
 * boundary rather than grepping for class names — the ADR-546 lesson: a gate
 * that pins a spelling goes red on a narrowing and green on a real regression.
 * The one structural assertion (no raw `md:` in the workbench) is a
 * DRIFT check with an explicit allowlist for the landing, which is an ordinary
 * scrolling page and not part of the ladder.
 *
 * Falsified before commit: each assertion was made to fail by inverting the
 * thing it claims, and restored.
 */

import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const ROOT = process.cwd();
const read = (p) => readFileSync(`${ROOT}/${p}`, 'utf8');

let pass = 0;
const failures = [];
const ok = (name, cond, detail = '') => {
  if (cond) {
    pass++;
  } else {
    failures.push(`${name}${detail ? ` — ${detail}` : ''}`);
  }
};

// ── 1. The thresholds have ONE declared home ──────────────────────────────
const prefs = read('web/lib/shell/surface-preferences.ts');
for (const k of [
  'WORKBENCH_SINGLE_PANE_PX',
  'WORKBENCH_THREE_COLUMN_PX',
  'WORKBENCH_FULL_LABELS_PX',
]) {
  ok(`threshold ${k} declared in surface-preferences`, prefs.includes(`export const ${k}`));
}
ok(
  'the shell breakpoint still lives beside them',
  prefs.includes('export const MOBILE_BREAKPOINT_PX'),
);

// Read the declared values so the ladder is checked against the SOURCE numbers,
// never against a copy that could drift out from under this gate.
const num = (k) => {
  const m = new RegExp(`export const ${k} = (\\d+)`).exec(prefs);
  if (!m) throw new Error(`gate cannot read ${k}`);
  return Number(m[1]);
};
const SINGLE = num('WORKBENCH_SINGLE_PANE_PX');
const THREE = num('WORKBENCH_THREE_COLUMN_PX');
const FULL = num('WORKBENCH_FULL_LABELS_PX');

ok('the ladder is strictly ordered', SINGLE < THREE && THREE < FULL, `${SINGLE}/${THREE}/${FULL}`);
ok(
  'three columns are never attempted below their measured ~1008px minimum',
  THREE >= 1008,
  `WORKBENCH_THREE_COLUMN_PX=${THREE}; measured minimum was ~1008 ` +
    `(strip 225 + toolbar 274 + boundary 141 + side 368)`,
);

// ── 2. EXECUTE the derivation at every boundary ───────────────────────────
const mod = await import(
  pathToFileURL(`${ROOT}/web/lib/authoring/workbench-width.ts`).href
).catch(async () => {
  // The module is TS; if this runtime can't import it directly, transpile the
  // two pure functions out rather than skipping the behavioural half of the
  // gate (a gate that silently degrades to structure-only is not a gate).
  const src = read('web/lib/authoring/workbench-width.ts');
  const body = src
    .replace(/^[\s\S]*?export type WorkbenchRung[^\n]*\n/, '')
    .replace(/export interface WorkbenchWidth \{[\s\S]*?\n\}/, '')
    .replace(/import[^\n]*\n/g, '')
    .replace(/^'use client';/m, '')
    .replace(/export function useWorkbenchWidth[\s\S]*$/, '')
    .replace(/: number \| null = null/g, ' = null')
    .replace(/: WorkbenchRung|: number|: WorkbenchWidth/g, '')
    .replace(/export /g, '');
  const fn = new Function(
    'WORKBENCH_SINGLE_PANE_PX',
    'WORKBENCH_THREE_COLUMN_PX',
    'WORKBENCH_FULL_LABELS_PX',
    `${body}; return { rungForWidth, widthFromRung };`,
  );
  return fn(SINGLE, THREE, FULL);
});

const { rungForWidth, widthFromRung } = mod;

// The boundary table. Each row is a WIDTH and the rung it must produce —
// asserted as behaviour, not as a class string.
const cases = [
  [320, 'single-pane'],
  [SINGLE - 1, 'single-pane'],
  [SINGLE, 'two-pane'],
  [820, 'two-pane'], // the measured defect width — iPad portrait
  [THREE - 1, 'two-pane'],
  [THREE, 'condensed'],
  [FULL - 1, 'condensed'],
  [FULL, 'full'],
  [1920, 'full'],
];
for (const [w, expected] of cases) {
  ok(`rung at ${w}px is ${expected}`, rungForWidth(w) === expected, `got ${rungForWidth(w)}`);
}

// ── 3. The ladder's INVARIANTS, at every rung ─────────────────────────────
// These are the rules the layout actually branches on. Deriving them once and
// asserting them here is what stops five call sites re-deriving "does this rung
// mean three columns" and disagreeing (the ADR-539 D1 drift).
for (const rung of ['full', 'condensed', 'two-pane', 'single-pane']) {
  const f = widthFromRung(rung);
  ok(`${rung}: exactly one layout posture is live`,
    [f.threeColumn, f.sideIsOverlay, f.singlePane].filter(Boolean).length === 1);
}
ok('full labels ONLY at the widest rung', widthFromRung('full').fullLabels === true);
for (const rung of ['condensed', 'two-pane', 'single-pane']) {
  ok(`${rung}: verbs are compact`, widthFromRung(rung).fullLabels === false);
}
ok('the side pane is an overlay ONLY at the two-pane rung',
  widthFromRung('two-pane').sideIsOverlay === true &&
    ['full', 'condensed', 'single-pane'].every((r) => !widthFromRung(r).sideIsOverlay));

// ── 4. THE CANVAS NEVER YIELDS ────────────────────────────────────────────
// The ordering principle. At every rung above single-pane the canvas column is
// present; it is the last thing to lose width. Asserted against the surface's
// own branch, which must not gate the canvas on anything but singlePane.
const surface = read('web/components/authoring/StudioSurface.tsx');
ok(
  'the canvas column is gated only by the single-pane rung',
  /!singlePane \|\| canvasActive \? 'flex' : 'hidden'/.test(surface),
  'the canvas must render at every rung above single-pane',
);

// ── 4b. The overlay has a positioning ancestor ────────────────────────────
// The two-pane rung's side pane is `absolute inset-y-0 right-0`, so the column
// band it sits in MUST be `relative` — otherwise it resolves against a distant
// ancestor and lands somewhere arbitrary. This shipped wrong once (the band was
// a bare `flex min-h-0 flex-1`) and is invisible to every other check: it type-
// checks, it builds, and it only misbehaves at one rung.
// Anchored to the BAND, not to any div that happens to share the class string:
// `canvasWrapRef` carries the identical classes one level in, so a bare match on
// them stayed green with the band broken (caught by falsifying this assertion).
// The band is the `relative` div that directly precedes the navigator's
// `isPaged &&` mount, and it carries no ref.
// The band is the FIRST <div> after the workbench root (the element carrying
// `ref={workbenchRef}`); comments may sit between them, so match on that anchor
// rather than on a fixed window of intervening text.
const bandMatch = /ref=\{workbenchRef\}[\s\S]*?<div className="([^"]*)">/.exec(surface);
ok(
  'the column band is a positioning ancestor for the side overlay',
  !!bandMatch && /\brelative\b/.test(bandMatch[1]),
  bandMatch
    ? `the band's classes are "${bandMatch[1]}" — the two-pane overlay is ` +
      '`absolute` and needs this row to be `relative`'
    : 'could not locate the column band (the div preceding the navigator mount)',
);

// ── 5. No raw breakpoint classes in the WORKBENCH ─────────────────────────
// The drift check. The landing (StudioStart) is an ordinary scrolling page and
// legitimately uses `sm:`/`lg:` grid columns, so the scan is scoped to the
// workbench half of the file — everything before the start-state component.
const workbenchOnly = surface.slice(0, surface.indexOf('// ── The start state'));
// Strip comments first: an absence assertion must not match its own
// explanatory prose (the recorded `feedback_gate_assertion_matches_its_own_comment`).
const stripped = workbenchOnly
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/^\s*\/\/.*$/gm, '');
const rawBp = [...stripped.matchAll(/\b(?:max-)?(?:sm|md|lg|xl|2xl):[a-z]/g)].map((m) => m[0]);
ok(
  'the workbench carries no raw breakpoint classes',
  rawBp.length === 0,
  rawBp.length ? `found ${rawBp.length}: ${[...new Set(rawBp)].join(', ')}` : '',
);

// The toolbar + boundary cluster must take the rung as a PROP, never re-derive.
for (const f of [
  'web/components/authoring/StudioToolbar.tsx',
  'web/components/authoring/StudioShareExport.tsx',
]) {
  const src = read(f).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
  const name = f.split('/').pop();
  ok(`${name} accepts compact as a prop`, /compact\??:\s*boolean/.test(src));
  ok(`${name} re-derives no breakpoint of its own`,
    ![...src.matchAll(/\b(?:max-)?(?:sm|md|lg|xl|2xl):[a-z]/g)].length);
}

// ── 6. Touch parity ───────────────────────────────────────────────────────
ok(
  'the surface consults the pointer CAPABILITY, not a width',
  surface.includes('useCoarsePointer'),
);
ok(
  'the single-pane tab bar meets the 44px touch floor',
  /min-h-\[44px\][^\n]*flex-1/.test(surface),
  'the bottom tab bar is the primary navigation on a phone',
);

// ── report ────────────────────────────────────────────────────────────────
if (failures.length) {
  console.error(`\n✗ authoring_width_ladder — ${pass} passed, ${failures.length} FAILED\n`);
  for (const f of failures) console.error(`  ✗ ${f}`);
  process.exit(1);
}
console.log(`✓ authoring_width_ladder — ${pass}/${pass} green`);
