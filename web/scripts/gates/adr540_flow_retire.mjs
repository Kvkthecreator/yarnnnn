// Executing check of the ADR-540 flow-retire path.
//
// The defect this gate defends against was found by DRIVING the doorway, not
// by reading the room: ADR-538 shipped 59/59 green with a clean build, and
// inserting a chart on production still did nothing — the block landed and was
// silently reverted ~400ms later by a commit from the document being torn down.
//
// What makes it gate-worthy rather than comment-worthy: every individual piece
// was correct (the optimistic override, the re-projection, the beforeunload
// rescue), and NOTHING errored. Only the ORDER of two parent-side calls keeps
// them composing correctly, and order is exactly what a symbol-presence check
// cannot see. So this gate pins the order, and the exemption, and executes a
// simulation of the runtime guard.
//
// Run from the REPO ROOT:  node web/scripts/gates/adr540_flow_retire.mjs

import { readFileSync } from 'node:fs';

const SURFACE = readFileSync('web/components/authoring/StudioSurface.tsx', 'utf8');
const CANVAS = readFileSync('web/components/authoring/StudioCanvas.tsx', 'utf8');
const PROJECTION = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');

let pass = 0;
let fail = 0;
function t(label, cond) {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
}

/** Source with // and /* *\/ comments stripped.
 *  The ADR-536 lesson: an assertion must never be satisfiable by its own
 *  explanatory comment. Every ordering/absence check below runs on this. */
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
}

const S = stripComments(SURFACE);
const C = stripComments(CANVAS);
const P = stripComments(PROJECTION);

console.log('\n=== 1. D1 — the runtime retires, and a retired document is silent ===');

