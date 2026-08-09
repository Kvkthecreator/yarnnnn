// Executing check of ADR-541 — the selection algebra.
//
// The scope ladder's execution matrix lives in adr528_range_scope.mjs (re-cut
// by ADR-541 to execute the one home). This gate owns what ADR-541 ADDED:
// arity, the unified set, the span/set op chaining, and the three verb
// entrances reading one answer.
//
// Run from the REPO ROOT: node web/scripts/gates/adr541_selection_algebra.mjs
import { readFileSync } from 'fs';

const selmod = readFileSync('web/components/studio/selection.ts', 'utf8');
const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');
const surface = readFileSync('web/components/studio/StudioSurface.tsx', 'utf8');
const menu = readFileSync('web/components/studio/StudioBlockMenu.tsx', 'utf8');
const ops = readFileSync('web/components/studio/artifactOps.ts', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

function bodyOf(src, sig) {
  const i = src.indexOf(sig);
  if (i < 0) return null;
  const open = src.indexOf('{\n', i);
  const close = src.indexOf('\n}', open);
  return src.slice(open + 1, close);
}

// ── 1. unify + arityOf, EXECUTED ───────────────────────────────────────────
const unify = new Function('primary', 'rangeBlockIds', 'groupIds', bodyOf(selmod, 'export function unify'));
const arityOf = new Function('u', bodyOf(selmod, 'export function arityOf'));

const P = { blockId: 'b1', blockKind: 'prose' };
t('unify: no set at all', arityOf(unify(null, [], [])) === 'none');
t('unify: a clicked primary alone is ONE subject', arityOf(unify(P, [], [])) === 'one');
t('unify: a single-member range is ONE subject (a caret drag is not a set)',
  arityOf(unify(null, ['b1'], [])) === 'one');
t('unify: a spanning range is MANY', arityOf(unify(P, ['b1', 'b2', 'b3'], [])) === 'many');
t('unify: a ⇧-click set is MANY with setKind objects', (() => {
  const u = unify(P, [], ['b1', 'b2']);
  return arityOf(u) === 'many' && u.setKind === 'objects';
})());
t('unify: a live range OUTRANKS the ⇧-click memory (what the member sees wins)',
  unify(P, ['r1', 'r2'], ['g1', 'g2']).setKind === 'range');
// FALSIFIER — order the ladder the other way and the precedence claim dies.
t('FALSIFIER: swapping the inputs flips the winner (precedence is live)',
  unify(P, [], ['g1', 'g2']).setKind === 'objects');

// ── 2. The span/set ops chain through the SINGLE ops, one revision ─────────
for (const [fn, single] of [
  ['convertBlocks', 'convertBlock(cur, id, kind, fragment)'],
  ['setTokenMany', "setToken(cur, { grain: 'block', anchor: { blockId: id } }, key, value)"],
]) {
  const body = bodyOf(ops, `export function ${fn}`);
  t(`${fn} chains the SINGLE op (one legality implementation)`, !!body && body.includes(single));
  t(`${fn} skips refusals per-block, never a whole-range veto`,
    !!body && body.includes('if (r)') && body.includes('hit'));
}
const delMany = bodyOf(ops, 'export function deleteBlocks');
t('deleteBlocks removes every found member and returns ONE result',
  !!delMany && delMany.includes('block.remove()') && delMany.includes('serialize(doc)'));

// ── 3. The three verb entrances read one answer ────────────────────────────
t('the PANE reads the derived arity (multi flags are readings of it)',
  /const arity = arityOf\(unified\);/.test(pane));
t('the KEYBOARD expands delete/duplicate over the set (the ⌫-deletes-one defect)',
  /const set = groupIds\.length > 1 && groupIds\.includes\(blockId\) \? groupIds : null;/.test(surface) &&
    /deleteBlocks\(html, set\)/.test(surface));
t('the pane/menu VERB row expands the same way (one expansion rule, two doors)',
  /const set = groupIds\.length > 1 && groupIds\.includes\(id\) \? groupIds : null;/.test(surface));
t('the MENU is told the count (setCount) from the SAME algebra',
  /setCount=\{/.test(surface) && /arityOf\(u\) === 'many'/.test(surface) &&
    /u\.set\.includes\(ctxMenu\.blockId\)/.test(surface));
t('the menu says the count on the set-taking rows',
  /`Delete \$\{setCount\} blocks`/.test(menu) && /`Duplicate \$\{setCount\} blocks`/.test(menu));
t('the menu withdraws single-subject rows over a set and SAYS so once',
  /isPaged && !inSet/.test(menu) && /target\.positioned && !inSet/.test(menu) &&
    /one block at a time \(\{setCount\} selected\)/.test(menu));
t('the menu turn-into takes the span when the clicked block is covered',
  /rangeBlockIds\.length > 1 && rangeBlockIds\.includes\(blockId\)/.test(surface));
t('a span token write is gated by the SERVED grain, never a key list',
  /applies \?\? \[\]\)\.includes\('block-flow'\)/.test(surface));

// ── 4. Revision messages carry the count (the one-⌘Z contract's receipt) ───
t('N-block revision messages say N',
  /delete \$\{set\.length\} blocks/.test(surface) &&
    /turn \$\{blockIds\.length\} blocks into/.test(surface) &&
    /on \$\{rangeBlockIds\.length\} blocks/.test(surface));

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail === 0 ? 0 : 1);
