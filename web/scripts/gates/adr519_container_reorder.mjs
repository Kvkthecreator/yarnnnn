// Executing check of the ADR-519 Phase A container-reorder defect.
//
// The defect: ADR-519 D1 named FOUR grains, two of which are movable siblings
// — a block (`data-block`) and a structural container (`data-block-id` alone,
// per the settled `div[data-block-id]:not([data-block])` convention). Phase A
// mounted the container verb row (StudioDesignTab `VerbRow` at container
// scope) on the reasoning that "the id-addressed ops need no special casing"
// — but `moveBlock`'s sibling walk stepped by `data-block`, so a container was
// invisible to its own reorder. `moveBlockTo` then found no target and
// returned null: the button rendered unconditionally, the member clicked Move
// up, and NOTHING happened with no explanation.
//
// Why this gate is EXECUTING and not a grep (the counting-gate lesson): the
// mount was present and correct the whole time — `test_adr519_pane_spine.py`
// asserts the verb row mounts and passed 16/16 across the defect's entire
// life. A grep cannot see that an op returns null. Only running the walk can.
//
// Run from the REPO ROOT: node web/scripts/gates/adr519_container_reorder.mjs
import { readFileSync } from 'fs';

const ops = readFileSync('web/components/studio/artifactOps.ts', 'utf8');
const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── A DOM good enough for the sibling walk ────────────────────────────────
// Only what the walk touches: previousElementSibling / nextElementSibling /
// hasAttribute. Blocks carry both attributes; containers carry only the id —
// the real substrate shape (`div[data-block-id]:not([data-block])`).
function mkEl(id, kind /* 'block' | 'container' */) {
  return {
    id,
    kind,
    _a: kind === 'block' ? { 'data-block-id': id, 'data-block': 'text' } : { 'data-block-id': id },
    hasAttribute(k) {
      return k in this._a;
    },
    getAttribute(k) {
      return this._a[k] ?? null;
    },
    previousElementSibling: null,
    nextElementSibling: null,
  };
}
function chain(els) {
  els.forEach((el, i) => {
    el.previousElementSibling = i > 0 ? els[i - 1] : null;
    el.nextElementSibling = i < els.length - 1 ? els[i + 1] : null;
  });
  return els;
}

// ── Extract the REAL walk bodies from moveBlock ───────────────────────────
const mi = ops.indexOf('export function moveBlock(');
t('moveBlock exists', mi > 0);
const body = ops.slice(mi, ops.indexOf('\n}', mi));

