// Executing check of ADR-528 D2 — a range is not a block.
//
// The decision: on the FLOW medium the pane's scope set is
// `document | range | object`. `block` is not a scope a continuous document
// can produce. Scope is DERIVED from the tier the runtime already declares
// (ADR-525 D1, rule 11) — the pane must not re-derive it and must not commit
// a scope before consulting it.
//
// The defect this locks out: scope used to be committed from
// `blockId && blockKind` alone, and the tier arrived ~50 lines later where it
// could only SUBTRACT (`!isTextTier && ...`). That is why AUTHORING.md's
// `block (text)` column was a column of absences — no path, no verb row, no
// Hug|Fill, no W/H. Four ADRs in three days each removed one more affordance
// from a scope that should never have been entered.
//
// Why this gate EXECUTES the real extracted expression rather than grepping
// for a spelling (the counting-gate lesson, and the six assertions that broke
// on FORMATTING this week while behaviour was intact): a grep for
// `scope === 'range'` cannot tell you that a text-tier selection actually
// REACHES it. Only evaluating the derivation over a matrix of selections can.
// A spelling pin would also break the moment the ternary is reformatted.
//
// Run from the REPO ROOT: node web/scripts/gates/adr528_range_scope.mjs
import { readFileSync } from 'fs';

const pane = readFileSync('web/components/authoring/StudioDesignTab.tsx', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── 1. Extract the REAL scope derivation from the ONE home ────────────────
// ADR-541 D2 re-cut: the ladder LEFT the pane for selection.ts (`scopeOf` +
// `unify`), and the pane became one consumer among several — which is this
// gate's own thesis carried to its end (the pane can no longer disagree with
// the menu about a selection, because neither derives anything). The matrix
// below is UNCHANGED: same inputs, same expected scopes, now executed against
// the single source.
import { readFileSync as rf } from 'fs';
const selmod = rf('web/components/authoring/selection.ts', 'utf8');
function bodyOf(src, sig) {
  const i = src.indexOf(sig);
  if (i < 0) return null;
  const open = src.indexOf('{\n', i);
  const close = src.indexOf('\n}', open);
  return src.slice(open + 1, close);
}
const unifyBody = bodyOf(selmod, 'export function unify');
const scopeBody = bodyOf(selmod, 'export function scopeOf');
t('ADR-528: the scope derivation is present and extractable', !!unifyBody && !!scopeBody);
if (!unifyBody || !scopeBody) {
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(1);
}

// The scope type must name the two scopes and NOT the retired one.
const unionSrc = (selmod.match(/export type PaneScope = ([^;]+);/) ?? [])[1] ?? '';
t("ADR-528 D2: the scope union declares 'range'", /'range'/.test(unionSrc));
t("ADR-528 D2: the scope union declares 'object'", /'object'/.test(unionSrc));
t("ADR-528 D2: the scope union no longer declares 'block'", !/'block'/.test(unionSrc));

// The pane CONSUMES the one home rather than keeping a local ladder.
t(
  'ADR-541 D2: the pane consumes scopeOf (no local ladder survives)',
  /scopeOf\(unified, mode,/.test(pane) && !/\? 'container'\s*:/.test(pane),
);

// ── 2. EXECUTE it over a selection matrix ─────────────────────────────────
let deriveScope;
try {
  // eslint-disable-next-line no-new-func
  const unifyFn = new Function('primary', 'rangeBlockIds', 'groupIds', unifyBody);
  // eslint-disable-next-line no-new-func
  const scopeFn = new Function('u', 'mode', 'tier', scopeBody);
  deriveScope = (selection, isTextTier, rangeBlockIds, mode) =>
    scopeFn(unifyFn(selection, rangeBlockIds, []), mode, isTextTier ? 'text' : 'object');
  deriveScope(null, false, [], 'flow');
} catch (e) {
  t(`ADR-528: the extracted derivation evaluates (${e.message})`, false);
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(1);
}
t('ADR-528: the extracted derivation evaluates', true);

const blk = { blockId: 'b1', blockKind: 'prose' };
const fig = { blockId: 'b2', blockKind: 'figure' };
const cont = { blockId: 'c1' };
const page = { slideIndex: 0 };
// Convenience: the click-derived ladder, with no live range.
const S = (sel, tier, m = 'flow') => deriveScope(sel, tier, [], m);

// The load-bearing rows: same payload, different tier → different scope.
t("ADR-528 D2: a TEXT-tier block derives 'range' (prose on flow)", S(blk, true) === 'range');
t(
  "ADR-528 D2: an OBJECT-tier block derives 'object' (a figure, or any paged block)",
  S(fig, false, 'paged') === 'object',
);
t(
  "ADR-528 D2: the SAME payload flips scope with the tier — the tier is load-bearing",
  S(blk, true) !== S(blk, false),
);
t("ADR-528 D2: no selection and no range derives 'document'", S(null, false) === 'document');
t(
  "ADR-528 D2: identity without vocabulary still derives 'container' (ADR-511 D3)",
  S(cont, false, 'paged') === 'container',
);
t("ADR-528 D2: a page selection still derives 'page'", S(page, false, 'paged') === 'page');

// ── 2b. THE ENTRANCE (fix 2026-08-06) — a range must be REACHABLE ─────────
//
// ADR-528 shipped `range` and left it unreachable from the gesture it exists
// for. Every branch keyed off `selection`, which only a CLICK writes; a drag
// posts `yarnnn-range` into separate state. So a range with no preceding click
// left `selection` null → 'document' scope → the whole TextSection (the
// ADR-527 emphasis set) never mounted. The operator caught it in production:
// six blocks selected, pane reading "Document — select a block on the canvas".
//
// Asserting the scope EXISTS is not asserting it can be ENTERED. These rows
// are the difference.
t(
  "ENTRANCE: a live range with NO click derives 'range' (the defect: it derived 'document')",
  deriveScope(null, false, ['b1', 'b2'], 'flow') === 'range',
);
t(
  'ENTRANCE: a SINGLE-block range with no click also derives range (a caret drag)',
  deriveScope(null, false, ['b1'], 'flow') === 'range',
);
t(
  'ENTRANCE: a live range OUTRANKS a stale click (what the member is looking at wins)',
  deriveScope(fig, false, ['b1', 'b2'], 'flow') === 'range',
);
t(
  'ENTRANCE: the range entrance is FLOW-only — a paged medium is unaffected',
  deriveScope(fig, false, ['b1', 'b2'], 'paged') === 'object',
);
t(
  "ENTRANCE: an EMPTY range list does not force range scope (a collapsed caret clears it)",
  deriveScope(null, false, [], 'flow') === 'document',
);

// COMPLETENESS: 'block' must be unreachable for EVERY input, not merely absent
// from the two rows above. A counting gate cannot defend a per-site invariant.
const everyPayload = [null, blk, fig, cont, page, {}, { blockId: 'x', blockKind: 'heading' }];
const everyScope = new Set();
for (const s of everyPayload) {
  for (const tier of [true, false]) {
    for (const ids of [[], ['b1'], ['b1', 'b2']]) {
      for (const m of ['flow', 'paged']) everyScope.add(deriveScope(s, tier, ids, m));
    }
  }
}
t(
  `ADR-528 D2: 'block' is unreachable across every payload×tier×range×medium (got: ${[...everyScope].sort().join(', ')})`,
  !everyScope.has('block'),
);

// ── 3. FALSIFY — inject the defect, confirm the gate trips ────────────────
// The pre-ADR-528 derivation: scope committed from blockId && blockKind with
// no tier term. If this still yielded a passing matrix, the checks above
// would be vacuous.
const defectScope = new Function(
  'selection',
  'isTextTier',
  `return (!selection ? 'document'
     : selection.blockId && selection.blockKind ? 'block'
     : selection.blockId ? 'container'
     : (selection.slideIndex != null || selection.pageIndex != null) ? 'page'
     : 'document');`,
);
t(
  'ADR-528 FALSIFY: the pre-528 derivation ignores the tier (same scope both ways)',
  defectScope(blk, true) === defectScope(blk, false),
);
t(
  "ADR-528 FALSIFY: the pre-528 derivation reaches 'block' — this gate would trip on it",
  defectScope(blk, true) === 'block',
);

// FALSIFY THE ENTRANCE — the shipped-but-unreachable shape. This is ADR-528 as
// it actually landed: `range` exists and is derived from the tier, but only a
// CLICK can reach it. It passes every structural check above and still leaves
// the member looking at "Document" over a six-block selection.
const unreachable = new Function(
  'selection',
  'isTextTier',
  `return (!selection ? 'document'
     : selection.blockId && selection.blockKind ? (isTextTier ? 'range' : 'object')
     : selection.blockId ? 'container'
     : (selection.slideIndex != null || selection.pageIndex != null) ? 'page'
     : 'document');`,
);
t(
  "ENTRANCE FALSIFY: the shipped-unreachable shape derives 'document' for a click-less " +
    'range — the exact production defect, and it passes every check that only ' +
    'asserts the scope EXISTS',
  unreachable(null, false) === 'document' && unreachable(null, true) === 'document',
);

// ── 4. The D4 deletion — the withdrawal apparatus is GONE, not re-gated ───
// A suppression guard behind a scope that cannot be entered is dead code that
// reads as live policy. `isTextTier` must survive ONLY as the scope's input.
//
// Strip COMMENTS before testing. The first cut of this gate matched its own
// D4 explanation ("the `!isTextTier && !multiBlockRange` guard is DELETED")
// and reported the defect it was written to prove absent — the exact failure
// the discipline names: an assertion that pins a spelling matches the prose
// describing the spelling. Test the CODE.
const code = pane
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/(^|[^:])\/\/[^\n]*/g, '$1')
  .replace(/\{\/\*[\s\S]*?\*\/\}/g, '');

const isTextTierUses = (code.match(/isTextTier/g) ?? []).length;
t(
  `ADR-528 D4: isTextTier survives only as declaration + scope input (${isTextTierUses} code uses, expect 2)`,
  isTextTierUses === 2,
);
t(
  'ADR-528 D4: no `!isTextTier &&` suppression guard remains in code',
  !/!isTextTier\s*&&/.test(code),
);
// The Layout section must no longer be gated on the range at all — under D2 a
// range cannot reach object scope, so the guard has nothing left to suppress.
t(
  'ADR-528 D4: the Layout section is not gated on multiBlockRange',
  !/!multiBlockRange\s*&&\s*\n?\s*\(nonColorTokens/.test(code),
);

// ── 5. Rule 11 — the pane READS the tier, never re-derives the medium ─────
// The fallback (for a pre-tier payload still in flight from an older
// projection) may consult `mode`, but the runtime's declaration wins.
t(
  'ADR-525 D1 / rule 11: the tier is read from the selection payload first',
  /selection\.tier\s*\?\?/.test(pane),
);

// ── 6. One implementation, two entrances (rule 7 / ADR-518 D2) ────────────
// Splitting the block branch in two must NOT duplicate the structure-tier
// sections. Each is declared once and referenced by both scopes.
for (const [name, decl] of [
  ['rampSection', /const rampSection\s*=/g],
  ['turnIntoSection', /const turnIntoSection\s*=/g],
]) {
  t(
    `ADR-518 D2: ${name} is declared exactly once (no forked per-scope copy)`,
    (pane.match(decl) ?? []).length === 1,
  );
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
