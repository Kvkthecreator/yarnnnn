/** ADR-547 → ADR-560 — the flow write grain, made structural.
 *
 * ADR-547's law: a commit may only report what its writer originated; a
 * parent-side op must reach the live document; a commit never removes an
 * annotation it cannot have authored. It was enforced by DISCIPLINE (every op
 * declares its blocks) plus a refusal guard, because two writers shared one
 * document across an async wall.
 *
 * ADR-560 collapsed the writers to one: the model. This gate holds the law's
 * three claims in their new, structural form:
 *   1. ONE writer — the whole-body iframe commit lane and editFlowRegion are
 *      gone; the model's serialization is the only flow commit.
 *   2. Ops reach the document — applyOp flushes the model before computing,
 *      and the editor re-parses the op's result synchronously (no stale
 *      snapshot can revert it).
 *   3. Nothing unauthored is removed — the schema PRESERVES what it does not
 *      understand (executed by adr560_flow_roundtrip.mjs over real substrate;
 *      asserted here as the guard's successor).
 * Paged is untouched (ADR-480's per-medium axiom): the per-block writer keeps
 * its grain and never carried the whole-body guard.
 *
 * Run from the REPO ROOT: node --import ./web/scripts/gates/_ts_register.mjs \
 *   web/scripts/gates/adr547_flow_write_grain.mjs
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
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const ops = strip(readFileSync('web/components/authoring/artifactOps.ts', 'utf8'));
const surface = strip(readFileSync('web/components/authoring/StudioSurface.tsx', 'utf8'));
const editor = strip(readFileSync('web/components/authoring/FlowEditor.tsx', 'utf8'));
const schema = strip(readFileSync('web/lib/authoring/flow/schema.ts', 'utf8'));
const roundtrip = strip(readFileSync('web/lib/authoring/flow/roundtrip.ts', 'utf8'));

console.log('=== 1. ONE writer (D1) ===');
t('editFlowRegion is deleted from the op layer', !/function editFlowRegion\(/.test(ops));
t(
  'the surface commits flow through the region splice, not a legacy compute',
  /replaceRegionInner\(liveHtml, newInner\)/.test(surface),
);
t(
  'a byte-identical region never writes (no-op, no revision)',
  /if \(cur == null \|\| cur === newInner\) return null;/.test(surface),
);
t(
  "the editor's commit serializes the model — the only flow writer",
  /const inner = serializeRegion\(schema, view\.state\.doc\);/.test(editor),
);

console.log('=== 2. Ops reach the document (D2, structural) ===');
t(
  'applyOp flushes the model before computing (the ONE chokepoint that replaced per-op declarations)',
  /if \(resolvedMode === 'flow'\) flowRef\.current\?\.flush\(\);/.test(surface),
);
t(
  "an external write re-enters the model synchronously (the op's result is re-parsed)",
  /const incoming = readRegionInner\(file\.content\);/.test(editor) &&
    /withMintedIds\(parseRegion\(schema, incoming\)\)/.test(editor),
);
t(
  'the caret survives the re-parse by block identity',
  /findBlockById\(doc, keepId\)/.test(editor),
);

console.log('=== 3. Nothing unauthored is removed (D3, structural) ===');
t(
  'the schema carries unknown substrate opaquely (the preservation island)',
  /island: \{/.test(schema) && /captureInertHtml\(el\)/.test(schema),
);
t(
  'every data-* annotation is modeled (the GUARDED predicate became the attr law)',
  /if \(name\.startsWith\('data-'\)\) extra\[name\] = el\.getAttribute\(name\)/.test(schema),
);
t(
  'the ownership rule survives at the serialize seam (interiors stay unannotated)',
  /function normalizeOwnership\(/.test(roundtrip),
);

console.log('=== 4. Paged untouched (ADR-480 per-medium axiom) ===');
{
  const i = ops.indexOf('export function editBlockText(');
  const j = ops.indexOf('export function', i + 10);
  const body = i >= 0 ? ops.slice(i, j > i ? j : undefined) : '';
  t('the paged per-block writer is extractable', body.length > 0);
  t(
    'the per-block writer never carried the whole-body guard',
    body.length > 0 && !/GUARDED_ANNOTATIONS\(/.test(body),
  );
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
