#!/usr/bin/env node
/**
 * GATE — the pane layout contract (2026-08-12, widened 2026-08-21).
 *
 * Run from the REPO ROOT: `node web/scripts/gates/pane_layout.mjs`
 *
 * ## What this defends
 *
 * ONE housing contract for every multi-pane surface: one ladder, one toggle
 * rule, one width store. Before the widening the ladder was real but its home
 * was a module named for ONE app, so Chat grew a fourth threshold beside it and
 * every check stayed green — the pane-spine failure one rung out.
 *
 * The original defects, measured live on prod, that the ladder half defends:
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
  'PANE_SINGLE_PX',
  'PANE_THREE_COLUMN_PX',
  'PANE_FULL_LABELS_PX',
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
const SINGLE = num('PANE_SINGLE_PX');
const THREE = num('PANE_THREE_COLUMN_PX');
const FULL = num('PANE_FULL_LABELS_PX');

ok('the ladder is strictly ordered', SINGLE < THREE && THREE < FULL, `${SINGLE}/${THREE}/${FULL}`);
ok(
  'three columns are never attempted below their measured ~1008px minimum',
  THREE >= 1008,
  `PANE_THREE_COLUMN_PX=${THREE}; measured minimum was ~1008 ` +
    `(strip 225 + toolbar 274 + boundary 141 + side 368)`,
);

// ── 2. EXECUTE the derivation at every boundary ───────────────────────────
const mod = await import(
  pathToFileURL(`${ROOT}/web/lib/shell/pane-layout.ts`).href
).catch(async () => {
  // The module is TS; if this runtime can't import it directly, transpile the
  // two pure functions out rather than skipping the behavioural half of the
  // gate (a gate that silently degrades to structure-only is not a gate).
  // Extract the TWO PURE FUNCTIONS and evaluate them directly. Slicing the
  // whole module and subtracting TS syntax was brittle — it was tuned to one
  // file's exact shape and broke twice on ordinary edits (a multi-line import,
  // then a type alias). Naming what it needs cannot rot that way: if either
  // function is renamed or deleted, this throws loudly instead of degrading to
  // a structure-only pass.
  const src = read('web/lib/shell/pane-layout.ts');
  const grab = (name) => {
    const m = new RegExp(
      `export function ${name}\\([\\s\\S]*?\\n\\}`, 'm',
    ).exec(src);
    if (!m) throw new Error(`gate cannot find ${name} in pane-layout.ts`);
    return m[0]
      .replace(/export /, '')
      .replace(/: PaneRung \| null = null/g, ' = null')
      .replace(/: number \| null = null/g, ' = null')
      .replace(/: PaneRung|: number|: PaneLadder/g, '');
  };
  const fn = new Function(
    'PANE_SINGLE_PX',
    'PANE_THREE_COLUMN_PX',
    'PANE_FULL_LABELS_PX',
    `${grab('rungForWidth')}\n${grab('ladderFromRung')}\n` +
      'return { rungForWidth, ladderFromRung };',
  );
  return fn(SINGLE, THREE, FULL);
});

const { rungForWidth, ladderFromRung: widthFromRung } = mod;

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
// The band is the FIRST <div> after the workbench root (the element whose ref
// feeds the width hook); comments may sit between them, so match on that anchor
// rather than on a fixed window of intervening text.
const bandMatch = /ref=\{setWorkbenchNode\}[\s\S]*?<div className="([^"]*)">/.exec(surface);
ok(
  'the column band is a positioning ancestor for the side overlay',
  !!bandMatch && /\brelative\b/.test(bandMatch[1]),
  bandMatch
    ? `the band's classes are "${bandMatch[1]}" — the two-pane overlay is ` +
      '`absolute` and needs this row to be `relative`'
    : 'could not locate the column band (the div preceding the navigator mount)',
);

// ── 4c. The measurement actually ATTACHES ─────────────────────────────────
// The hook must hand back a CALLBACK ref. The first spelling took a RefObject
// and observed it in a `useEffect([ref])`; the surface returns its START state
// before the workbench, so the effect's single run saw a null node, bailed, and
// never retried — the rung sat at its roomy `full` default forever and the
// tablet layout was byte-identical to the original defect.
//
// This gate was 33/33 GREEN through all of that: every assertion above tests the
// DERIVATION, and the derivation was always correct. What was broken was whether
// anything ever CALLED it with a real width. That is the "computed and never
// mounted" shape, and it is why this assertion is about wiring, not arithmetic.
const hook = read('web/lib/shell/pane-layout.ts');
ok(
  'the width hook returns a callback ref (not a RefObject it observes in an effect)',
  /usePaneLadder\(\):\s*\[\(node: HTMLElement \| null\) => void/.test(hook),
  'a RefObject + useEffect never re-runs when the workbench mounts on a later render',
);
ok(
  'the hook takes no ref parameter',
  /export function usePaneLadder\(\)/.test(hook),
  'accepting a ref is the shape that failed to attach',
);
ok(
  'the surface feeds the callback into the workbench root',
  /ref=\{setWorkbenchNode\}/.test(surface),
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

// ── 7. THE HOUSING CONTRACT — one ladder, one toggle rule, one width ──────
// The half the old gate could not see. It read two files, both Studio's, so a
// second spelling of the ladder in Chat (600px, hand-rolled) stayed green for
// as long as it existed. These assert the CONTRACT across every consumer.

const paneLayout = read('web/lib/shell/pane-layout.ts');

// 7a. Every multi-pane surface reads the ONE ladder. Listed explicitly: a
// derived list would pass vacuously the day a surface stops importing it.
const LADDER_CONSUMERS = [
  'web/components/authoring/StudioSurface.tsx',
  'web/components/text/TextEditor.tsx',
  'web/components/chat-surface/ChatSurface.tsx',
  'web/components/desk/DeskHousing.tsx',
  'web/components/settings/SettingsPaneShell.tsx',
];
for (const f of LADDER_CONSUMERS) {
  const src = read(f);
  ok(`${f.split('/').pop()} reads the shared ladder`,
    /from ['"]@\/lib\/shell\/pane-layout['"]/.test(src));
}

// 7b. NO second threshold anywhere. The drift that made this module necessary
// was a surface declaring its own "how wide is wide" — Chat's 600. Comments are
// stripped first so an absence assertion cannot match its own prose (the
// recorded `feedback_gate_assertion_matches_its_own_comment`).
for (const f of LADDER_CONSUMERS) {
  const src = read(f)
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
  const own = [...src.matchAll(/const\s+\w*(?:MIN_PX|_PX|BREAKPOINT\w*)\s*=\s*\d+/g)].map((m) => m[0]);
  ok(`${f.split('/').pop()} declares no threshold of its own`, own.length === 0,
    own.join(', '));
}

// 7c. The width store is SINGULAR. Three key schemes existed; the two that
// belonged to surface panes are gone. The chat DRAWER keeps its own — it is
// shell chrome sized against the VIEWPORT with a postural default keyed on the
// foregrounded surface, not a slot inside a surface, and folding it in would be
// a false unity. Named here so its exemption is a decision, not an oversight.
const RETIRED_KEYS = ['studio.navWidth', 'yarnnn:pane-shell:nav-width:'];
for (const k of RETIRED_KEYS) {
  const hits = LADDER_CONSUMERS.filter((f) => read(f).includes(k));
  ok(`the retired key ${k} has no writer left`, hits.length === 0, hits.join(', '));
}
ok('the shared store forms its key through shellStateSuffix',
  paneLayout.includes('shellStateSuffix'),
  'pane state must scope per (workspace, user) like every other piece of shell state');

// 7d. NO hand-rolled drag survives in a surface. Every resize goes through the
// slot; a surface reaching for clientX again is the drift returning.
for (const f of LADDER_CONSUMERS) {
  const src = read(f)
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
  const drag = [...src.matchAll(/addEventListener\(['"]pointermove|\bclientX\b\s*-|-\s*\bclientX\b/g)];
  ok(`${f.split('/').pop()} rolls no drag of its own`, drag.length === 0,
    `${drag.length} hand-rolled drag site(s) — resize belongs to usePaneSlot`);
}

// 7e. THE CLAMP. Execute it: a persisted width from a big monitor must be cut
// down by the container, and the floor must survive a container too small to
// honour both. This is the rule that actually protects the canvas.
const clampSrc = /export function clampPaneWidth\([\s\S]*?\n\}/.exec(paneLayout);
ok('clampPaneWidth is exported', !!clampSrc);
// Read the BAND and the SHARE from the source, never from a copy in this file.
// The first cut passed 180/560/(1/3) as literals into the Function ctor, so it
// validated the gate's own arithmetic and stayed GREEN when PANE_MAX_SHARE was
// falsified to 1 — a gate that cannot see the constant it is about. Caught by
// falsification, which is the whole reason for running it.
const constNum = (k) => {
  const m = new RegExp(`export const ${k} = ([\\d./\\s]+);`).exec(paneLayout);
  if (!m) throw new Error(`gate cannot read ${k}`);
  // eslint-disable-next-line no-new-func
  return Number(new Function(`return (${m[1]});`)());
};
/** Read a `Record<PaneSlot, number>` constant out of the source. The ceilings
 *  are PER SLOT — a rail is an index and a side pane is a working surface, so
 *  one number was wrong for both — and this gate must read whatever shape the
 *  source actually declares, never a copy. */
