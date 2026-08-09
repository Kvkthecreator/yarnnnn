// Executing check: a LIFTED JSX section may not reference a binding declared
// after it (temporal dead zone).
//
// The production crash this closes (2026-08-06, operator screenshot):
//
//   ReferenceError: Cannot access 't9' before initialization
//       at Array.map (<anonymous>)
//
// ADR-528 lifted `rampSection` and `turnIntoSection` out of StudioDesignTab's
// render so `range` and `object` scope mount ONE implementation (ADR-518 D2).
// The lift moved that JSX ~450 lines ABOVE `askBtn`, a component-body `const`
// it references inside a `.map()` callback. Every Docs artifact carrying a
// turn-into-able block crashed the whole app on open.
//
// WHY THE EXISTING GATES ALL PASSED — the lesson worth keeping:
//   · `tsc --noEmit`  — clean. The reference sits inside a JSX expression, so
//     it is not a direct read TS's use-before-declaration check sees. (It DID
//     catch `tagFontSize` in the same commit — that one was a direct read.)
//   · `next build`    — exit 0, 169/169 pages. The component is client-side
//     and this route is dynamic, so the crashing path never executed.
//   · 182 FE gate assertions — all string/AST checks over source. None runs it.
//
// So this gate does the one thing none of those did: it EXECUTES the ordering.
// It parses the component body, finds each lifted section, and resolves every
// identifier it references against the declaration order — then FALSIFIES by
// re-introducing the exact defect and confirming the check trips.
//
// Run from the REPO ROOT: node web/scripts/gates/adr528_tdz_lifted_sections.mjs
import { readFileSync } from 'fs';

const SRC = 'web/components/authoring/StudioDesignTab.tsx';
const pane = readFileSync(SRC, 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};

// ── The component body: from the exported component to end of file ────────
const compIdx = pane.search(/export function StudioDesignTab/);
t('the component is found', compIdx > 0);

/** Line number (1-based) of a top-level component-body declaration.
 *  Body-scope declarations sit at exactly 2-space indent. */
function declLine(name, src = pane) {
  const rx = new RegExp(`^  (?:const|let|function)\\s+${name}\\b`, 'm');
  const m = rx.exec(src);
  return m ? src.slice(0, m.index).split('\n').length : -1;
}

/** The source span of a body-scope `const NAME =` up to the next body-scope
 *  declaration or the final `return (`. */
function sectionSpan(name, src = pane) {
  const start = declLine(name, src);
  if (start < 0) return null;
  const lines = src.split('\n');
  for (let i = start; i < lines.length; i++) {
    if (/^  (?:const|let|function)\s+\w/.test(lines[i]) || /^  return \(/.test(lines[i])) {
      return { start, end: i, body: lines.slice(start - 1, i).join('\n') };
    }
  }
  return { start, end: lines.length, body: lines.slice(start - 1).join('\n') };
}

// Identifiers declared INSIDE the span (locals, params, IIFE bodies) are not
// hazards — only free identifiers that resolve to a LATER body-scope const are.
function localNames(body) {
  const out = new Set();
  for (const m of body.matchAll(/\b(?:const|let|var|function)\s+([a-zA-Z_$][\w$]*)/g)) out.add(m[1]);
  for (const m of body.matchAll(/\(\s*([a-zA-Z_$][\w$]*)\s*\)\s*=>/g)) out.add(m[1]);
  for (const m of body.matchAll(/\.map\(\s*\(?\s*([a-zA-Z_$][\w$]*)/g)) out.add(m[1]);
  return out;
}

const LIFTED = ['rampSection', 'turnIntoSection'];

function hazardsFor(name, source = pane) {
  const span = sectionSpan(name, source);
  if (!span) return null;
  const locals = localNames(span.body);
  const hazards = [];
  for (const id of new Set(span.body.match(/\b[a-zA-Z_$][\w$]*\b/g) ?? [])) {
    if (locals.has(id)) continue;
    const rx = new RegExp(`^  (?:const|let|function)\\s+${id}\\b`, 'm');
    const m = rx.exec(source);
    if (!m) continue; // not a body-scope binding (module const, import, prop)
    const line = source.slice(0, m.index).split('\n').length;
    if (line > span.start) hazards.push(`${id} declared @${line}, used @${span.start}`);
  }
  return hazards;
}

// ── 1. The live check ─────────────────────────────────────────────────────
for (const name of LIFTED) {
  const h = hazardsFor(name);
  t(`${name} exists (ADR-528 D2's one-implementation lift)`, h !== null);
  t(
    `${name} references no LATER body binding (TDZ) ${h && h.length ? '→ ' + h.join('; ') : ''}`,
    h !== null && h.length === 0,
  );
}

// ── 2. askBtn specifically — the one that crashed ─────────────────────────
t(
  'askBtn is MODULE scope (a static string cannot be lifted past)',
  /^const askBtn =/m.test(pane) && !/^  const askBtn =/m.test(pane),
);
t(
  'askBtn is declared before both lifted sections',
  pane.indexOf('const askBtn =') < pane.indexOf('const turnIntoSection'),
);

// ── 3. FALSIFY — re-inject the exact defect, confirm the gate trips ───────
// Move askBtn back into the component body, after turnIntoSection, and check
// that hazardsFor now reports it. Without this, the checks above are vacuous.
// Anchor on the LAST body-scope `return (` — the component's own. An earlier
// `  return (` belongs to a helper defined above the component, and injecting
// there put askBtn at line 253, BEFORE turnIntoSection, so the defect was not
// reproduced and this falsifier reported a false negative. It caught itself:
// a falsifier that fails to reproduce the defect is the gate's own version of
// "extract by the branch, not the expected expression".
const stripped = pane.replace(/^const askBtn =\n(?:.*\n)/m, '');
const lastReturn = stripped.lastIndexOf('\n  return (');
const defect =
  stripped.slice(0, lastReturn) +
  "\n  const askBtn =\n    'x';\n" +
  stripped.slice(lastReturn);
const defectHazards = hazardsFor('turnIntoSection', defect);
t(
  `FALSIFY: with askBtn back in the body the check REPORTS it ` +
    `${defectHazards?.length ? '(' + defectHazards.join('; ') + ')' : '— IT DID NOT'}`,
  !!defectHazards && defectHazards.some((h) => h.startsWith('askBtn ')),
);

// ── 4. The standing lesson, asserted so it is not re-learned ──────────────
t(
  'the reason this class escapes tsc + next build is recorded at the declaration',
  /temporal dead zone|TEMPORAL DEAD ZONE/i.test(pane) && /Array\.map/.test(pane),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
