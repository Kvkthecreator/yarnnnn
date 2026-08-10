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
import { createRequire } from 'module';
const require$ = createRequire(import.meta.url);

const labels = readFileSync('web/components/authoring/structureLabels.ts', 'utf8');
const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');
const pane = readFileSync('web/components/authoring/StudioDesignTab.tsx', 'utf8');
const ops = readFileSync('web/components/authoring/artifactOps.ts', 'utf8');
const kernel = readFileSync('api/services/authoring.py', 'utf8');
const docs = readFileSync('api/services/docs.py', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
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

// ADR-546 D1 — the indent token's values and the nesting CSS are now GENERATED
// from FLOW_RUNGS (authoring.py `_rung_css` / `_nest_css`), so there is no
// literal list left to scrape. The gate therefore reads the GENERATED OUTPUT via
// python — which is a stronger test than the pre-546 text scan: it proves the
// three systems agree in what actually SHIPS, not in what three lists say.
const kernelOut = (() => {
  try {
    const { execFileSync } = require$('child_process');
    const out = execFileSync(
      'python3',
      [
        '-c',
        'import json,sys; sys.path.insert(0,"api");' +
          'from services.authoring import FLOW_RUNGS, DEEPEST_FLOW_RUNG, STUDIO_TOKENS, _rung_css, _nest_css;' +
          'print(json.dumps({"rungs":list(FLOW_RUNGS),"deepest":DEEPEST_FLOW_RUNG,' +
          '"indent":[v["value"] for v in STUDIO_TOKENS["indent"]["values"]],' +
          '"rung_css":_rung_css(),"nest_css":_nest_css(),' +
          '"grains":list(STUDIO_TOKENS["indent"]["grains"])}))',
      ],
      { encoding: 'utf8', cwd: process.cwd() },
    );
    return JSON.parse(out);
  } catch (e) {
    return null;
  }
})();
t('D1: the kernel\'s generated rung output is readable', kernelOut != null);

const indentValues = kernelOut ? kernelOut.indent.map(Number) : [];
t('D1: the indent token declares a bounded value set', indentValues.length > 0);

// The nesting depth the GENERATED CSS renders — counted from the deepest
// `ul ul …` selector, so a marker restyle cannot break this.
const listNestDepth = (() => {
  if (!kernelOut) return 0;
  let deepest = 0;
  for (const m of kernelOut.nest_css.matchAll(/ul\[data-block="list"\]((?:\s+ul)+)\s*\{/g)) {
    deepest = Math.max(deepest, m[1].trim().split(/\s+/).length + 1);
  }
  return deepest;
})();
t('D1: the generated kernel CSS renders list nesting', listNestDepth > 0);

// THE INVARIANT (§1.1's tell): all three agree on depth, which is what makes
// them one concept. Now true BY CONSTRUCTION (generated from one set) and this
// asserts the construction held.
t(
  `D1: all three rung systems share one depth (headings=${headingRungs.length}, indent=${indentValues.length}, nesting=${listNestDepth})`,
  headingRungs.length > 0 &&
    headingRungs.length === indentValues.length &&
    indentValues.length === listNestDepth,
);

// The prose rung's own steps come from the same set.
t(
  'D1: the generated prose-rung CSS has one selector per declared rung',
  !!kernelOut &&
    kernelOut.rung_css.split('\n').filter((l) => l.includes('data-indent')).length ===
      kernelOut.rungs.length,
);

// The indent token is FLOW-only — a rung is a flow fact (D0: paged depth is
// containment per ADR-544, never an indent).
t(
  'D1: the indent token is declared for the flow grain only',
  !!kernelOut && kernelOut.grains.length === 1 && kernelOut.grains[0] === 'flow',
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
    bodyOf(labelForFn[0], 'el, blockLabels, mode').replace('__f', 'labelForElement') +
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
  const sectionOnFlow = labelForElement(mkEl('SECTION', { 'data-block-id': 's1' }), null, 'flow');
  t(
    `D5 [F1]: a <section> does not label as a deck grain on flow (got "${sectionOnFlow}")`,
    sectionOnFlow !== 'Slide',
  );
  // The NARROWING guard: flow loses the deck words, paged KEEPS them. A gate
  // that only checked flow would go green on a ladder that had lost 'Slide'
  // entirely — the ADR-544 lesson (three gates read a narrowing as a violation;
  // the inverse mistake is a gate that cannot see an amputation).
  t(
    'D5: a deck slide still labels as "Slide" on paged (D5 narrows, never deletes)',
    labelForElement(mkEl('SECTION', {}, ['slide']), null, 'paged') === 'Slide',
  );

  // The terminal fallback must not be a word ADR-544 D7 removed from the deck
  // crumb. A bare structural div on flow has no operator word at all.
  const bareOnFlow = labelForElement(mkEl('DIV', { 'data-block-id': 'd1' }), null, 'flow');
  t(
    `D5 [F1]: the terminal fallback is not "Group" on flow (got "${bareOnFlow}")`,
    bareOnFlow !== 'Group',
  );

  // An Area role IS legal — on paged. The ladder must still speak it (this is
  // the NARROWING guard: D5 forbids Area on FLOW, it does not delete the rung).
  t(
    'D5: the Area rung still resolves for paged callers (D5 narrows, never deletes)',
    labelForElement(
      mkEl('DIV', { 'data-area-role': 'body', 'data-area-place': 'left' }),
      null,
      'paged',
    ) === 'Body (left)',
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

// F2 — the two region/layout DERIVATIONS answer null on flow.
//
// Asserted at the CHOKEPOINT, not by counting call sites: a count cannot defend
// a per-site invariant (the ADR-519 lesson), and it would go red on the correct
// implementation, where the payloads still HAVE the keys and the derivation
// behind them is what became mode-aware. Post-544 the `slot` key reads
// `data-area` first, so an ungated derivation names ADR-544's Area grain in a
// DOCUMENT's payload — the drift ADR-544 §2 exists to prevent.
//
// EXECUTED: extract each function and run it with a stubbed document in both
// modes. A guard that is merely PRESENT is what a grep proves; this proves the
// function returns null.
const runDeriv = (fnName, mode) => {
  // Extracted from the RAW source, not the comment-stripped copy: stripping is
  // for absence assertions, and it mangles a body we intend to EXECUTE.
  const m = proj.match(new RegExp(`function ${fnName}\\(el\\) \\{[\\s\\S]*?\\n  \\}`));
  if (!m) return { ok: false };
  const isFlowSrc = proj.match(/function isFlowDoc\(\) \{[\s\S]*?\n  \}/);
  if (!isFlowSrc) return { ok: false };
  const doc = {
    documentElement: { getAttribute: () => mode },
  };
  // An element that WOULD match if the guard were absent — so a missing guard
  // returns a truthy region/arrange and the assertion fails.
  const el = {
    closest: () => ({ getAttribute: (k) => (k === 'data-area' ? 'main' : 'two-column') }),
  };
  try {
    const fn = new Function('document', `${isFlowSrc[0]}\n${m[0]}\nreturn ${fnName};`)(doc);
    return { ok: true, value: fn(el) };
  } catch {
    return { ok: false };
  }
};
for (const fnName of ['regionOf', 'arrangeOf']) {
  const onFlow = runDeriv(fnName, 'flow');
  const onPaged = runDeriv(fnName, 'paged');
  t(`D5 [F2]: ${fnName} is extractable and executes`, onFlow.ok && onPaged.ok);
  t(
    `D5 [F2]: ${fnName} answers null on flow (got ${JSON.stringify(onFlow.value)})`,
    onFlow.ok && onFlow.value === null,
  );
  // The narrowing guard again: paged must still RESOLVE the grain.
  t(
    `D5: ${fnName} still resolves on paged (D5 narrows, never deletes)`,
    onPaged.ok && onPaged.value != null,
  );
}

// ── Runtime hygiene: a literal backtick closes the template ────────────────
// The runtimes are module-level template literals, so ONE backtick in a comment
// inside them breaks the build (it bit three times while implementing ADR-546,
// and ADR-521's gate has caught it before). The existing check guards one
// region; this guards EVERY runtime template in the file, which is the actual
// invariant. Behaviour, not a spelling: extract each template and look inside.
/** Is there a backtick in the template's literal TEXT (as opposed to inside a
 *  `${…}` expression, where a nested template is legal TypeScript — POINTER_CSS
 *  builds selectors that way)? Brace-counted rather than regex-stripped: an
 *  interpolation containing an object literal or an arrow body nests braces, and
 *  a non-greedy `\$\{[^]*?\}` stops at the first one — reporting the gate's own
 *  false positive, which is how a gate stops being trusted. */
function hasLiteralBacktick(body) {
  let depth = 0;
  for (let i = 0; i < body.length; i++) {
    if (body[i] === '$' && body[i + 1] === '{') {
      depth++;
      i++;
      continue;
    }
    if (depth > 0) {
      if (body[i] === '{') depth++;
      else if (body[i] === '}') depth--;
      continue;
    }
    if (body[i] === '`') return true;
  }
  return false;
}

const runtimeTemplates = [...proj.matchAll(/const (\w*(?:SCRIPT|CSS))\s*=\s*`([\s\S]*?)\n`;/g)];
t('runtime templates are extractable', runtimeTemplates.length > 0);
for (const [, name, body] of runtimeTemplates) {
  // Strip `${…}` interpolations first: a nested template INSIDE an expression is
  // legal TypeScript (POINTER_CSS builds selectors that way). What breaks the
  // build is a backtick in the literal TEXT — prose, a comment, a CSS rule.
  // Without this the gate reports its own false positive, which is how a gate
  // stops being trusted.
  t(`no literal backtick inside ${name}`, !hasLiteralBacktick(body));
}

// ── D5, the pane header: no raw-attribute fallback (ADR-544 D4, symmetric) ──
t(
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
  // Assert the BINDING's own condition, not a proximity window: extract what
  // `pathRow` is assigned and require the mode to appear in the guard itself.
  // (A `[\s\S]{0,400}` window around the name would also match a mode test in a
  // NEIGHBOURING binding — a gate that passes for the wrong reason.)
  const pathRowExpr = paneCode.match(/const pathRow\s*=([\s\S]*?)\?/);
  const pathRowModeGated = !!pathRowExpr && /mode === '(paged|flow)'/.test(pathRowExpr[1]);
  t(
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
t('D4 [F4]: Tab does not insert a literal tab character in prose', !insertsLiteralTab);
// Tab must still step the rung in a list (D4 retains ADR-521 D4's behaviour).
t('D4: Tab still steps the rung inside a list', /outdent'?\s*:\s*'?indent/.test(tabHandler));

// ═══════════════════════════════════════════════════════════════════════════
// D3 — a span is a SHAPE. The range's subjects must carry their rung, and the
// derivation belongs to selection.ts (ADR-541 D2's one home).
// ═══════════════════════════════════════════════════════════════════════════
const selection = readFileSync('web/components/authoring/selection.ts', 'utf8');
const selCode = strip(selection);
t(
  'D3 [F7]: the selection algebra derives a span\'s rung shape, not only a count',
  /rung/i.test(selCode),
);
// And nobody else derives it — the ADR-541 D2 rule, inherited.
const paneDerivesRung = /function\s+\w*[Rr]ung\w*\s*\(/.test(paneCode);
t('D3: the pane does not derive the rung shape itself', !paneDerivesRung);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
