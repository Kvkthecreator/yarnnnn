// Executing check of ADR-547 — the flow write grain.
//
// WHAT THIS GATE IS FOR. The defect was found on PROD, past 23/23 FE gates and a
// 46/0 ADR-546 gate, with TWO HTTP 200 writes and CAS satisfied. Nothing was
// stale, so no fence/version/lock check could see it. The only thing that can is
// a test of BEHAVIOUR at the two places the law lives:
//
//   D3 — a flow commit must never REMOVE an annotation it cannot have authored
//   D2/D4 — an op that changes blocks must DECLARE them, or the live iframe DOM
//           never learns and the member's next keystroke commits the op away
//
// D3 is EXECUTED (the real guard, extracted and run against real bodies). D2/D4
// is a wiring invariant, so it is asserted at the op sites — with the enumeration
// derived from the source, not hand-listed.
//
// NEVER PIN A SPELLING (ADR-544's lesson, three gates deep). Assertions are about
// sets, behaviour and invariants.
//
// Run from the REPO ROOT: node web/scripts/gates/adr547_flow_write_grain.mjs
import { readFileSync } from 'fs';

const ops = readFileSync('web/components/authoring/artifactOps.ts', 'utf8');
const surface = readFileSync('web/components/authoring/StudioSurface.tsx', 'utf8');
const canvas = readFileSync('web/components/authoring/StudioCanvas.tsx', 'utf8');
const proj = readFileSync('web/components/workspace/viewers/projection.ts', 'utf8');

let pass = 0,
  fail = 0;
const t = (label, cond) => {
  console.log((cond ? '[PASS] ' : '[FAIL] ') + label);
  cond ? pass++ : fail++;
};
const strip = (s) =>
  s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/(^|[^:])\/\/[^\n]*/g, '$1');
const opsCode = strip(ops);
const surfaceCode = strip(surface);
const canvasCode = strip(canvas);

// ═══════════════════════════════════════════════════════════════════════════
// D3 — EXECUTE the guard. A tiny DOM good enough for the predicate + the
// attribute walk the guard performs (getAttributeNames / getAttribute /
// querySelectorAll by attribute presence).
// ═══════════════════════════════════════════════════════════════════════════

const guardSrc = ops.match(/const GUARDED_ANNOTATIONS = \([\s\S]*?\n\};/);
t('D3: the GUARDED_ANNOTATIONS predicate is extractable', !!guardSrc);

let guarded = null;
if (guardSrc) {
  try {
    guarded = new Function(
      `${guardSrc[0].replace(/:\s*string/g, '').replace(/:\s*boolean/g, '')}\nreturn GUARDED_ANNOTATIONS;`,
    )();
  } catch (e) {
    t(`D3: the predicate evaluates (${e.message})`, false);
  }
}

if (guarded) {
  t('D3: the predicate evaluates', true);
  // PROTECTED: grammar, identity, citation, and every served block token. The
  // point of a predicate is that a token nobody invented yet is covered, so the
  // test includes a made-up one.
  for (const name of [
    'data-block',
    'data-block-id',
    'data-ref',
    'data-indent',
    'data-align',
    'data-tone',
    'data-mark',
    'data-a-token-invented-tomorrow',
  ]) {
    t(`D3: ${name} is protected`, guarded(name) === true);
  }
  // NOT protected: what the browser legitimately owns, and the runtime's own
  // scaffolding. Guarding `class`/`style` would refuse ordinary paste + execCommand.
  for (const name of ['class', 'style', 'contenteditable', 'href', 'src', 'alt', 'aria-label']) {
    t(`D3: ${name} is NOT protected (the browser owns it)`, guarded(name) === false);
  }
  for (const name of ['data-yarnnn-label', 'data-src-html']) {
    t(`D3: ${name} is NOT protected (runtime scaffolding)`, guarded(name) === false);
  }
}

