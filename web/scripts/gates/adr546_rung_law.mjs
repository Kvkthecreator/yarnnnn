// Executing check of ADR-546 — the rung law: a document is a tree of text.
//
// WHAT THIS GATE IS FOR. The ADR-546 audit was made against a 22/22 GREEN
// battery (four arcs for four, this layer's defects are invisible to gates).
// So this gate does not assert that code is PRESENT — it EXECUTES the real
// extracted derivations and asserts BEHAVIOUR, and every claim has a falsifier
// that was watched go red.
//
// It asserts the CURRENT-STATE facts §1 receipts (so a silent regression of the
// audit's premises is caught) plus the D5/D1 invariants that must hold as the
// phases land. Where a decision is not yet implemented, the check names the
// defect it is DOCUMENTING rather than claiming a pass — a gate that goes green
// on unimplemented law is the "prose caveat where a gate belonged" shape
// ADR-544 D3 found in the measure registry.
//
// NEVER PIN A SPELLING (the ADR-544 lesson — three gates went red for it, one
// reading a NARROWING as a violation). Every assertion below is about a SET, a
// behaviour, or an invariant, never a literal string a rename would break.
//
// Run from the REPO ROOT: node web/scripts/gates/adr546_rung_law.mjs
import { readFileSync } from 'fs';

const labels = readFileSync('web/components/authoring/structureLabels.ts', 'utf8');
const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');
const pane = readFileSync('web/components/authoring/StudioDesignTab.tsx', 'utf8');
const ops = readFileSync('web/components/authoring/artifactOps.ts', 'utf8');
const kernel = readFileSync('api/services/authoring.py', 'utf8');
const docs = readFileSync('api/services/docs.py', 'utf8');

let pass = 0,
  fail = 0,
  pending = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};
// A decision this ADR RATIFIED but whose phase has not landed. It prints its
// real state and does NOT fail the run — but it is not silent either, and it
// flips to a hard assertion (`t`) in the commit that lands its phase. The
// phase number is required, so "pending" can never become a parking lot: a
// pending check with no phase is a decision nobody scheduled.
//
// Why this shape: a gate that goes GREEN on unimplemented law is the "prose
// caveat where a gate belonged" defect (ADR-544 D3). A gate that goes RED for
// weeks is a gate the next session learns to ignore. Neither is acceptable, so
// the state is NAMED.
const pendingChecks = [];
const p = (phase, label, cond) => {
  if (cond) {
    console.log(`[PASS] ${label}`);
    pass++;
    return;
  }
  console.log(`[PEND ${phase}] ${label}`);
  pending++;
  pendingChecks.push(`phase ${phase}: ${label}`);
};

// ── Strip comments before any source assertion ─────────────────────────────
// The ADR-544 lesson `feedback_gate_assertion_matches_its_own_comment`: an
// ABSENCE assertion matches its own explanatory comment, so "we do NOT do X"
// collides with the comment saying why. Every source test below runs on
// comment-stripped text.
const strip = (s) =>
  s
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/[^\n]*/g, '$1')
    .replace(/^\s*#[^\n]*$/gm, '');
const labelsCode = strip(labels);
const projCode = strip(proj);
const paneCode = strip(pane);
const opsCode = strip(ops);

// ═══════════════════════════════════════════════════════════════════════════
// D1 — depth is ONE concept. The three shipped rung systems must agree on
// their cardinality; if they ever disagree, §1.1 has re-opened with a NEW
// spelling and the law needs an amendment, not a silent widening.
// ═══════════════════════════════════════════════════════════════════════════

// The heading rungs, extracted from the kernel's declaration (the served set).
const rungMatch = kernel.match(/HEADING_RUNGS[^=]*=\s*\(([^)]*)\)/);
const headingRungs = rungMatch
  ? rungMatch[1].split(',').map((s) => s.trim()).filter(Boolean).map(Number)
  : [];
t('D1: HEADING_RUNGS is declared in the kernel and non-empty', headingRungs.length > 0);

// The indent token's value set, extracted from the served token row.
const indentBlock = kernel.match(/"indent"\s*:\s*\{[\s\S]*?\n    \}/);
const indentValues = indentBlock
  ? [...indentBlock[0].matchAll(/"value"\s*:\s*"(\d+)"/g)].map((m) => Number(m[1]))
  : [];
