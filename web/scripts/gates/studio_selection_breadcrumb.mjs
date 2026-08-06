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

console.log(`\nstudio selection breadcrumb: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