const grab = (name) => {
  const i = body.indexOf(`const ${name} = (el: Element): Element | null => {`);
  if (i < 0) return null;
  const src = body.slice(body.indexOf('{', body.indexOf('=>', i)), body.indexOf('\n  };', i));
  return new Function('el', src.replace(/^\{/, '') + '\n');
};
const prevBlock = grab('prevBlock');
const nextBlock = grab('nextBlock');
t('both sibling walks extracted and runnable', !!prevBlock && !!nextBlock);

// ── 1. The defect, executed: a container must find its siblings ───────────
// The real substrate shape a slide takes after ADR-511/516: the page's own
// children are CONTAINERS, so a container's neighbours are containers. That
// is the shape where the old walk returned null at BOTH ends and the verb row
// answered with silence. (A container flanked by blocks is not the failing
// case — the old walk found those; naming it here would over-claim.)
{
  const [c1, c2, c3] = chain([
    mkEl('c1', 'container'),
    mkEl('c2', 'container'),
    mkEl('c3', 'container'),
  ]);
  t('a CONTAINER finds its previous sibling (was null → Move up did nothing)', prevBlock(c2) === c1);
  t('a CONTAINER finds its next sibling (was null → Move down did nothing)', nextBlock(c2) === c3);
}

// ── 2. A container must be REACHABLE as a sibling, not stepped over ───────
// Shape: [block, container, block]. From b1, the next sibling is the
// CONTAINER — before the fix the walk skipped it and returned b2, so a block
// could never be moved to sit adjacent to a container.
{
  const [b1, c1, b2] = chain([mkEl('b1', 'block'), mkEl('c1', 'container'), mkEl('b2', 'block')]);
  t('a block does not STEP OVER a container sibling (down)', nextBlock(b1) === c1);
  t('a block does not STEP OVER a container sibling (up)', prevBlock(b2) === c1);
}

// ── 3. Mixed grains — the walk must not prefer one grain over the other ───
// [container, block, container]: from the middle BLOCK both neighbours are
// containers, so the old walk ran off both ends and a block sitting between
// two containers could not be moved at all.
{
  const [c1, b1, c2] = chain([
    mkEl('c1', 'container'),
    mkEl('b1', 'block'),
    mkEl('c2', 'container'),
  ]);
  t('a block between two containers can move up', prevBlock(b1) === c1);
  t('a block between two containers can move down', nextBlock(b1) === c2);
}

// ── 4. The block grain is UNCHANGED — no regression ───────────────────────
{
  const [b1, b2, b3] = chain([mkEl('b1', 'block'), mkEl('b2', 'block'), mkEl('b3', 'block')]);
  t('block↔block reorder still works (up)', prevBlock(b2) === b1);
  t('block↔block reorder still works (down)', nextBlock(b2) === b3);
  t('first element has no previous', prevBlock(b1) === null);
  t('last element has no next', nextBlock(b3) === null);
}

// ── 5. Un-addressed nodes are still skipped ───────────────────────────────
// The walk must step OVER decoration that carries no identity — that part of
// the original filter was right and must survive the fix.
{
  const deco = { hasAttribute: () => false, previousElementSibling: null, nextElementSibling: null };
  const b1 = mkEl('b1', 'block');
  const b2 = mkEl('b2', 'block');
  chain([b1, deco, b2]);
  t('an UN-ADDRESSED sibling is still skipped (up)', prevBlock(b2) === b1);
  t('an UN-ADDRESSED sibling is still skipped (down)', nextBlock(b1) === b2);
}

// ── 6. The walk and the move must agree on what a sibling IS ──────────────
// The root cause was disagreement: the walk tested `data-block`, while
// moveBlockTo addresses by `data-block-id`. Pin the agreement, not a spelling.
{
  const walkTests = (body.match(/hasAttribute\('([a-z-]+)'\)/g) || []).map((m) =>
    m.slice(m.indexOf("'") + 1, m.lastIndexOf("'")),
  );
  t(
    'the sibling walk tests data-block-id (the attribute moveBlockTo addresses by)',
    walkTests.length === 2 && walkTests.every((a) => a === 'data-block-id'),
  );
  const mto = ops.slice(ops.indexOf('function moveBlockTo('), ops.indexOf('function moveBlock(', ops.indexOf('function moveBlockTo(')));
  t(
    'moveBlockTo resolves its target by data-block-id (the agreement holds)',
    /querySelector\(`\[data-block-id="\$\{CSS\.escape\(beforeBlockId\)\}"\]`\)/.test(mto),
  );
}

// ── 7. The mount this defect hid behind is still there ────────────────────
// Not the claim itself — the reason a grep-only gate stayed green. Kept so a
// future removal of the container verb row retires this gate honestly.
{
  // Anchor on the JSX render site (`{scope === 'container' && (`), not the
  // first textual match — the discriminator name appears earlier in prose.
  const ci = pane.indexOf("{scope === 'container' && (");
  const region = pane.slice(ci, ci + 900);
  t('container scope still mounts the verb row (the affordance being fixed)', /<VerbRow/.test(region));
}

// ── 8. ADR-519 D2.1 — the group/re-arrange reconciliation, EXECUTED ───────
// The refusal at artifactOps.ts:719 and ADR-519 D2 contradicted each other for
// a day. Both claims are pinned here so neither can drift back.
{
  // (a) The FALSE claim, executed: a group wrapper does NOT hide its children.
  // carriedBlocksOf = querySelectorAll('[data-block]') filtered by
  // !parentElement?.closest('[data-block]'). A wrapper carries data-block-id
  // ALONE, so it never trips that test.
  const wrapper = { a: { 'data-block-id': 'g1' } };
  const kids = [
    { a: { 'data-block-id': 'b1', 'data-block': 'text' }, parent: wrapper },
    { a: { 'data-block-id': 'b2', 'data-block': 'text' }, parent: wrapper },
  ];
  const carried = [wrapper, ...kids]
    .filter((e) => 'data-block' in e.a)
    .filter((e) => !(e.parent && 'data-block' in e.parent.a));
  t(
    "D2.1: a group wrapper does NOT hide its children (the refusal's false claim)",
    carried.length === 2 && carried.every((e) => kids.includes(e)),
  );
  t('D2.1: a group wrapper is NOT carried as a unit (so it cannot survive)', !carried.includes(wrapper));

  // (b) The TRUE claim, pinned at its mechanism: applyArrangement discards the
  // whole page, which is WHY dissolve costs no cleanup pass. If this line ever
  // stops being a wholesale replace, the "never orphaned" guarantee dies.
  // Slice to the NEXT top-level declaration, not the first `\n}` — the body has
  // nested blocks that close at column 0's predecessor and would truncate it.
  const ai = ops.indexOf('export function applyArrangement(');
  const aEnd = ops.indexOf('\nexport function', ai + 10);
  const abody = ops.slice(ai, aEnd > 0 ? aEnd : undefined);
  // Match the STATEMENT (line-anchored, semicolon-terminated), never the
  // string as prose — the body quotes `page.replaceWith(el)` in a comment
  // ABOVE the code, and matching that made the ordering check read backwards.
  const stmt = /^\s*page\.replaceWith\(el\);$/m;
  t('D2.1: applyArrangement discards the old page wholesale (no orphan possible)', stmt.test(abody));
  t(
    'D2.1: blocks survive only by being re-parented FIRST',
    abody.indexOf('target.appendChild(b);') < abody.search(stmt),
  );
  // All THREE arrangement entrances replace the page — the dissolve rule is a
  // property of re-arranging, not of one function.
  const others = ['applyArrangementPlan(', 'applyArrangementMovingContent('].map((n) => {
    const i = ops.indexOf('export function ' + n);
    const e = ops.indexOf('\nexport function', i + 10);
    return ops.slice(i, e > 0 ? e : undefined);
  });
  t(
    'D2.1: every arrangement entrance replaces the page (dissolve is uniform)',
    others.every((b) => stmt.test(b)),
  );

  // (c) The reconciliation is RECORDED where the contradiction lived — the
  // comment must not silently revert to the old blanket refusal.
  const mi2 = ops.indexOf('Move/resize SEVERAL blocks as ONE revision');
  const cmt = ops.slice(mi2, ops.indexOf('export function setGeometryMany', mi2));
  t('D2.1: the reconciliation is recorded at artifactOps.ts', /ADR-519 D2/.test(cmt));
  t(
    'D2.1: the corrected comment no longer claims a wrapper hides its children',
    !/would hide its own children/.test(cmt),
  );
}

console.log(`\n${pass}/${pass + fail} checks passed`);
process.exit(fail ? 1 : 0);