t('D1: the indent token declares a bounded value set', indentValues.length > 0);

// The list-nesting depth the kernel CSS actually renders, counted from the
// deepest `ul ul ul` / `ol ol ol` selector present. Behaviour, not a literal:
// we count nesting steps, so restyling `circle`→`square` cannot break this.
const listNestDepth = (() => {
  let deepest = 0;
  for (const m of kernel.matchAll(/ul\[data-block="list"\]((?:\s+ul)+)\s*\{/g)) {
    deepest = Math.max(deepest, m[1].trim().split(/\s+/).length + 1);
  }
  return deepest;
})();
t('D1: the kernel CSS renders list nesting at some depth', listNestDepth > 0);

// THE INVARIANT (§1.1's tell): all three independently landed on the same
// depth, which is what makes them one concept. A future divergence means a
// fourth interpretation of depth shipped without the law.
t(
  `D1: all three rung systems share one depth (headings=${headingRungs.length}, indent=${indentValues.length}, nesting=${listNestDepth})`,
  headingRungs.length === indentValues.length && indentValues.length === listNestDepth,
);

// The indent token is FLOW-only — a rung is a flow fact (D0: paged depth is
// containment per ADR-544, never an indent).
t(
  'D1: the indent token is declared for the flow grain only',
  !!indentBlock && /"grains"\s*:\s*\(\s*"flow"\s*,?\s*\)/.test(indentBlock[0]),
);

// ═══════════════════════════════════════════════════════════════════════════
// D2 — the addressing floor stays the BLOCK. An <li> must never carry
// identity. This is the falsifier that must go red if D2 is ever widened
// without the §5 evidence (F8).
// ═══════════════════════════════════════════════════════════════════════════

// EXECUTE the real normalizeStructure subject predicate rather than grepping
// for it: extract the selector it addresses and prove LI is unmatched.
const subjectSel = opsCode.match(/querySelectorAll\(\s*'(\[data-block\][^']*)'\s*\)/);
t('D2: normalizeStructure addresses subjects by a data-attribute selector', !!subjectSel);
if (subjectSel) {
  const sel = subjectSel[1];
  // A selector that admits a bare tag would put LI in the subject set.
  const admitsBareTag = /(^|,)\s*[a-zA-Z]+\s*(,|$)/.test(sel);
  t('D2: the subject selector admits no bare tag (so no <li> is a subject)', !admitsBareTag);
}
// The promotion map is the other route to a `data-block`. LI must not be in it.
const promoteBlock = opsCode.match(/PROMOTE_KIND[^=]*=\s*\{[\s\S]*?\n\};/);
t('D2: PROMOTE_KIND is extractable', !!promoteBlock);
if (promoteBlock) {
  const promoted = [...promoteBlock[0].matchAll(/(\b[A-Z][A-Z0-9]*)\s*:/g)].map((m) => m[1]);
  t(
    `D2: LI is not a promotion target (promoted: ${promoted.length} tags)`,
    promoted.length > 0 && !promoted.includes('LI'),
  );
  // The rung spellings' own tags MUST be promotable — a list is a block (ADR-536 D1).
  t('D2: UL and OL promote to their own kinds (a list IS a block)',
    promoted.includes('UL') && promoted.includes('OL'));
}

// ═══════════════════════════════════════════════════════════════════════════
// D5 — the chrome says the four words. EXECUTE the real label ladder.
// ═══════════════════════════════════════════════════════════════════════════

// Extract labelForElement's body and run it against synthetic elements. This
// is the ladder the pane, the crumb and the navigator all consume.
const mkEl = (tag, attrs = {}, classes = []) => ({
  tagName: tag,
  classList: { contains: (n) => classes.includes(n) },
  getAttribute: (k) => (k in attrs ? attrs[k] : null),
});

// Re-implement the ladder by EXTRACTING it, so the gate cannot drift from the
// source: pull the function text and eval it in a scope with its dependency.
const areaRoleBlock = labels.match(/AREA_ROLE_LABELS[^=]*=\s*(\{[\s\S]*?\n\});/);
const areaLabelFn = labels.match(/export function areaLabel\([\s\S]*?\n\}/);
const labelForFn = labels.match(/export function labelForElement\([\s\S]*?\n\}/);
t('D5: the label ladder and its role map are both extractable', !!areaRoleBlock && !!areaLabelFn && !!labelForFn);

let labelForElement = null;
if (areaRoleBlock && areaLabelFn && labelForFn) {
  // Replace each TS signature wholesale with a plain-JS one, then keep the
  // BODY verbatim — so the executed ladder is the real source, and only the
  // types are discarded. (A per-annotation regex sweep cannot survive the
  // multi-line inline param type on labelForElement.)
  const bodyOf = (fnSrc, params) => {
    const open = fnSrc.indexOf('{', fnSrc.indexOf(')'));
    return `function __f(${params}) ` + fnSrc.slice(open);
  };
  const src =
    `const AREA_ROLE_LABELS = ${areaRoleBlock[1]};\n` +
    bodyOf(areaLabelFn[0], 'role, place').replace('__f', 'areaLabel') +
    '\n' +
    bodyOf(labelForFn[0], 'el, blockLabels').replace('__f', 'labelForElement') +
    '\nreturn labelForElement;';
  try {
    labelForElement = new Function(src)();
  } catch (e) {
    t(`D5: the extracted ladder evaluates (${e.message})`, false);
  }
}

if (labelForElement) {
  t('D5: the extracted ladder evaluates', true);

  // A block labels from the REGISTRY's word, never the attribute's (ADR-544 D4,
  // inherited). Behaviour: given a map, the map wins.
  t(
    'D5: a block labels from the served registry map, not the attribute',
    labelForElement(mkEl('DIV', { 'data-block': 'prose' }), { prose: 'Text' }) === 'Text',
  );

  // THE §1.6 FINDING, asserted as the invariant D5 establishes. A <section>
  // reachable in a DOCUMENT must not be labelled with the deck's word.
  // Today the ladder is mode-blind, so this documents the open defect: the
  // assertion is that the ladder does NOT hand a deck word to a document.
  const sectionLabel = labelForElement(mkEl('SECTION', { 'data-block-id': 's1' }));
  p(5,
    `D5 [F1]: a <section> does not label as a deck grain on flow (got "${sectionLabel}")`,
    sectionLabel !== 'Slide',
  );

  // The terminal fallback must not be a word ADR-544 D7 removed from the deck
  // crumb. A bare structural div on flow has no operator word at all.
  const bareLabel = labelForElement(mkEl('DIV', { 'data-block-id': 'd1' }));
  p(5,
    `D5 [F1]: the terminal fallback is not "Group" (got "${bareLabel}")`,
    bareLabel !== 'Group',
  );

  // An Area role IS legal — on paged. The ladder must still speak it (this is
  // the NARROWING guard: D5 forbids Area on FLOW, it does not delete the rung).
  t(
    'D5: the Area rung still resolves for paged callers (D5 narrows, never deletes)',
    labelForElement(mkEl('DIV', { 'data-area-role': 'body', 'data-area-place': 'left' })) ===
      'Body (left)',
  );
}

// ── D5, the payload rule: flow must not NAME grains its projection deletes ──
// The flow flatten pass and the payload builders are in one file; assert the
// relation between them rather than either literal.
const flattenTargets = (() => {
  const m = projCode.match(/mode === 'flow'\s*\)\s*\{([\s\S]{0,600}?)\n  \}/);
  return m ? m[1] : '';
})();
t('D5: the flow flatten pass is extractable', flattenTargets.length > 0);
const flowDeletesArrange = /\[data-arrange\]/.test(flattenTargets);
const flowDeletesRegion = /data-area|data-slot/.test(flattenTargets);
t('D5: the flow projection deletes the paged region + layout grains', flowDeletesArrange && flowDeletesRegion);

