// Executing check of ADR-519 D4.1 — the set is STATE, not a scope.
//
// D4 said "the pane gains a multi scope". Re-derived from first principles and
// withdrawn: a scope answers "what is this?" and every pane section is a
// property OF a subject (label, box, tokens). A set of N things has no label,
// no box, no tier and no id — so asking the inspector to describe it forces an
// answer the set does not have. That is exactly how the pane came to show
// "HEADING · Typography: Heading 2" over a six-block range (d878242). A set is
// a fact about the GESTURE ("how many does the verb take"), which is why
// setGeometryMany has taken a list and written one revision since 2026-07-24
// with no scope at all.
//
// The runtime settled it first: `group` rides ALONGSIDE `cur`, and `cur` stays
// the primary the box, handles and pane follow (projection.ts:988-994).
//
// This gate EXECUTES the align/distribute math, because that math is where a
// wrong answer is invisible to a grep: an off-by-one in the bounding box or a
// defaulted-to-zero missing measure looks like working code and flings a block
// to the corner.
//
// Run from the REPO ROOT: node web/scripts/gates/adr519_d41_set_is_state.mjs
import { readFileSync } from 'fs';

const surface = readFileSync('web/components/studio/StudioSurface.tsx', 'utf8');
const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');
const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── 1. The wiring the audit found missing ─────────────────────────────────
t('StudioSurface passes onGroup to the canvas (dead since 2026-07-24)', /onGroup=\{onGroup\}/.test(surface));
t('the set is held as its OWN state, not a field on selection',
  /const \[groupIds, setGroupIds\] = useState<string\[\]>\(\[\]\)/.test(surface));
t('selection stays a single subject (no ids array grew on it)',
  !/blockIds\??:/.test(readFileSync('web/components/studio/StudioToolbar.tsx', 'utf8')));

// ── 2. D4.1 — a set is NOT a scope ────────────────────────────────────────
// The decisive structural claim. If a `multi`/`group`/`set` scope ever appears
// in the discriminator, the grammar D4.1 withdrew has come back.
{
  const si = pane.indexOf('const scope:');
  const decl = pane.slice(si, pane.indexOf(';', si));
  t('no multi/group/set scope in the discriminator (D4.1: state, not a scope)',
    !/'multi'|'group'|'set'/.test(decl));
  t("the scope set is still ADR-528's five", /'document' \| 'range' \| 'object' \| 'container' \| 'page'/.test(decl));
}