const constRecord = (k) => {
  const m = new RegExp(`export const ${k}: Record<PaneSlot, number> = (\\{[^}]*\\});`).exec(paneLayout);
  if (!m) throw new Error(`gate cannot read ${k}`);
  // eslint-disable-next-line no-new-func
  return new Function(`return (${m[1]});`)();
};
const MIN = constNum('PANE_MIN_PX');
const MAXW = constRecord('PANE_MAX_PX');
const SHARE = constRecord('PANE_MAX_SHARE');

// The canvas is the SUBJECT: no slot may take more than half, and a rail —
// an index of names, not a working surface — is held to a third.
ok('a side pane may never take more than half its container', SHARE.side <= 1 / 2,
  `PANE_MAX_SHARE.side=${SHARE.side}; past half the canvas stops being the subject`);
ok('a rail may never take more than a third', SHARE.rail <= 1 / 3,
  `PANE_MAX_SHARE.rail=${SHARE.rail}; a rail is an index, not a working surface`);
ok('a side pane is allowed at least as much room as a rail',
  SHARE.side >= SHARE.rail && MAXW.side >= MAXW.rail);
for (const slot of ['rail', 'side']) {
  ok(`${slot}: the band is ordered and usable`, MIN >= 120 && MIN < MAXW[slot],
    `${MIN}/${MAXW[slot]}`);
}

