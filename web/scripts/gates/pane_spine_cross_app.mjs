// Executing check: the properties pane speaks ONE spine, in every authoring app.
//
// ADR-519 D3 fixed Studio's order (Identity → Position → Layout → Style →
// Content) and gated it in test_adr519_pane_spine.py. That gate reads exactly
// two files, BOTH Studio's — so when Text grew its own pane beside it, with its
// own heading styles, its own section rhythm and its own order, every check
// stayed green. The rule was real and the divergence was invisible, because the
// rule lived in a docstring about one component.
//
// This gate is the cross-app half: the spine generalized with a READBACK rung
// (facts last, after every control), asserted against BOTH panes.
//
// Run from the REPO ROOT: node web/scripts/gates/pane_spine_cross_app.mjs
import { readFileSync } from 'fs';

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// Strip comments before any assertion: a check that greps raw source can match
// the very prose written to explain the thing it forbids. That defect has cost
// this arc three separate false reds — never assert against un-stripped source.
const strip = (src) =>
  src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const spineMod = readFileSync('web/lib/authoring/pane-spine.ts', 'utf8');
const studio = readFileSync('web/components/authoring/StudioDesignTab.tsx', 'utf8');
const text = readFileSync('web/components/text/TextEditor.tsx', 'utf8');

// ── 1. The spine is DECLARED once, in a shared module ─────────────────────
{
  const decl = (spineMod.match(/export const PANE_SPINE = \[([\s\S]*?)\] as const;/) ?? [])[1] ?? '';
  const rungs = [...decl.matchAll(/'([a-z]+)'/g)].map((m) => m[1]);
  t('the spine is declared as an ordered list',
    rungs.length > 0);
  t('Identity leads and Readback ends (subject first, facts last)',
    rungs[0] === 'identity' && rungs[rungs.length - 1] === 'readback');
  t("ADR-519's control order survives inside it, unchanged",
    JSON.stringify(rungs.filter((r) => r !== 'identity' && r !== 'readback' && r !== 'text'))
      === JSON.stringify(['position', 'layout', 'style', 'content']));
}

// ── 2. Both apps IMPORT the grammar — no per-app copy ─────────────────────
{
  for (const [app, src] of [['Studio', studio], ['Text', text]]) {
    t(`${app} imports the shared pane grammar`,
      /from '@\/lib\/authoring\/pane-spine'/.test(src));
  }
  // The decisive check: the Tailwind strings must not be re-declared anywhere
  // outside the shared module. A copied string is identical on the day it is
  // written, which is exactly why nothing catches it drifting later.
  const literal = 'text-\\[10px\\] font-medium uppercase tracking-wide text-muted-foreground';
  for (const [app, src] of [['Studio', studio], ['Text', text]]) {
    t(`${app} does not re-declare the heading style inline`,
      !new RegExp(literal).test(strip(src)));
  }
  t('Studio does not re-declare the section box inline',
    !/'space-y-2 border-b border-border p-3'/.test(strip(studio)));
}

// ── 3. TEXT renders in spine order, readback LAST ─────────────────────────
//
// Text has no control rungs (markdown has no box), so its spine is Identity
// then readback. The claim under test is that the three FACTS sit together at
// the end — "Last edited" used to be interleaved above Length and Format.
{
  const src = strip(text);
  const at = (name) => src.indexOf(`\n                  ${name}\n`);
  const outline = at('Outline');
  const length = at('Length');
  const format = at('Format');
  const edited = at('Last edited');
  t('Text: all four pane sections are found',
    [outline, length, format, edited].every((i) => i > 0));
  t('Text: Identity (Outline) precedes every readback section',
    outline < length && outline < format && outline < edited);
  t('Text: the readback sections are CONTIGUOUS and last (no control after a fact)',
    length < format && format < edited);
  // The file card is the Identity rung and must lead the pane.
  const fileCard = src.indexOf('aria-label="File actions"');
  t('Text: the file card (Identity) leads the pane',
    fileCard > 0 && fileCard < outline);
}

// ── 4. STUDIO still leads with Identity at the object scope ───────────────
// The full per-scope ordering stays owned by test_adr519_pane_spine.py — this
// asserts only the cross-app invariant, so the two gates do not duplicate a
// claim and then disagree about it.
{
  const src = strip(studio);
  const oi = src.indexOf("{scope === 'object' && (");
  const obj = src.slice(oi, oi + 12000);
  const verbs = obj.indexOf('<VerbRow');
  const layout = obj.indexOf('>Layout<');
  t('Studio: Identity (the verb row) precedes Layout at the object scope',
    verbs > 0 && layout > 0 && verbs < layout);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