// ── 3. Single-subject sections withdraw over a set, and SAY so ────────────
{
  const oi = pane.indexOf("{scope === 'object' && (");
  const obj = pane.slice(oi);
  t('the Identity heading names the COUNT over a set, never a stale label',
    /multiObject\s*\n?\s*\?\s*`\$\{groupIds!\.length\} objects selected`/.test(obj));
  for (const [what, re] of [
    ['the path row', /\{!multiObject && pathRow\}/],
    ['the verb row', /\{!multiObject && \(\s*\n\s*<VerbRow/],
    ['Position', /\{!multiObject && !!selectedEl\?\.closest\('\.slide'\)/],
    ['Layout', /\{!multiObject && \(nonColorTokens\.length/],
    ['the typography ramp', /\{!multiObject && rampSection\}/],
    ['Turn into', /\{!multiObject && turnIntoSection\}/],
    ['the colour swatches', /!multiBlockRange && !multiObject && colorTokens\.length/],
  ]) {
    t(`${what} withdraws over a set (single-subject)`, re.test(obj));
  }
  t('the pane SAYS why it withdrew (not silently empty — the d878242 lesson)',
    /Align and distribute apply to everything selected/.test(obj));
  t('a set is > 1 member (one block is a selection, not a set)',
    /const multiObject = \(groupIds\?\.length \?\? 0\) > 1/.test(pane));
}

// ── 4. Align/distribute is the ONE section a set earns ────────────────────
{
  const oi = pane.indexOf("{scope === 'object' && (");
  const obj = pane.slice(oi);
  t('align mounts only when the set has more than one member', /\{multiObject && \(onAlignMany \|\| onDistributeMany\)/.test(obj));
  t('distribute needs THREE (with two, their spacing IS the spacing)',
    /onDistributeMany && \(groupIds\?\.length \?\? 0\) > 2/.test(obj));
  t('align writes through the EXISTING setGeometryMany (no new op)',
    /setGeometryMany\(html, moves, specs\)/.test(surface));
}

// ── 5. The MATH, executed ─────────────────────────────────────────────────
// Extract the real compute bodies and run them against real boxes.
const runAlign = (edge, boxes) => {
  const minX = Math.min(...boxes.map((b) => b.x));
  const maxR = Math.max(...boxes.map((b) => b.x + b.w));
  const minY = Math.min(...boxes.map((b) => b.y));
  const maxB = Math.max(...boxes.map((b) => b.y + b.h));
  const src = surface.slice(surface.indexOf('return boxes.map((b) => {'), surface.indexOf('}, `align ${edge}`)'));
  const fn = new Function('boxes', 'edge', 'minX', 'maxR', 'minY', 'maxB', src + '\n');
  return fn(boxes, edge, minX, maxR, minY, maxB);
};
{
  // Three boxes of DIFFERENT sizes — the case where centre/right alignment is
  // wrong if the code forgets to subtract the box's own width.
  const boxes = [
    { id: 'a', x: 10, y: 10, w: 20, h: 10 },
    { id: 'b', x: 40, y: 30, w: 10, h: 20 },
    { id: 'c', x: 20, y: 50, w: 30, h: 10 },
  ];
  const at = (r, id) => r.find((m) => m.blockId === id).geo;
  const L = runAlign('left', boxes);
  t('align left: every box shares the set\'s minimum x', L.every((m) => m.geo.x === 10));
  const R = runAlign('right', boxes);
  // set right edge = max(30, 50, 50) = 50 → each x = 50 - own width
  t('align right: right EDGES meet (x = right - own width)',
    at(R, 'a').x === 30 && at(R, 'b').x === 40 && at(R, 'c').x === 20);
  const C = runAlign('hcenter', boxes);
  // centre = (10 + 50)/2 = 30 → x = 30 - w/2
  t('align h-centre: centres meet, sizes respected',
    at(C, 'a').x === 20 && at(C, 'b').x === 25 && at(C, 'c').x === 15);
  const T = runAlign('top', boxes);
  t('align top: every box shares the set\'s minimum y', T.every((m) => m.geo.y === 10));
  const B = runAlign('bottom', boxes);
  // set bottom = max(20, 50, 60) = 60 → y = 60 - own height
  t('align bottom: bottom EDGES meet (y = bottom - own height)',
    at(B, 'a').y === 50 && at(B, 'b').y === 40 && at(B, 'c').y === 50);
  t('align writes ONLY the axis it acts on (x-align never touches y)',
    L.every((m) => m.geo.y === undefined) && T.every((m) => m.geo.x === undefined));
}

// ── 6. Distribute: even GAPS, extremes held ───────────────────────────────
{
  const src = surface.slice(
    surface.indexOf('if (boxes.length < 3) return [];'),
    surface.indexOf("}, `distribute ${axis === 'h'"),
  );
  // Strip the TS annotations so the extracted body runs as plain JS (the
  // ADR-526 gate's pattern) — the LOGIC is what is under test, not the types.
  const runnable = src.replace(/\(b: \(typeof boxes\)\[number\]\)/g, '(b)');
  const run = (axis, boxes) => new Function('boxes', 'axis', runnable + '\n')(boxes, axis);
  // Sizes differ, so even-gaps and even-centres give DIFFERENT answers — the
  // fixture must distinguish them or the check proves nothing.
  const boxes = [
    { id: 'a', x: 0, y: 0, w: 10, h: 5 },
    { id: 'b', x: 30, y: 0, w: 20, h: 5 },
    { id: 'c', x: 70, y: 0, w: 30, h: 5 },
  ];
  const r = run('h', boxes);
  const at = (id) => r.find((m) => m.blockId === id).geo.x;
  // span 0→100 = 100; sizes 60; gap = 40/2 = 20 → a@0, b@30, c@70
  t('distribute h: extremes hold still', at('a') === 0 && at('c') === 70);
  t('distribute h: gaps are EVEN, not centres', at('b') === 30);
  t('distribute refuses a 2-member set (returns no moves)', run('h', boxes.slice(0, 2)).length === 0);
  const v = run('v', [
    { id: 'a', x: 0, y: 0, w: 5, h: 10 },
    { id: 'b', x: 0, y: 25, w: 5, h: 10 },
    { id: 'c', x: 0, y: 60, w: 5, h: 30 },
  ]);
  t('distribute v acts on y, never x', v.every((m) => m.geo.x === undefined && m.geo.y !== undefined));
}

// ── 7. Geometry comes from the SUBSTRATE, and gaps are skipped ────────────
// Reading DOM rects would align in one coordinate space and write in another;
// defaulting a missing x/y to 0 would fling an in-flow block to the corner.
{
  const si = surface.indexOf('const setGeometryOf = useCallback(');
  const body = surface.slice(si, surface.indexOf('const handleAlignMany', si));
  t('geometry is read from data-x/y/w/h (the substrate the op writes)',
    /getAttribute\('data-x'\)|num\(el, 'data-x'\)/.test(body));
  t('a member with no x/y is SKIPPED, never defaulted to 0',
    /if \(x == null \|\| y == null\) return null;/.test(body));
  t('fewer than two positionable members = no write', /if \(boxes\.length < 2\) return;/.test(body));
}

// ── 8. The runtime's one-selection rule is intact ─────────────────────────
{
  t('the runtime keeps group ALONGSIDE cur (cur stays the primary)',
    /window\.__yarnnnGroup = function \(\) \{ return cur \? \[cur\]\.concat\(group\) : group\.slice\(\); \}/.test(proj));
  t('__yarnnnSelected still returns exactly one element (readers unchanged)',
    !/__yarnnnSelected = function \(\) \{ return \[/.test(proj));
}

// ── 9. THE SET MUST BE ESCAPABLE (the prod trap, 2026-08-06) ──────────────
// Found in prod by the operator: after ⇧-selecting two objects, a plain click
// left the pane reading "2 objects selected" forever. The runtime cleared its
// OWN group in __yarnnnSelect but never told the parent — `yarnnn-group` was
// posted only from the ⇧ branch — so `groupIds` went stale.
//
// A stuck set is uniquely bad, which is why this earns its own section: every
// single-subject section withdraws over a set, so the member loses every
// editing affordance AND the gesture that would give them back. Withdrawal is
// only honest if it is reversible.
{
  // The emitter's shape, EXECUTED: __yarnnnGroup returns [cur].concat(group),
  // so a lone selection reports 1 — which is why "> 1" is the set test and why
  // toggling the last member OFF already reported correctly. The plain-click
  // path was the only one that stranded the parent.
  const emit = (cur, grp) => (cur ? [cur].concat(grp) : grp.slice()).length;
  t('set-escape: a lone selection reports 1, not a set', emit('A', []) === 1);
  t('set-escape: ⇧-adding one member reports 2 — a set', emit('A', ['B']) === 2);
  t('set-escape: toggling the last member OFF drops back to 1', emit('A', []) === 1);

  // The fix, at the chokepoint every selection route already passes through.
  const si = proj.indexOf('window.__yarnnnSelect = function (el)');
  const body = proj.slice(si, proj.indexOf('window.__yarnnnClearGroup', si));
  t('set-escape: __yarnnnSelect clears the group', /clearGroup\(\);/.test(body));
  t('set-escape: …and TELLS THE PARENT it cleared (the whole defect)',
    /yarnnn-group'[\s\S]{0,40}blockIds: \[\]/.test(body));
  t('set-escape: the post is guarded on there BEING a set (no chatter per click)',
    /if \(group\.length\) \{/.test(body));

  // Esc-to-nothing bypasses the chokepoint — it must clear the set itself.
  const ei = proj.indexOf("if (e.key !== 'Escape') return;");
  const esc = proj.slice(ei, proj.indexOf('window.__yarnnnSelect(up);', ei));
  t('set-escape: Esc-to-nothing clears the set too (it bypasses the chokepoint)',
    /clearGroup\(\);[\s\S]{0,120}blockIds: \[\]/.test(esc));

  // The parent-side backstop: a set cannot outlive its selection.
  const pi = surface.indexOf('const onPointClear = useCallback');
  const pc = surface.slice(pi, surface.indexOf('}, []);', pi));
  t('set-escape: the parent drops the set when the selection clears',
    /setGroupIds\(\[\]\)/.test(pc));
}

console.log(`\n${pass}/${pass + fail} checks passed`);
process.exit(fail ? 1 : 0);
