/** ADR-540 → ADR-560 D8 — a retired document does not commit, made STRUCTURAL.
 *
 * ADR-540's defect: the iframe's teardown `beforeunload` fired one last
 * whole-body flowCommit whose DOM predated a structural op, and the parent
 * wrote that stale region back over the fresh block. The fence (`flowDead` +
 * the `yarnnn-flow-retire` channel) stopped one instance of a class the
 * architecture kept producing.
 *
 * ADR-560 deleted the class's host: flow no longer edits in an iframe, so
 * there is no teardown snapshot to fence. This gate holds BOTH halves of that
 * claim — the deletion is complete (no fence, no commit lane, no dual path
 * left behind), AND the replacement mechanism exists (the model is the one
 * writer; its teardown commit reports MODEL state, which cannot predate an
 * op because ops flush the model first). An absence is only asserted beside
 * the presence that replaced it.
 *
 * Run from the REPO ROOT: node --import ./web/scripts/gates/_ts_register.mjs \
 *   web/scripts/gates/adr540_flow_retire.mjs
 */
import { readFileSync } from 'node:fs';

let pass = 0;
let fail = 0;
const t = (label, cond) => {
  if (cond) {
    pass++;
    console.log(`[PASS] ${label}`);
  } else {
    fail++;
    console.log(`[FAIL] ${label}`);
  }
};
// Comments can legally NAME the deleted machinery (tombstones); code may not
// reach it. Strip comments before asserting absence — the lesson of
// [[gate_assertion_matches_its_own_comment]].
const strip = (s) =>
  s
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
    .replace(/^\s*\/\/:.*$/gm, '');

const proj = strip(readFileSync('web/components/workspace/viewers/projection.ts', 'utf8'));
const canvas = strip(readFileSync('web/components/authoring/StudioCanvas.tsx', 'utf8'));
const surface = strip(readFileSync('web/components/authoring/StudioSurface.tsx', 'utf8'));
const editor = strip(readFileSync('web/components/authoring/FlowEditor.tsx', 'utf8'));

console.log('=== 1. The deletion is complete (D8) ===');
t('the runtime has no flowCommit', !/function flowCommit\(/.test(proj));
t('the runtime has no enterFlow', !/function enterFlow\(/.test(proj));
t('the runtime has no flowDead fence', !/flowDead/.test(proj));
t('the retire verb is gone from the runtime', !/yarnnn-flow-retire/.test(proj));
t('the whole-body commit verb is gone from the runtime', !/yarnnn-flow-edit/.test(proj));
t('the flow caret restore verb is gone from the runtime', !/yarnnn-flow-caret/.test(proj));
t('the canvas no longer speaks the retire channel', !/flowRetire|yarnnn-flow-retire/.test(canvas));
t('the canvas no longer receives whole-body commits', !/yarnnn-flow-edit|onFlowEdit/.test(canvas));
t('the surface no longer retires documents', !/retireFlowCommits|flowRetire/.test(surface));

console.log('=== 2. The replacement exists (the absence is not a hole) ===');
t(
  'the model editor exists and the surface mounts it on flow',
  /resolvedMode === 'flow' && vocabulary \?/.test(surface) && /<FlowEditor/.test(surface),
);
t(
  "the teardown commit reports MODEL state (commitNow serializes the doc), never a DOM snapshot",
  /const inner = serializeRegion\(schema, view\.state\.doc\);/.test(editor),
);
t(
  'the unmount cleanup commits the model (a close cannot lose typing)',
  /commitNow\(\); \/\/ the teardown commit is the MODEL's own state/.test(
    readFileSync('web/components/authoring/FlowEditor.tsx', 'utf8'),
  ),
);
t(
  "an op flushes the model FIRST, so a commit can never predate an op (the defect's shape is unreachable)",
  /if \(resolvedMode === 'flow'\) flowRef\.current\?\.flush\(\);/.test(surface),
);
t(
  'the commit ledger suppresses echoes (own writes never re-parse the model)',
  /if \(incoming === knownInnerRef\.current\) return;/.test(editor),
);

console.log('=== 3. Paged is untouched ===');
t('the paged per-block commit lane survives (yarnnn-edit)', /yarnnn-edit'/.test(proj));
t('the paged patch channel survives (yarnnn-patch)', /yarnnn-patch/.test(proj));
t(
  'the patch is still sent for declared-grain ops on paged only',
  /touched\.length > 0 && resolvedMode !== 'flow'\) void sendPatch\(touched/.test(surface),
);

console.log(`\n${pass}/${pass + fail} passed`);
process.exit(fail === 0 ? 0 : 1);
