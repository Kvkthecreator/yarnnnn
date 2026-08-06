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

const pane = readFileSync('web/components/studio/StudioDesignTab.tsx', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── 1. Extract the REAL scope derivation from the source ──────────────────
// Anchored on the declaration, terminated at the first `;` — the whole
// ternary chain, whatever its formatting.
const scopeSrc = pane.match(
  /const scope:[^=]*=\s*(!selection[\s\S]*?);\n/,
);
t('ADR-528: the scope derivation is present and extractable', !!scopeSrc);
if (!scopeSrc) {
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(1);
}
const scopeExpr = scopeSrc[1];

// The union type must name the two new scopes and NOT the retired one.
const unionSrc = pane.match(/const scope:\s*([^=]+)=/)[1];
t(
  "ADR-528 D2: the scope union declares 'range'",
  /'range'/.test(unionSrc),
);
t(
  "ADR-528 D2: the scope union declares 'object'",
  /'object'/.test(unionSrc),
);
t(
  "ADR-528 D2: the scope union no longer declares 'block'",
  !/'block'/.test(unionSrc),
);

// ── 2. EXECUTE it over a selection matrix ─────────────────────────────────
// The derivation closes over `selection` and `isTextTier` only. Build it as a
// real function of those two and run it — this is the behaviour, not its
// spelling.
let deriveScope;
try {
  // eslint-disable-next-line no-new-func
  deriveScope = new Function('selection', 'isTextTier', `return (${scopeExpr});`);
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

// The load-bearing rows: same payload, different tier → different scope.
t(
  "ADR-528 D2: a TEXT-tier block derives 'range' (prose on flow)",
  deriveScope(blk, true) === 'range',
);
t(
  "ADR-528 D2: an OBJECT-tier block derives 'object' (a figure, or any paged block)",
  deriveScope(fig, false) === 'object',
);
t(
  "ADR-528 D2: the SAME payload flips scope with the tier — the tier is load-bearing",
  deriveScope(blk, true) !== deriveScope(blk, false),
);
t(
  "ADR-528 D2: no selection derives 'document'",
  deriveScope(null, false) === 'document',
);
t(
  "ADR-528 D2: identity without vocabulary still derives 'container' (ADR-511 D3)",
  deriveScope(cont, false) === 'container',
);
t(
  "ADR-528 D2: a page selection still derives 'page'",
  deriveScope(page, false) === 'page',
);

// COMPLETENESS: 'block' must be unreachable for EVERY input, not merely absent
// from the two rows above. A counting gate cannot defend a per-site invariant.
const everyPayload = [null, blk, fig, cont, page, {}, { blockId: 'x', blockKind: 'heading' }];
const everyScope = new Set();
for (const s of everyPayload) {
  for (const tier of [true, false]) everyScope.add(deriveScope(s, tier));
}
t(
  `ADR-528 D2: 'block' is unreachable across every payload×tier (got: ${[...everyScope].sort().join(', ')})`,
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