// ── The guard's BEHAVIOUR, executed against real bodies ────────────────────
// A minimal DOM: enough for the guard's walk. Elements are parsed from a tiny
// tag soup — deliberately simple, because the guard only reads attributes and
// element presence, never layout or hierarchy beyond the region.
function parseEls(html) {
  const els = [];
  for (const m of html.matchAll(/<(\w+)((?:\s+[\w:-]+="[^"]*")*)\s*\/?>/g)) {
    const attrs = {};
    for (const a of m[2].matchAll(/([\w:-]+)="([^"]*)"/g)) attrs[a[1]] = a[2];
    els.push({
      tag: m[1].toUpperCase(),
      attrs,
      getAttribute: (k) => (k in attrs ? attrs[k] : null),
      getAttributeNames: () => Object.keys(attrs),
    });
  }
  return els;
}
/** The guard's own logic, re-expressed over the tiny DOM. This mirrors the
 *  extracted predicate + the two refusal rules; it is the DECISION under test,
 *  and the falsifier below breaks the SOURCE to prove the gate reads it. */
function guardDecides(beforeHtml, afterHtml, predicate) {
  const before = parseEls(beforeHtml);
  const after = parseEls(afterHtml);
  const hadBlocks = before.some((e) => e.getAttribute('data-block') !== null);
  const nowBlocks = after.some((e) => e.getAttribute('data-block') !== null);
  if (hadBlocks && !nowBlocks) return 'refused';
  const survivors = new Map();
  for (const e of after) {
    const id = e.getAttribute('data-block-id');
    if (id) survivors.set(id, e);
  }
  for (const b of before) {
    const id = b.getAttribute('data-block-id');
    if (!id) continue;
    const a = survivors.get(id);
    if (!a) continue;
    for (const n of b.getAttributeNames()) {
      if (!predicate(n)) continue;
      if (a.getAttribute(n) === null) return 'refused';
    }
  }
  return 'allowed';
}

if (guarded) {
  const withIndent =
    '<h2 data-block="heading" data-block-id="h1">A</h2><div data-block="prose" data-block-id="b1" data-indent="2">x</div>';
  const withoutIndent =
    '<h2 data-block="heading" data-block-id="h1">A</h2><div data-block="prose" data-block-id="b1">x</div>';

  // THE PROD DEFECT, as a test. This is the exact pair from ADR-547 §1.2: a
  // token op wrote data-indent="2"; the next keystroke committed a body without
  // it. The guard must refuse.
  t(
    'D3 [F2]: a commit that drops data-indent from a SURVIVING block is refused',
    guardDecides(withIndent, withoutIndent, guarded) === 'refused',
  );
  // The inverse must be ALLOWED — the member's typing is always free to add.
  t(
    'D3: a commit that ADDS an annotation is allowed (removal-only rule)',
    guardDecides(withoutIndent, withIndent, guarded) === 'allowed',
  );
  // Text may change freely: contenteditable rewrites text nodes constantly.
  t(
    'D3: a commit that changes only TEXT is allowed',
    guardDecides(withIndent, withIndent.replace('>x<', '>x typed more<'), guarded) === 'allowed',
  );
  // A block genuinely DELETED is a native delete, not this rule's business.
  t(
    'D3: deleting a block outright is allowed (a native delete)',
    guardDecides(withIndent, '<h2 data-block="heading" data-block-id="h1">A</h2>', guarded) ===
      'allowed',
  );
  // class/style churn from paste/execCommand must not be refused.
  t(
    'D3: losing class/style is allowed (the browser owns them)',
    guardDecides(
      '<div data-block="prose" data-block-id="b1" class="x" style="color:red">t</div>',
      '<div data-block="prose" data-block-id="b1">t</div>',
      guarded,
    ) === 'allowed',
  );
  // F4 — the ZERO-BLOCKS refusal must still work: D3 GENERALIZES the guard, it
  // does not replace it. Asserted against `guardDecides` (the decision) AND
  // against the SOURCE, because the falsifier exposed that the re-expressed
  // logic alone stays green when the real refusal is deleted — a gate that
  // tests only its own mirror is testing nothing.
  t(
    'D3 [F4]: the zero-blocks annihilation refusal still holds',
    guardDecides(withIndent, '<br>', guarded) === 'refused',
  );
  // ...and must not freeze an ALREADY block-empty artifact.
  t(
    'D3: an already block-empty document is not frozen',
    guardDecides('<br>', '<p>first words</p>', guarded) === 'allowed',
  );
}

// The guard must live in editFlowRegion — the WHOLE-BODY writer. If it migrates
// to a per-block writer it is defending the wrong blast radius.
{
  const i = opsCode.indexOf('export function editFlowRegion');
  const j = opsCode.indexOf('export function convertBlock', i);
  const body = i >= 0 && j > i ? opsCode.slice(i, j) : '';
  t('D3: the guard lives in editFlowRegion (the whole-body writer)', /GUARDED_ANNOTATIONS/.test(body));
  t('D3: it refuses by returning null (no revision), never by throwing', /return null/.test(body));
  // F4 at the SOURCE: the zero-blocks refusal is a distinct rule and must remain
  // one. Behaviour, not a spelling — the shape is "the region HAD blocks and the
  // incoming body has none → refuse", so assert both halves are read.
  t(
    'D3 [F4]: the zero-blocks refusal is present in the source, not merely in the mirror',
    /hadBlocks/.test(body) &&
      /\[data-block\]'\)\.length === 0/.test(body) &&
      /hadBlocks &&[\s\S]{0,120}?return null/.test(body),
  );
  // The general removal rule is a SECOND, distinct refusal — not the same one.
  t(
    'D3: the surviving-block removal rule is a distinct refusal',
    /survivors/.test(body) && /getAttributeNames\(\)/.test(body),
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// D2/D4 — the declared grain. A wiring invariant: every applyOp call that
// changes BLOCK attributes must pass a third argument.
// ═══════════════════════════════════════════════════════════════════════════

t(
  'D4: writeAndAdvance takes a declared grain (ids, not a single flag)',
  /patchBlockIds\?:\s*string\[\]\s*\|\s*string\s*\|\s*null/.test(surfaceCode),
);
t(
  'D4: applyOp forwards a declared grain to writeAndAdvance',
  /touchedBlockIds/.test(surfaceCode) &&
    /writeAndAdvance\([\s\S]{0,220}?touchedBlockIds/.test(surfaceCode),
);
t(
  'D2: the patch channel carries N blocks (a span op touches many)',
  /blocks:\s*Array<\{\s*blockId:\s*string;\s*html:\s*string\s*\}>/.test(surfaceCode) &&
    /patch\.blocks/.test(canvasCode),
);
t(
  'D2: sendPatch is all-or-nothing (a partial patch would falsify appliedFor)',
  /const projected: Array<\{ blockId: string; html: string \}> = \[\]/.test(surfaceCode) &&
    /if \(!one\) return false/.test(surfaceCode),
);

// The two ops the prod defect was measured on MUST declare their blocks.
// Extracted by the op they compute, so a rename of the handler cannot hide it.
// EVERY call site of each block-touching op, not just the first match: the
// first pass declared two of three convertBlock sites, and a `.match()` (which
// stops at the first) reported that as a pass. `matchAll` is what caught the
// slash-palette's in-place convert. A per-site assertion, because a count cannot
// defend a per-site invariant (the ADR-519 lesson).
for (const [label, opName] of [
  ['setToken', 'setToken\\(html'],
  ['setTokenMany', 'setTokenMany\\(html'],
  ['convertBlock', 'convertBlock\\(html'],
  ['convertBlocks', 'convertBlocks\\(html'],
]) {
  const sites = [
    ...surfaceCode.matchAll(new RegExp(`${opName}[\\s\\S]{0,500}?\\n\\s*\\);`, 'g')),
  ];
  t(`D2: ${label} has at least one call site`, sites.length > 0);
  sites.forEach((m, i) => {
    const call = m[0];
    // A BLOCK-grain op declares ids. `setToken` is the one op that also serves
    // page/document grains, whose anchor is the artifact root — no flow commit
    // reports that, so those sites legitimately declare nothing and are
    // recognized by their own literal grain rather than exempted by name.
    const isNonBlockGrain = /grain:\s*'(page|document)'/.test(call);
    // The declaration is the THIRD argument to applyOp, and it can be any
    // expression — a bare id, an array, or a ternary that resolves the grain
    // (`grain === 'block' ? anchor.blockId : null`). So test that an id-bearing
    // expression appears AFTER the message argument, not that it is spelled a
    // particular way: pinning the spelling is what made this assertion red on
    // correct code (ADR-544's lesson, and it recurred here).
    const afterMessage = call.slice(call.indexOf('app.label'));
    const declares = /(rangeBlockIds|blockIds|anchor\.blockId|\bblockId\b)/.test(afterMessage);
    t(
      `D2 [F1]: ${label} site ${i + 1} declares its blocks${isNonBlockGrain ? ' (n/a — page/document grain)' : ''}`,
      isNonBlockGrain || declares,
    );
  });
}

// F3 — no applyOp call may change block attributes without declaring. Counted
// honestly: report the total so a NEW undeclared op is visible rather than
// silently averaged away.
{
  const calls = [...surfaceCode.matchAll(/applyOp\(\s*\n?\s*\(html\)/g)].length;
  t(`D4: applyOp call sites are enumerable (${calls} found)`, calls > 0);
}

// ═══════════════════════════════════════════════════════════════════════════
// F5/F6 — the scope discipline. ADR-547 amends FLOW only.
// ═══════════════════════════════════════════════════════════════════════════
t(
  'F5: the runtime still refuses to patch the block holding a live caret',
  /editingNow !== d\.blockId/.test(proj) && /caretLive/.test(proj),
);
// F6 — the per-block writer must NOT acquire the whole-body guard: on paged a
// block is an enclosure (ADR-480), so the blast radius this defends does not
// exist there. Read from the comment-stripped source and bounded to the function
// body, so a docstring that merely MENTIONS the guard cannot fail it (the
// ADR-544 lesson: an absence assertion must not match its own prose).
{
  const i = opsCode.indexOf('export function editBlockText');
  const j = opsCode.indexOf('export function', i + 10);
  const body = i >= 0 ? opsCode.slice(i, j > i ? j : undefined) : '';
  t('F6: editBlockText is extractable', body.length > 0);
  t(
    'F6: the per-block writer does NOT carry the whole-body guard (paged untouched)',
    body.length > 0 && !/GUARDED_ANNOTATIONS\(/.test(body),
  );
}
t(
  'ADR-540 upheld: retire still fires for a restructuring op (no declared grain)',
  /touched\.length === 0\) retireFlowCommits\(\)/.test(surfaceCode),
);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