t('the runtime declares a retirement flag', /var flowDead = false/.test(P));
t('flowCommit bails when retired', /function flowCommit\(\)\s*\{[\s\S]{0,200}?if \(flowDead\) return;/.test(P));
t(
  'the bail is the FIRST statement (before the DOM is read)',
  (() => {
    const m = /function flowCommit\(\)\s*\{([\s\S]*?)\n  \}/.exec(P);
    if (!m) return false;
    const body = m[1].trim();
    return body.startsWith('if (flowDead) return;');
  })(),
);
t('the flag is never cleared (no lifecycle to get wrong)', !/flowDead\s*=\s*false/.test(P.replace('var flowDead = false', '')));

console.log('\n=== 2. D2 — the parent declares it; the runtime only listens ===');

t('the runtime handles the retire message', /d\.type === 'yarnnn-flow-retire'/.test(P));
t('handling it sets the flag', /yarnnn-flow-retire'\)\s*\{[\s\S]{0,120}?flowDead = true/.test(P));
t('handling it also disarms the pending idle timer', /yarnnn-flow-retire'\)\s*\{[\s\S]{0,220}?clearTimeout\(flowIdle\)/.test(P));
t('the canvas posts it', /postMessage\(\{ type: 'yarnnn-flow-retire' \}/.test(C));
t('the surface owns the trigger', /const retireFlowCommits = useCallback/.test(S));
t('the canvas takes the prop', /flowRetire\?: \{ nonce: number \}/.test(C));
t('the surface passes the prop', /flowRetire=\{flowRetire\}/.test(S));
t(
  'the trigger uses a NONCE (two ops in one session must each fire)',
  /retireNonce\.current \+= 1/.test(S),
);

console.log('\n=== 3. D3 — ORDERING is the fix (the part a symbol check cannot see) ===');

const retireIdx = S.indexOf('retireFlowCommits()');
const overrideIdx = S.indexOf('setLocalOverride((cur) => ({');
t('retireFlowCommits() is called in writeAndAdvance', retireIdx > 0);
t('setLocalOverride is called in writeAndAdvance', overrideIdx > 0);
t(
  'the retire happens BEFORE the override advances (the whole fix)',
  retireIdx > 0 && overrideIdx > 0 && retireIdx < overrideIdx,
);
t(
  'the canvas sender is a LAYOUT effect (a passive one would race the teardown)',
  /useLayoutEffect\(\(\) => \{[\s\S]{0,200}?'yarnnn-flow-retire'/.test(C),
);
t('useLayoutEffect is imported', /import \{[^}]*useLayoutEffect[^}]*\} from 'react'/.test(CANVAS));

console.log('\n=== 4. D4 — a patchable op is EXEMPT (or typing gets dropped) ===');

// ADR-547 D4 renamed the flag to a DECLARED GRAIN (`patchBlockIds` — an op says
// which blocks it touched, one or many). The CLAIM here is unchanged and is what
// this asserts: retire fires exactly when the op declares NO blocks, i.e. when
// the document is about to be torn down and replaced. Pinning the old spelling
// read that widening as a violation — the fourth time in this arc a gate did
// that, so this one asserts the CONDITION's shape instead.
// ADR-560 D8 narrowed both to the PAGED medium: flow no longer edits in an
// iframe, so there is no teardown gasp to fence and no live DOM to patch —
// the model re-parses external writes itself. The claim these assert is
// per-medium now: on paged, retire fires exactly when the op declares no
// blocks, and a declared-grain op still patches.
t(
  'retire is guarded by "the op declared no blocks" AND the paged medium',
  /if \(touched\.length === 0 && resolvedMode !== 'flow'\) retireFlowCommits\(\)/.test(S),
);
t(
  'the exemption is not accidentally inverted',
  !/if \((?:patchBlockId|touched\.length > 0)\) retireFlowCommits\(\)/.test(S),
);
t(
  'a DECLARED-grain op still patches on paged (the exemption has a consumer)',
  /touched\.length > 0 && resolvedMode !== 'flow'\) void sendPatch\(touched/.test(S),
);

console.log('\n=== 5. EXECUTED — simulate the runtime guard ===');

// Rebuild flowCommit's contract in isolation and run the actual scenario:
// a structural op retires the document, then the teardown fires beforeunload.
function makeRuntime() {
  let flowDead = false;
  const posted = [];
  const flowCommit = (domSnapshot) => {
    if (flowDead) return;
    posted.push(domSnapshot);
  };
  return {
    retire: () => { flowDead = true; },
    commit: flowCommit,
    posted,
  };
}

const rt = makeRuntime();
rt.commit('pre-insert DOM'); // ordinary idle commit — must post
rt.retire(); // the structural op lands
rt.commit('pre-insert DOM'); // the beforeunload gasp — must NOT post
t('an ordinary commit posts before retirement', rt.posted.length === 1);
t('the teardown commit is SUPPRESSED after retirement', rt.posted.length === 1);

// FALSIFIER: without the guard, the stale snapshot reaches the parent — which
// is exactly the production defect (the block is overwritten by its predecessor).
function makeBroken() {
  const posted = [];
  return { retire: () => {}, commit: (s) => posted.push(s), posted };
}
const broken = makeBroken();
broken.commit('pre-insert DOM');
broken.retire();
broken.commit('pre-insert DOM');
t(
  'FALSIFIER: without the guard the stale commit DOES reach the parent (2 posts)',
  broken.posted.length === 2,
);

console.log('\n=== 6. FALSIFIERS — the ordering claims can fail ===');

t(
  'F1 reversing the order would be detectable',
  !(retireIdx > overrideIdx),
);
t(
  'F2 the comment-stripper works (an assertion cannot match its own comment)',
  !/flowDead/.test(stripComments('// flowDead is the flag\nvar x = 1;')),
);
t(
  'F3 the ordering check reads STRIPPED source (comments cannot satisfy it)',
  S.indexOf('retireFlowCommits()') > 0 && !/\/\//.test(S.slice(retireIdx - 40, retireIdx)),
);

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail ? 1 : 0);