const clamp = new Function(
  'PANE_MIN_PX', 'PANE_MAX_PX', 'PANE_MAX_SHARE',
  `${clampSrc[0].replace(/export /, '').replace(/: number \| null|: PaneSlot = 'rail'|: number/g, '')}
   return clampPaneWidth;`,
)(MIN, MAXW, SHARE);
for (const slot of ['rail', 'side']) {
  ok(`${slot}: a slot wider than its share is cut down to the container`,
    clamp(MAXW[slot], 800, slot) === Math.floor(800 * SHARE[slot]),
    `got ${clamp(MAXW[slot], 800, slot)}`);
  ok(`${slot}: the same width is honoured where it fits`,
    clamp(MAXW[slot], 4000, slot) === MAXW[slot], `got ${clamp(MAXW[slot], 4000, slot)}`);
  // The floor wins only where the share ceiling actually falls BELOW it — which
  // depends on the slot's own share, so the container has to be chosen per slot
  // rather than pinned at one width. (Pinned at 400px this asserted the wrong
  // thing for `side`: half of 400 is 200, which is above the floor, so 200 was
  // the correct answer and the gate was red against correct code.)
  const tooNarrow = Math.floor((MIN - 1) / SHARE[slot]);
  ok(`${slot}: the floor wins where the share ceiling falls below it`,
    clamp(MIN + 20, tooNarrow, slot) === MIN,
    `at ${tooNarrow}px the ${slot} share is ${Math.floor(tooNarrow * SHARE[slot])}, under the ${MIN} floor; got ${clamp(MIN + 20, tooNarrow, slot)}`);
  ok(`${slot}: an unmeasured container falls back to the band, never to Infinity`,
    clamp(9999, null, slot) === MAXW[slot], `got ${clamp(9999, null, slot)}`);
}
// The reported symptom: on a 1600px workbench the side pane stopped at 533px
// (the shared third) and the drag read as "hitting something". Asserted as the
// BEHAVIOUR the member sees, at a real width, so a future re-tightening of
// either half of the ceiling shows up here as the regression it would be.
ok('a 1600px workbench lets its side pane reach 800px',
  clamp(9999, 1600, 'side') === 800, `got ${clamp(9999, 1600, 'side')}`);

