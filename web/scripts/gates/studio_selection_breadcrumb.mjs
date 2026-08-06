// Executing check of the selection breadcrumb (AUTHORING.md Phase 3 §3).
//
// The crumb renders the Esc-walk's ancestor chain (page → containers →
// selection). The chain floor is the ATTRIBUTION floor (ADR-511 D3): only
// identity-carrying containers are segments; unaddressed wrappers are
// transparent; blocks are leaves (a legacy nested block must not read as a
// container). This gate EXECUTES the real `climbChain` (types stripped) over
// stub elements, checks the mount is paged-gated, and FALSIFIES each guard by
// deleting it from the source (receipted with a "mutated:" print).
//
// Run from the REPO ROOT: node web/scripts/gates/studio_selection_breadcrumb.mjs
import { readFileSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

const src = readFileSync('web/components/studio/SelectionBreadcrumb.tsx', 'utf8');
const surface = readFileSync('web/components/studio/StudioSurface.tsx', 'utf8');

// ── Extract + compile the real climb ────────────────────────────────────────
const compileClimb = (source) => {
  const at = source.indexOf('export function climbChain');
  const body = source.slice(source.indexOf('{', at) + 1, source.indexOf('\n}', at));
  const stripped = body
    .replace(/: ClimbableElement\[\]/g, '')
    .replace(/: ClimbableElement \| null/g, '')
    .replace(/const containers: ClimbableElement\[\]/, 'const containers');
  return new Function('el', 'pageEl', stripped + '\nreturn containers;');
};
const climbChain = compileClimb(src);

// ── Stub chain: page > wrapper(no id) > cols > col > block ──────────────────
function mkEl(attrs, parent = null) {
  return {
    parentElement: parent,
    tagName: attrs.tag ?? 'DIV',
    getAttribute: (k) => attrs[k] ?? null,
    hasAttribute: (k) => attrs[k] != null,
  };
}
const page = mkEl({ tag: 'SECTION' });
const wrapper = mkEl({}, page); // transparent — no identity
const cols = mkEl({ 'data-block-id': 'c1' }, wrapper);
const col = mkEl({ 'data-block-id': 'c2' }, cols);
const block = mkEl({ 'data-block-id': 'b1', 'data-block': 'prose' }, col);

const chain = climbChain(block, page);
t('the chain collects both containers, outermost first', chain.length === 2 && chain[0] === cols && chain[1] === col);
t('the unaddressed wrapper is transparent (attribution floor)', !chain.includes(wrapper));

// A legacy nested block between the selection and its containers is a LEAF,
// never a chain segment.
const legacyBlock = mkEl({ 'data-block-id': 'lb', 'data-block': 'callout' }, col);
const inner = mkEl({ 'data-block-id': 'b2', 'data-block': 'prose' }, legacyBlock);
const legacyChain = climbChain(inner, page);
t('a nested legacy BLOCK is not a chain segment', legacyChain.length === 2 && !legacyChain.includes(legacyBlock));

// A block directly on the page has an empty chain (page › block — no containers).
t('a page-direct block climbs to an empty container chain', climbChain(mkEl({ 'data-block-id': 'b3', 'data-block': 'prose' }, page), page).length === 0);

// ── The mount is paged-gated ────────────────────────────────────────────────
const mountAt = surface.indexOf('<SelectionBreadcrumb');
t('StudioSurface mounts <SelectionBreadcrumb exactly once', mountAt >= 0 && surface.indexOf('<SelectionBreadcrumb', mountAt + 1) < 0);
t(
  'the mount is gated `isPaged && selection &&` (flow earns no crumb)',
  surface.slice(Math.max(0, mountAt - 400), mountAt).includes('isPaged && selection && ('),
);

// ── FALSIFIERS — delete each guard from the SOURCE, the checks must flip ────
{
  const mutated = src.replace(" && !cur.hasAttribute('data-block')", '');
  console.log('mutated: removed the data-block leaf guard from climbChain (in memory)');
  if (mutated === src) {
    t('FALSIFIER: the leaf-guard removal actually mutated the source', false);
  } else {
    const c = compileClimb(mutated)(inner, page);
    t('FALSIFIER: without the leaf guard, the nested block JOINS the chain', c.includes(legacyBlock));
  }
}
{
  const mutated = src.replace("cur.getAttribute('data-block-id') && ", 'true && ');
  console.log('mutated: removed the identity requirement from climbChain (in memory)');
  if (mutated === src) {
    t('FALSIFIER: the identity-requirement removal actually mutated the source', false);
  } else {
    const c = compileClimb(mutated)(block, page);
    t('FALSIFIER: without the identity floor, the transparent wrapper JOINS the chain', c.includes(wrapper));
  }
}

// ── ADR-519 D4.1 — the SET's chain: shared parent + count ──────────────────
// A set has no single innermost rung (that is what makes it a set), so the
// crumb must climb from the members' SHARED parent and name the COUNT. Naming
// the primary's own ancestry would be the staleness the pane withdrew: five
// objects boxed on canvas while the crumb reads "› heading".
const compileShared = (source) => {
  const at = source.indexOf('export function sharedChain');
  const body = source.slice(source.indexOf('{', source.indexOf('):', at)) + 1, source.indexOf('\n}', at));
  const stripped = body
    .replace(/const shared: ClimbableElement\[\]/, 'const shared')
    .replace(/: ClimbableElement\[\]\[\]/g, '');
  return new Function('chains', stripped + '\nreturn shared;');
};
const sharedChain = compileShared(src);

{
  // Two members under the SAME column: everything up to and including that
  // column is shared.
  const a = ['P', 'cols', 'colA'];
  const b = ['P', 'cols', 'colA'];
  t('D4.1: identical chains are shared whole', sharedChain([a, b]).join(',') === 'P,cols,colA');

  // Members in DIFFERENT columns: shared stops at the divergence.
  t('D4.1: divergent chains share only their common prefix',
    sharedChain([['P', 'cols', 'colA'], ['P', 'cols', 'colB']]).join(',') === 'P,cols');

  // Nothing in common below the page → empty chain, and the crumb then reads
  // page › N objects, which is the honest answer.
  t('D4.1: no shared container = empty chain (the page IS the shared parent)',
    sharedChain([['colA'], ['colB']]).length === 0);

  // A member sitting directly on the page truncates the whole shared chain —
  // the shallowest member bounds it, never the first one listed.
  t('D4.1: the SHALLOWEST member bounds the shared chain',
    sharedChain([['P', 'cols', 'colA'], []]).length === 0);

  // Three members, the third diverging: the pair's agreement must not win.
  t('D4.1: EVERY member must agree, not just the first pair',
    sharedChain([['P', 'x'], ['P', 'x'], ['P', 'y']]).join(',') === 'P');

  t('D4.1: a single chain is entirely shared with itself', sharedChain([['P', 'x']]).join(',') === 'P,x');
  t('D4.1: no chains = no shared chain', sharedChain([]).length === 0);
}
{
  const mutated = src.replace('if (rest.every((c) => c[i] === first[i])) shared.push(first[i]);',
    'if (rest.some((c) => c[i] === first[i])) shared.push(first[i]);');
  console.log('mutated: every → some in sharedChain (in memory)');
  if (mutated === src) {
    t('FALSIFIER: the every→some swap actually mutated the source', false);
  } else {
    const s = compileShared(mutated)([['P', 'x'], ['P', 'x'], ['P', 'y']]);
    t('FALSIFIER: with `some`, a chain only TWO members share leaks in', s.join(',') === 'P,x');
  }
}
{
  const mutated = src.replace('else break; // the chains diverge here', 'else continue; // ');
  console.log('mutated: break → continue in sharedChain (in memory)');
  if (mutated === src) {
    t('FALSIFIER: the break→continue swap actually mutated the source', false);
  } else {
    // colB/colA diverge at index 2, but 'P' at index 0 and a later match would
    // rejoin — a chain that is not a common PREFIX is not an ancestry.
    const s = compileShared(mutated)([['P', 'q', 'z'], ['P', 'w', 'z']]);
    t('FALSIFIER: without break, a non-prefix "ancestry" rejoins after divergence',
      s.join(',') === 'P,z');
  }
}

// ── The set's crumb is WIRED, and the count is the innermost rung ───────────
t('D4.1: the crumb receives the set (groupIds passed from the surface)',
  /groupIds=\{groupIds\}/.test(surface));
t('D4.1: a set of ONE is not a set (the single-subject chain still renders)',
  /ids\.length > 1/.test(src));
t('D4.1: the innermost rung over a set is the COUNT, not the primary label',
  /label: `\$\{ids\.length\} objects`/.test(src));
t('D4.1: a set spanning pages draws no chain (no shared page, no ancestry)',
  /every\(\(m\) => m\.closest\(STRUCTURAL_PAGE_SEL\) === pageEl\)/.test(src));

console.log(`\nstudio selection breadcrumb: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