// Count the payload sites that name those grains. Post-544 the `slot` key
// reads `data-area` FIRST, so ADR-544's Area grain is named in flow's payload.
const payloadNamesRegion = [...projCode.matchAll(/slot:\s*\w+\s*\?/g)].length;
const payloadNamesArrange = [...projCode.matchAll(/arrange:\s*\w+\s*\?/g)].length;
p(5,
  `D5 [F2]: no selection payload names a grain the flow projection deletes (region=${payloadNamesRegion}, arrange=${payloadNamesArrange})`,
  payloadNamesRegion === 0 && payloadNamesArrange === 0,
);

// ── D5, the pane header: no raw-attribute fallback (ADR-544 D4, symmetric) ──
p(5,
  'D5 [F1]: the pane header does not fall back to the raw block attribute',
  !/selection\?\.label\s*\?\?\s*selection\?\.blockKind/.test(paneCode),
);

// ═══════════════════════════════════════════════════════════════════════════
// D6 — pathRow's premise. The claim "no <section> ancestor exists on flow"
// must be TRUE, not assumed: either the flatten lifts them, or the gate is
// mode-explicit. Assert the premise rather than the comment.
// ═══════════════════════════════════════════════════════════════════════════
const pageSel = labels.match(/STRUCTURAL_PAGE_SEL\s*=\s*'([^']+)'/);
t('D6: STRUCTURAL_PAGE_SEL is declared once', !!pageSel);
if (pageSel) {
  // Does the selector admit a plain <section> under main/article/body?
  const admitsPlainSection = /:is\([^)]*\)\s*>\s*section/.test(pageSel[1]);
  // Does the Docs kernel skin declare that very shape?
  const docsDeclaresSection = /section\[data-block\]/.test(docs);
  // If BOTH are true, the "always null" premise needs a mode gate to be honest.
  const premiseNeedsGate = admitsPlainSection && docsDeclaresSection;
  const pathRowModeGated = /pathRow[\s\S]{0,400}?mode === 'flow'/.test(paneCode) ||
    /mode === 'paged'[\s\S]{0,200}?pathRow/.test(paneCode);
  p(5,
    `D6: pathRow's always-null claim is gated, not assumed (selector admits=${admitsPlainSection}, skin declares=${docsDeclaresSection})`,
    !premiseNeedsGate || pathRowModeGated,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// D4 — Tab means ONE thing. The literal-tab-character branch is deleted.
// ═══════════════════════════════════════════════════════════════════════════
const tabHandler = (() => {
  const i = projCode.indexOf("if (e.key !== 'Tab') return;");
  return i === -1 ? '' : projCode.slice(i, i + 900);
})();
t('D4: the Tab handler is extractable', tabHandler.length > 0);
// A literal tab is inserted via a character code or an escape — assert the
// BEHAVIOUR (a tab character reaches the document), not one spelling of it.
const insertsLiteralTab =
  /fromCharCode\(\s*9\s*\)/.test(tabHandler) || /insertText'?\s*,\s*false\s*,\s*['"]\\t['"]/.test(tabHandler);