// 7f. A HIDDEN SLOT HAS A DOOR. The rule the old code broke in both directions:
// Studio/Text gated their door on `sideIsOverlay` (so the COLUMN rung — ordinary
// desktop — had none), and Chat had no door at all. An inescapable state is the
// ADR-519 lesson; assert every surface that can hide a slot can also show it.
const DOORS = [
  ['web/components/authoring/StudioSurface.tsx', 'side.toggle'],
  ['web/components/text/TextEditor.tsx', 'side.toggle'],
  ['web/components/chat-surface/ChatSurface.tsx', 'rail.toggle'],
];
//
// Counting call sites was the WRONG assertion, and this gate shipped RED against
// correct code for it before being falsified: Text has ONE button whose label
// flips (Hide / Show) — a two-way door in one element — while Chat needs two
// because its button lives INSIDE the rail it hides. The number of controls is
// not the property. The property is that at least one door renders under a
// guard that does NOT require the slot to be shown.
for (const [f, verb] of DOORS) {
  const src = read(f)
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
  const slot = verb.split('.')[0];
  const sites = [...src.matchAll(new RegExp(`onClick=\\{${slot}\\.toggle\\}`, 'g'))];
  ok(`${f.split('/').pop()} wires its slot door to the shared toggle`,
    sites.length > 0, `no onClick={${verb}} found`);
  // The door must survive the slot being hidden. `${slot}IsColumn` and
  // `${slot}.shown` both go false then, so a door guarded ONLY by those is
  // one-way. At least one site must sit outside such a guard.
  const guardedOnlyByShown = sites.every((m) => {
    const before = src.slice(Math.max(0, m.index - 400), m.index);
    const guard = before.slice(before.lastIndexOf('{'));
    return /IsColumn|\.shown/.test(guard) && !/!\s*\w+\.shown|!\s*\w+IsColumn/.test(guard);
  });
  ok(`${f.split('/').pop()}: a door is reachable while the slot is hidden`,
    !guardedOnlyByShown,
    'every door is gated on the slot being SHOWN — hiding it would be one-way');
}

// 7g. No door may be gated on the OVERLAY rung — the inversion itself. An
// overlay dismisses on scrim and Escape; the column is what needs the door.
for (const [f] of DOORS) {
  const src = read(f)
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '');
  ok(`${f.split('/').pop()} does not gate its door on sideIsOverlay`,
    !/\{sideIsOverlay && \(\s*<button/.test(src),
    'the overlay rung already dismisses itself; the COLUMN rung is the one that needs a door');
}

// ── 8. THE COMPOSER NAMES A SPEAKER, NEVER A SUBJECT ──────────────────────
// `laneName` is the lane's SUBJECT, and on every bound app that subject is a
// FILE — so the composer read "Message Learn: embed-application-2026-08-10.md…",
// addressing a document as if it could reply. `speakerLabel` (ADR-562 D5) is the
// prop that answers "who is working, for the member to read", and every caller
// already passes it. The fallback is GENERIC: a sentence true of every surface
// beats a name true of none.
const composer = read('web/components/chat-surface/LanePanel.tsx')
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/^\s*\/\/.*$/gm, '');
const placeholderBlock = /placeholder=\{([\s\S]*?)\n\s*\}/.exec(composer);
ok('the composer composes a placeholder', !!placeholderBlock);
ok('the composer never addresses the lane SUBJECT',
  !/\$\{laneName\}/.test(placeholderBlock[1]),
  'a lane is named for its subject — on a bound app that is a FILE, not a speaker');
ok('the composer names the SPEAKER',
  /\$\{speakerLabel\}/.test(placeholderBlock[1]),
  'speakerLabel resolves to the app resident, the colleague, or the engine');
ok('the composer falls back to a GENERIC prompt, not a guessed name',
  /Write a message/.test(placeholderBlock[1]),
  'with no speaker resolved, a generic sentence is true where a name would not be');

// ── report ────────────────────────────────────────────────────────────────
if (failures.length) {
  console.error(`\n✗ pane_layout — ${pass} passed, ${failures.length} FAILED\n`);
  for (const f of failures) console.error(`  ✗ ${f}`);
  process.exit(1);
}
console.log(`✓ pane_layout — ${pass}/${pass} green`);