p(4, 'D4 [F4]: Tab does not insert a literal tab character in prose', !insertsLiteralTab);
// Tab must still step the rung in a list (D4 retains ADR-521 D4's behaviour).
t('D4: Tab still steps the rung inside a list', /outdent'?\s*:\s*'?indent/.test(tabHandler));

// ═══════════════════════════════════════════════════════════════════════════
// D3 — a span is a SHAPE. The range's subjects must carry their rung, and the
// derivation belongs to selection.ts (ADR-541 D2's one home).
// ═══════════════════════════════════════════════════════════════════════════
const selection = readFileSync('web/components/authoring/selection.ts', 'utf8');
const selCode = strip(selection);
p(3,
  'D3 [F7]: the selection algebra derives a span\'s rung shape, not only a count',
  /rung/i.test(selCode),
);
// And nobody else derives it — the ADR-541 D2 rule, inherited.
const paneDerivesRung = /function\s+\w*[Rr]ung\w*\s*\(/.test(paneCode);
t('D3: the pane does not derive the rung shape itself', !paneDerivesRung);

console.log(`\n${pass} passed, ${fail} failed, ${pending} pending`);
if (pendingChecks.length) {
  console.log('\nPENDING (ratified, phase not landed) \u2014 each flips to a hard');
  console.log('assertion in the commit that lands its phase:');
  for (const c of pendingChecks) console.log('  \u2022 ' + c);
}
process.exit(fail === 0 ? 0 : 1);
